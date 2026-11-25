# -*- coding: utf-8 -*-
"""Adiciona a cena final sc_30 (despedida canonica) ao projeto da Parte 2.

O pipeline_v2 nao aplica a despedida sozinho (no v7 isso foi feito pelo build_v7).
Aqui materializamos sc_30.mp4 via prepare_goodbye, geramos a fala e reescrevemos
o script e os timings para que o pipeline remonte reaproveitando tudo.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import FFMPEG_EXE  # noqa: E402
from core.goodbye_video import prepare_goodbye  # noqa: E402
from core.voice_studio import synthesize_all_scenes  # noqa: E402

PROJ = ROOT / 'projects' / 'primeiro-dia-de-praia-parte2'
ART = PROJ / 'artifacts'

script = json.loads((ART / 'script_v2.json').read_text(encoding='utf-8'))
timings = json.loads((ART / 'tts_timings_v2.json').read_text(encoding='utf-8'))

final_text = 'Se você curtiu a Guga e a bagunça, se inscreve no canal e vem com a gente na próxima praia!'
sc30 = {
    'scene_id': 'sc_30',
    'act': 3,
    'speaker': 'narrador',
    'emotion_direction': 'contando a historia como uma brincadeira, muito alegre, sorridente e saltitante',
    'text': final_text,
    'location': 'Despedida canônica com YOUTUBE e SUBSCRIBE',
    'visual_action': 'Frida, Luna e Guga acenando com confete, botão do YouTube e SUBSCRIBE na tela.',
    'sfx': 'cartoon fanfare',
    'comedy_beat': 'As três acenam para a câmera com confete caindo.',
    'avatar_mode': 'none',
    'avatar_pip': False,
    'characters': ['Frida', 'Luna', 'Guga'],
}

if not any(s['scene_id'] == 'sc_30' for s in script['scenes']):
    script['scenes'].append(sc30)
    (ART / 'script_v2.json').write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding='utf-8')

bye = prepare_goodbye(PROJ)
print(f'[despedida] {bye["source"]} | {bye["duration"]}s | audio={bye["audio"]}')

# quadro da despedida para a cena (usado como referencia visual)
frame = PROJ / 'assets' / 'images' / 'sc_30_p1.jpg'
if not frame.exists():
    subprocess.run([FFMPEG_EXE, '-y', '-v', 'error', '-ss', '1.0',
                    '-i', str(PROJ / 'assets' / 'videos' / 'sc_30.mp4'),
                    '-frames:v', '1', '-q:v', '3', str(frame)], capture_output=True)

if not any(t['scene_id'] == 'sc_30' for t in timings):
    mini = {'scenes': [sc30]}
    new = synthesize_all_scenes(
        mini, PROJ / 'assets' / 'audio', provider='voice_studio',
        enable_whisper_qa=True, enable_prosody_gate=True, force=False,
    )
    if len(new) != 1:
        raise RuntimeError(f'Falha ao sintetizar sc_30: {new}')
    timings.append(new[0])
    (ART / 'tts_timings_v2.json').write_text(
        json.dumps(timings, ensure_ascii=False, indent=2), encoding='utf-8')

wav = Path(timings[-1]['wav_path'])
print(f'[despedida] cenas no roteiro: {len(script["scenes"])} | timings: {len(timings)} | wav: {wav.exists()}')
print(f'[despedida] fala: {timings[-1].get("duration")}s')
