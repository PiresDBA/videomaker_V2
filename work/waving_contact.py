# -*- coding: utf-8 -*-
"""Contact sheet dos videos de 'waving'/despedida para escolher o correto (4 patas)."""
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
FF = ROOT / "bin" / "ffmpeg.exe"
REF = ROOT / "assets" / "reference" / "primeiro-dia-de-praia"
D = REF / "waving_contact"
D.mkdir(exist_ok=True)

d = json.loads((REF / "analise_v2_all.json").read_text(encoding="utf-8"))
vids = [x for x in d if x.get("kind") == "video"]
import re
pat = re.compile(r"wave|waving|goodbye|tchau|bye|hello|adeus|desped", re.I)
hits = [x for x in vids if pat.search(x.get("aria", ""))]

tw, th = 320, 180
cols = 4
rows = len(hits)
sheet = Image.new("RGB", (cols * tw, rows * (th + 30)), (25, 25, 25))
dr = ImageDraw.Draw(sheet)
for r, x in enumerate(hits):
    src = Path(x["path"])
    for c, ts in enumerate((0.5, 2.0, 4.0, 6.0)):
        frame = D / f"f_{r}_{c}.png"
        subprocess.run([str(FF), "-y", "-v", "error", "-ss", str(ts), "-i", str(src),
                        "-frames:v", "1", str(frame)], capture_output=True)
        if frame.exists():
            im = Image.open(frame).convert("RGB")
            im.thumbnail((tw, th))
            sheet.paste(im, (c * tw, r * (th + 30)))
        dr.text((c * tw + 4, r * (th + 30) + th + 2),
                f"{x['account_id']} {x.get('class','?')} t={ts}s", fill=(255, 255, 255))
    dr.text((4, r * (th + 30) + th + 14), x.get("aria", "")[:60], fill=(255, 220, 120))
out = D / "contato.jpg"
sheet.save(out, quality=90)
print(out)
for i, x in enumerate(hits):
    print(i, x["account_id"], x.get("class"), x.get("aria", "")[:50], x["path"])
