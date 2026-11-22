# -*- coding: utf-8 -*-
"""4 vozes no MESMO texto com gatilhos de humor — só voz (sem SFX/BGM) para isolar a emoção."""
import json, sys, urllib.request, base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.voice_studio import _get_chirp3_auth_headers

OUT = Path("work/teste_vozes_final"); OUT.mkdir(parents=True, exist_ok=True)
TEXTO = ("Eeeei, atletas de quatro patas! Olha só... o cronômetro já tá correndo! "
         "O grande Campeonato de Patinhas começou — e olha que essa vai ser a corrida "
         "mais engraçada que vocês já viram! Hahaha! Peraí, eu tô rindo só de pensar!")
VOZES = ["Puck", "Fenrir", "Zephyr", "Aoede"]
h = _get_chirp3_auth_headers(); h["Content-Type"] = "application/json; charset=utf-8"
for v in VOZES:
    payload = json.dumps({"input":{"text":TEXTO},
                          "voice":{"languageCode":"pt-BR","name":f"pt-BR-Chirp3-HD-{v}"},
                          "audioConfig":{"audioEncoding":"MP3","speakingRate":1.10}}).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            "https://texttospeech.googleapis.com/v1/text:synthesize", data=payload, headers=h, method="POST"), timeout=60)
        data = base64.b64decode(json.loads(r.read().decode())["audioContent"])
        (OUT/f"{v}.mp3").write_bytes(data)
        print(f"OK {v:8s} {len(data)} bytes")
    except Exception as e:
        print(f"ERR {v}: {e}")
