# -*- coding: utf-8 -*-
"""Prompts travados na Biblia Visual, geracao 16:9 sem colagens e 3 Thumbnails CTR."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from config import (
    MAX_VEO_GENERATIONS_PER_SCENE,
    NEGATIVE_IMAGE_RULE,
    POSITIVE_IMAGE_RULE,
    TARGET_VEO_VIDEOS,
    THUMB_HEIGHT,
    THUMB_WIDTH,
    VENDOR_DIR,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
    VISUAL_BIBLE,
)

_INTERNAL_MARKERS_RE = (
    re.compile(r"\b(?:CENA|SCENE|IMAGEM|IMAGE|PAINEL|PANEL)\s*\d*\s*(?:\([^)]*\))?\s*:?", re.I),
    re.compile(r"B[IÍ]BLIA\s+DE\s+CONTINUIDADE\s*(?:\([^)]*\))?\s*:?", re.I),
    re.compile(r"REGRA\s+ANTI-?REPETI[CÇ][AÃ]O\s*(?:\([^)]*\))?\s*:?", re.I),
    re.compile(r"\(\s*prioridade\s+m[aá]xima[^)]*\)", re.I),
    re.compile(r"desenhe\s+exatamente\s+esta\s+a[cç][aã]o[^:.\n]*[:.]?", re.I),
    re.compile(r"<[^>]+>"),
    re.compile(r"\b(?:hahaha+|ha\s+ha\s+ha+|kkkk+|rsrs+)\b[!.]*", re.I),
    re.compile(r"\b(?:pixar|disney|ghibli|dreamworks|illumination)\b", re.I),
)

_VARIANT_CAMERA_NOTES = {
    "main": "medium wide cinematic shot, clear foreground action",
    "reaction": "dynamic closer angle focusing on facial expressions and reaction, same exact setting",
    "angle_b": "low dog-eye-level reverse angle showing characters in motion, same exact setting",
    "detail": "tight expressive two-shot highlighting body language and props, same exact setting",
}


def sanitize_image_prompt(text: str) -> str:
    """Remove rotulos internos de roteiro, HTML, risadas e nomes de estudio."""
    cleaned = str(text or "")
    cleaned = cleaned.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    for rx in _INTERNAL_MARKERS_RE:
        cleaned = rx.sub(" ", cleaned)
    cleaned = re.sub(r"\[\s*[^\]]{0,40}\s*\]", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" ,;:-")


def build_image_prompt(
    scene: dict[str, Any],
    variant: str = "main",
    max_chars: int = 2400,
    secondary_characters: list[dict[str, str]] | None = None,
    story_props: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Gera prompt positivo e negativo travados na Biblia Visual, personagens secundarios e objetos da historia."""
    location = sanitize_image_prompt(scene.get("location") or "")
    action = sanitize_image_prompt(scene.get("visual_action") or scene.get("text") or "")
    if not location:
        raise ValueError(f"Cena '{scene.get('scene_id')}' sem 'location' para travar ambiente.")
    if not action:
        raise ValueError(f"Cena '{scene.get('scene_id')}' sem 'visual_action' ou 'text'.")

    cam_note = _VARIANT_CAMERA_NOTES.get(variant, _VARIANT_CAMERA_NOTES["main"])
    speaker = (scene.get("speaker") or "narrador").lower()
    focus_hint = ""
    if speaker == "frida":
        focus_hint = "Frida is the main focal point of the action."
    elif speaker == "luna":
        focus_hint = "Luna is the main focal point of the action."

    scene_chars = [str(c).strip() for c in (scene.get("characters") or ["Frida", "Luna"]) if str(c).strip()]
    chars_lower = {c.lower() for c in scene_chars}
    sec_map = {str(s.get("name") or "").strip().lower(): s for s in (secondary_characters or []) if isinstance(s, dict)}
    sec_notes = []
    for ch in scene_chars:
        if ch.lower() in sec_map and sec_map[ch.lower()].get("description"):
            sec_notes.append(f"@{ch} ({ch}): {sanitize_image_prompt(sec_map[ch.lower()]['description'])}")

    prop_notes = []
    for pr in (story_props or []):
        if isinstance(pr, dict) and pr.get("name") and pr.get("description"):
            prop_notes.append(f"{pr['name']}: {sanitize_image_prompt(pr['description'])}")

    bible_parts = []
    if "frida" in chars_lower:
        bible_parts.append(VISUAL_BIBLE["frida"])
    if "luna" in chars_lower:
        bible_parts.append(VISUAL_BIBLE["luna"])
    bible_parts.extend(sec_notes)
    if not bible_parts:
        bible_parts = [VISUAL_BIBLE["frida"], VISUAL_BIBLE["luna"]]

    positive_parts = [
        POSITIVE_IMAGE_RULE,
        f"Environment strictly locked to: {location}",
        f"Action matching narration: {action}",
        focus_hint,
        (f"Story Objects Continuity (whenever visible in scene, MUST look identical): {'; '.join(prop_notes)}" if prop_notes else ""),
        f"Camera framing: {cam_note}",
        f"Character Bible: {'; '.join(bible_parts)}",
        f"Style: {VISUAL_BIBLE['style']}",
    ]
    positive = ". ".join(p.strip().rstrip(".") for p in positive_parts if p and p.strip()) + "."
    if len(positive) > max_chars:
        positive = positive[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;.") + "."

    return {
        "positive": positive,
        "negative": NEGATIVE_IMAGE_RULE,
        "combined": f"{positive}\nNegative prompt: {NEGATIVE_IMAGE_RULE}",
        "characters": scene_chars,
        "story_props": list(story_props or []),
        "location": location,
        "visual_action": action,
        "narration_pt": str(scene.get("text") or ""),
    }


def generate_prompts_for_script(
    script_data: dict[str, Any],
    out_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Cria o manifesto inicial de prompts (1 prompt base por cena)."""
    prompts: dict[str, dict[str, Any]] = {}
    sec_chars = script_data.get("secondary_characters") or []
    props = script_data.get("story_props") or []
    for sc in script_data.get("scenes", []):
        sid = sc["scene_id"]
        prompts[f"{sid}_p1"] = build_image_prompt(
            sc, variant="main", secondary_characters=sec_chars, story_props=props
        )
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8")
    return prompts


def detect_split_collage(image_path: Path) -> int:
    """Retorna >1 se detectar linhas divisorias verticais/horizontais tipicas de colagem."""
    im = Image.open(image_path).convert("RGB")
    im.thumbnail((640, 640))
    arr = np.asarray(im, dtype=np.float32)
    h, w = arr.shape[:2]

    def score_line(pos: int, axis: int) -> float:
        if axis == 1:
            if pos < 8 or pos > w - 8:
                return 0.0
            left = arr[:, max(0, pos - 3):pos].mean(axis=1)
            right = arr[:, pos + 1:min(w, pos + 4)].mean(axis=1)
        else:
            if pos < 8 or pos > h - 8:
                return 0.0
            left = arr[max(0, pos - 3):pos, :].mean(axis=0)
            right = arr[pos + 1:min(h, pos + 4), :].mean(axis=0)
        diff = np.abs(left - right).mean(axis=-1)
        return float((diff > 28.0).mean())

    for n, xs in ((2, [w // 2]), (3, [w // 3, 2 * w // 3]), (4, [w // 4, w // 2, 3 * w // 4])):
        if all(score_line(x, 1) > 0.55 for x in xs):
            return n
    for n, ys in ((2, [h // 2]), (3, [h // 3, 2 * h // 3])):
        if all(score_line(y, 0) > 0.55 for y in ys):
            return n
    return 1


def fit_aspect_jpeg(src: Path, dst: Path, tw: int = VIDEO_WIDTH, th: int = VIDEO_HEIGHT) -> None:
    """Ajusta imagem gerada para resolucao alvo sem distorcao."""
    im = Image.open(src).convert("RGB")
    sw, sh = im.size
    scale = max(tw / sw, th / sh)
    nw, nh = int(round(sw * scale)), int(round(sh * scale))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    x0 = (nw - tw) // 2
    y0 = (nh - th) // 2
    im = im.crop((x0, y0, x0 + tw, y0 + th))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, format="JPEG", quality=93)


_UNAVAILABLE_CDP_URLS: set[str] = set()


def generate_single_image(
    prompt: str,
    out_path: Path,
    aspect: str = "16:9",
    ref_image: Path | None = None,
    wait_s: int = 240,
    pause_s: float = 3.0,
    characters: tuple[str, ...] = ("Frida", "Luna"),
    ref_images: tuple[Path, ...] = (),
    script_data: dict[str, Any] | None = None,
    ensured_accounts: set[str] | None = None,
    proj_dir: Path | None = None,
) -> Path:
    """Gera uma unica imagem via Flow (CDP direto com @Personagem + ref de objeto) com fallback."""
    flow_script = VENDOR_DIR / "flow_fetch.py"
    gemini_script = VENDOR_DIR / "gemini_fetch.py"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sec_portrait_dir = (proj_dir / "assets" / "characters") if proj_dir else None

    # Caminho preferencial: motor direto core.flow_continuity (Nano Banana 2.1, x1, 0 creditos) usando pool CDP ativo
    try:
        import asyncio, os, urllib.request
        from core.flow_continuity import DEFAULT_CDP_URL, DEFAULT_FLOW_PROJECT_URL, generate_flow_image
        from core.flow_accounts import (
            cdp_is_alive,
            check_needs_google_login,
            ensure_story_characters_created,
            get_next_available_accounts,
            load_accounts_config,
            upload_media_to_flow,
        )
        from playwright.async_api import async_playwright

        candidates: list[tuple[str, str]] = []
        seen_urls: set[str] = set()
        accounts_cfg = load_accounts_config().get("accounts", [])
        port_to_proj = {f"http://127.0.0.1:{int(a['cdp_port'])}": a.get("project_url") or DEFAULT_FLOW_PROJECT_URL for a in accounts_cfg}

        env_cdp = os.environ.get("GEMINI_CDP_URL", "").strip().rstrip("/")
        if env_cdp and env_cdp not in _UNAVAILABLE_CDP_URLS:
            candidates.append((env_cdp, port_to_proj.get(env_cdp, DEFAULT_FLOW_PROJECT_URL)))
            seen_urls.add(env_cdp)

        for acc in get_next_available_accounts(ignore_soft_daily_cap=True):
            port = int(acc["cdp_port"])
            cdp_url = f"http://127.0.0.1:{port}"
            if cdp_url not in seen_urls and cdp_url not in _UNAVAILABLE_CDP_URLS and cdp_is_alive(port):
                candidates.append((cdp_url, acc.get("project_url") or DEFAULT_FLOW_PROJECT_URL))
                seen_urls.add(cdp_url)

        # Nano Banana 2.1 usa 0 creditos: contas sem cota Veo ainda servem para gerar imagens
        for acc in accounts_cfg:
            if not acc.get("enabled", True):
                continue
            port = int(acc["cdp_port"])
            cdp_url = f"http://127.0.0.1:{port}"
            if cdp_url not in seen_urls and cdp_url not in _UNAVAILABLE_CDP_URLS and cdp_is_alive(port):
                candidates.append((cdp_url, acc.get("project_url") or DEFAULT_FLOW_PROJECT_URL))
                seen_urls.add(cdp_url)

        if DEFAULT_CDP_URL not in seen_urls and DEFAULT_CDP_URL not in _UNAVAILABLE_CDP_URLS:
            try:
                with urllib.request.urlopen(f"{DEFAULT_CDP_URL}/json/version", timeout=2):
                    candidates.append((DEFAULT_CDP_URL, port_to_proj.get(DEFAULT_CDP_URL, DEFAULT_FLOW_PROJECT_URL)))
            except Exception:
                pass

        all_refs: list[Path] = []
        if ref_image and Path(ref_image).exists():
            all_refs.append(Path(ref_image))
        for rp in ref_images:
            if rp and Path(rp).exists() and Path(rp) not in all_refs:
                all_refs.append(Path(rp))

        async def _run_direct(cdp_url: str, proj_url: str) -> None:
            async with async_playwright() as pw:
                b = await pw.chromium.connect_over_cdp(cdp_url, timeout=10000)
                try:
                    ctx = b.contexts[0]
                    pg = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or await ctx.new_page()
                    if "flow.google.com" not in pg.url or "/project/" not in pg.url or "/character" in pg.url or "/edit/" in pg.url:
                        await pg.goto(proj_url, wait_until="domcontentloaded", timeout=30000)
                        await pg.wait_for_timeout(2000)
                    if await check_needs_google_login(pg):
                        _UNAVAILABLE_CDP_URLS.add(cdp_url)
                        raise RuntimeError(f"Conta Flow {cdp_url} deslogada; pulando.")
                    if script_data and ensured_accounts is not None and cdp_url not in ensured_accounts:
                        try:
                            present = await ensure_story_characters_created(
                                pg, script_data, proj_url, portrait_dir=sec_portrait_dir
                            )
                            needed = tuple(characters or ("Frida", "Luna"))
                            if all(present.get(c, False) for c in needed):
                                ensured_accounts.add(cdp_url)
                            else:
                                missing = [c for c in needed if not present.get(c, False)]
                                print(f"  [FlowChars] AVISO: personagens pendentes em {cdp_url}: {missing}", flush=True)
                        except Exception as char_exc:
                            print(f"  [FlowChars] ERRO ao garantir personagens em {cdp_url}: {char_exc}", flush=True)
                    ref_names: list[str] = []
                    for rp in all_refs[:2]:
                        try:
                            if await upload_media_to_flow(pg, rp):
                                ref_names.append(rp.name)
                        except Exception:
                            pass
                    await generate_flow_image(
                        pg,
                        sanitize_image_prompt(prompt),
                        out_path,
                        characters=characters or ("Frida", "Luna"),
                        ref_images=tuple(ref_names),
                        wait_s=min(wait_s, 180),
                    )
                finally:
                    await b.close()

        for cdp_url, proj_url in candidates:
            try:
                asyncio.run(_run_direct(cdp_url, proj_url))
                if out_path.exists() and out_path.stat().st_size >= 10000:
                    tw, th = (1080, 1920) if aspect == "9:16" else (VIDEO_WIDTH, VIDEO_HEIGHT)
                    fit_aspect_jpeg(out_path, out_path, tw, th)
                    return out_path
            except Exception as exc:
                err_low = str(exc).lower()
                print(f"  [FlowImg] {cdp_url} falhou: {str(exc).splitlines()[0]}", flush=True)
                if any(tok in err_low for tok in ("configuracao direta", "fazer login", "deslogada", "has been closed", "target page")):
                    _UNAVAILABLE_CDP_URLS.add(cdp_url)
                continue
    except Exception:
        pass

    cmd_flow = [
        sys.executable, str(flow_script),
        "--kind", "image",
        "--characters", ",".join(characters or ("Frida", "Luna")),
        "--prompt", sanitize_image_prompt(prompt),
        "--name", out_path.stem,
        "--out-dir", str(out_path.parent),
        "--wait", str(wait_s),
        "--pause", str(pause_s),
        "--aspect", aspect,
        "--skip-confirm",
    ]
    if ref_image and ref_image.exists():
        cmd_flow.extend(["--ref-image", str(ref_image)])

    r = subprocess.run(cmd_flow, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not out_path.exists() or out_path.stat().st_size == 0:
        cmd_gem = [
            sys.executable, str(gemini_script),
            "--kind", "image",
            "--prompt", sanitize_image_prompt(prompt),
            "--name", out_path.stem,
            "--out-dir", str(out_path.parent),
            "--wait", str(wait_s),
        ]
        subprocess.run(cmd_gem, capture_output=True, text=True, encoding="utf-8", errors="replace")

    if not out_path.exists() or out_path.stat().st_size < 10000:
        raise RuntimeError(f"Falha ao gerar imagem {out_path.name}")
    tw, th = (1080, 1920) if aspect == "9:16" else (VIDEO_WIDTH, VIDEO_HEIGHT)
    fit_aspect_jpeg(out_path, out_path, tw, th)
    return out_path


def generate_images_for_plan(
    prompts_manifest: dict[str, dict[str, Any]],
    images_dir: Path,
    wait_s: int = 240,
    pause_s: float = 3.5,
    max_retries_collage: int = 2,
    force: bool = False,
    script_data: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Gera imagens 16:9 bloqueando colagens (rejeita se detect_split_collage > 1) e mantendo referencia de objetos/personagens."""
    images_dir.mkdir(parents=True, exist_ok=True)
    generated: dict[str, Path] = {}
    ensured_accounts: set[str] = set()
    anchor_prop_img: Path | None = None

    for img_id, pdata in prompts_manifest.items():
        dst = images_dir / f"{img_id}.jpg"
        if not force and dst.exists() and dst.stat().st_size > 15000 and detect_split_collage(dst) == 1:
            generated[img_id] = dst
            if anchor_prop_img is None and img_id.endswith("_p1"):
                anchor_prop_img = dst
            continue

        chars = tuple(pdata.get("characters") or ("Frida", "Luna"))
        refs: list[Path] = []
        base_p1 = images_dir / f"{img_id.rsplit('_p', 1)[0]}_p1.jpg"
        if not img_id.endswith("_p1") and base_p1.exists():
            refs.append(base_p1)
        elif anchor_prop_img is not None and anchor_prop_img.exists():
            refs.append(anchor_prop_img)

        full_prompt = f"{sanitize_image_prompt(pdata['positive'])}\nNegative prompt: {pdata['negative']}"
        for attempt in range(1, max_retries_collage + 1):
            try:
                generate_single_image(
                    full_prompt,
                    dst,
                    aspect="16:9",
                    wait_s=wait_s,
                    pause_s=pause_s,
                    characters=chars,
                    ref_images=tuple(refs),
                    script_data=script_data,
                    ensured_accounts=ensured_accounts,
                )
                panels = detect_split_collage(dst)
                if panels == 1:
                    generated[img_id] = dst
                    if anchor_prop_img is None:
                        anchor_prop_img = dst
                    print(f"  [IMG] {img_id}: OK (single full-frame)", flush=True)
                    break
                print(f"  [IMG] {img_id}: colagem detectada ({panels} paineis) na tentativa {attempt}, regenerando...", flush=True)
                dst.unlink(missing_ok=True)
            except Exception as exc:
                print(f"  [IMG] {img_id}: erro tentativa {attempt} -> {exc}", flush=True)

        if img_id not in generated:
            raise RuntimeError(f"Nao foi possivel gerar imagem limpa para '{img_id}'.")
    return generated


def select_veo_scenes(
    script_data: dict[str, Any],
    visual_clips: list[dict[str, Any]],
    target_count: int = TARGET_VEO_VIDEOS,
) -> list[dict[str, Any]]:
    """Seleciona N cenas (padrao 10 -> ~80s) distribuidas nos 3 atos para animacao 8s no Veo 3.1 Lite."""
    scenes = list(script_data.get("scenes") or [])
    if not scenes or target_count <= 0:
        return []
    if len(scenes) <= target_count:
        return scenes

    scene_durs: dict[str, float] = {}
    for c in (visual_clips or []):
        sid = c.get("scene_id")
        if sid:
            scene_durs[sid] = scene_durs.get(sid, 0.0) + float(c.get("duration") or 0.0)

    # Evita ultima cena se for apenas CTA final quando houver margem
    pool = scenes[:-1] if len(scenes) > target_count + 1 else scenes
    step = len(pool) / float(target_count)
    chosen: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for i in range(target_count):
        b_start = int(i * step)
        b_end = min(len(pool), max(b_start + 1, int(round((i + 1) * step))))
        cands = [s for s in pool[b_start:b_end] if s["scene_id"] not in used_ids]
        if not cands:
            cands = [s for s in pool if s["scene_id"] not in used_ids]
        if scene_durs and cands:
            sc = min(cands, key=lambda s: abs(scene_durs.get(s["scene_id"], 8.0) - 8.0))
        else:
            idx = min(len(pool) - 1, int(round(i * step + step * 0.35)))
            sc = pool[idx]
            if sc["scene_id"] in used_ids and cands:
                sc = cands[0]
        used_ids.add(sc["scene_id"])
        chosen.append(sc)
    return chosen


def _resolve_veo_ledger_path(videos_dir: Path, proj_dir: Path | None) -> Path:
    if proj_dir is not None:
        return proj_dir / "artifacts" / "veo_generation_ledger.json"
    return videos_dir.parent.parent / "artifacts" / "veo_generation_ledger.json"


def _load_veo_ledger(ledger_path: Path) -> dict[str, Any]:
    if ledger_path.exists():
        try:
            data = json.loads(ledger_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("scenes"), dict):
                return data
        except Exception:
            pass
    return {"schema": "VEO_LEDGER_V1", "scenes": {}}


def _save_veo_ledger(ledger_path: Path, data: dict[str, Any]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_single_veo_video(
    scene: dict[str, Any],
    images_dir: Path,
    videos_dir: Path,
    script_data: dict[str, Any],
    proj_dir: Path | None = None,
    fix_hint: str = "",
    force: bool = False,
    allow_extra_veo: bool = False,
    max_per_scene: int = MAX_VEO_GENERATIONS_PER_SCENE,
) -> dict[str, Any]:
    """Gera 1 video de 8s no Veo 3.1 Lite para uma cena especifica com failover, continuidade e ledger anti-loop."""
    import asyncio
    from core.flow_accounts import generate_video_with_failover
    from core.voice_studio import probe_duration

    videos_dir.mkdir(parents=True, exist_ok=True)
    sid = scene["scene_id"]
    out_mp4 = videos_dir / f"{sid}.mp4"
    if not force and out_mp4.exists() and out_mp4.stat().st_size > 100_000:
        return {"ok": True, "reused": True, "path": str(out_mp4), "account_id": "cache", "elapsed_s": 0.0}

    ledger_path = _resolve_veo_ledger_path(videos_dir, proj_dir)
    ledger = _load_veo_ledger(ledger_path)
    entries = ledger.setdefault("scenes", {}).setdefault(sid, [])
    prior_count = sum(1 for e in entries if isinstance(e, dict) and e.get("status") in ("dispatched", "downloaded"))
    archived_count = (
        len([p for p in (videos_dir / "_archive").glob(f"{sid}_*.mp4") if p.stat().st_size >= 50_000])
        if (videos_dir / "_archive").exists()
        else 0
    )
    extra_disk_count = len([p for p in videos_dir.glob(f"{sid}_v*.mp4") if p.stat().st_size >= 50_000])
    effective_prior = max(prior_count, archived_count + extra_disk_count)
    if (not allow_extra_veo) and effective_prior >= max(1, int(max_per_scene)):
        raise RuntimeError(
            f"[TRAVA-VEO-CENA] Cena {sid} ja atingiu o limite de {max_per_scene} geracao(oes) Veo paga(s) "
            f"(ledger={prior_count}, disco/arquivo={archived_count + extra_disk_count}); bloqueado para impedir loop de creditos."
        )

    sec_chars = script_data.get("secondary_characters") or []
    props = script_data.get("story_props") or []
    pinfo = build_image_prompt(scene, variant="main", secondary_characters=sec_chars, story_props=props)
    veo_prompt = (
        f"8-second continuous smooth 3D animated motion scene following the exact attached keyframe composition: "
        f"{pinfo['positive']} STRICT RULE: ZERO text, ZERO letters, ZERO words, ZERO banners, ZERO entrance arches or signs with writing, ZERO subtitles or UI buttons anywhere in frame."
    )
    if fix_hint:
        veo_prompt += f" STRICT CORRECTION: {fix_hint}"
    keyframe = images_dir / f"{sid}_p1.jpg"
    prop_names = [
        str(pr.get("name") or "").strip()
        for pr in props
        if isinstance(pr, dict) and pr.get("name")
        and (
            str(pr["name"]).lower() in f"{scene.get('text','')} {scene.get('visual_action','')}".lower()
            or any(
                tok in f"{scene.get('text','')} {scene.get('visual_action','')} {scene.get('location','')}".lower()
                for tok in re.findall(r"[a-z0-9áéíóúâêôãõç]{4,}", str(pr["name"]).lower())
            )
        )
    ]
    chars_list = list(scene.get("characters") or ["Frida", "Luna"])
    for pn in prop_names:
        if pn not in chars_list:
            chars_list.append(pn)
    chars = tuple(chars_list)

    entry: dict[str, Any] = {
        "ts": int(time.time()),
        "status": "dispatched",
        "prompt_sha1": hashlib.sha1(veo_prompt.encode("utf-8", errors="ignore")).hexdigest()[:12],
        "out_mp4": str(out_mp4),
    }
    entries.append(entry)
    _save_veo_ledger(ledger_path, ledger)

    try:
        res = asyncio.run(
            generate_video_with_failover(
                prompt=veo_prompt,
                out_mp4=out_mp4,
                characters=chars,
                keyframe_path=keyframe if keyframe.exists() else None,
                script_data=script_data,
                proj_dir=proj_dir,
            )
        )
        dur = probe_duration(out_mp4) if out_mp4.exists() else 0.0
        if not out_mp4.exists() or out_mp4.stat().st_size < 50_000 or dur < 2.0:
            raise RuntimeError(
                f"Arquivo Veo baixado invalido para {sid}: bytes={out_mp4.stat().st_size if out_mp4.exists() else 0}, dur={dur:.2f}s"
            )
        entry["status"] = "downloaded"
        entry["account_id"] = str((res or {}).get("account_id") or "")
        entry["bytes"] = out_mp4.stat().st_size
        entry["duration_s"] = round(dur, 2)
        _save_veo_ledger(ledger_path, ledger)
        return res
    except Exception as exc:
        err_low = str(exc).lower()
        pre_dispatch = any(
            tok in err_low
            for tok in (
                "offline", "deslogada", "nao encontrado no flow",
                "creditos insuficientes", "quota", "esgotaram",
                "nenhuma conta", "configurada",
            )
        )
        if pre_dispatch:
            entry["status"] = "pre_dispatch_error"
        entry["error"] = str(exc)[:180]
        _save_veo_ledger(ledger_path, ledger)
        if out_mp4.exists() and out_mp4.stat().st_size < 100_000:
            out_mp4.unlink(missing_ok=True)
        raise


def generate_veo_videos_for_episode(
    script_data: dict[str, Any],
    visual_clips: list[dict[str, Any]],
    images_dir: Path,
    videos_dir: Path,
    target_count: int = TARGET_VEO_VIDEOS,
    force: bool = False,
    proj_dir: Path | None = None,
) -> dict[str, Path]:
    """Gera ate target_count (10) videos de 8s no Veo 3.1 Lite com failover de contas e consistencia."""
    from core.flow_accounts import is_quota_error_text

    videos_dir.mkdir(parents=True, exist_ok=True)
    selected = select_veo_scenes(script_data, visual_clips, target_count=target_count)
    generated: dict[str, Path] = {}

    for idx, sc in enumerate(selected, 1):
        sid = sc["scene_id"]
        out_mp4 = videos_dir / f"{sid}.mp4"
        try:
            res = generate_single_veo_video(
                sc,
                images_dir=images_dir,
                videos_dir=videos_dir,
                script_data=script_data,
                proj_dir=proj_dir,
                force=force,
            )
            generated[sid] = out_mp4
            if res.get("reused"):
                print(f"  [VEO] {idx}/{len(selected)} {sid}: reutilizado ({out_mp4.name})", flush=True)
            else:
                print(
                    f"  [VEO] {idx}/{len(selected)} {sid}: OK via {res.get('account_id', '?')} "
                    f"({res.get('elapsed_s', '?')}s)",
                    flush=True,
                )
        except Exception as exc:
            err_low = str(exc).lower()
            print(f"  [VEO] {idx}/{len(selected)} {sid}: erro -> {exc}", flush=True)
            if is_quota_error_text(str(exc)) or "todas as contas flow" in err_low or "nenhuma conta google flow" in err_low:
                break
            continue

    return generated


def _load_bold_font(size: int):
    for p in (
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
    ):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def generate_thumbnail_variants(
    hero_image: Path,
    out_dir: Path,
    hook_words: str = "ELAS FALARAM?!",
) -> list[Path]:
    """Gera 3 miniaturas 1280x720 de alto CTR prontas para Teste A/B do YouTube."""
    out_dir.mkdir(parents=True, exist_ok=True)
    base = ImageOps.fit(Image.open(hero_image).convert("RGB"), (THUMB_WIDTH, THUMB_HEIGHT), method=Image.Resampling.LANCZOS)
    vibrant = ImageEnhance.Color(base).enhance(1.32)
    vibrant = ImageEnhance.Contrast(vibrant).enhance(1.18)
    vibrant = ImageEnhance.Sharpness(vibrant).enhance(1.25)

    # A) Limpa (Pixar look sem texto — otima para teste A/B infantil)
    p_a = out_dir / "thumb_A_clean.jpg"
    vibrant.save(p_a, format="JPEG", quality=94)

    # B) Hook gigante de 2-3 palavras no topo/canto inferior com sombra pesada
    img_b = vibrant.copy().convert("RGBA")
    grad = Image.new("RGBA", (THUMB_WIDTH, THUMB_HEIGHT), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grad)
    gdraw.rectangle([0, int(THUMB_HEIGHT * 0.68), THUMB_WIDTH, THUMB_HEIGHT], fill=(0, 0, 0, 145))
    img_b = Image.alpha_composite(img_b, grad).convert("RGB")
    draw_b = ImageDraw.Draw(img_b)
    font_big = _load_bold_font(112)
    text = " ".join((hook_words or "ELAS FALARAM?!").upper().split()[:4])
    cx, cy = THUMB_WIDTH // 2, int(THUMB_HEIGHT * 0.84)
    for dx in range(-6, 7, 2):
        for dy in range(-6, 7, 2):
            draw_b.text((cx + dx, cy + dy), text, font=font_big, fill=(15, 10, 5), anchor="mm")
    draw_b.text((cx, cy), text, font=font_big, fill=(255, 224, 50), anchor="mm")
    p_b = out_dir / "thumb_B_hook.jpg"
    img_b.save(p_b, format="JPEG", quality=94)

    # C) Selo superior de alto contraste ("NOVO EPISODIO" + borda dourada luminosa)
    img_c = vibrant.copy()
    draw_c = ImageDraw.Draw(img_c)
    draw_c.rounded_rectangle([46, 36, 420, 112], radius=22, fill=(225, 38, 45), outline=(255, 255, 255), width=4)
    font_tag = _load_bold_font(40)
    draw_c.text((233, 74), "REACAO AO VIVO!", font=font_tag, fill=(255, 255, 255), anchor="mm")
    draw_c.rectangle([0, 0, THUMB_WIDTH - 1, THUMB_HEIGHT - 1], outline=(255, 212, 55), width=10)
    p_c = out_dir / "thumb_C_badge.jpg"
    img_c.save(p_c, format="JPEG", quality=94)

    return [p_a, p_b, p_c]
