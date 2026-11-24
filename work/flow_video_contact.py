# -*- coding: utf-8 -*-
"""Contato de TODOS os videos ja gerados no Flow (para escolher despedida limpa)."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FLOW = ROOT / "assets" / "reference" / "primeiro-dia-de-praia" / "flow_all"
OUT = ROOT / "work" / "flow_video_contact"
OUT.mkdir(parents=True, exist_ok=True)
FF = ROOT / "bin" / "ffmpeg.exe"
FFPROBE = ROOT / "bin" / "ffprobe.exe"


def dur(p: Path) -> float:
    r = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def main() -> None:
    vids = sorted(FLOW.glob("acc_*/videos/*.mp4"))
    print(f"videos no Flow: {len(vids)}")
    font = ImageFont.load_default()
    tw, th, cols = 320, 180, 4
    items = []
    for i, v in enumerate(vids):
        d = dur(v)
        t = min(max(0.3, d * 0.6), max(0.3, d - 0.3))
        p = OUT / f"v{i:03d}.png"
        subprocess.run([str(FF), "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(v),
                        "-frames:v", "1", str(p)], capture_output=True)
        if p.exists():
            items.append((v, d, Image.open(p).convert("RGB")))
    for page in range(0, len(items), 16):
        chunk = items[page:page + 16]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * (th + 30)), (12, 12, 16))
        dr = ImageDraw.Draw(sheet)
        for i, (v, d, im) in enumerate(chunk):
            x, y = (i % cols) * tw, (i // cols) * (th + 30)
            im.thumbnail((tw, th))
            sheet.paste(im, (x, y))
            label = f"{v.stem[:26]} {d:.1f}s"
            dr.text((x + 2, y + th + 2), label, fill=(255, 225, 120), font=font)
        out = OUT / f"flow_videos_{page // 16 + 1}.jpg"
        sheet.save(out, quality=86)
        print(out)


if __name__ == "__main__":
    main()
