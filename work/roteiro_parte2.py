# -*- coding: utf-8 -*-
"""Monta o roteiro da Parte 2 da praia e encaixa os videos validados.

Uso: python work/roteiro_parte2.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'work' / 'selecao_continuacao' / 'dados.json'
OUT = ROOT / 'work' / 'roteiro_parte2.json'

# Cenas: (speaker, texto, sfx, acao visual, personagens, subtipo de video desejado)
SCENES: list[tuple[str, str, str, str, list[str], str]] = [
    ('narrador',
     'No dia seguinte, Frida e Luna voltaram correndo pra praia. O plano era simples: relaxar, tomar sol e não molhar nem uma patinha.',
     'cartoon fanfare', 'Frida e Luna caminhando na areia com a toalha colorida.',
     ['Frida', 'Luna'], 'areia'),
    ('narrador',
     'A Luna trazia uma sacolinha cheia de biscoitinhos. O problema é que biscoito na praia chama mais golpista que abeja chama mel.',
     'cartoon giggle', 'Luna com a sacolinha de biscoitos perto da toalha.',
     ['Luna'], 'toalha'),
    ('frida',
     'Luna, esconde esse biscoito! Aqui tem gaivota esperando a gente abrir a boca!',
     'cartoon bird whistle', 'Frida olhando desconfiada para o céu.',
     ['Frida'], 'geral'),
    ('narrador',
     'E não é que apareceu uma gaivota branca, bem fofinha, com cara de quem nunca comeu um biscoito na vida?',
     'cartoon fanfare', 'Guga, a gaivota branca, pousando na areia perto das duas.',
     ['Guga'], 'gaivota'),
    ('narrador',
     'Ela se chamava Guga. Chegou pomposa, deu uma volta no ar e pousou do ladinho da Luna, como quem não quer nada.',
     'cartoon spin', 'Guga planando sobre a toalha e pousando ao lado da Luna.',
     ['Guga', 'Luna'], 'gaivota'),
    ('luna',
     'Oi, Guga! Esse biscoito é meu... acho. Tô comendo, tá? Tô só guardando!',
     'cartoon giggle', 'Luna protegendo a sacolinha com as patinhas.',
     ['Luna', 'Guga'], 'carinho'),
    ('narrador',
     'Guga piscou, deu um pulinho e... SUMIU! O biscoito voou direto pro bico dela.',
     'cartoon boing', 'Guga saltando com o biscoito no bico.',
     ['Guga'], 'gaivota'),
    ('narrador',
     'A Luna ficou com aquela cara: "eu não vi nada, mas meu biscoito foi embora".',
     'cartoon giggle', 'Luna com expressão de surpresa, olhando a sacolinha vazia.',
     ['Luna'], 'geral'),
    ('frida',
     'Pega ladrão! É uma gaivota de bico doce e coração de biscoito!',
     'cartoon run', 'Frida e Luna correndo atrás da gaivota.',
     ['Frida', 'Luna', 'Guga'], 'correndo'),
    ('narrador',
     'Guga correu pela areia com o biscoito, e as duas saíram no encalço, levantando uma poeirinha dourada.',
     'cartoon run', 'As três correndo pela areia, poeira subindo.',
     ['Frida', 'Luna', 'Guga'], 'correndo'),
    ('narrador',
     'Corre que corre, a gaivota pousou em cima do castelo de areia que a Frida tinha feito na véspera, ou do que sobrou dele.',
     'cartoon boing', 'Guga pousando sobre as torres do castelo de areia.',
     ['Guga'], 'areia'),
    ('luna',
     'Esse castelo tá com cara de biscoito gigante! Guga, volta aqui, eu divido!',
     'cartoon giggle', 'Luna cavando perto do castelo e chamando a gaivota.',
     ['Luna', 'Guga'], 'areia'),
    ('narrador',
     'Guga não dividiu. Em vez disso, bicou uma concha brilhante e saiu voando com o tesouro.',
     'cartoon bird whistle', 'Guga voando com uma concha brilhante no bico.',
     ['Guga'], 'concha'),
    ('narrador',
     'A Frida então teve uma ideia genial: construir um castelo novo, mas com uma armadilha de conchas.',
     'cartoon fanfare', 'Frida com o focinho na areia, planejando o novo castelo.',
     ['Frida'], 'areia'),
    ('frida',
     'Luna, pega a pá! A gente vai fazer o castelo mais seguro da praia, com alarme de gaivota!',
     'cartoon giggle', 'Frida e Luna empilhando areia para o novo castelo.',
     ['Frida', 'Luna'], 'areia'),
    ('narrador',
     'Elas cavaram, empilharam e decoraram, enquanto Guga observava de cima, com o biscoito ainda no bico.',
     'cartoon crunch bite', 'As duas construindo; Guga espiando de cima.',
     ['Frida', 'Luna', 'Guga'], 'areia'),
    ('luna',
     'Olha, Frida! Fiz uma torre baixinha pra gaivota não derrubar. Tipo um praça de gaivota!',
     'cartoon giggle', 'Luna exibindo uma torre baixinha do castelo.',
     ['Luna'], 'areia'),
    ('narrador',
     'Foi quando a maré resolveu entrar na brincadeira e começou a lamber as torres de leve.',
     'cartoon splash', 'A água chegando devagar nas torres de areia.',
     ['Frida', 'Luna'], 'agua'),
    ('narrador',
     'A água chegou, levou a concha, levou o biscoito e quase levou a Guga junto.',
     'cartoon splash', 'Uma ondinha envolvendo o castelo e a gaivota.',
     ['Guga'], 'agua'),
    ('luna',
     'Segura a gaivota, Frida! Ela é ladrã, mas é a nossa ladrã!',
     'cartoon boing', 'Frida segurando Guga com cuidado.',
     ['Frida', 'Luna', 'Guga'], 'carinho'),
    ('narrador',
     'A Frida segurou Guga pela asinha com todo o cuidado, e as três subiram para a areia seca.',
     'cartoon giggle', 'As três na areia seca, Guga sacudindo as penas.',
     ['Frida', 'Luna', 'Guga'], 'carinho'),
    ('narrador',
     'Guga sacudiu as penas, soltou um "guiiii" de agradecimento e devolveu o biscoito meio molhado, mas devolveu.',
     'cartoon bird whistle', 'Guga devolvendo o biscoito para a Luna.',
     ['Guga', 'Luna'], 'gaivota'),
    ('frida',
     'Tá vendo? Ladrão que volta é amigo. Ladrão que some é só... biscoito.',
     'cartoon giggle', 'Frida sorrindo com a Luna e a Guga.',
     ['Frida'], 'carinho'),
    ('narrador',
     'Elas sentaram juntinhas na toalha: duas cachorras e uma gaivota, dividindo o que sobrou do lanche.',
     'cartoon fanfare', 'As três sentadas na toalha colorida dividindo o lanche.',
     ['Frida', 'Luna', 'Guga'], 'toalha'),
    ('luna',
     'Guga, pode ficar com a concha. Só não rouba meu biscoito de novo, tá? Eu aviso: eu mordo!',
     'cartoon giggle', 'Luna entregando a concha para a Guga.',
     ['Luna', 'Guga'], 'concha'),
    ('narrador',
     'O sol começou a derreter no mar de novo, pintando as penas brancas da Guga de dourado.',
     'cartoon fanfare', 'Guga e as cachorras olhando o pôr do sol.',
     ['Guga', 'Frida', 'Luna'], 'agua'),
    ('narrador',
     'E a praia, que parecia só areia e água, virou um lugar com três amigos e uma história pra contar.',
     'cartoon giggle', 'As três juntinhas olhando o mar.',
     ['Frida', 'Luna', 'Guga'], 'geral'),
    ('frida',
     'Vem com a gente na próxima aventura, Guga!',
     'cartoon fanfare', 'Frida acenando para a câmera com a Guga ao lado.',
     ['Frida', 'Guga'], 'geral'),
    ('narrador',
     'Se você gostou da Guga e da bagunça, se inscreve no canal e volta pra próxima praia com a gente!',
     'cartoon fanfare', 'As três acenando na beira do mar com o sol baixando.',
     ['Frida', 'Luna', 'Guga'], 'geral'),
]

EMOTION = {
    'narrador': 'contando a historia como uma brincadeira, muito alegre, sorridente e saltitante',
    'frida': 'animada, confiante e muito engriffada, como uma buldogue crianca',
    'luna': 'curiosa, assustada e engracada, como uma salsicha crianca',
}


def main() -> int:
    data = json.loads(DATA.read_text(encoding='utf-8'))
    usable = [x for x in data if x['category'] == 'praia' and x['kind'] == 'video'
              and x.get('duration', 0) > 1.0]
    images = [x for x in data if x['category'] == 'praia' and x['kind'] == 'imagem']
    new = [x for x in usable if not x['usado_v7']]
    reused = [x for x in usable if x['usado_v7']]
    print('[roteiro] videos utilizaveis:', len(usable), '(novos', len(new), '| reaproveitados', len(reused), ')')
    print('[roteiro] fotos:', len(images))

    def pick(pref: str, i: int) -> dict[str, Any]:
        pool = [x for x in usable if x['subcategory'].lower().startswith(pref[:4])] or usable
        item = pool[i % len(pool)]
        return item

    # usa TODOS os videos de praia validados (novos + os que ja eram do v7)
    order = new + reused
    scenes = []
    last_img = ''
    for i, (speaker, text, sfx, action, chars, pref) in enumerate(SCENES):
        v = order[i % len(order)]
        imgs = [x for x in images if x['subcategory'].lower().startswith(pref[:4])] or images
        chosen = imgs[i % len(imgs)]['name']
        if chosen == last_img and len(imgs) > 1:
            chosen = imgs[(i + 1) % len(imgs)]['name']
        last_img = chosen
        scenes.append({
            'scene_id': f'sc_{i + 1:02d}',
            'act': 1 if i < 10 else (2 if i < 20 else 3),
            'speaker': speaker,
            'emotion_direction': EMOTION[speaker],
            'text': text,
            'location': 'Praia ensolarada com toalha colorida, areia, ondas e gaivota',
            'visual_action': action,
            'sfx': sfx,
            'comedy_beat': action,
            'avatar_mode': 'none' if speaker == 'narrador' else speaker,
            'avatar_pip': speaker != 'narrador',
            'characters': chars,
            'video': v['name'],
            'video_path': str(ROOT / 'work' / 'selecao_continuacao' / v['relative']),
            'image': chosen,
        })

    payload = {
        'title': 'A PRAIA PARTE 2 — O BISCOITO ROUBADO DA GUGA',
        'thumb_hook': 'A GAIVOTA ROUBOU O BISCOITO!',
        'description': ('Frida e Luna voltam à praia e conhecem Guga, uma gaivota branca muito atrevida '
                        'que rouba biscoito, esconde conchas e apronta com a maré!'),
        'tags': ['frida e luna', 'gaivota guga', 'historia infantil', 'desenho animado', 'praia parte 2'],
        'target_minutes': 4.0,
        'catchphrase': 'Ladrão que volta é amigo. Ladrão que some é só biscoito!',
        'secondary_characters': [{
            'name': 'Guga',
            'species': 'gaivota branca',
            'description': 'Gaivota branca fofinha e muito atrevida, mora na praia e adora biscoito.',
        }],
        'story_props': [{'name': 'Biscoitinho da Luna', 'description': 'Sacolinha de biscoitos que a Guga rouba.'}],
        'scenes': scenes,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    from collections import Counter
    print('[roteiro] cenas:', len(scenes), '| speakers:', dict(Counter(s['speaker'] for s in scenes)))
    print('[roteiro] arquivo:', OUT)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
