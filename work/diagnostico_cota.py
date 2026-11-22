# -*- coding: utf-8 -*-
"""Diagnostico de cota: mostra QUAL API/modelo esta sendo chamado e o erro 429 completo.
NAO imprime valores de chaves (apenas os nomes das variaveis no .env)."""
import json, re, sys, urllib.request, urllib.error
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import ENV_FILE, GEMINI_TTS_MODELS, CHIRP3_MONTHLY_CHAR_LIMIT
from core.voice_studio import _load_google_tts_keys

print("=== 1) QUAL API ESTA SENDO USADA PELO TTS ===")
print("Modelos em config.GEMINI_TTS_MODELS:", GEMINI_TTS_MODELS)
print("Endpoint: https://generativelanguage.googleapis.com/v1beta/models/<modelo>:generateContent")
print("(e o Chirp 3 HD usa OUTRA API: Cloud TTS / speech.googleapis.com, limite local =", CHIRP3_MONTHLY_CHAR_LIMIT, "chars/mes)")

print("\n=== 2) VARIAVEIS DE CHAVE PRESENTES NO .env (sem valores) ===")
raw = ENV_FILE.read_bytes()
txt = raw.decode("utf-16", "ignore") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", "ignore")
names = []
for line in txt.splitlines():
    line = line.strip().lstrip("\ufeff")
    if "=" in line and not line.startswith("#"):
        n = line.split("=", 1)[0].strip()
        if any(s in n for s in ("API_KEY", "GEMINI", "GOOGLE", "TTS")):
            names.append(n)
print("Chaves de API encontradas:", names)

keys = _load_google_tts_keys()
print("Total de chaves carregadas pelo pipeline:", len(keys))
print("Nomes que o codigo procura: GOOGLE_TTS_API_KEY, GOOGLE_TTS_API_KEY_1..20, GEMINI_API_KEY")

print("\n=== 3) CHAMADA DE TESTE (1 requisicao) -> erro 429 completo ===")
if not keys:
    print("Nenhuma chave disponivel")
    sys.exit(0)
k = keys[0]
model = GEMINI_TTS_MODELS[0]
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={k}"
obj = {
    "contents": [{"parts": [{"text": "Oi, tudo bem?"}]}],
    "generationConfig": {"responseModalities": ["AUDIO"],
                         "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Zephyr"}}}},
}
try:
    r = urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(obj).encode(),
              headers={"Content-Type": "application/json"}, method="POST"), timeout=45)
    d = json.loads(r.read().decode())
    print("SUCESSO:", list(d.keys()))
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", "ignore")
    print("HTTP", e.code)
    print("Mensagem completa:")
    try:
        print(json.dumps(json.loads(body), indent=2, ensure_ascii=False))
    except Exception:
        print(body)
    print("Headers uteis:")
    for h in ("x-ratelimit-limit-requests", "x-ratelimit-remaining-requests", "retry-delay"):
        v = e.headers.get(h)
        if v:
            print(f"  {h}: {v}")
except Exception as e:
    print("ERRO", type(e).__name__, str(e)[:300])
