# -*- coding: utf-8 -*-
"""Estudio de Avatares Dual-PiP (Frida & Luna) com sincronizacao de boca em 3 niveis."""
from __future__ import annotations

import asyncio
import math
import random
import subprocess
import time
import wave
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from config import AVATAR_PROFILES, FFMPEG_EXE, FRIDA_LUNA_REF_SHEET, VENDOR_DIR, VIDEO_FPS, get_avatar_clips

_BANK_CACHE: dict[str, dict[str, Any]] = {}


def _compute_speech_levels(
    wav_path: Path,
    fps: int,
    n_frames: int,
    threshold: float = 0.015,
    silence_ms: int = 450,
) -> list[int]:
    """Calcula nivel por frame: 0=silencio (reposo), 1=fala suave, 2=fala forte/aberta."""
    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if nch > 1:
        samples = samples.reshape(-1, nch).mean(axis=1)

    step = max(1, int(sr / fps))
    hold = max(1, math.ceil((silence_ms / 1000.0) * fps))

    rms_vals: list[float] = []
    for f in range(n_frames):
        a = f * step
        b = min(len(samples), a + step)
        rms = float(np.sqrt(np.mean(samples[a:b] ** 2))) if b > a else 0.0
        rms_vals.append(rms)

    ativos = [r for r in rms_vals if r > threshold]
    strong_thr = float(np.percentile(ativos, 58)) if ativos else 0.06

    levels: list[int] = []
    silent_cnt = hold + 1
    for rms in rms_vals:
        if rms > threshold:
            silent_cnt = 0
            levels.append(2 if rms >= strong_thr else 1)
        else:
            silent_cnt += 1
            levels.append(1 if silent_cnt <= hold else 0)
    return levels


def _estimate_head_center_ratio(frames: list[np.ndarray]) -> float:
    """Estima o centro horizontal da cabeca para alinhar varios clipes do mesmo avatar."""
    if not frames:
        return 0.5
    idxs = [min(len(frames) - 1, int(len(frames) * r)) for r in (0.15, 0.5, 0.85)]
    cxs: list[float] = []
    for idx in idxs:
        fr = frames[idx]
        h, w = fr.shape[:2]
        band = cv2.cvtColor(fr[int(h * 0.22):int(h * 0.65), :], cv2.COLOR_BGR2GRAY)
        gx = np.abs(cv2.Sobel(band, cv2.CV_32F, 1, 0, ksize=3))
        col_energy = gx.mean(axis=0)
        xs = np.arange(w, dtype=np.float32)
        # Foca nos 60% centrais para ignorar cortina/luminaria da borda
        win = (xs >= w * 0.18) & (xs <= w * 0.82)
        weights = np.maximum(0.0, col_energy - np.percentile(col_energy, 35)) * win
        total = float(weights.sum())
        if total > 1e-3:
            cxs.append(float((xs * weights).sum() / total) / w)
    return float(np.median(cxs)) if cxs else 0.5


def _prepare_aligned_square(
    frame: np.ndarray,
    out_size: int = 420,
    y_top_ratio: float = 0.20,
    y_bot_ratio: float = 0.84,
    cx_ratio: float = 0.5,
    luma_gain: float = 1.0,
) -> np.ndarray:
    """Recorta e alinha a cabeca do avatar em um quadrado nitido com laterais suavizadas."""
    h, w = frame.shape[:2]
    y1 = max(0, min(h - 10, int(round(h * y_top_ratio))))
    y2 = max(y1 + 10, min(h, int(round(h * y_bot_ratio))))
    band = frame[y1:y2, 0:w]
    bh, bw = band.shape[:2]

    crop_w = min(bw, int(round(bh * 0.92)))
    cx = int(round(cx_ratio * bw))
    x1 = max(0, min(bw - crop_w, cx - crop_w // 2))
    focused = band[:, x1:x1 + crop_w]

    if abs(luma_gain - 1.0) > 0.02:
        focused = np.clip(focused.astype(np.float32) * luma_gain, 0, 255).astype(np.uint8)

    bg = cv2.GaussianBlur(cv2.resize(focused, (out_size, out_size), interpolation=cv2.INTER_AREA), (0, 0), sigmaX=out_size * 0.045)
    fh, fw = focused.shape[:2]
    scale = out_size / fh
    new_w = min(out_size, int(round(fw * scale)))
    fg = cv2.resize(focused, (new_w, out_size), interpolation=cv2.INTER_AREA)
    xoff = max(0, (out_size - new_w) // 2)

    feather = max(8, int(new_w * 0.09))
    alpha = np.ones(new_w, dtype=np.float32)
    ramp = np.linspace(0.0, 1.0, feather, dtype=np.float32)
    alpha[:feather] = ramp
    alpha[-feather:] = ramp[::-1]
    a = alpha[None, :, None]
    roi = bg[:, xoff:xoff + new_w].astype(np.float32)
    bg[:, xoff:xoff + new_w] = np.clip(roi * (1.0 - a) + fg.astype(np.float32) * a, 0, 255).astype(np.uint8)
    return bg


def _load_aligned_frames(
    video_path: Path,
    y_top: float,
    y_bot: float,
    base_size: int = 420,
    target_luma: float | None = None,
) -> tuple[list[np.ndarray], float]:
    cap = cv2.VideoCapture(str(video_path))
    raw: list[np.ndarray] = []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        raw.append(fr)
    cap.release()
    if not raw:
        return [], 104.0

    cx_ratio = _estimate_head_center_ratio(raw)
    sample_luma = float(np.mean([cv2.cvtColor(raw[i], cv2.COLOR_BGR2GRAY).mean() for i in range(0, len(raw), max(1, len(raw) // 6))]))
    gain = 1.0 if target_luma is None else float(np.clip(target_luma / max(20.0, sample_luma), 0.88, 1.14))
    aligned = [_prepare_aligned_square(fr, base_size, y_top, y_bot, cx_ratio, gain) for fr in raw]
    return aligned, sample_luma


def _index_character_bank(character: str) -> dict[str, Any] | None:
    """Carrega reposo.mp4 + hablando_*.mp4 com alinhamento de cabeca e indexacao da boca."""
    key = character.lower()
    if key in _BANK_CACHE:
        return _BANK_CACHE[key]

    clips = get_avatar_clips(key)
    rep_path = clips.get("reposo")
    hab_paths = clips.get("hablando", [])
    if not rep_path or not hab_paths:
        return None

    y_top, y_bot = (0.18, 0.82) if key == "luna" else (0.25, 0.98)
    rep_frames, target_luma = _load_aligned_frames(rep_path, y_top, y_bot)
    if not rep_frames:
        return None

    s = rep_frames[0].shape[0]
    y1, y2 = int(s * 0.38), int(s * 0.72)
    x1, x2 = int(s * 0.28), int(s * 0.72)
    mouth_base = cv2.cvtColor(rep_frames[0][y1:y2, x1:x2], cv2.COLOR_BGR2GRAY).astype(np.float32)

    hab_bank = []
    for p in hab_paths:
        frames, _ = _load_aligned_frames(p, y_top, y_bot, target_luma=target_luma)
        if len(frames) < 12:
            continue
        scores: list[float] = []
        for fr in frames:
            roi = cv2.cvtColor(fr[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY).astype(np.float32)
            diff = float(np.mean(np.abs(roi - mouth_base)))
            dark = float(np.mean(roi < 55)) * 40.0
            scores.append(diff + dark)
        p55 = float(np.percentile(scores, 55))
        peak_starts = [i for i, sc in enumerate(scores[:-12]) if sc >= p55] or [4]
        hab_bank.append({"name": p.name, "frames": frames, "scores": scores, "peak_starts": peak_starts})

    if not hab_bank:
        return None

    bank = {"reposo": rep_frames, "hablando": hab_bank}
    _BANK_CACHE[key] = bank
    return bank


def _make_card_mask(size: int) -> dict[str, Any]:
    """Mascara arredondada com contorno 2px + anel duplo + sombra projetada suave."""
    margin = max(12, int(size * 0.025))
    r = max(32, int(size * 0.10))
    x0, y0, x1, y1 = margin, margin, size - margin, size - margin
    card = np.zeros((size, size), np.uint8)
    cv2.rectangle(card, (x0 + r, y0), (x1 - r, y1), 255, -1)
    cv2.rectangle(card, (x0, y0 + r), (x1, y1 - r), 255, -1)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        cv2.circle(card, (cx, cy), r, 255, -1)

    erode6 = cv2.erode(card, np.ones((6, 6), np.uint8), iterations=1)
    erode8 = cv2.erode(card, np.ones((8, 8), np.uint8), iterations=1)
    outline = cv2.subtract(cv2.dilate(card, np.ones((3, 3), np.uint8), iterations=1), card)

    sh = np.zeros((size, size), np.uint8)
    sx, sy = 7, 10
    cv2.rectangle(sh, (min(size - 1, x0 + r + sx), min(size - 1, y0 + sy)), (min(size - 1, x1 - r + sx), min(size - 1, y1 + sy)), 255, -1)
    cv2.rectangle(sh, (min(size - 1, x0 + sx), min(size - 1, y0 + r + sy)), (min(size - 1, x1 + sx), min(size - 1, y1 - r + sy)), 255, -1)
    for cx, cy in ((x0 + r + sx, y0 + r + sy), (x1 - r + sx, y0 + r + sy), (x0 + r + sx, y1 - r + sy), (x1 - r + sx, y1 - r + sy)):
        cv2.circle(sh, (min(size - 1, cx), min(size - 1, cy)), r, 255, -1)
    sh = cv2.GaussianBlur(sh, (25, 25), 0)
    sh = (sh.astype(np.float32) * 0.52).astype(np.uint8)
    sh[card > 0] = 0

    base_mask = np.maximum(np.maximum(card, sh), outline)
    return {
        "outer_border": cv2.subtract(card, erode6),
        "inner_border": cv2.subtract(erode6, erode8),
        "inner": erode8,
        "outline": outline,
        "alpha": base_mask,
        "margin": margin,
    }


def detect_emptiest_corners(image_path: Path) -> list[str]:
    """Mede densidade visual dos 4 cantos da imagem e ordena do mais vazio ao mais cheio."""
    im = cv2.imread(str(image_path))
    if im is None:
        return ["BL", "BR", "TL", "TR"]
    h, w = im.shape[:2]
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(np.float32)
    edges = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(gray, cv2.CV_32F, 0, 1))

    cw, ch = int(w * 0.26), int(h * 0.34)
    boxes = {
        "TL": (0, 0, cw, ch),
        "TR": (w - cw, 0, w, ch),
        "BL": (0, h - ch, cw, h),
        "BR": (w - cw, h - ch, w, h),
    }
    scored = []
    for name, (x0, y0, x1, y1) in boxes.items():
        e_score = float(edges[y0:y1, x0:x1].mean())
        sat_score = float(hsv[y0:y1, x0:x1, 1].mean()) * 0.15
        # Leve preferencia por cantos inferiores (BL/BR) para fluxo natural de leitura
        bias = 0.0 if name.startswith("B") else 4.0
        scored.append((e_score + sat_score + bias, name))
    scored.sort(key=lambda t: t[0])
    return [name for _, name in scored]


def render_avatar_pip_clip(
    scene_id: str,
    character: str,
    wav_path: Path,
    dur: float,
    out_mov: Path,
    card_size: int = 290,
    is_active_speaker: bool = True,
) -> Path | None:
    """Renderiza card RGBA (.mov qtrle) continuo com alinhamento e crossfade suave por transparencia."""
    char = character.lower()
    bank = _index_character_bank(char)
    if not bank:
        return None

    prof = AVATAR_PROFILES[char]
    n_frames = max(1, int(round(dur * VIDEO_FPS)))
    levels = _compute_speech_levels(wav_path, VIDEO_FPS, n_frames) if is_active_speaker else [0] * n_frames
    assets = _make_card_mask(card_size)

    tmp_rgb = out_mov.with_suffix(".rgb.mp4")
    tmp_msk = out_mov.with_suffix(".msk.mp4")
    out_mov.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw_rgb = cv2.VideoWriter(str(tmp_rgb), fourcc, VIDEO_FPS, (card_size, card_size))
    vw_msk = cv2.VideoWriter(str(tmp_msk), fourcc, VIDEO_FPS, (card_size, card_size))

    rng = random.Random(abs(hash(f"{scene_id}_{char}")) % (2 ** 31))
    rep_frames = bank["reposo"]
    hab_bank = bank["hablando"]

    cur_vid_idx = rng.randrange(len(hab_bank))
    cur_vid = hab_bank[cur_vid_idx]
    idx_rep = rng.randint(0, max(0, len(rep_frames) - 1))
    idx_hab = rng.choice(cur_vid["peak_starts"])
    was_talking = False

    # Crossfade gradual (9 frames ~ 0.30s) sempre que trocar reposo <-> falando ou mudar de clipe
    crossfade_len = 9
    blend_rem = 0
    prev_sq: np.ndarray | None = None

    fade_n = max(1, int(0.24 * VIDEO_FPS))
    opacity_scale = 1.0 if is_active_speaker else 0.88
    inner_sz = card_size - 2 * assets["margin"]

    def _pick_next_hab_clip(prefer_peak: bool = False) -> None:
        nonlocal cur_vid_idx, cur_vid, idx_hab, blend_rem
        if len(hab_bank) > 1:
            cands = [k for k in range(len(hab_bank)) if k != cur_vid_idx]
            cur_vid_idx = rng.choice(cands)
        cur_vid = hab_bank[cur_vid_idx]
        if prefer_peak and cur_vid["peak_starts"]:
            idx_hab = rng.choice(cur_vid["peak_starts"])
        else:
            max_start = max(4, len(cur_vid["frames"]) - 24)
            idx_hab = rng.randint(4, max_start)
        blend_rem = crossfade_len

    for i, lv in enumerate(levels):
        if lv == 0:
            if was_talking:
                blend_rem = crossfade_len
            raw_sq = rep_frames[idx_rep % len(rep_frames)]
            idx_rep += 1
            was_talking = False
        else:
            if not was_talking:
                _pick_next_hab_clip(prefer_peak=(lv == 2))
            else:
                idx_hab += 1
                # Antes de atingir o fim do clipe falando (~8s), dissolve suavemente para outro clipe!
                if idx_hab >= len(cur_vid["frames"]) - 6:
                    _pick_next_hab_clip(prefer_peak=(lv == 2))
            raw_sq = cur_vid["frames"][idx_hab % len(cur_vid["frames"])]
            was_talking = True

        sq = cv2.resize(raw_sq, (inner_sz, inner_sz), interpolation=cv2.INTER_AREA)
        if blend_rem > 0 and prev_sq is not None:
            alpha_w = (crossfade_len - blend_rem + 1) / float(crossfade_len + 1)
            sq = cv2.addWeighted(sq, alpha_w, prev_sq, 1.0 - alpha_w, 0)
            blend_rem -= 1
        prev_sq = sq

        canvas = np.zeros((card_size, card_size, 3), np.uint8)
        av_pad = np.zeros_like(canvas)
        av_pad[assets["margin"]:card_size - assets["margin"], assets["margin"]:card_size - assets["margin"]] = sq

        canvas[assets["inner"] > 0] = av_pad[assets["inner"] > 0]
        canvas[assets["outer_border"] > 0] = prof["border_gold_bgr"] if is_active_speaker else (140, 140, 140)
        canvas[assets["inner_border"] > 0] = prof["border_accent_bgr"]
        canvas[assets["outline"] > 0] = (24, 30, 40)

        factor = opacity_scale
        if i < fade_n:
            factor *= (i + 1) / fade_n
        elif i >= n_frames - fade_n:
            factor *= max(0.0, (n_frames - i) / fade_n)
        msk = (assets["alpha"].astype(np.float32) * factor).astype(np.uint8)

        vw_rgb.write(canvas)
        vw_msk.write(cv2.cvtColor(msk, cv2.COLOR_GRAY2BGR))

    vw_rgb.release()
    vw_msk.release()

    subprocess.run(
        [FFMPEG_EXE, "-y", "-v", "error", "-i", str(tmp_rgb), "-i", str(tmp_msk),
         "-filter_complex", "[0:v][1:v]alphamerge,format=rgba[out]",
         "-map", "[out]", "-c:v", "qtrle", "-r", str(VIDEO_FPS), str(out_mov)],
        check=True,
    )
    tmp_rgb.unlink(missing_ok=True)
    tmp_msk.unlink(missing_ok=True)
    return out_mov


def render_magic_sparkles_overlay(duration: float, out_mov: Path, width: int = 1920, height: int = 1080) -> Path:
    """Gera overlay leve RGBA de particulas douradas sutis para cenas magicas de gancho."""
    n_frames = max(1, int(round(duration * VIDEO_FPS)))
    tmp_rgb = out_mov.with_suffix(".sp_rgb.mp4")
    tmp_msk = out_mov.with_suffix(".sp_msk.mp4")
    out_mov.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw_rgb = cv2.VideoWriter(str(tmp_rgb), fourcc, VIDEO_FPS, (width, height))
    vw_msk = cv2.VideoWriter(str(tmp_msk), fourcc, VIDEO_FPS, (width, height))

    rng = random.Random(42)
    parts = [
        {
            "x": rng.uniform(0.08 * width, 0.92 * width),
            "y": rng.uniform(0.08 * height, 0.85 * height),
            "vy": rng.uniform(-32.0, -12.0),
            "vx": rng.uniform(-10.0, 10.0),
            "r": rng.randint(3, 7),
            "phase": rng.uniform(0, math.tau),
        }
        for _ in range(28)
    ]

    for i in range(n_frames):
        t = i / VIDEO_FPS
        rgb = np.zeros((height, width, 3), np.uint8)
        msk = np.zeros((height, width), np.uint8)
        for p in parts:
            px = int((p["x"] + p["vx"] * t + 14 * math.sin(t * 1.4 + p["phase"])) % width)
            py = int((p["y"] + p["vy"] * t) % height)
            pulse = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * 3.0 + p["phase"]))
            cv2.circle(rgb, (px, py), p["r"], (110, 225, 255), -1)
            cv2.circle(msk, (px, py), p["r"] + 2, int(190 * pulse), -1)
        msk = cv2.GaussianBlur(msk, (9, 9), 0)
        vw_rgb.write(rgb)
        vw_msk.write(cv2.cvtColor(msk, cv2.COLOR_GRAY2BGR))

    vw_rgb.release()
    vw_msk.release()
    subprocess.run(
        [FFMPEG_EXE, "-y", "-v", "error", "-i", str(tmp_rgb), "-i", str(tmp_msk),
         "-filter_complex", "[0:v][1:v]alphamerge,format=rgba[out]",
         "-map", "[out]", "-c:v", "qtrle", "-r", str(VIDEO_FPS), str(out_mov)],
        check=True,
    )
    tmp_rgb.unlink(missing_ok=True)
    tmp_msk.unlink(missing_ok=True)
    return out_mov


def generate_flow_video_clip(
    prompt: str,
    ref_image: Path | None,
    save_mp4: Path,
    flow_project_url: str = "https://flow.google.com/project/2700c141-d4ed-4bd2-9f7a-2f82cffa8083",
    cdp_url: str = "http://127.0.0.1:18800",
    wait_s: int = 360,
    ref_image_aria: str = "",
) -> Path:
    """Gera 1 clipe de video (~8s) via Google Flow (Veo 3.1 - Lite, x1, 10 creditos)."""
    from core.flow_continuity import generate_flow_video
    from playwright.async_api import async_playwright

    async def _run():
        async with async_playwright() as pw:
            b = await pw.chromium.connect_over_cdp(cdp_url, timeout=10000)
            ctx = b.contexts[0]
            page = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or await ctx.new_page()
            if flow_project_url not in page.url:
                await page.goto(flow_project_url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(2000)
            refs = (ref_image_aria,) if ref_image_aria else ()
            await generate_flow_video(page, prompt, save_mp4, ref_images=refs, wait_s=wait_s)
            await b.close()
        return save_mp4

    return asyncio.run(_run())


def build_luna_avatar_pack(out_dir: Path | None = None, base_image: Path | None = None) -> dict[str, Path]:
    """Cria a imagem base da Luna no estudio da Frida e os 4 clipes (reposo + 3 hablando) no Flow."""
    from core.media_studio import generate_single_image

    target_dir = out_dir or AVATAR_PROFILES["luna"]["dir"]
    target_dir.mkdir(parents=True, exist_ok=True)

    if base_image is None:
        base_image = target_dir / "luna_studio_base.jpg"
    if not base_image.exists():
        base_prompt = (
            "Single vertical 9:16 3D family animated movie portrait matching studio streaming webcam framing. "
            "LUNA: miniature smooth-haired dachshund (sausage dog), dark chocolate-brown glossy coat with warm tan markings "
            "on muzzle, eyebrows, chest and paws, elongated cute body, short front legs, long floppy ears, "
            "big expressive brown eyes with eyelashes, small pearl ear stud, delicate double golden chain necklace with tiny heart pendants. "
            "Luna is sitting upright front-facing centered at eye-level, calm closed-mouth gentle smile looking directly at camera. "
            "Background: cozy warm living room with soft beige curtain on left and softly blurred warm table lamp on right, matching soft studio lighting. "
            "No text, no split screen, no humans, no extra dogs."
        )
        generate_single_image(
            prompt=base_prompt,
            out_path=base_image,
            aspect="9:16",
            ref_image=FRIDA_LUNA_REF_SHEET if FRIDA_LUNA_REF_SHEET.exists() else None,
        )

    prompts = {
        "reposo.mp4": (
            "Smooth continuous idle animation of this exact dark brown dachshund dog sitting in front of camera: "
            "gentle chest breathing, natural eye blinking every 2 seconds, subtle curious head tilt, mouth stays closed calmly. Keep exact background and framing."
        ),
        "hablando_1.mp4": (
            "Continuous lively talking animation of this exact dark brown dachshund dog: "
            "mouth opening and closing nonstop as if excitedly talking in a podcast, expressive ears bouncing slightly, raising right front paw gesturing happily. Keep exact studio framing."
        ),
        "hablando_2.mp4": (
            "Continuous expressive storytelling talking animation of this exact dark brown dachshund dog: "
            "continuous animated jaw and lips speaking nonstop with joyful surprise, wide bright eyes, gentle nodding and paw gestures. Keep exact studio background."
        ),
        "hablando_3.mp4": (
            "Continuous dramatic energetic talking animation of this exact dark brown dachshund dog: "
            "mouth actively speaking continuously without stopping, playful eyebrow expressions, expressive small head turns and paw movements. Keep exact lighting and camera."
        ),
    }

    created = {"base": base_image}
    for fname, pr in prompts.items():
        dst = target_dir / fname
        if not dst.exists() or dst.stat().st_size < 10000:
            generate_flow_video_clip(pr, base_image, dst)
        created[fname] = dst
    return created
