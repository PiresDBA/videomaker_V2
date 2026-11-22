# -*- coding: utf-8 -*-
"""AMOSTRA final: voz Puck (a melhor, confirmada pelo usuario), SEM risada escrita.
A alegria vem so do texto conversacional + ritmo (speakingRate 1.10)."""
import json, sys, urllib.request, base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.voice_studio import _get_chirp3_auth_headers

OUT = Path("work/amostra_puck"); OUT.mkdir(parents=True, exist_ok=True)
# SEM "hahaha" — a risada e sentimento, nunca texto. Gatilhos: interjeicoes, frases curtas, punchline.
TEXTO = ("Oi, gente! Olha só... o cronômetro já tá correndo! O campeonato começou, "
         "e olha que essa vai ser a corrida mais engraçada que vocês já viram! "
         "Peraí, deixa eu te contar! Tô feliz demais, viu? Vem comigo que a diversão vai começar!")
h = _get_chirp3_auth_headers(); h["Content-Type"] = "application/json; charset=utf-8"
payload = json.dumps({"input":{"text":TEXTO},
                      "voice":{"languageCode":"pt-BR","name":"pt-BR-Chirp3-HD-Puck"},
                      "audioConfig":{"audioEncoding":"MP3","speakingRate":1.10}}).encode()
r = urllib.request.urlopen(urllib.request.Request(
    "https://texttospeech.googleapis.com/v1/text:synthesize", data=payload, headers=h, method="POST"), timeout=60)
data = base64.b64decode(json.loads(r.read().decode())["audioContent"])
out = OUT/"PUCK_SEM_RISADA_ESCRITA.mp3"
out.write_bytes(data)
print("OK:", out, len(data), "bytes")
print("Texto usado (sem hahaha):", TEXTO)
