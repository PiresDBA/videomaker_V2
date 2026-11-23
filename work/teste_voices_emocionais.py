# -*- coding: utf-8 -*-
"""Amostras de vozes COM EMOCAO via Chirp 3 HD (cota 1M gratuita) — SEM Gemini-TTS.
Tecnica do usuario: texto expressivo (interjeicoes, travessao, reticencias) + speaking_rate 1.10."""
import json, sys, urllib.request, urllib.error, base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.voice_studio import _get_chirp3_auth_headers

OUT = Path("work/teste_emocao")
OUT.mkdir(parents=True, exist_ok=True)
AMOSTRAS = [
    ("narradora_Zephyr", "pt-BR-Chirp3-HD-Zephyr",
     "Olha só que incrível! Hoje eu trouxe uma novidade que vai transformar o seu dia — sério, você vai adorar! Vem comigo, que agora a diversão vai começar!"),
    ("frida_Sulafat", "pt-BR-Chirp3-HD-Sulafat",
     "Ai, Luna, olha só isso! Eu estou pulando de tanta alegria! Vamos brincar, vamos sim! Você vai amar, eu prometo, prometo, prometo!"),
    ("luna_Leda", "pt-BR-Chirp3-HD-Leda",
     "Frida, olha que legal! Estou felizíssima, de verdade! Vem cá, rápido — você precisa ver isso... é a coisa mais divertida do mundo!"),
]
headers = _get_chirp3_auth_headers()
headers["Content-Type"] = "application/json; charset=utf-8"
for label, voice, text in AMOSTRAS:
    payload = json.dumps({
        "input": {"text": text},
        "voice": {"languageCode": "pt-BR", "name": voice},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.10},
    }).encode("utf-8")
    req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize",
                                 data=payload, headers=headers, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=60)
        d = json.loads(r.read().decode())
        audio = base64.b64decode(d["audioContent"])
        out = OUT / f"{label}.mp3"
        out.write_bytes(audio)
        print(f"OK {label:22s} -> {len(audio)} bytes | {out}")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} {voice}: {e.read().decode()[:200]}")
    except Exception as e:
        print(f"ERR {voice}: {type(e).__name__} {str(e)[:200]}")
print("---cota---")
print(Path(".credentials/chirp3_usage.json").read_text(encoding="utf-8"))
