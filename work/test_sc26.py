import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.voice_studio import synthesize_all_scenes  # noqa: E402

sc = {"scenes": [{
    "scene_id": "sc26test", "act": 3, "speaker": "luna",
    "text": "Que aventura! Meu coração está batendo rápido... mas eu adorei quando a onda empurrou a gente!",
    "location": "Praia", "visual_action": "Luna sacode o pelo", "characters": ["Luna"],
    "emotion_direction": "feliz e sacudindo o pelo",
}]}
with tempfile.TemporaryDirectory() as td:
    out = synthesize_all_scenes(sc, Path(td) / "audio", provider="voice_studio", enable_prosody_gate=False)
    print(json.dumps({"voice": out[0]["voice"], "qa": out[0]["qa"]}, ensure_ascii=False, indent=2))
