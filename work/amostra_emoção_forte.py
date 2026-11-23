# -*- coding: utf-8 -*-
"""AMOSTRA com emoção FORTE: risada exagerada escrita no texto + voz Puck (a mais brincalhona) + 1.12."""
import json, sys, urllib.request, base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.voice_studio import _get_chirp3_auth_headers

OUT = Path("work/amostra_emocao_forte"); OUT.mkdir(parents=True, exist_ok=True)
# Texto COM risada pronunciada e frases curtas (gatilhos de humor do usuario)
TEXTO = ("Oi, gente! Olha só pra mim! Hahaha! Hahahaha! Eu tô rindo, sério! "
         "O cronômetro tá correndo e o campeonato já começou! Ui, que legal! "
         "Essa vai ser a corrida mais engraçada da vida! Hahaha! Peraí... "
         "deixa eu te contar! Tô feliz demais, viu? Hahaha!")
VOZES = ["Puck", "Fenrir", "Zephyr"]
h = _get_chirp3_auth_headers(); h["Content-Type"] = "application/json; charset=utf-8"
for v in VOZES:
    payload = json.dumps({"input":{"text":TEXTO},
                          "voice":{"languageCode":"pt-BR","name":f"pt-BR-Chirp3-HD-{v}"},
                          "audioConfig":{"audioEncoding":"MP3","speakingRate":1.12}}).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            "https://texttospeech.googleapis.com/v1/text:synthesize", data=payload, headers=h, method="POST"), timeout=60)
        data = base64.b64decode(json.loads(r.read().decode())["audioContent"])
        (OUT/f"EMOCAO_FORTE_{v}.mp3").write_bytes(data)
        print(f"OK {v} -> {len(data)} bytes")
    except Exception as e:
        print(f"ERR {v}: {e}")
