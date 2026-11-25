# -*- coding: utf-8 -*-
"""Prepara projects/primeiro-dia-de-praia-parte2 com o material da selecao."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEL = ROOT / 'work' / 'selecao_continuacao'
ROTEIRO = ROOT / 'work' / 'roteiro_parte2.json'
PROJ = ROOT / 'projects' / 'primeiro-dia-de-praia-parte2'

data = json.loads(ROTEIRO.read_text(encoding='utf-8'))
sel = {x['name']: x for x in json.loads((SEL / 'dados.json').read_text(encoding='utf-8'))}

for d in ('artifacts', 'assets/images', 'assets/videos', 'assets/audio/raw',
          'assets/audio/wav', 'assets/characters', 'work', 'output/thumbs'):
    (PROJ / d).mkdir(parents=True, exist_ok=True)

n_img = n_vid = 0
for sc in data['scenes']:
    sid = sc['scene_id']
    iname = sc.get('image')
    if iname and iname in sel:
        src = SEL / sel[iname]['relative']
        dst = PROJ / 'assets' / 'images' / f'{sid}_p1.jpg'
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            n_img += 1
    vname = sc.get('video')
    if vname and vname in sel:
        src = SEL / sel[vname]['relative']
        dst = PROJ / 'assets' / 'videos' / f'{sid}.mp4'
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            n_vid += 1

# retrato isolado da Guga (imagem chamada "Guga" no harvest)
guga = Path('assets/reference/primeiro-dia-de-praia/flow_all/acc_2/images/acc_2_1f7e3f9b_img_03_9b639bd663.jpg')
dst = PROJ / 'assets' / 'characters' / 'guga_portrait.jpg'
if guga.exists() and not dst.exists():
    shutil.copy2(guga, dst)

(PROJ / 'artifacts' / 'script_v2.json').write_text(
    json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'[projeto] {PROJ}')
print(f'[projeto] imagens copiadas: {n_img} | videos copiados: {n_vid}')
print(f'[projeto] retrato Guga: {dst.exists()}')
