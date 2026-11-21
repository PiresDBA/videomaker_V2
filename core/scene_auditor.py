# -*- coding: utf-8 -*-
"""Auditor cena-a-cena de sincronia Narracao x Imagem/Video, Personagens (@nome), Objetos e Vozes."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import FFMPEG_EXE, FFPROBE_EXE, SPEAKER_VOICE_PROFILES, TARGET_VEO_VIDEOS  # noqa: E402
from core.flow_accounts import is_quota_error_text  # noqa: E402
from core.media_studio import (  # noqa: E402
    detect_split_collage,
    generate_single_image,
    generate_single_veo_video,
    sanitize_image_prompt,
)
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
        raw_v = voice.split(":")[-1].strip()
        short_v = raw_v.split("-")[-1].strip() if "Chirp3-HD-" in raw_v else raw_v
        seen_by_speaker.setdefault(spk, set()).add(short_v)
        if short_v != expected:
            errors.append(
                f"{item.get('scene_id')}: speaker '{spk}' usou voz '{short_v}' em vez da voz travada '{expected}'"
            )
    for spk, voices in seen_by_speaker.items():
        if len(voices) > 1:
            errors.append(f"speaker '{spk}' trocou de voz ao longo do video: {sorted(voices)}")
    return errors


def _scene_matching_props(scene: dict[str, Any], story_props: list[dict[str, str]]) -> list[dict[str, str]]:
    """Retorna apenas os story_props realmente citados/visiveis nesta cena."""
    if not story_props:
        return []
    explicit = {str(x).strip().lower() for x in (scene.get("props") or []) if str(x).strip()}
    hay = f"{scene.get('text', '')} {scene.get('visual_action', '')} {scene.get('location', '')}".lower()
    matched: list[dict[str, str]] = []
    for pr in story_props:
        if not isinstance(pr, dict) or not pr.get("name"):
            continue
        pname = str(pr["name"]).strip().lower()
        tokens = [t for t in re.findall(r"[a-z0-9áéíóúâêôãõç]{4,}", pname)]
        if pname in explicit or pname in hay or any(t in hay for t in tokens):
            matched.append(pr)
    return matched


def _extract_stills_for_veo_subclips(
    video_path: Path,
    sc_clips: list[dict[str, Any]],
    images_dir: Path,
) -> None:
    """Extrai frames 1920x1080 do video Veo aprovado para sub-clips _p2/_p3 sem gerar imagens extras."""
    if not video_path.exists() or len(sc_clips) <= 1:
        return
    dur = max(1.0, _probe_dur(video_path))
    extra_clips = sc_clips[1:]
    for idx, clip in enumerate(extra_clips, 1):
        dst = images_dir / f"{clip['clip_id']}.jpg"
        if dst.exists() and dst.stat().st_size > 15000:
            continue
        frac = min(0.88, 0.25 + 0.55 * (idx / max(1, len(extra_clips))))
        t = min(max(0.2, dur * frac), max(0.2, dur - 0.2))
        subprocess.run(
            [
                FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video_path),
                "-vframes", "1", "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
                "-q:v", "3", str(dst),
            ],
            capture_output=True,
        )


def _encode_vision_jpeg_b64(img_path: Path, max_w: int = 960) -> str:
    """Redimensiona frame para <=960px antes de enviar ao Vision QA (payload leve e rapido)."""
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            if im.width > max_w:
                nh = max(1, int(round(im.height * (max_w / float(im.width)))))
                im = im.resize((max_w, nh), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=82)
            return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return base64.b64encode(img_path.read_bytes()).decode("ascii")


def _file_sha1(path: Path) -> str:
    """Hash SHA-1 + tamanho para detectar alteracao real de imagem/video em cache."""
    if not path.exists() or not path.is_file():
        return ""
    h = hashlib.sha1()
    st = path.stat()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return f"{st.st_size}:{h.hexdigest()}"


def _scene_audit_fingerprint(
    media_path: Path,
    scene: dict[str, Any],
    matched_props: list[dict[str, str]],
    anchor_prop_image: Path | None = None,
    clip_variant: str = "",
    audio_heard_pt: str = "",
) -> str:
    payload = {
        "schema": "AUDIT_CACHE_V1",
        "media_hash": _file_sha1(media_path),
        "anchor_hash": _file_sha1(anchor_prop_image) if anchor_prop_image and anchor_prop_image.exists() else "",
        "text": str(scene.get("text") or ""),
        "location": str(scene.get("location") or ""),
        "visual_action": str(scene.get("visual_action") or ""),
        "characters": sorted(str(x) for x in (scene.get("characters") or [])),
        "props": sorted(f"{p.get('name','')}:{p.get('description','')}" for p in matched_props if isinstance(p, dict)),
        "clip_variant": clip_variant,
        "audio_heard_pt": audio_heard_pt,
    }
    return hashlib.sha1(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def audit_scene_visual_with_vision(
    frame_paths: list[Path],
    scene: dict[str, Any],
    secondary_characters: list[dict[str, str]] | None = None,
    story_props: list[dict[str, str]] | None = None,
    anchor_prop_image: Path | None = None,
    strict_vision: bool = True,
    clip_variant: str = "",
    audio_heard_pt: str = "",
    is_video_keyframes: bool = False,
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

    is_video = bool(is_video_keyframes or len(valid_frames) > 1)
    keys = _get_google_keys()
    if not keys:
        return {
            "checked": False,
            "ok": not strict_vision,
            "vision_unavailable": True,
            "reason": "sem chave Google para Vision QA",
            "fix_prompt_hint": "",
        }

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
        f"Spoken Narration (Portuguese Script): \"{scene.get('text', '')}\"\n"
        + (f"Actual Audio Heard in WAV (Whisper Transcription): \"{audio_heard_pt}\"\n" if audio_heard_pt else "")
        + f"Expected Location: {scene.get('location', '')}\n"
        f"Expected Visual Action: {scene.get('visual_action', '')}\n"
        f"Expected Characters in Scene: {chars_txt}\n"
        + (f"Sub-clip Shot Variant: {clip_variant} (may be a tighter reaction or reverse angle of the same scene)\n" if clip_variant else "")
        + "Character & Breed Design Rules (STRICT):\n"
        "- Frida: soft fawn golden-tan young English bulldog puppy (3D cartoon, white pearl necklace with small gold paw pendant; NEVER Golden Retriever, NEVER black-and-white spotted, NEVER adult/old dog).\n"
        "- Luna: dark chocolate-brown young miniature dachshund puppy with tan markings and double gold heart chain (NEVER Cocker Spaniel, NEVER random brown/black dog).\n"
        "- ZERO unrequested dog breeds or random extra animals! Background/crowd dogs are allowed ONLY when Expected Visual Action or Narration explicitly mentions multiple dogs/competitors (e.g. \"vários cães\", \"competidores\"), and Frida & Luna MUST stay clearly recognizable in the foreground. Unscripted fantasy creatures (like a literal red furry monster) or unscripted foreground props (like a trophy when not mentioned in this scene) MUST NOT appear.\n"
        + (f"- Secondary Characters: {sec_desc}\n" if sec_desc else "")
        + (f"Story Key Objects (treated as FIXED characters, MUST keep exact same color, material and shape across ALL scenes): {props_desc}\n" if props_desc else "")
        + (
            f"VIDEO KEYFRAMES AUDIT: The first {len(valid_frames)} attached images are sequential temporal snapshots "
            "(start, middle, end) extracted from ONE continuous 8-second video. It is EXPECTED that you received multiple sequential images. "
            "NEVER reject or claim the sequence is a collage of frames; ALWAYS set has_collage_or_split to false for sequential video snapshots.\n"
            if is_video
            else ""
        )
        + ("The LAST image attached is the reference anchor portrait for the story's key object/prop. REJECT (matches_story_props=false) if the key object in the scene changed color (e.g. changed color, material, or shape compared to the attached anchor portrait), changed design, or vanished when expected.\n"
           if anchor_prop_image and anchor_prop_image.exists() else "")
        + "Reject (false) if: the visual contradicts or ignores what the narration is saying, shows wrong dog breeds/colors, "
          "changes the key story object's appearance/color, "
        + ("" if is_video else "has comic-strip/split-screen panels inside the frame, ")
        + "or has visible watermark/text.\n"
        "Respond ONLY in JSON with keys: "
        '{"matches_narration": bool, "matches_location": bool, "matches_characters": bool, '
        '"matches_story_props": bool, "has_collage_or_split": bool, "has_visible_text": bool, '
        '"reason": "short summary in Portuguese", "fix_prompt_hint": "short English prompt fix if any check is false, else empty"}'
    )

    parts: list[dict[str, Any]] = [{"text": prompt}]
    for fp in valid_frames[:3]:
        parts.append({"inlineData": {"mimeType": "image/jpeg", "data": _encode_vision_jpeg_b64(fp)}})
    if anchor_prop_image and anchor_prop_image.exists() and anchor_prop_image not in valid_frames:
        parts.append({"inlineData": {"mimeType": "image/jpeg", "data": _encode_vision_jpeg_b64(anchor_prop_image)}})

    payload = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }).encode("utf-8")

    last_err = "timeout/erro"
    for round_idx in range(2):
        for model in ("gemini-3.1-flash-lite-preview", "gemini-3-flash-preview"):
            for key in keys:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(key)}"
                )
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                try:
                    with urllib.request.urlopen(req, timeout=28) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    txt = data["candidates"][0]["content"]["parts"][0]["text"]
                    res = json.loads(txt)
                    if isinstance(res, list):
                        res = next((x for x in res if isinstance(x, dict)), {})
                    if not isinstance(res, dict):
                        raise ValueError(f"Vision JSON inesperado: {type(res).__name__}")
                    # Para video, frames individuais ja passaram por detect_split_collage(); evita falso positivo do modelo ao ver 3 keyframes.
                    collage_flag = False if is_video else bool(res.get("has_collage_or_split", False))
                    res["has_collage_or_split"] = collage_flag
                    ok = (
                        bool(res.get("matches_narration", True))
                        and bool(res.get("matches_location", True))
                        and bool(res.get("matches_characters", True))
                        and bool(res.get("matches_story_props", True))
                        and not collage_flag
                        and not bool(res.get("has_visible_text", False))
                    )
                    res["checked"] = True
                    res["ok"] = ok
                    return res
                except Exception as exc:
                    last_err = str(exc)[:80]
                    time.sleep(0.5)
                    continue
        if round_idx == 0:
            time.sleep(3.0)
    return {
        "checked": False,
        "ok": not strict_vision,
        "vision_unavailable": True,
        "reason": f"Vision QA indisponivel ({last_err})",
        "fix_prompt_hint": "",
    }


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
    force: bool = False,
    veo_scene_ids: set[str] | None = None,
    generate_veo_inline: bool = False,
    veo_max_retries: int = 2,
    strict_vision: bool = True,
    stop_on_scene_failure: bool = True,
) -> dict[str, Any]:
    """Gera e audita CENA POR CENA (imagem + Veo) antes de passar para a proxima cena; regenera se nao fizer sentido."""
    images_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = proj_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    report_path = artifacts_dir / "scene_audit_report.json"
    cache_path = artifacts_dir / "scene_audit_cache.json"
    cache_entries: dict[str, dict[str, Any]] = {}
    if not force and cache_path.exists():
        try:
            loaded_c = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(loaded_c, dict) and isinstance(loaded_c.get("entries"), dict):
                cache_entries = dict(loaded_c["entries"])
        except Exception:
            cache_entries = {}

    legacy_approved: dict[str, dict[str, Any]] = {}
    report_mtime = 0.0
    if not force and report_path.exists():
        try:
            report_mtime = report_path.stat().st_mtime
            rep_prev = json.loads(report_path.read_text(encoding="utf-8"))
            scenes_by_id = {str(s.get("scene_id") or ""): s for s in script_data.get("scenes", [])}
            for sc_rep in (rep_prev.get("scenes") or []):
                sid_r = str(sc_rep.get("scene_id") or "")
                sc_cur = scenes_by_id.get(sid_r)
                if not sc_cur or str(sc_rep.get("text") or "") != str(sc_cur.get("text") or ""):
                    continue
                for cl in (sc_rep.get("clips") or []):
                    if isinstance(cl, dict) and cl.get("checked") and cl.get("ok") and cl.get("clip_id"):
                        legacy_approved[f"img:{cl['clip_id']}"] = dict(cl)
                v_rep = sc_rep.get("video")
                if isinstance(v_rep, dict) and v_rep.get("checked") and v_rep.get("ok"):
                    legacy_approved[f"vid:{sid_r}"] = dict(v_rep)
        except Exception:
            legacy_approved = {}

    def _save_audit_cache() -> None:
        try:
            cache_path.write_text(
                json.dumps({"schema": "AUDIT_CACHE_V1", "entries": cache_entries}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _lookup_cached_approval(
        cache_key: str,
        media_path: Path,
        sc: dict[str, Any],
        matched_props: list[dict[str, str]],
        anchor_path: Path | None,
        min_bytes: int,
        clip_variant: str = "",
        audio_heard_pt: str = "",
        check_collage: bool = False,
    ) -> tuple[dict[str, Any] | None, str]:
        if force or not media_path.exists() or media_path.stat().st_size < min_bytes:
            return None, ""
        if check_collage and detect_split_collage(media_path) > 1:
            return None, ""
        fp = _scene_audit_fingerprint(
            media_path,
            sc,
            matched_props,
            anchor_path,
            clip_variant=clip_variant,
            audio_heard_pt=audio_heard_pt,
        )
        cached = cache_entries.get(cache_key)
        if cached and cached.get("fingerprint") == fp and cached.get("checked") and cached.get("ok"):
            return dict(cached.get("result") or {"checked": True, "ok": True, "reason": "cache_aprovado"}), fp
        leg = legacy_approved.get(cache_key)
        if leg and leg.get("checked") and leg.get("ok") and media_path.stat().st_mtime <= report_mtime + 2.0:
            clean_res = {k: v for k, v in leg.items() if k not in ("clip_id", "scene_id", "path", "video_path")}
            cache_entries[cache_key] = {"fingerprint": fp, "checked": True, "ok": True, "result": clean_res}
            _save_audit_cache()
            return dict(clean_res), fp
        return None, fp

    def _store_cached_approval(
        cache_key: str,
        media_path: Path,
        sc: dict[str, Any],
        matched_props: list[dict[str, str]],
        anchor_path: Path | None,
        res: dict[str, Any],
        clip_variant: str = "",
        audio_heard_pt: str = "",
    ) -> None:
        if not (res.get("checked") and res.get("ok")):
            return
        fp = _scene_audit_fingerprint(
            media_path,
            sc,
            matched_props,
            anchor_path,
            clip_variant=clip_variant,
            audio_heard_pt=audio_heard_pt,
        )
        cache_entries[cache_key] = {"fingerprint": fp, "checked": True, "ok": True, "result": dict(res)}
        _save_audit_cache()

    sec_chars = script_data.get("secondary_characters") or []
    story_props = script_data.get("story_props") or []
    heard_by_scene: dict[str, str] = {}
    timings_p_early = artifacts_dir / "tts_timings_v2.json"
    if timings_p_early.exists():
        try:
            for item in json.loads(timings_p_early.read_text(encoding="utf-8")):
                if isinstance(item, dict) and item.get("scene_id"):
                    qa_d = item.get("qa") or {}
                    if qa_d.get("heard"):
                        heard_by_scene[str(item["scene_id"])] = str(qa_d["heard"])
        except Exception:
            pass

    clips_by_scene: dict[str, list[dict[str, Any]]] = {}
    for c in visual_clips:
        clips_by_scene.setdefault(c["scene_id"], []).append(c)

    ensured_accounts: set[str] = set()
    prop_anchors: dict[str, Path] = {}
    chars_dir = proj_dir / "assets" / "characters"
    for pr in story_props:
        if isinstance(pr, dict) and pr.get("name"):
            pname = str(pr["name"]).strip()
            safe_slug = re.sub(r"[^a-z0-9]+", "_", pname.lower()).strip("_") or "objeto"
            p_port = chars_dir / f"{safe_slug}_portrait.jpg"
            if p_port.exists() and p_port.stat().st_size > 10000:
                prop_anchors[pname.lower()] = p_port

    if videos_dir and videos_dir.exists():
        for bad_mp4 in videos_dir.glob("*.mp4"):
            if bad_mp4.stat().st_size < 50000:
                bad_mp4.unlink(missing_ok=True)

    scene_reports: list[dict[str, Any]] = []
    regenerated_ids: list[str] = []
    failed_ids: list[str] = []
    veo_quota_exhausted = False

    def _run_clip(
        sc: dict[str, Any],
        clip: dict[str, Any],
        matched_props: list[dict[str, str]],
        prop_refs: list[Path],
    ) -> dict[str, Any]:
        sid = sc["scene_id"]
        cid = clip["clip_id"]
        pdata = prompts_manifest.get(cid) or prompts_manifest.get(f"{sid}_p1") or {}
        dst = images_dir / f"{cid}.jpg"
        chars_list = list(sc.get("characters") or pdata.get("characters") or ["Frida", "Luna"])
        for mp in matched_props:
            pn = str(mp.get("name") or "").strip()
            if pn and pn not in chars_list:
                chars_list.append(pn)
        chars = tuple(chars_list)

        # Atualiza ancora isolada caso tenha acabado de ser gerada em assets/characters
        for mp in matched_props:
            pn = str(mp.get("name") or "").strip()
            safe_slug = re.sub(r"[^a-z0-9]+", "_", pn.lower()).strip("_") or "objeto"
            p_port = chars_dir / f"{safe_slug}_portrait.jpg"
            if p_port.exists() and p_port.stat().st_size > 10000:
                prop_anchors[pn.lower()] = p_port
                if p_port not in prop_refs:
                    prop_refs.insert(0, p_port)

        base_p1 = images_dir / f"{sid}_p1.jpg"
        refs: list[Path] = []
        if not cid.endswith("_p1") and base_p1.exists():
            refs.append(base_p1)
        for pr in prop_refs:
            if pr.exists() and pr not in refs:
                refs.append(pr)

        base_pos = sanitize_image_prompt(pdata.get("positive") or sc.get("visual_action") or sc.get("text") or "")
        neg = pdata.get("negative") or ""
        fix_hint = ""
        final_vis: dict[str, Any] = {"checked": False, "ok": True}
        anchor_for_vision = prop_refs[0] if (prop_refs and prop_refs[0] != dst) else None

        attempts = max(1, max_retries) if auto_fix else 1
        last_vision_unavail = False
        for attempt in range(1, attempts + 1):
            need_gen = (
                (force and attempt == 1)
                or not dst.exists()
                or dst.stat().st_size < 15000
                or detect_split_collage(dst) > 1
                or (attempt > 1 and not last_vision_unavail)
            )
            if need_gen:
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
                        proj_dir=proj_dir,
                    )
                    regenerated_ids.append(cid)
                except Exception as exc:
                    final_vis = {"checked": True, "ok": False, "reason": f"erro geracao: {exc}"}
                    continue

            if attempt == 1 and not need_gen:
                cached_vis, _ = _lookup_cached_approval(
                    f"img:{cid}",
                    dst,
                    sc,
                    matched_props,
                    anchor_for_vision,
                    min_bytes=15000,
                    clip_variant=str(clip.get("prompt_variant") or ""),
                    audio_heard_pt=heard_by_scene.get(sid, ""),
                    check_collage=True,
                )
                if cached_vis is not None:
                    final_vis = cached_vis
                    for mp in matched_props:
                        prop_anchors.setdefault(mp["name"].lower(), dst)
                    print(f"  [AUDIT-CACHE] {cid}: reaprovada do cache ({cached_vis.get('reason', 'OK')})", flush=True)
                    break

            if attempt == 1 and not force_audit_cached and not force and dst.exists():
                final_vis = {"checked": False, "ok": True, "reason": "cache_aprovado"}
                break

            vis = audit_scene_visual_with_vision(
                [dst],
                sc,
                secondary_characters=sec_chars,
                story_props=matched_props,
                anchor_prop_image=anchor_for_vision,
                strict_vision=strict_vision,
                clip_variant=str(clip.get("prompt_variant") or ""),
                audio_heard_pt=heard_by_scene.get(sid, ""),
            )
            final_vis = vis
            if vis.get("ok", False):
                _store_cached_approval(
                    f"img:{cid}",
                    dst,
                    sc,
                    matched_props,
                    anchor_for_vision,
                    vis,
                    clip_variant=str(clip.get("prompt_variant") or ""),
                    audio_heard_pt=heard_by_scene.get(sid, ""),
                )
                for mp in matched_props:
                    prop_anchors.setdefault(mp["name"].lower(), dst)
                print(f"  [AUDIT-CENA] {cid}: APROVADA ({vis.get('reason', 'OK')})", flush=True)
                break

            last_vision_unavail = bool(vis.get("vision_unavailable"))
            print(
                f"  [AUDIT-CENA] {cid} tentativa {attempt}/{attempts} REPROVADA: {vis.get('reason')}",
                flush=True,
            )
            if last_vision_unavail:
                time.sleep(4.0)
                continue
            fix_hint = str(vis.get("fix_prompt_hint") or vis.get("reason") or "")
            if auto_fix and attempt < attempts:
                dst.unlink(missing_ok=True)
                for k, v in list(prop_anchors.items()):
                    if v == dst:
                        prop_anchors.pop(k, None)

        if not final_vis.get("ok", False):
            failed_ids.append(cid)
        return {"clip_id": cid, "path": str(dst), **final_vis}

    for sc in script_data.get("scenes", []):
        sid = sc["scene_id"]
        sc_clips = clips_by_scene.get(sid) or [{"clip_id": f"{sid}_p1", "scene_id": sid}]
        matched_props = _scene_matching_props(sc, story_props)
        prop_refs = [
            prop_anchors[mp["name"].lower()]
            for mp in matched_props
            if mp["name"].lower() in prop_anchors and prop_anchors[mp["name"].lower()].exists()
        ]

        is_veo_target = (
            videos_dir is not None
            and bool(veo_scene_ids)
            and sid in veo_scene_ids
        )
        clips_upfront = (
            sc_clips[:1]
            if (is_veo_target and generate_veo_inline and not veo_quota_exhausted)
            else sc_clips
        )
        sc_entries: list[dict[str, Any]] = [
            _run_clip(sc, clip, matched_props, prop_refs)
            for clip in clips_upfront
        ]

        # Audita e/ou gera+audita video Veo 3.1 Lite da cena antes de passar para a proxima cena
        vid_entry: dict[str, Any] | None = None
        if videos_dir is not None:
            v_mp4 = videos_dir / f"{sid}.mp4"
            should_run_veo_inline = is_veo_target and generate_veo_inline and not veo_quota_exhausted
            should_audit_existing = (not generate_veo_inline) and v_mp4.exists() and v_mp4.stat().st_size > 50000

            if should_run_veo_inline or should_audit_existing:
                v_attempts = max(1, veo_max_retries) if auto_fix else 1
                v_fix_hint = ""
                v_approved = False
                v_vis: dict[str, Any] = {"checked": False, "ok": False}
                last_veo_vision_unavail = False

                for v_try in range(1, v_attempts + 1):
                    need_veo_gen = (
                        should_run_veo_inline
                        and (force or not v_mp4.exists() or v_mp4.stat().st_size < 50000 or (v_try > 1 and not last_veo_vision_unavail))
                    ) or (should_audit_existing and v_try > 1 and not last_veo_vision_unavail)

                    if need_veo_gen:
                        try:
                            generate_single_veo_video(
                                sc,
                                images_dir=images_dir,
                                videos_dir=videos_dir,
                                script_data=script_data,
                                proj_dir=proj_dir,
                                fix_hint=v_fix_hint,
                                force=(force or v_try > 1),
                            )
                            regenerated_ids.append(f"{sid}.mp4")
                        except Exception as exc:
                            err_low = str(exc).lower()
                            v_vis = {"checked": True, "ok": False, "reason": f"erro Veo: {exc}"}
                            print(f"  [AUDIT-VIDEO] {sid}.mp4 erro na geracao: {exc}", flush=True)
                            if is_quota_error_text(str(exc)) or "esgotaram" in err_low or "nenhuma conta google flow" in err_low:
                                veo_quota_exhausted = True
                                break
                            if v_try < v_attempts:
                                continue
                            break

                    if not v_mp4.exists() or v_mp4.stat().st_size <= 50000:
                        v_vis = {"checked": True, "ok": False, "reason": "video Veo ausente"}
                        break

                    if v_try == 1 and not need_veo_gen:
                        cached_vid, _ = _lookup_cached_approval(
                            f"vid:{sid}",
                            v_mp4,
                            sc,
                            matched_props,
                            prop_refs[0] if prop_refs else None,
                            min_bytes=50001,
                            audio_heard_pt=heard_by_scene.get(sid, ""),
                        )
                        if cached_vid is not None:
                            v_vis = cached_vid
                            v_approved = True
                            _extract_stills_for_veo_subclips(v_mp4, sc_clips, images_dir)
                            print(f"  [AUDIT-CACHE] {sid}.mp4: reaprovado do cache ({cached_vid.get('reason', 'OK')})", flush=True)
                            break

                    with tempfile.TemporaryDirectory() as td:
                        kf = _extract_video_keyframes(v_mp4, Path(td), sid, count=3)
                        v_vis = audit_scene_visual_with_vision(
                            kf,
                            sc,
                            secondary_characters=sec_chars,
                            story_props=matched_props,
                            anchor_prop_image=prop_refs[0] if prop_refs else None,
                            strict_vision=strict_vision,
                            audio_heard_pt=heard_by_scene.get(sid, ""),
                            is_video_keyframes=True,
                        )
                    if v_vis.get("ok", False):
                        v_approved = True
                        _store_cached_approval(
                            f"vid:{sid}",
                            v_mp4,
                            sc,
                            matched_props,
                            prop_refs[0] if prop_refs else None,
                            v_vis,
                            audio_heard_pt=heard_by_scene.get(sid, ""),
                        )
                        _extract_stills_for_veo_subclips(v_mp4, sc_clips, images_dir)
                        print(f"  [AUDIT-VIDEO] {sid}.mp4: APROVADO ({v_vis.get('reason', 'OK')})", flush=True)
                        break

                    last_veo_vision_unavail = bool(v_vis.get("vision_unavailable"))
                    print(
                        f"  [AUDIT-VIDEO] {sid}.mp4 tentativa {v_try}/{v_attempts} REPROVADO: {v_vis.get('reason')}",
                        flush=True,
                    )
                    if last_veo_vision_unavail:
                        time.sleep(4.0)
                        continue
                    v_fix_hint = str(v_vis.get("fix_prompt_hint") or v_vis.get("reason") or "")
                    if auto_fix:
                        v_mp4.unlink(missing_ok=True)

                vid_entry = {"scene_id": sid, "video_path": str(v_mp4), **v_vis}
                if not v_approved:
                    failed_ids.append(f"{sid}.mp4")

                if should_run_veo_inline and not v_approved and len(sc_entries) < len(sc_clips) and not stop_on_scene_failure:
                    for extra_clip in sc_clips[1:]:
                        sc_entries.append(_run_clip(sc, extra_clip, matched_props, prop_refs))

        scene_reports.append({
            "scene_id": sid,
            "speaker": sc.get("speaker"),
            "text": sc.get("text"),
            "clips": sc_entries,
            "video": vid_entry,
        })
        scene_failed = any(
            fid == f"{sid}.mp4" or fid.startswith(f"{sid}_")
            for fid in failed_ids
        )
        if stop_on_scene_failure and scene_failed:
            stop_msg = (
                f"[TRAVA-CRITICA] Parei na cena {sid}: tentei varias vezes e nao consegui gerar/validar "
                f"({[f for f in failed_ids if f == f'{sid}.mp4' or f.startswith(f'{sid}_')]}). "
                "Nao avancei para a proxima cena para nao gerar video inconsistente."
            )
            print(stop_msg, flush=True)
            report_path.write_text(
                json.dumps(
                    {
                        "approved": False,
                        "stopped_at_scene": sid,
                        "stop_reason": stop_msg,
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
            break

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
