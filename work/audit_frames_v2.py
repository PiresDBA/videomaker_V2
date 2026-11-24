# -*- coding: utf-8 -*-
"""Auditoria visual: extrai 1 frame por cena do MP4 final e monta contato com a narração."""
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FF = ROOT / "bin" / "ffmpeg.exe"
proj = ROOT / "projects" / "primeiro-dia-de-praia-2"
video = proj / "output" / "primeiro-dia-de-praia-2_16x9.mp4"
pacing = json.loads((proj / "artifacts" / "pacing_plan_v2.json").read_text(encoding="utf-8"))
OUT = ROOT / "work" / "audit_v2_frames"
OUT.mkdir(parents=True, exist_ok=True)

# pega 1 clip por cena (o p1) e seu texto
scenes = {}
for c in pacing:
    sid = c["scene_id"]
    if sid not in scenes or c["clip_id"].endswith("_p1"):
        scenes[sid] = c

font = ImageFont.load_default()
TW, TH = 420, 236
COLS = 3
per_page = 12
items = sorted(scenes.items())
for page in range(0, len(items), per_page):
    chunk = items[page:page + per_page]
    rows = (len(chunk) + COLS - 1) // COLS
    cell_h = TH + 92
    sheet = Image.new("RGB", (COLS * TW, rows * cell_h), (20, 20, 24))
    dr = ImageDraw.Draw(sheet)
    for i, (sid, c) in enumerate(chunk):
        t = (float(c["start"]) + float(c["end"])) / 2
        frame = OUT / f"{sid}.png"
        subprocess.run([str(FF), "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video),
                        "-frames:v", "1", str(frame)], capture_output=True)
        x = (i % COLS) * TW
        y = (i // COLS) * cell_h
        if frame.exists():
            im = Image.open(frame).convert("RGB")
            im.thumbnail((TW, TH))
            sheet.paste(im, (x, y))
        txt = c.get("text", "")
        # quebra em linhas
        words = txt.split()
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) > 52:
                lines.append(cur); cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur: lines.append(cur)
        dr.text((x + 4, y + TH + 2), f"{sid}  t={t:.1f}s  video={'SIM' if any(v['scene_id']==sid for v in []) else ''}", fill=(255, 220, 120), font=font)
        for j, ln in enumerate(lines[:4]):
            dr.text((x + 4, y + TH + 18 + j * 14), ln, fill=(230, 230, 230), font=font)
    out = OUT / f"contato_{page // per_page + 1}.jpg"
    sheet.save(out, quality=85)
    print(out)
