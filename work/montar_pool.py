# -*- coding: utf-8 -*-
"""Catalogo ampliado de imagens para a Parte 2: Flow + primeiro video (v7) + concha revisar."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'work' / 'pool_ampliado.json'

dados = json.loads((ROOT / 'work' / 'selecao_continuacao' / 'dados.json').read_text(encoding='utf-8'))

pool = {}  # key -> {path, desc, kind, source}

# 1) imagens do Flow na categoria praia (ja tem descricao)
for x in dados:
    if x['category'] == 'praia' and x['kind'] == 'imagem':
        key = x['name']
        pool[key] = {'path': x['path'], 'desc': x['aria'] or x['name'],
                     'kind': 'imagem', 'source': 'flow'}

# 2) a concha "conchacantora" que estava em revisar
concha = next((x for x in dados if x['name'] == 'acc_3_225a8b1e_img_09_e07f473af9.jpg'), None)
if concha:
    pool['concha_portrait'] = {'path': concha['path'], 'desc': 'Concha cantora retrato',
                               'kind': 'imagem', 'source': 'revisar'}

# 3) imagens do PRIMEIRO VIDEO (v7) — descricao vem do visual_action do roteiro v7
v7_script = json.loads((ROOT / 'projects' / 'primeiro-dia-de-praia-v7' / 'artifacts' / 'script_v2.json').read_text(encoding='utf-8'))
v7_scenes = {s['scene_id']: s for s in v7_script['scenes']}
v7_dir = ROOT / 'projects' / 'primeiro-dia-de-praia-v7' / 'assets' / 'images'
# cenas do v7 que queremos reusar (concha, abraco, protetor, areia, onda, toalha)
REUSE_V7 = {
    'sc_16': 'concha_rosa',
    'sc_17': 'concha_lambida',
    'sc_29': 'abraco_por_do_sol',
    'sc_07': 'protetor',
    'sc_09': 'protetor_escorrega',
    'sc_10': 'luna_espuma',
    'sc_12': 'luna_enterrada',
    'sc_02': 'onda_patinhas',
    'sc_03': 'onda_espuma',
}
for sid, key in REUSE_V7.items():
    p = v7_dir / f'{sid}_p1.jpg'
    if p.exists():
        sc = v7_scenes.get(sid, {})
        pool[key] = {'path': str(p), 'desc': sc.get('visual_action', key),
                     'kind': 'imagem', 'source': 'v7'}

OUT.write_text(json.dumps(pool, ensure_ascii=False, indent=2), encoding='utf-8')
print('pool ampliado:', len(pool), 'imagens')
for k, v in pool.items():
    print(f'  [{v["source"]:7s}] {k:22s} | {v["desc"][:55]}')
