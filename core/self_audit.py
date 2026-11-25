# -*- coding: utf-8 -*-
"""Auto-auditoria final obrigatoria (cenas x imagens x audio x video x Short x Thumbs)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image

from config import (
    FFPROBE_EXE, MAX_IMAGE_SECONDS, NARRATION_MAX_CONSECUTIVE, NARRATION_MIN_RATIO,
    SHORT_HEIGHT, SHORT_WIDTH, THUMB_HEIGHT, THUMB_WIDTH, VIDEO_HEIGHT, VIDEO_WIDTH,
)
from core.audio_fx import detect_pauses_in_wav, run_earshot_critique
from core.delivery_audit import audit_delivery, clip_has_video
from core.legacy_auditor import audit_image_with_vision
from core.media_studio import detect_split_collage
from core.scene_auditor import audit_voice_consistency
from core.script_engine import count_total_words, validate_script_schema
from core.sync_audit import audit_narration_sync


def _probe_media(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size < 1000:
        return {"exists": False}
    try:
        out = subprocess.check_output(
            [FFPROBE_EXE, "-v", "error", "-show_entries",
             "stream=codec_type,codec_name,width,height,duration",
             "-show_entries", "format=duration",
             "-of", "json", str(path)],
            text=True,
        )
        info = json.loads(out)
        streams = info.get("streams", [])
        v = next((s for s in streams if s.get("codec_type") == "video"), {})
        a = next((s for s in streams if s.get("codec_type") == "audio"), {})
        fdur = float((info.get("format") or {}).get("duration") or 0.0)
        return {
            "exists": True,
            "size_bytes": path.stat().st_size,
            "duration": round(fdur, 3),
            "width": v.get("width"),
            "height": v.get("height"),
            "has_audio": bool(a),
            "av_diff_s": round(abs(float(v.get("duration") or fdur) - float(a.get("duration") or fdur)), 3) if (v and a) else 0.0,
        }
    except Exception as exc:
        return {"exists": True, "error": str(exc)[:140]}


def narration_issues(scenes: list[dict[str, Any]]) -> list[str]:
    """Regra 29: a historia e contada pelo narrador; personagens so comentam.

    Devolve a lista de problemas (vazia = aprovado). Funcao pura para testar.
    """
    if not scenes:
        return []

    def _spk(sc: dict[str, Any]) -> str:
        return str(sc.get("speaker") or "narrador").strip().lower()

    out: list[str] = []
    narr = sum(1 for s in scenes if _spk(s) == "narrador")
    ratio = narr / len(scenes)
    if ratio < NARRATION_MIN_RATIO:
        out.append(
            f"narracao: apenas {narr}/{len(scenes)} cenas narradas "
            f"({ratio:.0%} < {NARRATION_MIN_RATIO:.0%}) — historia precisa de narrador"
        )
    run = 0
    for s in scenes:
        run = run + 1 if _spk(s) != "narrador" else 0
        if run > NARRATION_MAX_CONSECUTIVE:
            out.append(
                f"narracao: {run} cenas seguidas so de personagens "
                f"(max {NARRATION_MAX_CONSECUTIVE}) — o narrador desaparece da historia"
            )
            break
    return out


def run_final_audit(
    proj_dir: Path,
    script_data: dict[str, Any],
    tts_timings: list[dict[str, Any]],
    visual_clips: list[dict[str, Any]],
    images_dir: Path,
    out_16_9: Path,
    out_short: Path | None,
    thumbs_dir: Path,
    vision_check: bool = False,
    min_veo_videos: int = 0,
    require_media_manifest: bool = False,
) -> dict[str, Any]:
    """Executa auditoria completa apos a montagem e salva final_audit_report.json."""
    issues: list[str] = []

    # 1. Roteiro
    script_errs = validate_script_schema(script_data)
    issues.extend(f"script: {e}" for e in script_errs)

    # 2. Audio / QA / Prosodia
    audio_failures = []
    for t in tts_timings:
        wp = Path(t.get("wav_path") or "")
        if not wp.exists() or float(t.get("duration") or 0.0) <= 0.2:
            audio_failures.append(f"{t.get('scene_id')}: wav ausente ou vazio")
        elif t.get("qa") and not t["qa"].get("ok", True):
            audio_failures.append(f"{t.get('scene_id')}: Whisper QA reprovado ({t['qa'].get('reason')})")
    issues.extend(f"audio: {e}" for e in audio_failures)
    issues.extend(f"voice: {e}" for e in audit_voice_consistency(tts_timings))

    # 3. Cenas x Imagens (ritmo <= 5s, sem colagem, resolucao, coerencia visual opcional)
    image_failures = []
    vision_samples = []
    for c in visual_clips:
        if float(c.get("duration") or 0.0) > MAX_IMAGE_SECONDS + 0.05:
            image_failures.append(f"{c['clip_id']}: duracao {c['duration']}s > {MAX_IMAGE_SECONDS}s")
        im_p = images_dir / f"{c['clip_id']}.jpg"
        if not im_p.exists():
            # Cena com vídeo Veo é renderizada pelo MP4, não por um JPG.
            # Com reuse_clips o JPG auxiliar nem chega a ser gerado — não é defeito.
            if clip_has_video(c, images_dir):
                continue
            image_failures.append(f"{c['clip_id']}: imagem ausente")
            continue
        with Image.open(im_p) as im:
            if im.size != (VIDEO_WIDTH, VIDEO_HEIGHT):
                image_failures.append(f"{c['clip_id']}: resolucao {im.size} != {VIDEO_WIDTH}x{VIDEO_HEIGHT}")
        cols = detect_split_collage(im_p)
        if cols > 1:
            image_failures.append(f"{c['clip_id']}: colagem detectada ({cols} paineis)")
        elif vision_check and c["clip_id"].endswith("_p1"):
            vis = audit_image_with_vision(im_p, c.get("location", ""), c.get("text", ""))
            vision_samples.append({"clip_id": c["clip_id"], **vis})
            if vis.get("checked") and not vis.get("ok"):
                image_failures.append(f"{c['clip_id']}: reprovado no Vision ({vis.get('reason')})")
    issues.extend(f"visual: {e}" for e in image_failures)

    # 3b. PORTA DE ENTREGA OBRIGATORIA (Regras 9 e 13) — compara os FRAMES RENDERIZADOS
    #     com as imagens/videos designados de cada cena. Nao depende de Vision API.
    #     So roda em EPISODIOS REAIS (projeto sob ROOT/projects); testes sinteticos
    #     em pastas temporarias nao sao entregas e nao passam por aqui.
    projects_root = Path(__file__).resolve().parent.parent / "projects"
    in_projects = str(proj_dir.resolve()).startswith(str(projects_root.resolve()))
    delivery_rep: dict[str, Any] = {"approved": True, "issues": [], "frames_checked": 0}
    if in_projects and out_16_9.exists() and out_16_9.stat().st_size > 1000:
        delivery_rep = audit_delivery(proj_dir, out_16_9, visual_clips, images_dir)
        issues.extend(f"delivery: {e}" for e in delivery_rep.get("issues", []))

    # 3c. NARRACAO DOMINANTE (Regra 29): a historia e contada pelo narrador;
    #     Frida e Luna entram de vez em quando. Dialogo demais deixa a historia
    #     "sem pe nem cabeca" (feedback direto do usuario em 2026-11-24).
    if in_projects and script_data.get("scenes"):
        issues.extend(narration_issues(script_data["scenes"]))

    # 3d. SINCRONIA NARRACAO x VISUAL (midia reutilizada): o pipeline que gera do
    #     zero ja tem o scene_auditor (Vision) para casar cena x imagem. Mas no
    #     caminho de REUTILIZACAO essa checagem nao roda — e foi assim que saiu
    #     narracao de gaivota em cima de video de cachorro. Este passo exige um
    #     manifesto de midia (media_assignment.json) e audita cobertura de
    #     personagem e alinhamento de ancora, sem depender de Vision.
    if in_projects and script_data.get("scenes"):
        manifest = proj_dir / "artifacts" / "media_assignment.json"
        if require_media_manifest or manifest.exists():
            issues.extend(f"sync: {e}" for e in audit_narration_sync(proj_dir, script_data))

    # 4. Video 16:9 e Short 9:16
    v16 = _probe_media(out_16_9)
    if not v16.get("exists") or v16.get("width") != VIDEO_WIDTH or v16.get("height") != VIDEO_HEIGHT or not v16.get("has_audio"):
        issues.append(f"video_16x9 invalido: {v16}")
    elif float(v16.get("av_diff_s") or 0.0) > 0.8:
        issues.append(f"video_16x9 dessincronizado (diff={v16['av_diff_s']}s)")

    v9 = None
    if out_short is not None:
        v9 = _probe_media(out_short)
        if not v9.get("exists") or v9.get("width") != SHORT_WIDTH or v9.get("height") != SHORT_HEIGHT or not v9.get("has_audio"):
            issues.append(f"short_9x16 invalido: {v9}")

    # 5. Earshot Audio Critique & Pauses
    earshot_rep = run_earshot_critique(out_16_9, fast=True) if v16.get("exists") else {"ran": False}
    nar_wav = proj_dir / "work" / "narration_master.wav"
    pauses = detect_pauses_in_wav(nar_wav) if nar_wav.exists() else []
    if earshot_rep.get("ran"):
        metrics = earshot_rep.get("metrics") or {}
        if isinstance(metrics, dict):
            gap = metrics.get("max_gap_s")
            if isinstance(gap, (int, float)) and gap > 2.5:
                issues.append(f"earshot: silencio excessivo no meio do video ({gap:.2f}s > 2.5s)")
            first_s = metrics.get("first_sound_s")
            if isinstance(first_s, (int, float)) and first_s > 1.2:
                issues.append(f"earshot: inicio mudo muito longo ({first_s:.2f}s > 1.2s)")

    # 6. Thumbnails 1280x720
    thumb_files = sorted(thumbs_dir.glob("*.jpg")) if thumbs_dir.exists() else []
    for tp in thumb_files:
        with Image.open(tp) as tim:
            if tim.size != (THUMB_WIDTH, THUMB_HEIGHT):
                issues.append(f"thumb {tp.name}: tamanho {tim.size} != {THUMB_WIDTH}x{THUMB_HEIGHT}")

    videos_dir = images_dir.parent / "videos"
    veo_count = len(list(videos_dir.glob("*.mp4"))) if videos_dir.exists() else 0
    if min_veo_videos > 0 and veo_count < int(min_veo_videos):
        issues.append(f"veo: apenas {veo_count}/{int(min_veo_videos)} videos Veo 3.1 Lite presentes em assets/videos")

    report = {
        "approved": len(issues) == 0,
        "issues_count": len(issues),
        "issues": issues,
        "metrics": {
            "words": count_total_words(script_data),
            "scenes": len(script_data.get("scenes", [])),
            "visual_clips": len(visual_clips),
            "veo_videos": veo_count,
            "thumbs": len(thumb_files),
            "detected_pauses": len(pauses),
        },
        "video_16x9": v16,
        "short_9x16": v9,
        "earshot_critique": earshot_rep,
        "vision_samples": vision_samples,
        "delivery_audit": delivery_rep,
    }
    report_path = proj_dir / "artifacts" / "final_audit_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
