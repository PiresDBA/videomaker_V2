# -*- coding: utf-8 -*-
import json
from pathlib import Path
proj = Path("projects/o-campeonato-de-caes-mais-maluco-do-mundo")
p = json.loads((proj / "artifacts/pacing_plan_v2.json").read_text(encoding="utf-8"))
t = json.loads((proj / "artifacts/tts_timings_v2.json").read_text(encoding="utf-8"))
pacing = {c["scene_id"]: c for c in p}
new = {x["scene_id"]: float(x["duration"]) for x in t}
pv = next(c for c in p if c["scene_id"] == "sc_01")
print("keys do clip:", list(pv.keys())[:22])
print("\ncena  speaker  pacing_dur  wav_novo  delta   pacing_start")
for sid in ["sc_01", "sc_02", "sc_03", "sc_04", "sc_10", "sc_21", "sc_25"]:
    c = pacing.get(sid, {})
    pd = float(c.get("scene_audio_dur") or 0)
    nd = new.get(sid, 0)
    print(f"{sid:6s} {c.get('speaker','?'):9s} {pd:8.2f} {nd:9.2f} {nd-pd:+7.2f} {c.get('scene_audio_start',0):8.2f}")
print("\nSOMA pacing:", round(sum(float(c.get('scene_audio_dur') or 0) for c in p), 2))
print("SOMA novo  :", round(sum(new.values()), 2))
print("\nPiP .mov:")
for f in sorted((proj / "work/avatar_pip").glob("*.mov"))[:6]:
    import datetime
    ts = datetime.datetime.fromtimestamp(f.stat().st_mtime)
    print(" ", f.name, ts)
