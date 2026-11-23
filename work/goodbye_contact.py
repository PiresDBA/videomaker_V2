# -*- coding: utf-8 -*-
"""Contact sheet das 3 despedidas candidatas a juntar no final (sem a de 3 patas)."""
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
FF = ROOT / "bin" / "ffmpeg.exe"
REF = ROOT / "assets" / "reference" / "primeiro-dia-de-praia" / "flow_all"
D = REF / "goodbye_contact"
D.mkdir(exist_ok=True)

cands = [
    ("confetti", "acc_3", "acc_3_225a8b1e_vid_11_ae84f4b6a0.mp4"),
    ("subscribe_plaqueta", "acc_3", "acc_3_225a8b1e_vid_10_f3c7928cd5.mp4"),
    ("living_room_confete", "acc_1", "acc_1_2700c141_vid_08_f901f98df7.mp4"),
]
tw, th = 400, 225
cols = 4
sheet = Image.new("RGB", (cols * tw, len(cands) * (th + 26)), (25, 25, 25))
dr = ImageDraw.Draw(sheet)
for r, (label, acc, name) in enumerate(cands):
    src = REF / acc / "videos" / name
    for c, ts in enumerate((0.5, 2.0, 4.0, 6.0)):
        frame = D / f"g_{r}_{c}.png"
        subprocess.run([str(FF), "-y", "-v", "error", "-ss", str(ts), "-i", str(src),
                        "-frames:v", "1", str(frame)], capture_output=True)
        if frame.exists():
            im = Image.open(frame).convert("RGB")
            im.thumbnail((tw, th))
            sheet.paste(im, (c * tw, r * (th + 26)))
        dr.text((c * tw + 4, r * (th + 26) + th + 2), f"{label} t={ts}s", fill=(255, 255, 255))
out = D / "contato.jpg"
sheet.save(out, quality=90)
print(out)
