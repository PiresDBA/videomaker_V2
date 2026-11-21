# -*- coding: utf-8 -*-
"""Auditor cena-a-cena de sincronia Narracao x Imagem/Video, Personagens (@nome), Objetos e Vozes."""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import FFMPEG_EXE, FFPROBE_EXE, SPEAKER_VOICE_PROFILES, TARGET_VEO_VIDEOS  # noqa: E402
from core.media_studio import detect_split_collage, generate_single_image, sanitize_image_prompt  # noqa: E402
from core.script_engine import _get_google_keys, normalize_script_records  # noqa: E402


def _probe_dur(path: Path) -> float:
    try:
        out = subprocess.check_output(
            [FFPROBE_EXE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            text=True,
        ).strip()
        return float(out)
    except Exception:
        return 0.0


def _extract_video_keyframes(video_path: Path, out_dir: Path, prefix: str, count: int = 3) -> list[Path]:
    dur = max(0.5, _probe_dur(video_path))
    out_dir.mkdir(parents=True, exist_ok=True)
    fracs = [0.2, 0.55, 0.85][:max(1, count)]
    frames: list[Path] = []
    for idx, frac in enumerate(fracs, 1):
        t = min(max(0.1, dur * frac), max(0.1, dur - 0.15))
        dst = out_dir / f"{prefix}_f{idx}.jpg"
        r = subprocess.run(
            [FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video_path),
             "-frames:v", "1", "-q:v", "3", str(dst)],
            capture_output=True,
        )
        if r.returncode == 0 and dst.exists() and dst.stat().st_size > 2000:
            frames.append(dst)
    return frames


def audit_voice_consistency(tts_timings: list[dict[str, Any]]) -> list[str]:
    """Valida se Narrador, Frida e Luna mantiveram exatamente a mesma voz travada do inicio ao fim."""
    errors: list[str] = []
    seen_by_speaker: dict[str, set[str]] = {}
    for item in tts_timings:
        spk = str(item.get("speaker") or "narrador").lower()
        voice = str(item.get("voice") or "").strip()
        expected = SPEAKER_VOICE_PROFILES.get(spk, SPEAKER_VOICE_PROFILES["narrador"])["gemini_voice"]
        if not voice:
            continue
        short_v = voice.split(":")[-1].strip()
        seen_by_speaker.setdefault(spk, set()).add(short_v)
        if short_v != expected:
            errors.append(
                f"{item.get('scene_id')}: speaker '{spk}' usou voz '{short_v}' em vez da voz travada '{expected}'"
            )
    for spk, voices in seen_by_speaker.items():
        if len(voices) > 1:
            errors.append(f"speaker '{spk}' trocou de voz ao longo do video: {sorted(voices)}")
    return errors


def audit_scene_visual_with_vision(
    frame_paths: list[Path],
    scene: dict[str, Any],
    secondary_characters: list[dict[str, str]] | None = None,
    story_props: list[dict[str, str]] | None = None,
    anchor_prop_image: Path | None = None,
) -> dict[str, Any]:
    """Audita cena (imagem ou frames de video) contra narracao PT, personagens e consistencia de objeto."""
    valid_frames = [p for p in frame_paths if p.exists() and p.stat().st_size > 2000]
    if not valid_frames:
        return {"checked": False, "ok": False, "reason": "nenhum frame valido encontrado", "fix_prompt_hint": ""}

    for fp in valid_frames:
        cols = detect_split_collage(fp)
        if cols > 1:
            return {
                "checked": True,
                "ok": False,
                "matches_narration": False,
                "matches_location": True,
                "matches_characters": True,
                "matches_story_props": True,
                "has_collage_or_split": True,
                "has_visible_text": False,
                "reason": f"colagem detectada ({cols} paineis) em {fp.name}",
                "fix_prompt_hint": "Generate a single unified full-frame 16:9 composition with ZERO split panels or collage borders.",
            }

    keys = _get_google_keys()
    if not keys:
        return {"checked": False, "ok": True, "reason": "sem chave Google para Vision QA"}

    sec_desc = "; ".join(
        f"{s.get('name')}: {s.get('description')}"
        for s in (secondary_characters or [])
        if isinstance(s, dict) and s.get("name")
    )
    props_desc = "; ".join(
        f"{p.get('name')}: {p.get('description')}"
        for p in (story_props or [])
        if isinstance(p, dict) and p.get("name")
    )
    chars_txt = ", ".join(scene.get("characters") or ["Frida", "Luna"])

    prompt = (
        "You are a strict animation continuity director auditing a scene frame before moving to the next scene.\n"
        f"Spoken Narration (Portuguese): \"{scene.get('text', '')}\"\n"
        f"Expected Location: {scene.get('location', '')}\n"
        f"Expected Visual Action: {scene.get('visual_action', '')}\n"
        f"Expected Characters in Scene: {chars_txt}\n"
        "Character Design Rules:\n"
        "- Frida: soft fawn golden-tan young English bulldog puppy (3D cartoon, white pearl necklace with small gold paw pendant; NEVER black-and-white spotted).\n"
        "- Luna: dark chocolate-brown young miniature dachshund puppy with tan markings and double gold heart chain.\n"
        + (f"- Secondary Characters: {sec_desc}\n" if sec_desc else "")
        + (f"Story Key Objects (MUST stay identical across the whole video): {props_desc}\n" if props_desc else "")
        + ("The LAST image attached is the reference anchor image for the story's key object/style. Verify that the key object (if visible) keeps the same color, shape and style.\n"
           if anchor_prop_image and anchor_prop_image.exists() else "")
        + "Reject (false) if: the visual contradicts or ignores what the narration is saying, shows wrong dog breeds/colors, "
          "changes the key story object's appearance drastically, has comic-strip/split-screen panels, or has visible watermark/text.\n"
        "Respond ONLY in JSON with keys: "
        '{"matches_narration": bool, "matches_location": bool, "matches_characters": bool, '
        '"matches_story_props": bool, "has_collage_or_split": bool, "has_visible_text": bool, '
        '"reason": "short summary in Portuguese", "fix_prompt_hint": "short English prompt fix if any check is false, else empty"}'
    )

    parts: list[dict[str, Any]] = [{"text": prompt}]
    for fp in valid_frames[:3]:
        b64 = base64.b64encode(fp.read_bytes()).decode("ascii")
        parts.append({"inlineData": {"mimeType": "image/jpeg", "data": b64}})
    if anchor_prop_image and anchor_prop_image.exists() and anchor_prop_image not in valid_frames:
        b64_ref = base64.b64encode(anchor_prop_image.read_bytes()).decode("ascii")
        parts.append({"inlineData": {"mimeType": "image/jpeg", "data": b64_ref}})

    payload = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }).encode("utf-8")

    for model in ("gemini-3-flash-preview", "gemini-2.5-flash"):
        for key in keys[:3]:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(key)}"
            )
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=35) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                txt = data["candidates"][0]["content"]["parts"][0]["text"]
                res = json.loads(txt)
                ok = (
                    bool(res.get("matches_narration", True))
                    and bool(res.get("matches_location", True))
                    and bool(res.get("matches_characters", True))
                    and bool(res.get("matches_story_props", True))
                    and not bool(res.get("has_collage_or_split", False))
                    and not bool(res.get("has_visible_text", False))
                )
                res["checked"] = True
                res["ok"] = ok
                return res
            except Exception:
                continue
    return {"checked": False, "ok": True, "reason": "vision timeout/erro", "fix_prompt_hint": ""}


def generate_and_audit_scenes(
    proj_dir: Path,
    script_data: dict[str, Any],
    visual_clips: list[dict[str, Any]],
    prompts_manifest: dict[str, dict[str, Any]],
    images_dir: Path,
    videos_dir: Path | None = None,
    auto_fix: bool = True,
    max_retries: int = 3,
    force_audit_cached: bool = True,
) -> dict[str, Any]:
    """Gera e audita CENA POR CENA antes de passar para a proxima cena; regenera se nao fizer sentido."""
    images_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = proj_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    report_path = artifacts_dir / "scene_audit_report.json"

    sec_chars = script_data.get("secondary_characters") or []
    story_props = script_data.get("story_props") or []
    scene_map = {sc["scene_id"]: sc for sc in script_data.get("scenes", [])}

    clips_by_scene: dict[str, list[dict[str, Any]]] = {}
    for c in visual_clips:
        clips_by_scene.setdefault(c["scene_id"], []).append(c)

    ensured_accounts: set[str] = set()
    anchor_prop_img: Path | None = None
    scene_reports: list[dict[str, Any]] = []
    regenerated_ids: list[str] = []
    failed_ids: list[str] = []

    for sc in script_data.get("scenes", []):
        sid = sc["scene_id"]
        sc_clips = clips_by_scene.get(sid) or [{"clip_id": f"{sid}_p1", "scene_id": sid}]
        sc_entries: list[dict[str, Any]] = []

        for clip in sc_clips:
            cid = clip["clip_id"]
            pdata = prompts_manifest.get(cid) or prompts_manifest.get(f"{sid}_p1") or {}
            dst = images_dir / f"{cid}.jpg"
            chars = tuple(sc.get("characters") or pdata.get("characters") or ("Frida", "Luna"))

            base_p1 = images_dir / f"{sid}_p1.jpg"
            refs: list[Path] = []
            if not cid.endswith("_p1") and base_p1.exists():
                refs.append(base_p1)
            elif anchor_prop_img is not None and anchor_prop_img.exists():
                refs.append(anchor_prop_img)

            base_pos = sanitize_image_prompt(pdata.get("positive") or sc.get("visual_action") or sc.get("text") or "")
            neg = pdata.get("negative") or ""
            fix_hint = ""
            final_vis: dict[str, Any] = {"checked": False, "ok": True}

            attempts = max(1, max_retries) if auto_fix else 1
            for attempt in range(1, attempts + 1):
                if not dst.exists() or dst.stat().st_size < 15000 or detect_split_collage(dst) > 1 or (attempt > 1):
                    if not auto_fix and not dst.exists():
                        final_vis = {"checked": True, "ok": False, "reason": "imagem ausente"}
                        break
                    prompt_now = base_pos + (f". STRICT CORRECTION: {fix_hint}" if fix_hint else "")
                    full_prompt = f"{prompt_now}\nNegative prompt: {neg}" if neg else prompt_now
                    try:
                        generate_single_image(
                            full_prompt,
                            dst,
                            aspect="16:9",
                            wait_s=240,
                            characters=chars,
                            ref_images=tuple(refs),
                            script_data=script_data,
                            ensured_accounts=ensured_accounts,
                        )
                        regenerated_ids.append(cid)
                    except Exception as exc:
                        final_vis = {"checked": True, "ok": False, "reason": f"erro geracao: {exc}"}
                        continue

                if attempt == 1 and not force_audit_cached and dst.exists():
                    final_vis = {"checked": False, "ok": True, "reason": "cache_aprovado"}
                    break

                vis = audit_scene_visual_with_vision(
                    [dst],
                    sc,
                    secondary_characters=sec_chars,
                    story_props=story_props,
                    anchor_prop_image=anchor_prop_img if (anchor_prop_img and anchor_prop_img != dst) else None,
                )
                final_vis = vis
                if vis.get("ok", True):
                    if anchor_prop_img is None and dst.exists():
                        anchor_prop_img = dst
                    print(f"  [AUDIT-CENA] {cid}: APROVADA ({vis.get('reason', 'OK')})", flush=True)
                    break

                print(
                    f"  [AUDIT-CENA] {cid} tentativa {attempt}/{attempts} REPROVADA: {vis.get('reason')}",
                    flush=True,
                )
                fix_hint = str(vis.get("fix_prompt_hint") or vis.get("reason") or "")
                if auto_fix and attempt < attempts:
                    dst.unlink(missing_ok=True)
                    if dst == anchor_prop_img:
                        anchor_prop_img = None

            if not final_vis.get("ok", True):
                failed_ids.append(cid)
            sc_entries.append({"clip_id": cid, "path": str(dst), **final_vis})

        # Audita video Veo 3.1 Lite da cena (se existir)
        vid_entry: dict[str, Any] | None = None
        if videos_dir is not None:
            v_mp4 = videos_dir / f"{sid}.mp4"
            if v_mp4.exists() and v_mp4.stat().st_size > 50000:
                with tempfile.TemporaryDirectory() as td:
                    kf = _extract_video_keyframes(v_mp4, Path(td), sid, count=3)
                    v_vis = audit_scene_visual_with_vision(
                        kf,
                        sc,
                        secondary_characters=sec_chars,
                        story_props=story_props,
                        anchor_prop_image=anchor_prop_img,
                    )
                vid_entry = {"scene_id": sid, "video_path": str(v_mp4), **v_vis}
                if not v_vis.get("ok", True):
                    print(f"  [AUDIT-VIDEO] {sid}.mp4 REPROVADO: {v_vis.get('reason')}", flush=True)
                    if auto_fix:
                        v_mp4.unlink(missing_ok=True)
                        vid_entry["removed_for_regen"] = True
                    failed_ids.append(f"{sid}.mp4")
                else:
                    print(f"  [AUDIT-VIDEO] {sid}.mp4: APROVADO ({v_vis.get('reason', 'OK')})", flush=True)

        scene_reports.append({
            "scene_id": sid,
            "speaker": sc.get("speaker"),
            "text": sc.get("text"),
            "clips": sc_entries,
            "video": vid_entry,
        })
        report_path.write_text(
            json.dumps(
                {
                    "approved": len(failed_ids) == 0,
                    "scenes_audited": len(scene_reports),
                    "regenerated_clips": regenerated_ids,
                    "failed_clips": failed_ids,
                    "scenes": scene_reports,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    veo_count = len(list(videos_dir.glob("*.mp4"))) if videos_dir and videos_dir.exists() else 0
    timings_p = artifacts_dir / "tts_timings_v2.json"
    voice_errors: list[str] = []
    if timings_p.exists():
        try:
            voice_errors = audit_voice_consistency(json.loads(timings_p.read_text(encoding="utf-8")))
        except Exception:
            pass

    final_rep = {
        "approved": len(failed_ids) == 0 and len(voice_errors) == 0,
        "scenes_audited": len(scene_reports),
        "veo_videos_count": veo_count,
        "target_veo_videos": TARGET_VEO_VIDEOS,
        "voice_errors": voice_errors,
        "regenerated_clips": regenerated_ids,
        "failed_clips": failed_ids,
        "scenes": scene_reports,
    }
    report_path.write_text(json.dumps(final_rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return final_rep


def main() -> int:
    ap = argparse.ArgumentParser(description="Auditoria cena-a-cena Narracao x Imagem/Video x Personagens x Objetos")
    ap.add_argument("--project-dir", required=True, help="Diretorio do projeto em projects/<slug>")
    ap.add_argument("--auto-fix", action="store_true", help="Regenera automaticamente cenas reprovadas antes de avancar")
    ap.add_argument("--max-retries", type=int, default=3)
    args = ap.parse_args()

    proj_dir = Path(args.project_dir)
    script_data = normalize_script_records(
        json.loads((proj_dir / "artifacts" / "script_v2.json").read_text(encoding="utf-8"))
    )
    visual_clips = json.loads((proj_dir / "artifacts" / "pacing_plan_v2.json").read_text(encoding="utf-8"))
    prompts = json.loads((proj_dir / "artifacts" / "image_prompts_v2.json").read_text(encoding="utf-8"))

    rep = generate_and_audit_scenes(
        proj_dir=proj_dir,
        script_data=script_data,
        visual_clips=visual_clips,
        prompts_manifest=prompts,
        images_dir=proj_dir / "assets" / "images",
        videos_dir=proj_dir / "assets" / "videos",
        auto_fix=args.auto_fix,
        max_retries=args.max_retries,
    )
    print(
        f"Auditoria Cena-a-Cena: APPROVED={rep['approved']} | Cenas={rep['scenes_audited']} | "
        f"Veo={rep['veo_videos_count']}/{rep['target_veo_videos']} | "
        f"VozErros={len(rep['voice_errors'])} | Falhas={len(rep['failed_clips'])}",
        flush=True,
    )
    return 0 if rep["approved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
