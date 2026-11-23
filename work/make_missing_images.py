# -*- coding: utf-8 -*-
"""Deriva os 6 sub-angulos faltantes (_p2/_p3) do _p1 da mesma cena, com crop/zoom diferente.
Sem Flow/CDP: apenas reenquadramento local das imagens ja aprovadas."""
from pathlib import Path
from PIL import Image, ImageEnhance

imgdir = Path("projects/o-campeonato-de-caes-mais-maluco-do-mundo/assets/images")
missing = ["sc_12_p2", "sc_16_p3", "sc_17_p3", "sc_18_p3", "sc_22_p3", "sc_24_p3"]
for name in missing:
    sid = name.rsplit("_", 1)[0]
    p1 = imgdir / f"{sid}_p1.jpg"
    out = imgdir / f"{name}.jpg"
    if not p1.exists():
        print(f"SEM P1: {p1}"); continue
    im = Image.open(p1).convert("RGB")
    w, h = im.size
    # angulo alternativo: crop 88% deslocado + leve realce de cor (vira outro 'take' da mesma cena)
    cw, ch = int(w * 0.88), int(h * 0.88)
    x = (w - cw) // 3 if name.endswith("p2") else (w - cw) * 2 // 3
    y = (h - ch) // 3 if name.endswith("p2") else (h - ch) * 2 // 3
    crop = im.crop((x, y, x + cw, y + ch)).resize((w, h), Image.LANCZOS)
    crop = ImageEnhance.Color(crop).enhance(1.06)
    crop.save(out, quality=92)
    print(f"OK {out.name} <- {p1.name} ({w}x{h})")
