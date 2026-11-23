import json
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.voice_studio import _get_whisper, _load_mono_16k  # noqa: E402

project = ROOT / "projects" / "primeiro-dia-de-praia-2"
script = json.loads((project / "artifacts" / "script_v2.json").read_text(encoding="utf-8"))
sc = next(s for s in script["scenes"] if s["scene_id"] == "sc_26")
print("SPEAKER:", sc["speaker"])
print("EMOCAO:", sc.get("emotion_direction"))
print("TEXTO:", sc["text"])

for label, p in (
    ("NOVO", project / "assets" / "audio" / "wav" / "sc_26.wav"),
    ("BACKUP", ROOT / "work" / "vozes_primeira_tentativa" / "sc_26.wav"),
):
    if not p.exists():
        print(label, "AUSENTE")
        continue
    with wave.open(str(p), "rb") as w:
        dur = w.getnframes() / w.getframerate()
    a = _load_mono_16k(p)
    m = _get_whisper("small")
    for vad in (True, False):
        segs, _ = m.transcribe(a, language="pt", vad_filter=vad)
        txt = " ".join(s.text.strip() for s in segs).strip()
        print(f"{label} dur={dur:.2f}s vad={vad}: {txt}")
