# -*- coding: utf-8 -*-
"""Folhas de contato da auditoria fina: 1 frame por cena do MP4 final + narracao.

Complementa `core/fine_audit.py` (que compara sub-clip a sub-clip de forma
automatica): aqui o objetivo e EVIDENCIA HUMANA — ver, cena a cena, se a imagem
mostrada corresponde ao que esta sendo narrado.

Uso: python work/audit_fino_sheets.py [slug]
     (padrao: primeiro-dia-de-praia-v7)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FF = ROOT / "bin" / "ffmpeg.exe"


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "primeiro-dia-de-praia-v7"
    proj = ROOT / "projects" / slug
    video = proj / "output" / f"{slug}_16x9.mp4"
    pacing_path = proj / "artifacts" / "pacing_plan_v2.json"
    if not video.exists():
        print(f"video final ausente: {video}")
        return 2
    if not pacing_path.exists():
        print(f"pacing ausente: {pacing_path}")
        return 2
    pacing = json.loads(pacing_path.read_text(encoding="utf-8"))
    out_dir = ROOT / "work" / f"audit_fino_{slug.split('-')[-1]}"
    out_dir.mkdir(parents=True, exist_ok=True)

    scenes: dict[str, dict] = {}
    for c in pacing:
        sid = c["scene_id"]
        if sid not in scenes or c["clip_id"].endswith("_p1"):
            scenes[sid] = c

    font = ImageFont.load_default()
    tw, th, cols = 400, 225, 3
    items = sorted(scenes.items())
    for page in range(0, len(items), 10):
        chunk = items[page:page + 10]
        cell_h = th + 96
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * cell_h), (16, 16, 20))
        dr = ImageDraw.Draw(sheet)
        for i, (sid, c) in enumerate(chunk):
            t = (float(c["start"]) + float(c["end"])) / 2
            frame = out_dir / f"{sid}.png"
            subprocess.run([str(FF), "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video),
                            "-frames:v", "1", str(frame)], capture_output=True)
            x, y = (i % cols) * tw, (i // cols) * cell_h
            if frame.exists():
                im = Image.open(frame).convert("RGB")
                im.thumbnail((tw, th))
                sheet.paste(im, (x, y))
            spk = str(c.get("speaker") or "narrador")
            dr.text((x + 4, y + th + 2), f"{sid}  t={t:.1f}s  [{spk}]",
                    fill=(255, 220, 120), font=font)
            lines, cur = [], ""
            for w in str(c.get("text", "")).split():
                if len(cur) + len(w) > 50:
                    lines.append(cur)
                    cur = w
                else:
                    cur = (cur + " " + w).strip()
            if cur:
                lines.append(cur)
            for j, ln in enumerate(lines[:5]):
                dr.text((x + 4, y + th + 17 + j * 14), ln, fill=(235, 235, 235), font=font)
        out = out_dir / f"fino_{page // 10 + 1}.jpg"
        sheet.save(out, quality=87)
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
