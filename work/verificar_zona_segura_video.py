# -*- coding: utf-8 -*-
"""Verifica num Short renderizado se ha conteudo (nao background) na faixa segura y 1620..1920.
Compara a faixa segura com o palco de referencia vazio (y local 276..576) via variancia/diferenca."""
import sys, subprocess, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import FFMPEG_EXE, VIDEO_FPS

for slug in ("primeiro-dia-de-praia-v7", "primeiro-dia-de-praia-parte2"):
    v = Path("projects") / slug / "output" / f"{slug}_short_01_hook.mp4"
    if not v.exists():
        print(slug, "SEM VIDEO"); continue
    # Extrai 1 frame em t=5s e corta a faixa 1620..1920
    frame = Path("work") / f"zcheck_{slug}.png"
    subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-ss", "5", "-i", str(v), "-frames:v", "1", str(frame)], check=True)
    import cv2, numpy as np
    im = cv2.imread(str(frame))
    print(f"{slug}: frame {im.shape[1]}x{im.shape[0]} | faixa segura y 1620..1920")
    band = im[1620:1920, :, :]
    # Fundo do palco e gradiente pastel suave: se houver avatar/badge, ha muita variacao e bordas.
    gray = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 40, 120)
    print(f"   area da faixa: {band.shape[0]}px | intensidade de bordas: {int(edges.sum()/255)} px de borda")
    print(f"   => {'ZONA LIVRE OK' if edges.sum()/255 < 4000 else 'ATENCAO: pode haver conteudo na zona'}")
