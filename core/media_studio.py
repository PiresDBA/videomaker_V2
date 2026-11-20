# -*- coding: utf-8 -*-
"""Prompts travados na Biblia Visual, geracao 16:9 sem colagens e 3 Thumbnails CTR."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from config import (
    NEGATIVE_IMAGE_RULE,
    POSITIVE_IMAGE_RULE,
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
    max_chars: int = 2200,
) -> dict[str, str]:
    """Gera prompt positivo e negativo travados na Biblia Visual e na localizacao da cena."""
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

    positive_parts = [
        POSITIVE_IMAGE_RULE,
        f"Environment strictly locked to: {location}",
        f"Action: {action}",
        focus_hint,
        f"Camera framing: {cam_note}",
        f"Character Bible: {VISUAL_BIBLE['frida']}; {VISUAL_BIBLE['luna']}",
        f"Style: {VISUAL_BIBLE['style']}",
    ]
    positive = ". ".join(p.strip().rstrip(".") for p in positive_parts if p and p.strip()) + "."
    if len(positive) > max_chars:
        positive = positive[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;.") + "."

    return {
        "positive": positive,
        "negative": NEGATIVE_IMAGE_RULE,
        "combined": f"{positive}\nNegative prompt: {NEGATIVE_IMAGE_RULE}",
    }


def generate_prompts_for_script(
    script_data: dict[str, Any],
    out_path: Path | None = None,
) -> dict[str, dict[str, str]]:
    """Cria o manifesto inicial de prompts (1 prompt base por cena)."""
    prompts: dict[str, dict[str, str]] = {}
    for sc in script_data.get("scenes", []):
        sid = sc["scene_id"]
        prompts[f"{sid}_p1"] = build_image_prompt(sc, variant="main")
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


def generate_single_image(
    prompt: str,
    out_path: Path,
    aspect: str = "16:9",
    ref_image: Path | None = None,
    wait_s: int = 240,
    pause_s: float = 3.0,
) -> Path:
    """Gera uma unica imagem via Flow (CDP direto Nov-2026 ou flow_fetch) com fallback para Gemini Web."""
    flow_script = VENDOR_DIR / "flow_fetch.py"
    gemini_script = VENDOR_DIR / "gemini_fetch.py"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Caminho preferencial: motor direto core.flow_continuity (Nano Banana 2.1, x1, 0 creditos) quando CDP estiver vivo
    try:
        import asyncio, urllib.request
        from core.flow_continuity import DEFAULT_CDP_URL, DEFAULT_FLOW_PROJECT_URL, generate_flow_image
        from playwright.async_api import async_playwright

        with urllib.request.urlopen(f"{DEFAULT_CDP_URL}/json/version", timeout=2):
            pass

        async def _run_direct():
            async with async_playwright() as pw:
                b = await pw.chromium.connect_over_cdp(DEFAULT_CDP_URL, timeout=10000)
                ctx = b.contexts[0]
                pg = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or await ctx.new_page()
                if "flow.google.com/project/" not in pg.url:
                    await pg.goto(DEFAULT_FLOW_PROJECT_URL, wait_until="domcontentloaded", timeout=30000)
                    await pg.wait_for_timeout(2000)
                await generate_flow_image(pg, sanitize_image_prompt(prompt), out_path, wait_s=min(wait_s, 180))
                await b.close()

        asyncio.run(_run_direct())
        if out_path.exists() and out_path.stat().st_size >= 10000:
            tw, th = (1080, 1920) if aspect == "9:16" else (VIDEO_WIDTH, VIDEO_HEIGHT)
            fit_aspect_jpeg(out_path, out_path, tw, th)
            return out_path
    except Exception:
        pass

    cmd_flow = [
        sys.executable, str(flow_script),
        "--kind", "image",
        "--characters", "",
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
    prompts_manifest: dict[str, dict[str, str]],
    images_dir: Path,
    wait_s: int = 240,
    pause_s: float = 3.5,
    max_retries_collage: int = 2,
    force: bool = False,
) -> dict[str, Path]:
    """Gera imagens 16:9 bloqueando colagens (rejeita se detect_split_collage > 1)."""
    images_dir.mkdir(parents=True, exist_ok=True)
    generated: dict[str, Path] = {}

    for img_id, pdata in prompts_manifest.items():
        dst = images_dir / f"{img_id}.jpg"
        if not force and dst.exists() and dst.stat().st_size > 15000 and detect_split_collage(dst) == 1:
            generated[img_id] = dst
            continue

        full_prompt = f"{sanitize_image_prompt(pdata['positive'])}\nNegative prompt: {pdata['negative']}"
        for attempt in range(1, max_retries_collage + 1):
            try:
                generate_single_image(full_prompt, dst, aspect="16:9", wait_s=wait_s, pause_s=pause_s)
                panels = detect_split_collage(dst)
                if panels == 1:
                    generated[img_id] = dst
                    print(f"  [IMG] {img_id}: OK (single full-frame)", flush=True)
                    break
                print(f"  [IMG] {img_id}: colagem detectada ({panels} paineis) na tentativa {attempt}, regenerando...", flush=True)
                dst.unlink(missing_ok=True)
            except Exception as exc:
                print(f"  [IMG] {img_id}: erro tentativa {attempt} -> {exc}", flush=True)

        if img_id not in generated:
            raise RuntimeError(f"Nao foi possivel gerar imagem limpa para '{img_id}'.")
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
