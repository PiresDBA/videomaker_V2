# -*- coding: utf-8 -*-
"""Overlay de CTA infantil (joinha + sininho + SUBSCRIBE) com fundo transparente (.mov qtrle).

Fica fixo na parte inferior do vídeo, entra com fade, faz o movimentozinho e sai.
Reutilizavel em todos os episodios (Regra 25).
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import cv2
import numpy as np

from config import BASE_DIR, VIDEO_FPS

FFMPEG_EXE = BASE_DIR / "bin" / "ffmpeg.exe"


def _ease(t: float) -> float:
    """Suaviza 0..1 (ease in-out)."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def render_cta_subscribe_overlay(out_mov: Path, width: int = 1920, height: int = 1080,
                                  duration: float = 5.2) -> Path:
    """Gera overlay RGBA animado: mãozinha dando joinha + sininho balançando + botão SUBSCRIBE.

    - Fundo transparente (qtrle) para sobrepor qualquer cena.
    - Posicionado no TERÇO INFERIOR (y ~ 0.80*height).
    - Entra (fade+slide), faz plim-plim e joinha, e sai (fade) antes do fim.
    """
    n_frames = max(1, int(round(duration * VIDEO_FPS)))
    tmp_rgb = out_mov.with_suffix(".cta_rgb.mp4")
    tmp_msk = out_mov.with_suffix(".cta_msk.mp4")
    out_mov.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw_rgb = cv2.VideoWriter(str(tmp_rgb), fourcc, VIDEO_FPS, (width, height))
    vw_msk = cv2.VideoWriter(str(tmp_msk), fourcc, VIDEO_FPS, (width, height))

    cy = int(height * 0.83)  # bem embaixo
    cx = width // 2

    for i in range(n_frames):
        t = i / VIDEO_FPS
        p = t / duration  # 0..1
        # entra 0..0.18, sai 0.82..1.0
        enter = _ease(p / 0.18) if p < 0.18 else 1.0
        exit_ = _ease((1.0 - p) / 0.18) if p > 0.82 else 1.0
        env = max(0.0, min(enter, exit_))
        slide = int((1.0 - enter) * 90)  # sobe vindo de baixo
        yy = cy + slide

        rgb = np.zeros((height, width, 3), np.uint8)
        msk = np.zeros((height, width), np.uint8)
        if env <= 0.01:
            vw_rgb.write(rgb)
            vw_msk.write(cv2.cvtColor(msk, cv2.COLOR_GRAY2BGR))
            continue

        A = lambda v: int(max(0, min(255, v * env)))

        # --- Botao SUBSCRIBE (pill vermelho com borda branca) ---
        bw, bh = 360, 104
        bx1, bx2 = cx - bw // 2 - 130, cx + bw // 2 - 130
        by1, by2 = yy - bh // 2, yy + bh // 2
        cv2.rectangle(rgb, (bx1, by1), (bx2, by2), (60, 60, 235), -1, cv2.LINE_AA)
        cv2.rectangle(msk, (bx1, by1), (bx2, by2), A(255), -1, cv2.LINE_AA)
        cv2.rectangle(rgb, (bx1, by1), (bx2, by2), (255, 255, 255), 5, cv2.LINE_AA)
        cv2.putText(rgb, "SUBSCRIBE", (bx1 + 26, yy + 16), cv2.FONT_HERSHEY_SIMPLEX,
                    1.15, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(msk, "SUBSCRIBE", (bx1 + 26, yy + 16), cv2.FONT_HERSHEY_SIMPLEX,
                    1.15, A(255), 5, cv2.LINE_AA)

        # --- Sininho balancando (amarelo) com plim-plim ---
        bell_x = cx + 210
        swing = int(16 * math.sin(t * 7.0))
        bell_y = yy - 34 + abs(int(6 * math.sin(t * 14.0)))
        cv2.circle(rgb, (bell_x + swing, bell_y), 30, (40, 215, 255), -1, cv2.LINE_AA)
        cv2.circle(msk, (bell_x + swing, bell_y), 32, A(255), -1, cv2.LINE_AA)
        cv2.circle(rgb, (bell_x + swing, bell_y + 26), 8, (30, 170, 220), -1, cv2.LINE_AA)
        # brilho plim
        if math.sin(t * 14.0) > 0.4:
            for k in range(3):
                sx = bell_x + swing + (k - 1) * 26
                sy = bell_y - 42 - (k % 2) * 8
                cv2.line(rgb, (sx - 5, sy), (sx + 5, sy), (255, 255, 210), 2, cv2.LINE_AA)
                cv2.line(msk, (sx - 5, sy), (sx + 5, sy), A(255), 2, cv2.LINE_AA)

        # --- Maozinha dando joinha (simbolo do like), pulsando ---
        hx, hy = cx - 250, yy - 6
        pulse = 1.0 + 0.10 * math.sin(t * 6.0)
        r = int(34 * pulse)
        cv2.circle(rgb, (hx, hy), r, (120, 200, 255), -1, cv2.LINE_AA)  # palma
        cv2.circle(msk, (hx, hy), r + 2, A(255), -1, cv2.LINE_AA)
        # polegar para cima
        cv2.rectangle(rgb, (hx - 10, hy - r - 26), (hx + 10, hy - r + 6), (140, 215, 255), -1, cv2.LINE_AA)
        cv2.rectangle(msk, (hx - 10, hy - r - 26), (hx + 10, hy - r + 6), A(255), -1, cv2.LINE_AA)

        vw_rgb.write(rgb)
        vw_msk.write(cv2.cvtColor(msk, cv2.COLOR_GRAY2BGR))

    vw_rgb.release()
    vw_msk.release()
    subprocess.run(
        [str(FFMPEG_EXE), "-y", "-v", "error", "-i", str(tmp_rgb), "-i", str(tmp_msk),
         "-filter_complex", "[0:v][1:v]alphamerge,format=rgba[out]",
         "-map", "[out]", "-c:v", "qtrle", "-r", str(VIDEO_FPS), str(out_mov)],
        check=True,
    )
    tmp_rgb.unlink(missing_ok=True)
    tmp_msk.unlink(missing_ok=True)
    return out_mov
