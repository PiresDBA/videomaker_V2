# -*- coding: utf-8 -*-
"""Publica os 3 Shorts (o principal ja foi publicado: KttQvaipMAE)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.youtube_publisher import publish_shorts_pack_youtube_pt

proj = Path("projects/o-campeonato-de-caes-mais-maluco-do-mundo")
script = json.loads((proj / "artifacts/script_v2.json").read_text(encoding="utf-8"))
names = ["01_hook", "02_storybook", "03_final"]
paths = [proj / "output" / f"o-campeonato-de-caes-mais-maluco-do-mundo_short_{n}.mp4" for n in names]
recs = publish_shorts_pack_youtube_pt(proj, script, paths, privacy="public",
                                      main_video_url="https://youtu.be/KttQvaipMAE")
for r in recs:
    print("SHORT", r.get("title"), "->", r.get("url"))
print("OK", len(recs))
