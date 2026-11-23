import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.voice_studio import synthesize_all_scenes  # noqa: E402

script = {"scenes": [{
    "scene_id": "sc_vs_test", "act": 1, "speaker": "luna",
    "text": "Eita! A areia me mordeu! Está entrando entre os meus dedinhos e fazendo cócegas, Frida! Olha só que coisa mais esquisita, eu juro que o chão está me mordendo!", "location": "Praia",
    "visual_action": "Luna pulando", "characters": ["Luna"],
}]}
with tempfile.TemporaryDirectory() as td:
    audio = Path(td) / "assets" / "audio"
    out = synthesize_all_scenes(
        script, audio, provider="voice_studio",
        enable_whisper_qa=False, enable_prosody_gate=False,
    )
    item = out[0]
    print(json.dumps({
        "voice": item["voice"], "emotion_mode": item["emotion_mode"],
        "duration": round(item["duration"], 3), "wav_exists": Path(item["wav_path"]).exists(),
    }, ensure_ascii=False, indent=2))
