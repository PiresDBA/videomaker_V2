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


def _index_character_bank(character: str) -> dict[str, Any] | None:
    """Carrega reposo.mp4 e indexa frames de hablando_*.mp4 em nivel 1 e nivel 2 (receita v3)."""
    key = character.lower()
    if key in _BANK_CACHE:
        return _BANK_CACHE[key]

    clips = get_avatar_clips(key)
    rep_path = clips.get("reposo")
    hab_paths = clips.get("hablando", [])
    if not rep_path or not hab_paths:
        return None

    cap_rep = cv2.VideoCapture(str(rep_path))
    rep_frames: list[np.ndarray] = []
    while True:
        ok, fr = cap_rep.read()
        if not ok:
            break
        rep_frames.append(fr)
    cap_rep.release()
    if not rep_frames:
        return None

    h, w, _ = rep_frames[0].shape
    y1, y2 = int(h * 0.42), int(h * 0.68)
    x1, x2 = int(w * 0.30), int(w * 0.70)
    mouth_base = cv2.cvtColor(rep_frames[0][y1:y2, x1:x2], cv2.COLOR_BGR2GRAY).astype(np.float32)

    hab_bank = []
    for p in hab_paths:
        cap = cv2.VideoCapture(str(p))
        frames: list[np.ndarray] = []
        scores: list[float] = []
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            frames.append(fr)
            roi = cv2.cvtColor(fr[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY).astype(np.float32)
            diff = float(np.mean(np.abs(roi - mouth_base)))
            dark = float(np.mean(roi < 55)) * 40.0
            scores.append(diff + dark)
        cap.release()
        if not frames:
            continue
        p20 = float(np.percentile(scores, 20))
        p60 = float(np.percentile(scores, 60))
        n1 = [i for i, s in enumerate(scores) if p20 <= s < p60] or list(range(len(frames)))
        n2 = [i for i, s in enumerate(scores) if s >= p60] or n1
        hab_bank.append({"name": p.name, "frames": frames, "nivel1": n1, "nivel2": n2})

    if not hab_bank:
        return None

    bank = {"reposo": rep_frames, "hablando": hab_bank}
    _BANK_CACHE[key] = bank
    return bank


def _prepare_square_frame(frame: np.ndarray, size: int) -> np.ndarray:
    h, w, _ = frame.shape
    band = frame[int(h * 0.25):h, 0:w]
    bh, bw, _ = band.shape
    bg = cv2.GaussianBlur(cv2.resize(band, (size, size), interpolation=cv2.INTER_AREA), (0, 0), sigmaX=size * 0.04)
    new_w = int(round(bw * (size / bh)))
    fg = cv2.resize(band, (new_w, size), interpolation=cv2.INTER_AREA)
    xoff = max(0, (size - new_w) // 2)
    fit_w = min(new_w, size - xoff)
    feather = max(8, int(fit_w * 0.09))
    alpha = np.ones(fit_w, dtype=np.float32)
    ramp = np.linspace(0.0, 1.0, feather, dtype=np.float32)
    alpha[:feather] = ramp
    alpha[-feather:] = ramp[::-1]
    a = alpha[None, :, None]
    roi = bg[:, xoff:xoff + fit_w].astype(np.float32)
    bg[:, xoff:xoff + fit_w] = np.clip(roi * (1.0 - a) + fg[:, :fit_w].astype(np.float32) * a, 0, 255).astype(np.uint8)
    return bg


def _make_card_mask(size: int) -> dict[str, Any]:
    margin = max(10, int(size * 0.02))
    r = max(30, int(size * 0.12))
    x0, y0, x1, y1 = margin, margin, size - margin, size - margin
    card = np.zeros((size, size), np.uint8)
    cv2.rectangle(card, (x0 + r, y0), (x1 - r, y1), 255, -1)
    cv2.rectangle(card, (x0, y0 + r), (x1, y1 - r), 255, -1)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        cv2.circle(card, (cx, cy), r, 255, -1)
    erode6 = cv2.erode(card, np.ones((6, 6), np.uint8), iterations=1)
    erode8 = cv2.erode(card, np.ones((8, 8), np.uint8), iterations=1)
    return {
        "outer_border": cv2.subtract(card, erode6),
        "inner_border": cv2.subtract(erode6, erode8),
        "inner": erode8,
        "alpha": card,
        "margin": margin,
    }


def render_avatar_pip_clip(
    scene_id: str,
    character: str,
    wav_path: Path,
    dur: float,
    out_mov: Path,
    card_size: int = 290,
    is_active_speaker: bool = True,
) -> Path | None:
    """Renderiza card RGBA (.mov qtrle) para 'frida' ou 'luna' com boca em 3 niveis."""
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
    cur_vid = rng.choice(hab_bank)
    idx_rep = rng.randint(0, len(rep_frames) - 1)
    idx_hab = 0
    was_talking = False
    fade_n = max(1, int(0.22 * VIDEO_FPS))
    opacity_scale = 1.0 if is_active_speaker else 0.86

    for i, lv in enumerate(levels):
        if lv == 0:
            if was_talking:
                cur_vid = rng.choice(hab_bank)
            frm = rep_frames[idx_rep % len(rep_frames)]
            idx_rep += 1
            was_talking = False
        else:
            was_talking = True
            pool = cur_vid["nivel2"] if lv == 2 else cur_vid["nivel1"]
            # Avanca continuamente pelo pool correspondente ao volume da fala para a boca nunca travar
            idx_hab += 1
            f_idx = pool[idx_hab % len(pool)]
            frm = cur_vid["frames"][f_idx]

        sq = _prepare_square_frame(frm, card_size)
        canvas = np.zeros((card_size, card_size, 3), np.uint8)
        inner_sz = card_size - 2 * assets["margin"]
        av = cv2.resize(sq, (inner_sz, inner_sz), interpolation=cv2.INTER_AREA)
        av_pad = np.zeros_like(canvas)
        av_pad[assets["margin"]:card_size - assets["margin"], assets["margin"]:card_size - assets["margin"]] = av

        canvas[assets["inner"] > 0] = av_pad[assets["inner"] > 0]
        canvas[assets["outer_border"] > 0] = prof["border_gold_bgr"] if is_active_speaker else (140, 140, 140)
        canvas[assets["inner_border"] > 0] = prof["border_accent_bgr"]

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


def generate_flow_video_clip(
    prompt: str,
    ref_image: Path,
    save_mp4: Path,
    flow_project_url: str = "https://flow.google.com/project/d43a0933-5310-4951-b511-911f96a6bc22",
    cdp_url: str = "http://127.0.0.1:18800",
    wait_s: int = 600,
) -> Path:
    """Gera 1 clipe de video (~8s) via Google Flow (Veo 3.1 Lite) usando vendor/flow_fetch."""
    import sys
    sys.path.insert(0, str(VENDOR_DIR))
    import flow_fetch as ff  # noqa: E402
    from playwright.async_api import async_playwright

    async def _run():
        async with async_playwright() as pw:
            b = await pw.chromium.connect_over_cdp(cdp_url)
            ctx = b.contexts[0]
            page = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or await ctx.new_page()
            await page.goto(flow_project_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(1500)
            if await ff.needs_login(page):
                raise RuntimeError("Google Flow deslogado no Chrome CDP")
            await ff.dismiss_ads_and_permissions(page)
            await ff._dismiss_overlays(page)

            trig = await ff._loc_first_visible(page, ff.SETTINGS_TRIGGER_SELECTORS, timeout_ms=6000)
            if trig is None:
                raise RuntimeError("Painel de configuracoes do Flow nao encontrado")
            await trig.click(timeout=5000)
            await page.wait_for_timeout(800)

            for label in ("Vídeo", "Video", "Veo"):
                cand = page.locator(f'mat-button-toggle:has-text("{label}")').first
                if await cand.count():
                    if not await ff._toggle_checked(cand):
                        await cand.click(timeout=5000)
                    break

            for label_d in ("8s", "8 s"):
                dur = page.locator(f'mat-button-toggle:has-text("{label_d}")').first
                if await dur.count() and not await ff._toggle_checked(dur):
                    await dur.click(timeout=4000)
                    break
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(400)

            if ref_image.exists():
                await ff.attach_reference(page, str(ref_image))
            ed = await ff.editor(page)
            await ed.click()
            await ed.fill(prompt)
            await page.wait_for_timeout(400)
            gen = page.locator('button[aria-label*="Iniciar"], button:has(mat-icon:has-text("arrow_forward"))').first
            await (gen.click(timeout=8000) if await gen.count() else page.keyboard.press("Enter"))

            save_mp4.parent.mkdir(parents=True, exist_ok=True)
            dl = page.locator(ff.DL_SELECTOR)
            antes = await dl.count()
            net_url = None

            def on_resp(resp):
                nonlocal net_url
                ct = (resp.headers or {}).get("content-type", "").split(";")[0].lower()
                if ct.startswith("video/") and resp.status in (200, 206) and net_url is None:
                    net_url = resp.url

            page.on("response", on_resp)
            t0 = time.time()
            while time.time() - t0 < wait_s:
                await page.wait_for_timeout(4000)
                if await dl.count() > antes:
                    try:
                        async with page.expect_download(timeout=30000) as dinfo:
                            await dl.last.click(timeout=10000)
                        d = await dinfo.value
                        await d.save_as(str(save_mp4))
                        return save_mp4
                    except Exception:
                        pass
                if net_url:
                    data, _ = await ff.fetch_url(page, net_url)
                    if data and len(data) > 20000:
                        save_mp4.write_bytes(data)
                        return save_mp4
            raise TimeoutError(f"Timeout aguardando video Veo em {save_mp4}")

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
