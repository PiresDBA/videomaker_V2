# -*- coding: utf-8 -*-
"""Motor Unico e Autocontido do Videomaker v2 (Novo Episodio, Legados 30+, Dual-Avatar & Auto-Auditoria)."""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from config import PROJECTS_DIR
from core.avatar_studio import build_luna_avatar_pack
from core.legacy_auditor import batch_scan_legacy_root, import_and_upgrade_legacy
from core.media_studio import (
    generate_images_for_plan,
    generate_prompts_for_script,
    generate_thumbnail_variants,
)
from core.pacing_planner import build_pacing_plan
from core.script_engine import generate_script, normalize_script_records, validate_script_schema
from core.self_audit import run_final_audit
from core.video_assembler import assemble_video, export_short_9_16
from core.voice_studio import synthesize_all_scenes


def slugify(text: str, max_len: int = 44) -> str:
    norm = unicodedata.normalize("NFKD", (text or "projeto").lower().strip())
    ascii_txt = "".join(c for c in norm if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_txt).strip("-")
    return slug[:max_len].strip("-") or "projeto"


def run_pipeline(args: argparse.Namespace) -> int:
    if args.batch_scan:
        rows = batch_scan_legacy_root(Path(args.batch_scan))
        out_rep = PROJECTS_DIR.parent / "legacy_batch_audit.json"
        out_rep.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Batch scan concluido: {len(rows)} projetos -> {out_rep}")
        for r in rows:
            print(f"  - {r['project']:48s} | palavras={r['words']:4d} | imgs_ok={r['images_usable']:2d} | colagem={r['images_collage']:2d} | acoes={len(r['recommended_actions'])}")
        return 0

    if args.build_avatar:
        created = build_luna_avatar_pack()
        print("Avatar Luna gerado/atualizado:", {k: str(v) for k, v in created.items()})
        if args.stage == "avatar-only":
            return 0

    if args.legacy_dir:
        leg = Path(args.legacy_dir)
        slug = args.slug or slugify(leg.name)
    else:
        slug = args.slug or slugify(args.prompt or Path(args.script_file).stem)

    proj_dir = PROJECTS_DIR / slug
    artifacts_dir = proj_dir / "artifacts"
    images_dir = proj_dir / "assets" / "images"
    audio_dir = proj_dir / "assets" / "audio"
    work_dir = proj_dir / "work"
    output_dir = proj_dir / "output"
    thumbs_dir = output_dir / "thumbs"
    for d in (artifacts_dir, images_dir, audio_dir, work_dir, output_dir, thumbs_dir):
        d.mkdir(parents=True, exist_ok=True)

    script_path = artifacts_dir / "script_v2.json"
    prompts_path = artifacts_dir / "image_prompts_v2.json"
    timings_path = artifacts_dir / "tts_timings_v2.json"
    pacing_path = artifacts_dir / "pacing_plan_v2.json"
    meta_path = artifacts_dir / "youtube_metadata_v2.json"

    # 1. ROTEIRO / IMPORTACAO DE LEGADO
    if args.legacy_dir and (not script_path.exists() or args.force):
        imp = import_and_upgrade_legacy(Path(args.legacy_dir), proj_dir, reuse_clean_images=True, vision_filter=args.vision_audit)
        print(f"Legado importado: {imp['images_reused']} imagens limpas reaproveitadas | acoes={imp['audit']['recommended_actions']}")
        script_data = normalize_script_records(json.loads(script_path.read_text(encoding="utf-8")))
    elif args.script_file:
        raw = json.loads(Path(args.script_file).read_text(encoding="utf-8"))
        script_data = normalize_script_records(raw)
        errs = validate_script_schema(script_data)
        if errs:
            raise ValueError("Roteiro invalido:\n - " + "\n - ".join(errs))
        script_path.write_text(json.dumps(script_data, ensure_ascii=False, indent=2), encoding="utf-8")
    elif script_path.exists() and not args.force:
        script_data = normalize_script_records(json.loads(script_path.read_text(encoding="utf-8")))
    else:
        if not args.prompt:
            raise ValueError("Informe --prompt, --script-file ou --legacy-dir.")
        script_data = generate_script(args.prompt, script_path)

    meta_path.write_text(json.dumps({
        "title": script_data["title"],
        "thumb_hook": script_data["thumb_hook"],
        "description": script_data["description"],
        "tags": script_data["tags"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. PROMPTS DE IMAGEM
    generate_prompts_for_script(script_data, prompts_path)
    if args.stage == "script":
        print(f"OK script + prompts + metadados -> {script_path}")
        return 0

    # 3. TTS EMOCIONAL EMBUTIDO + PORTAO DE PROSODIA + WHISPER QA
    timings = synthesize_all_scenes(
        script_data,
        audio_dir,
        provider=args.tts_provider,
        enable_whisper_qa=not args.skip_whisper_qa,
        enable_prosody_gate=not args.skip_prosody_gate,
        allow_flat_fallback=args.allow_flat_fallback,
        force=args.force,
    )
    timings_path.write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.stage == "tts":
        return 0

    # 4. RITMO (DIVISAO <= 5s + KEN BURNS + DUAL AVATAR)
    visual_clips, final_prompts = build_pacing_plan(script_data, timings)
    pacing_path.write_text(json.dumps(visual_clips, ensure_ascii=False, indent=2), encoding="utf-8")
    prompts_path.write_text(json.dumps(final_prompts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Pacing: {len(visual_clips)} sub-clips visuais (<= 5s cada)", flush=True)
    if args.stage == "pacing":
        return 0

    # 5. IMAGENS 16:9 SEM COLAGEM (recria apenas o que faltar ou reprovar)
    if not args.skip_images:
        generate_images_for_plan(final_prompts, images_dir, force=args.force)
    if args.stage == "images":
        return 0

    out_16_9 = output_dir / f"{slug}_16x9.mp4"
    out_srt = output_dir / f"{slug}.srt"
    out_9_16 = None if args.skip_short else (output_dir / f"{slug}_short_9x16.mp4")

    if args.stage != "audit":
        bgm = Path(args.bgm) if args.bgm else None
        assemble_video(
            visual_clips,
            images_dir,
            work_dir,
            out_16_9,
            out_srt,
            bgm_wav=bgm,
            with_avatar=not args.no_avatar,
            burn_captions=args.burn_captions,
        )
        print(f"Video 16:9 pronto: {out_16_9}", flush=True)

        if out_9_16 is not None:
            export_short_9_16(
                out_16_9,
                visual_clips,
                out_9_16,
                hook_badge=script_data["thumb_hook"],
                engine=args.short_engine,
            )
            print(f"Short 9:16 ({args.short_engine}) pronto: {out_9_16}", flush=True)

        if not args.skip_thumbs:
            first_img = images_dir / f"{visual_clips[0]['clip_id']}.jpg"
            if first_img.exists():
                thumbs = generate_thumbnail_variants(first_img, thumbs_dir, hook_words=script_data["thumb_hook"])
                print("Thumbnails A/B prontas:", [t.name for t in thumbs], flush=True)

    # 7. AUTO-AUDITORIA FINAL OBRIGATORIA
    audit = run_final_audit(
        proj_dir=proj_dir,
        script_data=script_data,
        tts_timings=timings,
        visual_clips=visual_clips,
        images_dir=images_dir,
        out_16_9=out_16_9,
        out_short=out_9_16,
        thumbs_dir=thumbs_dir,
        vision_check=args.vision_audit,
    )
    print(f"Auto-Auditoria Final: APPROVED={audit['approved']} | Issues={audit['issues_count']}", flush=True)
    if not audit["approved"]:
        for iss in audit["issues"]:
            print("  [AUDIT-FAIL]", iss, flush=True)
        return 2
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Videomaker v2 — Motor Unico Frida & Luna")
    ap.add_argument("--prompt", default="", help="Tema do novo episodio")
    ap.add_argument("--slug", default="", help="Slug do projeto")
    ap.add_argument("--script-file", default="", help="Caminho para script_v2.json pronto")
    ap.add_argument("--legacy-dir", default="", help="Pasta de um video legado para auditar e refazer no motor v2")
    ap.add_argument("--batch-scan", default="", help="Escaneia e audita todas as pastas de video dentro de um diretorio")
    ap.add_argument("--stage", choices=("all", "avatar-only", "script", "tts", "pacing", "images", "audit"), default="all")
    ap.add_argument("--build-avatar", choices=("luna",), default="", help="Gera o pacote de avatar Luna dentro do programa")
    ap.add_argument("--tts-provider", choices=("gemini_emotion", "edge"), default="gemini_emotion")
    ap.add_argument("--short-engine", choices=("auto", "motion_hud", "remotion"), default="auto")
    ap.add_argument("--allow-flat-fallback", action="store_true")
    ap.add_argument("--skip-prosody-gate", action="store_true")
    ap.add_argument("--skip-whisper-qa", action="store_true")
    ap.add_argument("--skip-images", action="store_true")
    ap.add_argument("--skip-short", action="store_true")
    ap.add_argument("--skip-thumbs", action="store_true")
    ap.add_argument("--vision-audit", action="store_true", help="Compara imagens geradas x cenario via Gemini Vision")
    ap.add_argument("--burn-captions", action="store_true")
    ap.add_argument("--no-avatar", action="store_true")
    ap.add_argument("--bgm", default="", help="Trilha instrumental opcional (.wav)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    return run_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
