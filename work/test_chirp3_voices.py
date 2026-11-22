# -*- coding: utf-8 -*-
"""Teste de vozes Chirp 3 HD (Cloud TTS, cota 1M chars/mes) - 1 frase por voz.
Purpose: confirmar que as 3 vozes travadas (Zephyr/Sulafat/Leda) existem e tem emoção."""
import json, sys, urllib.request, urllib.error
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.voice_studio import _get_chirp3_auth_headers

OUT = Path("work/teste_chirp3")
OUT.mkdir(parents=True, exist_ok=True)
VOICES = ["pt-BR-Chirp3-HD-Zephyr", "pt-BR-Chirp3-HD-Sulafat", "pt-BR-Chirp3-HD-Leda"]
TEXTS = {
    "narrador": "Atenção, atletas de quatro patas! O campeonato mais maluco do mundo vai começar!",
    "frida": "Ai, Luna! Eu nem consigo parar de pular de tanta animação! Vamos ganhar!",
    "luna": "Frida, olha só esse osso brilhante! É a nossa grande chance, eu estou felizíssima!",
}
labels = ["narrador", "frida", "luna"]

headers = _get_chirp3_auth_headers()
headers["Content-Type"] = "application/json; charset=utf-8"
for voice, label in zip(VOICES, labels):
    payload = json.dumps({
        "input": {"text": TEXTS[label]},
        "voice": {"languageCode": "pt-BR", "name": voice},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.06},
    }).encode("utf-8")
    req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize",
                                 data=payload, headers=headers, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=60)
        d = json.loads(r.read().decode())
        import base64
        audio = base64.b64decode(d["audioContent"])
        out = OUT / f"{label}_{voice.split('-')[-1]}.mp3"
        out.write_bytes(audio)
        print(f"OK {label:9s} {voice:28s} -> {len(audio)} bytes | {out}")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} {voice}: {e.read().decode()[:200]}")
    except Exception as e:
        print(f"ERR {voice}: {type(e).__name__} {str(e)[:200]}")
