import json
import wave
from pathlib import Path

root = Path(r"E:\videos\videomaker_v2\projects\primeiro-dia-de-praia-2")
t = json.loads((root / "artifacts" / "tts_timings_v2.json").read_text(encoding="utf-8"))
raw = root / "assets" / "audio" / "raw"
script = {s["scene_id"]: s for s in json.loads((root / "artifacts" / "script_v2.json").read_text(encoding="utf-8"))["scenes"]}

def dur(p):
    with wave.open(str(p), "rb") as w:
        return w.getnframes() / w.getframerate()

print("cena | palavras | bruto | final | diff")
for x in t[:12]:
    sid = x["scene_id"]
    rp = raw / f"{sid}_vs.wav"
    fp = Path(x["wav_path"])
    words = len(script[sid]["text"].split())
    if rp.exists() and fp.exists():
        d1, d2 = dur(rp), dur(fp)
        print(f"{sid} | {words:>3} | {d1:5.2f} | {d2:5.2f} | {d2-d1:+.2f}")
