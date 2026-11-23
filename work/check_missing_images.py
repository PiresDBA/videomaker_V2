# -*- coding: utf-8 -*-
"""Compara as imagens pedidas pelo pacing com as existentes; procura faltantes no projeto legado."""
import json, shutil
from pathlib import Path
proj = Path("projects/o-campeonato-de-caes-mais-maluco-do-mundo")
legacy = Path(r"E:\videos\o-campeonato-de-caes-mais-maluco-do-mundo\assets\images")
imgdir = proj / "assets/images"
clips = json.loads((proj / "artifacts/pacing_plan_v2.json").read_text(encoding="utf-8"))
need = sorted({c["clip_id"] + ".jpg" for c in clips})
missing = [n for n in need if not (imgdir / n).exists()]
print("pedidas:", len(need), "| existentes:", len(need) - len(missing), "| faltando:", len(missing))
for n in missing:
    src = legacy / n
    print(f"  {n}: legado={'SIM' if src.exists() else 'NAO'}")
    if src.exists():
        shutil.copy2(src, imgdir / n)
        print("    -> copiado para assets/images")
print("faltando agora:", [n for n in need if not (imgdir / n).exists()])
