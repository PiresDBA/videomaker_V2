# -*- coding: utf-8 -*-
"""AMOSTRA da cena sc_01: roteiro engraçado + voz Zephyr (Chirp 3 HD, 1.10) +
3 SFX cartoon sincronizados + trecho da BGM original. NAO altera o projeto."""
import json, sys, urllib.request, urllib.error, base64, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import FFMPEG_EXE
from core.voice_studio import _get_chirp3_auth_headers
from core.audio_fx import resolve_sfx_file

OUT = Path("work/amostra_cena1")
OUT.mkdir(parents=True, exist_ok=True)
BGM = Path(r"E:\videos\o-campeonato-de-caes-mais-maluco-do-mundo\assets\audio\o-campeonato-de-caes-mais-maluco-do-mundo_musica.wav")

# Texto reescrito: engraçado, interjeições, travessão — mantém "atletas de quatro patas"/"campeonato" (auditoria)
TEXTO = ("Eeeei, atletas de quatro patas! Atenção que o cronômetro já tá correndo! "
         "O grande Campeonato de Patinhas acabou de começar — e olha que essa vai ser "
         "a corrida mais engraçada que vocês já viram! Tô rindo só de pensar!")

def tts_chirp(text, voice, rate, out):
    h = _get_chirp3_auth_headers(); h["Content-Type"] = "application/json; charset=utf-8"
    payload = json.dumps({"input":{"text":text},"voice":{"languageCode":"pt-BR","name":voice},
                          "audioConfig":{"audioEncoding":"MP3","speakingRate":rate}}).encode()
    req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize", data=payload, headers=h, method="POST")
    r = urllib.request.urlopen(req, timeout=60)
    out.write_bytes(base64.b64decode(json.loads(r.read().decode())["audioContent"]))

print("[1/3] voz...")
voz = OUT / "voz_zephyr.mp3"
tts_chirp(TEXTO, "pt-BR-Chirp3-HD-Zephyr", 1.10, voz)
print("  ", voz, voz.stat().st_size, "bytes")

print("[2/3] SFX cartoon...")
sfxs = []
for hint in ("cartoon fanfare", "cartoon boing", "cartoon giggle"):
    p, _ = resolve_sfx_file(hint)
    print(f"   {hint}: {p}")
    if p: sfxs.append((hint, p))

print("[3/3] mistura voz + SFX + BGM...")
# Converte voz p/ wav, coloca SFX em 0.2s/2.5s/5s, BGM original em -20dB
vozwav = OUT / "voz.wav"
subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-i", str(voz), "-ar", "44100", "-ac", "2", str(vozwav)], check=True)
cmd = [FFMPEG_EXE, "-y", "-v", "error", "-i", str(vozwav)]
for _, p in sfxs:
    cmd += ["-i", str(p)]
cmd += ["-ss", "0", "-t", "12", "-i", str(BGM)]
parts = ["[0:a]volume=1.0[v]"]
for i, (hint, _) in enumerate(sfxs, 1):
    at = {0: 0.2, 1: 2.6, 2: 5.4}.get(i-1, 3.0)
    parts.append(f"[{i}:a]adelay={int(at*1000)}|{int(at*1000)},volume=0.9[s{i}]")
parts.append(f"[{1+len(sfxs)}:a]volume=0.16[bgm]")
mix = "[v]" + "".join(f"[s{i}]" for i in range(1, len(sfxs)+1)) + f"[bgm]amix=inputs={len(sfxs)+2}:normalize=0[out]"
parts.append(mix)
cmd += ["-filter_complex", ";".join(parts), "-map", "[out]", "-t", "12", str(OUT / "AMOSTRA_CENA1_COMPLETA.wav")]
subprocess.run(cmd, check=True)
print("\nAMOSTRA:", OUT / "AMOSTRA_CENA1_COMPLETA.wav")
