# -*- coding: utf-8 -*-
"""Sanidade do xfade que preserva duracao (Regra 13: narracao sem dessincronia).

Gera 3 clipes de cor solida (2,0s cada), concatena com dissolve de 0,5s usando
`_concat_segments_with_smooth_xfade` e confere se o resultado continua com 6,0s
(antes o xfade encurtava 0,5s por transicao e a narracao ia atrasando).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import FFMPEG_EXE  # noqa: E402
from core.video_assembler import (  # noqa: E402
    _concat_segments_with_smooth_xfade,
    probe_duration,
)
import subprocess

work = ROOT / "work" / "_xfade_check"
work.mkdir(parents=True, exist_ok=True)
colors = ["red", "green", "blue"]
segs = []
for i, col in enumerate(colors):
    p = work / f"c{i}.mp4"
    subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"color=c={col}:s=320x180:r=30:d=2.0",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(p)],
                   check=True)
    segs.append(p)

clips = [{"clip_id": f"sc_0{i+1}_p1", "scene_id": f"sc_0{i+1}", "xfade_duration": 0.5}
         for i in range(3)]
out = work / "merged.mp4"
_concat_segments_with_smooth_xfade(segs, clips, out, work_dir=work)
d = probe_duration(out)
print(f"duracao montada: {d:.3f}s (esperado ~6.000s)")
ok = 5.90 <= d <= 6.15
print("OK" if ok else "FALHOU: o xfade encurtou a timeline")
raise SystemExit(0 if ok else 1)
