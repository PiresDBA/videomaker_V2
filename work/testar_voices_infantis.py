# -*- coding: utf-8 -*-
"""Testa vozes candidatas a narradora infantil (Chirp 3 HD) no MESMO texto da cena 1."""
import json, sys, urllib.request, base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.voice_studio import _get_chirp3_auth_headers

OUT = Path("work/teste_voices_infantis"); OUT.mkdir(parents=True, exist_ok=True)
TEXTO = ("Eeeei, atletas de quatro patas! Atenção que o cronômetro já tá correndo! "
         "O grande Campeonato de Patinhas acabou de começar — e olha que essa vai ser "
         "a corrida mais engraçada que vocês já viram! Tô rindo só de pensar!")
VOZES = ["Zephyr", "Aoede", "Laomedeia", "Sulafat", "Pulcherrima", "Callirrhoe"]
h = _get_chirp3_auth_headers(); h["Content-Type"] = "application/json; charset=utf-8"
for v in VOZES:
    payload = json.dumps({"input": {"text": TEXTO},
                          "voice": {"languageCode": "pt-BR", "name": f"pt-BR-Chirp3-HD-{v}"},
                          "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.12}}).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            "https://texttospeech.googleapis.com/v1/text:synthesize", data=payload, headers=h, method="POST"), timeout=60)
        data = base64.b64decode(json.loads(r.read().decode())["audioContent"])
        (OUT / f"{v}.mp3").write_bytes(data)
        print(f"OK {v:14s} {len(data)} bytes")
    except Exception as e:
        print(f"ERR {v}: {e}")
