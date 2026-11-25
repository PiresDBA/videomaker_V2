# -*- coding: utf-8 -*-
"""Constroi a Parte 2 da praia com ATRIBUICAO SEMANTICA de midia.

A versao anterior usava rodizio mecanico (video = ordem[i % total]) e saiu com
narracao de gaivota em cima de video de cachorro. Aqui cada cena aponta
EXPLICITAMENTE para o video OU a imagem correta (pela descricao real do material),
e gera o media_assignment.json para a auditoria de sincronia do motor.

Regras respeitadas:
  - cenas de video -> assets/videos/sc_XX.mp4
  - cenas de imagem -> assets/images/sc_XX_p1.jpg (SEM video; o motor faz Ken Burns)
  - a Guga (gaivota) aparece nas IMAGENS de gaivota, intercaladas entre os videos
  - narracao dominante (>= 55%), max 2 cenas seguidas so de personagem
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import FFMPEG_EXE  # noqa: E402

SEL = ROOT / 'work' / 'selecao_continuacao'
DATA = SEL / 'dados.json'
OUT_SCRIPT = ROOT / 'work' / 'roteiro_parte2.json'
PROJ = ROOT / 'projects' / 'primeiro-dia-de-praia-parte2'

# (speaker, texto, sfx, acao_visual, tipo_media, chave_media)
# tipo_media: "video" | "image". chave_media: sub-chave resolvida abaixo.
STORY: list[tuple[str, str, str, str, str, str]] = [
    ('narrador', 'No dia seguinte, Frida e Luna voltaram à praia mais cedo ainda, com o sol nascendo, o cheirinho de mar e energia de sobra.',
     'cartoon fanfare', 'Frida e Luna caminhando na areia da praia.', 'video', 'walk_beach'),
    ('narrador', 'A Luna foi logo se jogando na areia e saiu sacudindo as patinhas para tirar o grude do pelo.',
     'cartoon giggle', 'Luna sacudindo a areia do corpo na praia.', 'video', 'shake_sand'),
    ('luna', 'Essa areia gruda mais que adesivo! Eu tô parecendo um bolo de areia com recheio de salsicha!',
     'cartoon boing', 'Luna lambendo a areia do focinho.', 'video', 'lick_face'),
    ('narrador', 'A Frida então mostrou como se pula: foi longe, aterrissou na areia fofa e riu de orelha a orelha.',
     'cartoon fanfare', 'Dachshund pulando na areia fofa.', 'video', 'jump_sand'),
    ('frida', 'Vem, Luna! A areia fofa é o melhor trampolim do mundo!',
     'cartoon run', 'Cachorrinhas pulando e brincando na areia.', 'video', 'jump_beach'),
    ('narrador', 'Antes de qualquer aventura, tinha uma missão muito séria: passar protetor solar em cada dobrinha.',
     'cartoon fanfare', 'Frida apertando o tubo de protetor solar.', 'image', 'protetor'),
    ('luna', 'Esse protetor escorrega mais que salsicha na areia molhada! Segura firme, Frida!',
     'cartoon giggle', 'As duas escorregando juntas no creme branco de protetor.', 'image', 'protetor_escorrega'),
    ('narrador', 'A Luna saiu patinando pelo creme e virou uma bolinha branca e cheirosa.',
     'cartoon boing', 'Luna coberta de espuma branca de protetor.', 'image', 'luna_espuma'),
    ('narrador', 'Depois da bagunça, as duas pegaram o balde amarelo para começar a obra de areia.',
     'cartoon fanfare', 'Um balde amarelo de plástico na areia.', 'image', 'bucket'),
    ('narrador', 'A Luna cavou tanto que desapareceu dentro do buraco, e só o rabinho ficou de fora, balançando para chamar a Frida.',
     'cartoon boing', 'Luna enterrada na areia até o pescoço.', 'image', 'luna_enterrada'),
    ('narrador', 'De repente, uma sombra branca passou por cima delas e pousou na frente das duas: era a Guga, uma gaivota branca e fofinha, de olho na sacola de biscoito.',
     'cartoon bird whistle', 'Uma gaivota branca fofa pousando na areia.', 'image', 'guga_cookie'),
    ('luna', 'Oi, gaivota... esse lanchinho é meu, viu? Eu tô só... guardando ele com carinho!',
     'cartoon giggle', 'Guga de olho no biscoito da Luna.', 'image', 'guga_dive_2'),
    ('narrador', 'Guga deu um pulinho, subiu, desceu, desceu mais... e num piscar de olhos o biscoito já estava no bico dela.',
     'cartoon boing', 'A gaivota descendo em câmera lenta até o biscoito.', 'seq', 'guga_dive'),
    ('frida', 'Pega, Luna! Essa gaivota tem bico rápido e coração de doce!',
     'cartoon run', 'As cachorrinhas correndo atrás da gaivota.', 'video', 'jump_sunny'),
    ('narrador', 'As duas saíram correndo atrás da Guga, levantando uma poeirinha dourada de areia.',
     'cartoon run', 'Cachorrinhas correndo e pulando na praia ensolarada.', 'video', 'jump_sunny'),
    ('narrador', 'A Guga pousou na beira da água e ficou olhando as duas, como quem diz: me pega se conseguir!',
     'cartoon bird whistle', 'Guga parada na beira da água.', 'image', 'guga_dive_2'),
    ('luna', 'Ei, gaivota! Metade do lanchinho é seu, prometo!',
     'cartoon giggle', 'Luna chamando a gaivota de volta.', 'image', 'guga_cookie'),
    ('narrador', 'A Frida apontou para o mar e teve uma ideia: usar a onda como armadilha.',
     'cartoon fanfare', 'Frida apontando para o oceano.', 'video', 'point_ocean'),
    ('frida', 'Luna, espera a onda! Quando ela chegar, a Guga vai ter que levantar voo bem na nossa frente!',
     'cartoon giggle', 'As duas olhando a onda se aproximando.', 'video', 'look_wave'),
    ('narrador', 'E não é que a onda veio mesmo, grandona e cheia de espuma, e quase pegou as duas de surpresa bem na beirinha.',
     'cartoon splash', 'Uma onda grande chegando perto das cachorrinhas.', 'video', 'react_wave'),
    ('narrador', 'A Guga voou na hora... mas soltou o biscoito, que caiu na areia molhada, e a Luna achou na hora: estava molhado, mas era dela!',
     'cartoon bird whistle', 'A gaivota voando e soltando o biscoito.', 'image', 'guga_biscuit'),
    ('narrador', 'E no meio da correria, a Luna viu uma concha rosa brilhando na areia, e ficou com os olhos acesos.',
     'cartoon fanfare', 'Frida e Luna com a concha rosa na areia.', 'image', 'concha_rosa'),
    ('luna', 'Olha que concha linda! Parece que ela guarda o mar lá dentro!',
     'cartoon fanfare', 'Luna lambendo a concha rosa com cara de surpresa.', 'image', 'concha_lambida'),
    ('narrador', 'Era uma concha cantora: quando a Luna encostou a orelha, ela ouviu o mar inteiro lá dentro.',
     'cartoon fanfare', 'Uma concha cantora retratada de perto.', 'image', 'concha_portrait'),
    ('narrador', 'A água tinha molhado todo mundo, e a Luna aproveitou para sacudir a água bem pertinho da Frida.',
     'cartoon splash', 'Luna sacudindo água em cima da Frida.', 'video', 'shake_water'),
    ('frida', 'Luna! Você molhou meu focinho inteiro! Isso não se faz... deixa eu secar.',
     'cartoon giggle', 'Frida sacudindo a água do focinho.', 'video', 'lick_face'),
    ('narrador', 'A Frida pegou a toalha e as duas se esfregaram, virando duas bolinhas de pano feliz.',
     'cartoon fanfare', 'As duas se secando na toalha colorida.', 'image', 'towel_slide'),
    ('narrador', 'A Guga voltou, pousou devagar e deixou o biscoito molhado bem na frente da Luna.',
     'cartoon bird whistle', 'A gaivota devolvendo o biscoito.', 'image', 'guga_cookie'),
    ('narrador', 'No fim, as três sentaram juntinhas na areia: duas cachorrinhas e uma gaivota, dividindo o lanche e virando amigas de verdade.',
     'cartoon fanfare', 'Duas cachorrinhas se abraçando na praia com a gaivota por perto.', 'image', 'hug'),
    ('narrador', 'O sol foi descendo devagar, pintando o mar de dourado e laranja, e a praia ficou quietinha, só com o barulho das ondas.',
     'cartoon fanfare', 'Frida e Luna abraçadas na areia ao pôr do sol.', 'image', 'abraco_sunset'),
    ('narrador', 'E assim terminou mais um dia na praia: com areia no focinho, uma gaivota de amiga nova e o coração quentinho de alegria.',
     'cartoon giggle', 'As cachorrinhas deslizando juntas na areia.', 'image', 'slide_sand'),
]

# Resolucao por chave -> subcategoria e palavras-chave da descricao real.
MEDIA_KEYS = {
    'walk_beach': ('video', 'walking on beach'),
    'shake_sand': ('video', 'shaking sand on beach'),
    'lick_face': ('video', 'licks sand making face'),
    'jump_sand': ('video', 'jumping on sand'),
    'jump_beach': ('video', 'jumping on beach'),
    'jump_sunny': ('video', 'jumping on sunny beach'),
    'look_wave': ('video', 'looking at approaching wave'),
    'point_ocean': ('video', 'pointing at ocean'),
    'react_wave': ('video', 'reacting to ocean wave'),
    'pose_wave': ('video', 'posing before ocean wave'),
    'shake_water': ('video', 'shaking water on friend'),
    'lick_sand': ('video', 'licks sand on beach'),
    'guga_cookie': ('image', 'diving toward cookie'),
    'guga_dive_2': ('image', 'mergulhando'),
    'guga_biscuit': ('image', 'diving toward biscuit'),
    'hug': ('image', 'hugging on beach'),
    'towel_slide': ('image', 'sliding on beach towel'),
    'slide_sand': ('image', 'sliding together on sand'),
    'concha_rosa': ('image', 'concha_rosa'),
    'concha_portrait': ('image', 'concha_portrait'),
    'concha_lambida': ('image', 'concha_lambida'),
    'abraco_sunset': ('image', 'abraco_por_do_sol'),
    'protetor': ('image', 'protetor'),
    'protetor_escorrega': ('image', 'protetor_escorrega'),
    'luna_espuma': ('image', 'luna_espuma'),
    'luna_enterrada': ('image', 'luna_enterrada'),
    'bucket': ('image', 'Balde Amarelo'),
}

# Sequencias de imagens para STOP-MOTION (quadros progressivos em ordem).
# Regra nova: imagens sao gratis; colocar 2-3 sequencias por video economiza Veo.
SEQUENCES: dict[str, list[str]] = {
    'guga_dive': ['guga_cookie', 'guga_dive_2', 'guga_biscuit'],
}

EMOTION = {
    'narrador': 'contando a historia como uma brincadeira, muito alegre, sorridente e saltitante',
    'frida': 'animada, confiante e engracada, como uma buldogue crianca',
    'luna': 'curiosa, assustada e engracada, como uma salsicha crianca',
}


def main() -> int:
    dados = json.loads(DATA.read_text(encoding='utf-8'))
    pool = [x for x in dados if x['category'] == 'praia']
    # imagens ampliadas (primeiro video v7 + concha revisar)
    amp = json.loads((ROOT / 'work' / 'pool_ampliado.json').read_text(encoding='utf-8'))

    def resolve(kind: str, needle: str) -> dict:
        needle = needle.lower()
        # imagens do pool ampliado (v7/concha) por chave direta
        if kind == 'image' and needle in amp:
            e = amp[needle]
            return {'kind': 'imagem', 'name': needle, 'aria': e['desc'],
                    'abs_path': e['path']}
        # procura item da subcategoria correspondente cuja descricao contenha o needle
        for x in pool:
            if x['kind'] != ('video' if kind == 'video' else 'imagem'):
                continue
            if needle in (x['aria'] or '').lower():
                return x
        # fallback: qualquer item com o needle em qualquer campo
        for x in pool:
            if x['kind'] != ('video' if kind == 'video' else 'imagem'):
                continue
            hay = f"{x['aria']} {x['name']}".lower()
            if needle in hay:
                return x
        raise LookupError(f'media nao encontrada: {kind}:{needle}')

    scenes = []
    assignment = {}
    last_speaker = ['narrador']
    for i, (speaker, text, sfx, action, mtype, mkey) in enumerate(STORY):
        sid = f'sc_{i + 1:02d}'
        characters = ['Frida', 'Luna']
        if any(t in text.lower() for t in ('guga', 'gaivota')):
            characters.append('Guga')
        if mtype == 'seq':
            seq_media = []
            for n in SEQUENCES[mkey]:
                k2, needle2 = MEDIA_KEYS[n]
                seq_media.append(resolve(k2, needle2))
            scenes.append({
                'scene_id': sid,
                'act': 1 if i < 9 else (2 if i < 18 else 3),
                'speaker': speaker,
                'emotion_direction': EMOTION[speaker],
                'text': text,
                'location': 'Praia ensolarada com areia, ondas, toalha e a gaivota Guga',
                'visual_action': action,
                'sfx': sfx,
                'comedy_beat': action,
                'avatar_mode': 'none' if speaker == 'narrador' else speaker,
                'avatar_pip': speaker != 'narrador',
                'characters': characters,
                'video': '',
                'image': seq_media[0]['name'],
                'image_sequence': [m['name'] for m in seq_media],
            })
            assignment[sid] = {
                'video': '', 'video_desc': '',
                'image': seq_media[0]['name'], 'image_desc': ' '.join(m['aria'] for m in seq_media),
                'image_sequence': [m['name'] for m in seq_media],
            }
            continue
        kind, needle = MEDIA_KEYS[mkey]
        media = resolve(kind, needle)
        is_video = (media['kind'] == 'video')
        scenes.append({
            'scene_id': sid,
            'act': 1 if i < 9 else (2 if i < 18 else 3),
            'speaker': speaker,
            'emotion_direction': EMOTION[speaker],
            'text': text,
            'location': 'Praia ensolarada com areia, ondas, toalha e a gaivota Guga',
            'visual_action': action,
            'sfx': sfx,
            'comedy_beat': action,
            'avatar_mode': 'none' if speaker == 'narrador' else speaker,
            'avatar_pip': speaker != 'narrador',
            'characters': characters,
            'video': media['name'] if is_video else '',
            'image': '' if is_video else media['name'],
        })
        assignment[sid] = {
            'video': media['name'] if is_video else '',
            'video_desc': media['aria'] if is_video else '',
            'image': '' if is_video else media['name'],
            'image_desc': '' if is_video else media['aria'],
        }

    # despedida canonica (video) — cena final com id dinamico
    goodbye_sid = f'sc_{len(scenes) + 1:02d}'
    scenes.append({
        'scene_id': goodbye_sid, 'act': 3, 'speaker': 'narrador',
        'emotion_direction': EMOTION['narrador'],
        'text': 'Se você curtiu a Guga e a bagunça, se inscreve no canal e vem com a gente na próxima praia!',
        'location': 'Despedida com YOUTUBE e SUBSCRIBE',
        'visual_action': 'Frida, Luna e Guga acenando com confete, YouTube e SUBSCRIBE na tela.',
        'sfx': 'cartoon fanfare', 'comedy_beat': 'As três acenam para a câmera.',
        'avatar_mode': 'none', 'avatar_pip': False,
        'characters': ['Frida', 'Luna', 'Guga'],
        'video': f'{goodbye_sid}.mp4', 'image': '',
    })
    assignment[goodbye_sid] = {
        'video': f'{goodbye_sid}.mp4', 'video_desc': 'Despedida canonica com YOUTUBE e SUBSCRIBE',
        'image': '', 'image_desc': '',
    }

    script_data = {
        'title': 'A PRAIA PARTE 2 — O BISCOITO ROUBADO DA GUGA',
        'thumb_hook': 'A GAIVOTA ROUBOU O BISCOITO!',
        'description': ('Frida e Luna voltam à praia e conhecem Guga, uma gaivota branca muito atrevida '
                        'que rouba o biscoito e apronta com a maré!'),
        'tags': ['frida e luna', 'gaivota guga', 'historia infantil', 'desenho animado', 'praia parte 2'],
        'target_minutes': 4.0,
        'catchphrase': 'Pode ficar com a concha, mas o biscoito, nem pensar!',
        'secondary_characters': [{
            'name': 'Guga',
            'description': 'Gaivota branca fofinha e atrevida, mora na praia e adora biscoito.',
        }],
        'story_props': [{'name': 'Biscoitinho da Luna', 'description': 'Sacolinha de biscoitos que a Guga rouba.'}],
        'scenes': scenes,
    }
    OUT_SCRIPT.write_text(json.dumps(script_data, ensure_ascii=False, indent=2), encoding='utf-8')

    # copia arquivos + manifesto
    sel_by_name = {x['name']: x for x in pool}
    for d in ('artifacts', 'assets/images', 'assets/videos', 'assets/audio/raw',
              'assets/audio/wav', 'assets/characters'):
        (PROJ / d).mkdir(parents=True, exist_ok=True)
    for sid, a in assignment.items():
        if a['video'] and a['video'] != 'sc_30.mp4':
            x = sel_by_name.get(a['video'])
            if x:
                src = SEL / x['relative']
                dst = PROJ / 'assets' / 'videos' / f'{sid}.mp4'
                if src.exists() and not dst.exists():
                    shutil.copy2(src, dst)
        elif a.get('image_sequence'):
            # stop-motion: N quadros progressivos -> sc_XX_p1..pN.jpg
            for idx, name in enumerate(a['image_sequence'], 1):
                src = None
                x = sel_by_name.get(name)
                if x:
                    src = SEL / x['relative']
                elif name in amp:
                    src = Path(amp[name]['path'])
                if src and src.exists():
                    dst = PROJ / 'assets' / 'images' / f'{sid}_p{idx}.jpg'
                    if not dst.exists():
                        shutil.copy2(src, dst)
        elif a['image']:
            # Regra 28: cena parada = MESMA imagem base em todas as partes (p1..p5),
            # com Ken Burns + dissolve longo. Copiamos a imagem para cada parte.
            src = None
            x = sel_by_name.get(a['image'])
            if x:
                src = SEL / x['relative']
            elif a['image'] in amp:
                src = Path(amp[a['image']]['path'])
            if src and src.exists():
                for pidx in range(1, 6):
                    dst = PROJ / 'assets' / 'images' / f'{sid}_p{pidx}.jpg'
                    if not dst.exists():
                        shutil.copy2(src, dst)

    # retrato da Guga (personagem recorrente) — a gaivota BRANCA que voa (diving),
    # NAO a gaivota gorda de oculos de sol (imagem "Guga"/"chubby" que e outra personagem).
    guga_src = ROOT / 'assets' / 'reference' / 'primeiro-dia-de-praia' / 'flow_all' / \
        'acc_2' / 'images' / 'acc_2_d43a0933_img_04_800d311569.jpg'
    guga_dst = PROJ / 'assets' / 'characters' / 'guga_portrait.jpg'
    if guga_src.exists() and not guga_dst.exists():
        shutil.copy2(guga_src, guga_dst)

    # despedida canonica (materializa video + frame no id dinamico)
    from core.goodbye_video import prepare_goodbye
    prepare_goodbye(PROJ)
    gb_src = PROJ / 'assets' / 'videos' / 'sc_30.mp4'
    gb_dst = PROJ / 'assets' / 'videos' / f'{goodbye_sid}.mp4'
    if gb_src.exists() and not gb_dst.exists():
        shutil.copy2(gb_src, gb_dst)
    gb_frame = PROJ / 'assets' / 'images' / f'{goodbye_sid}_p1.jpg'
    if not gb_frame.exists():
        subprocess.run([FFMPEG_EXE, '-y', '-v', 'error', '-ss', '1.0', '-i', str(gb_dst),
                        '-frames:v', '1', '-q:v', '3', str(gb_frame)], capture_output=True)

    (PROJ / 'artifacts' / 'media_assignment.json').write_text(
        json.dumps(assignment, ensure_ascii=False, indent=2), encoding='utf-8')
    (PROJ / 'artifacts' / 'script_v2.json').write_text(
        json.dumps(script_data, ensure_ascii=False, indent=2), encoding='utf-8')

    from collections import Counter
    spk = Counter(s['speaker'] for s in scenes)
    narr_ratio = spk.get('narrador', 0) / len(scenes)
    n_img = sum(1 for a in assignment.values() if a['image'])
    n_vid = sum(1 for a in assignment.values() if a['video'])
    print(f'[construir] {len(scenes)} cenas | speakers={dict(spk)} | narracao={narr_ratio:.0%}')
    print(f'[construir] cenas de VIDEO: {n_vid} | cenas de IMAGEM (intercaladas): {n_img}')
    print(f'[construir] roteiro: {OUT_SCRIPT} | manifesto: media_assignment.json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
