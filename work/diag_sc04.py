import json
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.voice_studio import _get_whisper, _load_mono_16k  # noqa: E402

root = ROOT / "projects" / "primeiro-dia-de-praia-2"
script = json.loads((root / "artifacts" / "script_v2.json").read_text(encoding="utf-8"))
sc = next(s for s in script["scenes"] if s["scene_id"] == "sc_04")
print("TEXTO:", sc["text"])
print("PALAVRAS:", len(sc["text"].split()), "CHARS:", len(sc["text"]))

for label, p in (
    ("FINAL", root / "assets" / "audio" / "wav" / "sc_04.wav"),
    ("BRUTO", root / "assets" / "audio" / "raw" / "sc_04_vs.wav"),
):
    if not p.exists():
        print(label, "AUSENTE")
        continue
    with wave.open(str(p), "rb") as w:
        print(label, "dur", round(w.getnframes() / w.getframerate(), 2), "s")
    a = _load_mono_16k(p)
    m = _get_whisper("small")
    segs, _ = m.transcribe(a, language="pt", vad_filter=False)
    print(label, "OUVIU:", " ".join(s.text.strip() for s in segs).strip())
