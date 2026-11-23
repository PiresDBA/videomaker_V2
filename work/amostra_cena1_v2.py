# -*- coding: utf-8 -*-
"""AMOSTRA v2 cena sc_01: texto com gatilhos de humor + Zephyr (1.10) + SFX cartoon
a ~20 dB ABAIXO da voz e colados no que é narrado + BGM original suave.
Usa measuring por earshot/ffprobe. NAO altera o projeto."""
import json, sys, urllib.request, base64, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import FFMPEG_EXE
from core.voice_studio import _get_chirp3_auth_headers
from core.audio_fx import resolve_sfx_file

OUT = Path("work/amostra_cena1_v2"); OUT.mkdir(parents=True, exist_ok=True)
BGM = Path(r"E:\videos\o-campeonato-de-caes-mais-maluco-do-mundo\assets\audio\o-campeonato-de-caes-mais-maluco-do-mundo_musica.wav")

# Texto: gatilhos do usuario (Hahaha!, Olha só, Peraí), pontuacao de piada (! ?! ... —), frases curtas
TEXTO = ("Eeeei, atletas de quatro patas! Olha só... o cronômetro já tá correndo! "
         "O grande Campeonato de Patinhas começou — e olha que essa vai ser a corrida "
         "mais engraçada que vocês já viram! Hahaha! Peraí, eu tô rindo só de pensar!")

def tts(text, out):
    h = _get_chirp3_auth_headers(); h["Content-Type"] = "application/json; charset=utf-8"
    payload = json.dumps({"input":{"text":text},
                          "voice":{"languageCode":"pt-BR","name":"pt-BR-Chirp3-HD-Zephyr"},
                          "audioConfig":{"audioEncoding":"MP3","speakingRate":1.10}}).encode()
    r = urllib.request.urlopen(urllib.request.Request(
        "https://texttospeech.googleapis.com/v1/text:synthesize", data=payload, headers=h, method="POST"), timeout=60)
    out.write_bytes(base64.b64decode(json.loads(r.read().decode())["audioContent"]))

print("[1] voz..."); voz = OUT/"voz.mp3"; tts(TEXTO, voz)
vozwav = OUT/"voz.wav"
subprocess.run([FFMPEG_EXE,"-y","-v","error","-i",str(voz),"-ar","44100","-ac","2",str(vozwav)], check=True)

# SFX sincronizados com o SENTIDO: abertura (pop), "começou" (fanfare), "Hahaha" (giggle)
# Volume: alvo ~ -40 dB (voz -20 dB => SFX 20 dB abaixo). escala 0.08 (~ -22 dB) sobre arquivos -14..-18.
print("[2] SFX...")
cues = []
for hint, when in (("ui_pop_soft", 0.30), ("cartoon fanfare", 2.55), ("cartoon giggle", 6.10)):
    p, _ = resolve_sfx_file(hint)
    if p:
        cues.append((p, when))
        print(f"   {hint} @ {when}s -> {p.name}")

print("[3] mix...")
cmd = [FFMPEG_EXE,"-y","-v","error","-i",str(vozwav)]
for p,_ in cues: cmd += ["-i",str(p)]
cmd += ["-ss","0","-t","12","-i",str(BGM)]
parts = ["[0:a]volume=1.0[v]"]
for i,(p,when) in enumerate(cues,1):
    parts.append(f"[{i}:a]adelay={int(when*1000)}|{int(when*1000)},volume=0.08[s{i}]")
parts.append(f"[{1+len(cues)}:a]volume=0.10[bgm]")
mix = "[v]" + "".join(f"[s{i}]" for i in range(1,len(cues)+1)) + f"[bgm]amix=inputs={len(cues)+2}:normalize=0[m]"
parts += [mix, "[m]loudnorm=I=-16:TP=-1.5:LRA=11[out]"]
cmd += ["-filter_complex",";".join(parts),"-map","[out]","-t","12",str(OUT/"AMOSTRA_CENA1_V2.wav")]
subprocess.run(cmd, check=True)
print("OK:", OUT/"AMOSTRA_CENA1_V2.wav")
