import json
from pathlib import Path

root = Path(r"E:\videos\videomaker_v2\projects\primeiro-dia-de-praia-2")
sp = root / "artifacts" / "script_v2.json"
d = json.loads(sp.read_text(encoding="utf-8"))
for s in d["scenes"]:
    if s["scene_id"] == "sc_26":
        s["text"] = "Que aventura! Meu coração está batendo rápido... mas eu adorei quando a onda empurrou a gente!"
        s["comedy_beat"] = "Luna sacode o pelo → cartoon giggle → pausa de riso"
        print("NOVO TEXTO:", s["text"])
sp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

tp = root / "artifacts" / "tts_timings_v2.json"
if tp.exists():
    t = [x for x in json.loads(tp.read_text(encoding="utf-8")) if x["scene_id"] != "sc_26"]
    tp.write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")
    print("timings: removido sc_26")

wav = root / "assets" / "audio" / "wav" / "sc_26.wav"
if wav.exists():
    wav.unlink()
    print("wav removido")
raw = root / "assets" / "audio" / "raw" / "sc_26_vs.wav"
if raw.exists():
    raw.unlink()
    print("raw removido")
