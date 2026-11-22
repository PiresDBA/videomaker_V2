# -*- coding: utf-8 -*-
"""Garante TODOS os _pN do pacing atual, derivando de _p1 da mesma cena (sem Flow/CDP)."""
import json
from pathlib import Path
from PIL import Image, ImageEnhance
proj = Path("projects/o-campeonato-de-caes-mais-maluco-do-mundo")
imgdir = proj / "assets/images"
clips = json.loads((proj / "artifacts/pacing_plan_v2.json").read_text(encoding="utf-8"))
need = sorted({c["clip_id"] + ".jpg" for c in clips})
made = 0
for n in need:
    if (imgdir / n).exists():
        continue
    sid = n.rsplit(".", 1)[0].rsplit("_", 1)[0]
    p1 = imgdir / f"{sid}_p1.jpg"
    if not p1.exists():
        print("SEM P1:", n); continue
    im = Image.open(p1).convert("RGB"); w, h = im.size
    cw, ch = int(w*0.88), int(h*0.88)
    part = int(n.rsplit("_",1)[1].split(".")[0][1:]) if "_p" in n else 2
    x = (w-cw) * (part % 3) // 3; y = (h-ch) * (part % 2) // 2
    crop = im.crop((x,y,x+cw,y+ch)).resize((w,h), Image.LANCZOS)
    crop = ImageEnhance.Color(crop).enhance(1.05)
    crop.save(imgdir / n, quality=92)
    made += 1
    print("CRIADA:", n)
print("totais: pedidas", len(need), "| criadas", made, "| faltando",
      [n for n in need if not (imgdir/n).exists()])
