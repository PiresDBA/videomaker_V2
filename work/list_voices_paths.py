import json
from pathlib import Path

root = Path(r"E:\videos\videomaker_v2\projects\primeiro-dia-de-praia-2")
t = json.loads((root / "artifacts" / "tts_timings_v2.json").read_text(encoding="utf-8"))
for x in t:
    rel = Path(x["wav_path"]).relative_to(root).as_posix()
    print(f"{x['scene_id']:>7} | {x['speaker']:<10} | {x['voice']:<28} | {rel}")
