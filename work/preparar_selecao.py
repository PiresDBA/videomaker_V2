# -*- coding: utf-8 -*-
"""Separa todo o material gerado em pastas por categoria e gera o carrossel HTML.

Categorias (pastas):
  praia/          - desenhos Disney de cachorros na praia (o que vai para a continue)
  humano_avatar/  - videos/fotos de pessoa falando a camera (avatar do usuario)
  boneco_palito/  - stick figures / kinetic typography / motion graphics
  outro_desenho/  - outros desenhos (nave, parque, banheira, obstaculos...)
  revisar/        - sem descricao e sem correspondencia visual confiavel

Dentro de cada categoria ha subpastas imagens/ e videos/. Nada e movido: os
originais em assets/reference/.../flow_all permanecem intactos.

Uso: python work/preparar_selecao.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import FFMPEG_EXE  # noqa: E402
from core.delivery_audit import sha256, signature, sim  # noqa: E402

REF = ROOT / 'assets' / 'reference' / 'primeiro-dia-de-praia'
FLOW = REF / 'flow_all'
META_PATH = REF / 'analise_v2_all.json'
OUT = ROOT / 'work' / 'selecao_continuacao'
THUMBS = OUT / 'thumbs'

CATS = ('praia', 'humano_avatar', 'boneco_palito', 'outro_desenho', 'revisar')

# --- regras de categorizacao (ordem de prioridade) -------------------------
HUMANO = re.compile(
    r'man speaking|camera|man looking|man pointing|man typing|man holding|'
    r'girl crouch|woman|person|human|talking head|selfie|studio|\bman\b|\bgirl\b',
    re.I,
)
PALITO = re.compile(
    r'stick\s?figure|stickman|stickbrain|kinetic typography|motion graphi|'
    r'motion graphic|lighthouse|storm over the lamp|inspector pell|wren|'
    r'flipping|scrolling and forgett',
    re.I,
)
BEACH = re.compile(
    r'beach|praia|ocean|sea|wave|onda|sand|areia|shell|concha|castle|castelo|'
    r'water|\bagua\b|wet|molh|foam|espuma|surf|bucket|balde|towel|toalha|'
    r'umbrella|guarda-sol|sunset|por do sol|dune|duna|shore|costa|seaside|'
    r'swim|flutu|seagull|gaivota|sunscreen|protetor',
    re.I,
)
OFF_CARTOON = re.compile(
    r'spaceship|park|grass|bathtub|bath|pet shop|hallway|\bcars?\b|bird|pigeon|'
    r'\bants?\b|backpack|forest|trophy|living room|sofa|snow|mountain|street|'
    r'bedroom|kitchen|butterfly|cat|fountain|daisy|bicycle|skater|\bone\b|'
    r'kitten|groom|cliff|couch|pillow|\bbed\b|oak|\btree\b|biscuit|cookie|'
    r'duck|flower|garden|\btoy\b|treat|track|\bhill\b|rug|carpet|window|'
    r'obstacle course|confetti|monster|glowing hearts|green ball|sneeze|'
    r'fork path|\bspear\b|\bclock\b|question mark|in room|\broom\b|'
    r'\bmap\b|\bphone\b|smartphone|\bstudio\b',
    re.I,
)

# subcategorias da praia (para filtros no carrossel)
SUBCATS: list[tuple[str, re.Pattern]] = [
    ('Areia', re.compile(r'sand|areia|dig|escav|slide|desliz|fall|cai', re.I)),
    ('Água e ondas', re.compile(r'water|wave|ocean|sea|wet|molh|foam|espuma|swim|splash|surf', re.I)),
    ('Toalha e guarda-sol', re.compile(r'towel|toalha|umbrella|guarda-sol|sunscreen|protetor|loung', re.I)),
    ('Balde e brinquedos', re.compile(r'bucket|balde|ball|bola|shovel|pá ', re.I)),
    ('Conchas e gaivota', re.compile(r'shell|concha|seagull|gaivota', re.I)),
    ('Carinho', re.compile(r'hug|abraç|cudd|kiss|beij|heads together|leaning', re.I)),
    ('Correndo e brincando', re.compile(r'run|corr|jump|salt|play|brinc|circle|racing', re.I)),
    ('Dormindo', re.compile(r'sleep|dorm|nap|cochil|rest', re.I)),
    ('Retratos', re.compile(r'portrait|close|face|cara|smile|sorris|posing', re.I)),
    ('Céu e pôr do sol', re.compile(r'sky|sunset|por do sol|cloud|nuvem|sun', re.I)),
]


def meta_map() -> dict[str, dict[str, Any]]:
    data = json.loads(META_PATH.read_text(encoding='utf-8'))
    return {str(x.get('path', '')): x for x in data if isinstance(x, dict)}


def text_of(m: dict[str, Any], p: Path, mm: dict[str, Any]) -> str:
    if mm:
        return f"{mm.get('aria', '')} {mm.get('scene', '')}".strip()
    return p.stem


def classify(m: dict[str, Any], p: Path, mm: dict[str, Any]) -> tuple[str, str]:
    """Retorna (categoria, subcategoria)."""
    text = text_of(m, p, mm)
    # 1) humano / avatar tem prioridade maxima
    if HUMANO.search(text) and not re.search(r'puppy|dog|bulldog|dachshund', text, re.I):
        return 'humano_avatar', ''
    # 2) bonecos de palito / motion graphics
    if PALITO.search(text):
        return 'boneco_palito', ''
    # 3) Guga (a gaivota branca) tem prioridade: mesmo roubando biscoito, e praia
    if re.search(r'seagull|gaivota|\bguga\b', text, re.I):
        return 'praia', 'Conchas e gaivota'
    # 4) praia (tem palavra de praia e nao tem outro cenario)
    if BEACH.search(text) and not OFF_CARTOON.search(text):
        sub = 'Geral'
        for name, rx in SUBCATS:
            if rx.search(text):
                sub = name
                break
        return 'praia', sub
    # 5) outros desenhos
    if OFF_CARTOON.search(text):
        return 'outro_desenho', ''
    return 'revisar', ''


def unique_files(pattern: str) -> list[Path]:
    seen, out = set(), []
    for p in sorted(FLOW.glob(pattern)):
        h = sha256(p)
        if h not in seen:
            seen.add(h)
            out.append(p)
    return out


def video_frame(video: Path, dest: Path) -> bool:
    """Extrai um quadro com timeout (video corrompido nao pode travar o lote)."""
    if dest.exists() and dest.stat().st_size > 500:
        return True
    for ss in ('0.5', '0.1', '0'):
        try:
            r = subprocess.run(
                [FFMPEG_EXE, '-y', '-v', 'error', '-ss', ss, '-i', str(video),
                 '-frames:v', '1', '-vf', 'scale=320:180', str(dest)],
                capture_output=True, timeout=20,
            )
            if r.returncode == 0 and dest.exists() and dest.stat().st_size > 500:
                return True
        except (subprocess.TimeoutExpired, OSError):
            continue
    dest.unlink(missing_ok=True)
    return False


def main() -> int:
    mm = meta_map()
    for c in CATS:
        for kind in ('imagens', 'videos'):
            (OUT / c / kind).mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)

    imgs = unique_files('acc_*/images/*.jpg')
    vids = unique_files('acc_*/videos/*.mp4')

    proj = ROOT / 'projects' / 'primeiro-dia-de-praia-v7' / 'assets'
    used_sha = {sha256(p) for p in list((proj / 'images').glob('*.jpg')) +
                list((proj / 'videos').glob('*.mp4'))}

    # assinaturas de referencia por categoria para herdar em arquivos sem descricao
    refs: dict[str, list] = {c: [] for c in CATS}
    classified: list[dict[str, Any]] = []

    def add(p: Path, kind: str) -> dict[str, Any]:
        m = mm.get(str(p), {})
        aria = str(m.get('aria') or '').strip()
        described = bool(aria) and not aria.lower().endswith(('.jpg', '.png', '.jpeg'))
        cat, sub = classify(m, p, m)
        item = {
            'kind': kind, 'name': p.name, 'path': str(p), 'account': p.parent.parent.name,
            'aria': aria, 'scene': str(m.get('scene') or ''), 'described': described,
            'category': cat, 'subcategory': sub, 'sha256': sha256(p),
            'size': p.stat().st_size, 'usado_v7': sha256(p) in used_sha,
        }
        classified.append(item)
        return item

    for p in imgs:
        add(p, 'imagem')
    for p in vids:
        add(p, 'video')

    # heranca visual para itens sem descricao confiavel (assinaturas em cache)
    sig_cache: dict[str, Any] = {}

    def sig_of(path: Path) -> Any:
        key = str(path)
        if key not in sig_cache:
            try:
                sig_cache[key] = signature(path)
            except Exception:
                sig_cache[key] = None
        return sig_cache[key]

    for kind in ('imagem', 'video'):
        refs: list[tuple[Any, str, str]] = []
        for other in classified:
            if other['kind'] != kind or not other['described']:
                continue
            if kind == 'imagem':
                s0 = sig_of(Path(other['path']))
            else:
                q = THUMBS / f"ref_{other['name']}.jpg"
                if not video_frame(Path(other['path']), q):
                    continue
                s0 = sig_of(q)
            if s0 is not None:
                refs.append((s0, other['category'], other['subcategory']))
        for item in [x for x in classified if x['kind'] == kind and not x['described']]:
            p = Path(item['path'])
            if kind == 'imagem':
                s = sig_of(p)
            else:
                dest = THUMBS / f"match_{abs(hash(item['name']))}.jpg"
                if not video_frame(p, dest):
                    item['category'], item['subcategory'] = 'revisar', ''
                    continue
                s = sig_of(dest)
            best, bestcat, bestsub = 0.0, '', ''
            if s is not None:
                for s0, cat0, sub0 in refs:
                    try:
                        v = sim(s, s0)
                    except Exception:
                        continue
                    if v > best:
                        best, bestcat, bestsub = v, cat0, sub0
            threshold = 0.70 if kind == 'imagem' else 0.65
            if best >= threshold and bestcat:
                item['category'], item['subcategory'] = bestcat, bestsub
                item['inherited'] = round(best, 2)
            else:
                item['category'], item['subcategory'] = 'revisar', ''
                item['inherited'] = round(best, 2)

    # copia para as pastas + gera thumbs
    for item in classified:
        p = Path(item['path'])
        sub = 'imagens' if item['kind'] == 'imagem' else 'videos'
        dest_dir = OUT / item['category'] / sub
        dest = dest_dir / p.name
        if not dest.exists():
            shutil.copy2(p, dest)
        item['relative'] = f"{item['category']}/{sub}/{p.name}"
        item['thumb'] = ''
        tdest = THUMBS / f"{p.stem}.jpg"
        if item['kind'] == 'imagem':
            if not tdest.exists():
                with Image.open(p) as im:
                    im.thumbnail((400, 400))
                    im.convert('RGB').save(tdest, quality=82)
            item['thumb'] = f"thumbs/{tdest.name}"
        else:
            if not tdest.exists():
                video_frame(p, tdest)
            item['thumb'] = f"thumbs/{tdest.name}" if tdest.exists() else ''

    (OUT / 'dados.json').write_text(
        json.dumps(classified, ensure_ascii=False, indent=2), encoding='utf-8')
    write_html(classified)

    from collections import Counter
    print('[selecao] categorias:', dict(Counter(x['category'] for x in classified)))
    print('[selecao] praia por subcategoria:',
          dict(Counter(x['subcategory'] for x in classified if x['category'] == 'praia')))
    print('[selecao] pasta:', OUT)
    return 0


def write_html(items: list[dict[str, Any]]) -> None:
    """Gera carrossel auto-contido com filtros, busca e selecao."""
    from collections import Counter
    cats = Counter(x['category'] for x in items)
    subs = Counter(x['subcategory'] for x in items if x['category'] == 'praia')
    payload = json.dumps(items, ensure_ascii=False).replace('</', '<\\/')
    tpl = r'''<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Seleção da Continuação — Praia</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0f1116;color:#e9edf5;font:14px/1.4 system-ui,"Segoe UI",sans-serif}
header{padding:18px 22px;background:linear-gradient(90deg,#123,#1a2b3a);border-bottom:1px solid #2b3b4d;position:sticky;top:0;z-index:20}
h1{margin:0;font-size:20px;color:#7ee3ff}header p{margin:6px 0 0;color:#9fb3c8;font-size:13px}
.bar{padding:12px 22px;background:#151922;border-bottom:1px solid #263042;display:flex;flex-wrap:wrap;gap:12px;align-items:center;position:sticky;top:78px;z-index:19}
.tab,.chip,.sub{background:#20283a;color:#cbd8e8;border:1px solid #34435a;border-radius:20px;padding:6px 13px;cursor:pointer;font-size:13px}
.tab.on,.chip.on{background:#0aa3c2;color:#fff;border-color:#0aa3c2}.sub.on{background:#c2860a;color:#fff;border-color:#c2860a}
input#q{flex:1;min-width:180px;background:#0d1017;color:#e9edf5;border:1px solid #34435a;border-radius:8px;padding:8px 12px}
#count{margin-left:auto;color:#8fa3ba;font-size:13px}#selCount{color:#7ee3ff;font-weight:bold}
main{padding:18px 22px;display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:14px}
.card{background:#171c26;border:1px solid #2b3648;border-radius:10px;overflow:hidden;cursor:pointer;transition:.15s}
.card:hover{border-color:#0aa3c2;transform:translateY(-2px)}
.card .thumb{height:130px;background:#0a0d13;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative}
.card img{width:100%;height:100%;object-fit:cover}.play{position:absolute;color:#fff;background:#0009;border-radius:50%;width:38px;height:38px;display:grid;place-items:center;font-size:17px}
.card .body{padding:9px 11px}.card .desc{height:38px;overflow:hidden;font-size:12px;color:#e9edf5}
.card .meta{font-size:11px;color:#8296ad;margin-top:6px;display:flex;justify-content:space-between;align-items:center}
.badge{background:#26415a;color:#9fe0ff;border-radius:9px;padding:2px 7px;font-size:10px}
.badge.avatar{background:#5a2638;color:#ffb3cb}.badge.palito{background:#4a3a1e;color:#ffd98a}
.badge.outro{background:#3a3a44;color:#c8c8d4}.badge.revisar{background:#5a4a1e;color:#ffe08a}
.card a{color:#7ee3ff;text-decoration:none;font-size:11px}.card label{display:flex;gap:5px;align-items:center;margin-top:7px;font-size:11px;color:#9fb3c8;cursor:pointer}
#modal{display:none;position:fixed;inset:0;background:#000d;z-index:50;align-items:center;justify-content:center;padding:30px}
#modal.show{display:flex}.stage{background:#131823;border:1px solid #34435a;border-radius:12px;max-width:96vw;max-height:94vh;overflow:auto;padding:14px}
#stageMedia{max-width:90vw;max-height:70vh;border-radius:8px;display:block;margin:auto}
#stageInfo{display:flex;gap:10px;align-items:center;justify-content:center;margin-top:12px;flex-wrap:wrap}
#stageInfo button{background:#20283a;color:#fff;border:1px solid #34435a;border-radius:8px;padding:8px 14px;cursor:pointer}
#stageInfo a{color:#7ee3ff}.nav{position:fixed;top:50%;font-size:36px;color:#fff;background:#0007;border:0;border-radius:50%;width:52px;height:52px;cursor:pointer}
#prev{left:14px}#next{right:14px}
footer{padding:14px 22px;color:#8296ad;font-size:12px;border-top:1px solid #263042}
</style></head><body>
<header><h1>🎬 Seleção da Continuação — tudo que é da praia</h1>
<p id="resumo"></p></header>
<div class="bar">
<button class="tab on" data-tab="video">🎞 Vídeos</button>
<button class="tab" data-tab="imagem">🖼 Fotos</button>
<button class="chip on" data-cat="todos">Tudo</button>
<button class="chip" data-cat="praia">✅ Praia (usar)</button>
<button class="chip" data-cat="humano_avatar">🧑 Humano/Avatar</button>
<button class="chip" data-cat="boneco_palito">🪆 Boneco de palito</button>
<button class="chip" data-cat="outro_desenho">🎨 Outro desenho</button>
<button class="chip" data-cat="revisar">❓ Revisar</button>
<button class="chip" data-cat="novo">🆕 Só não usados no v7</button>
<button class="chip" data-cat="usado">♻️ Já usados no v7</button>
<span id="subs"></span>
<input id="q" placeholder="Buscar descrição, arquivo, conta...">
<span id="count"></span><span id="selCount"></span>
</div>
<main id="grid"></main>
<footer>Escolha os itens com o checkbox e use "Exportar seleção" para gerar a lista do batimento. Clique no card para ampliar; ← → navegam no carrossel.</footer>
<div id="modal"><button class="nav" id="prev">‹</button>
<div class="stage"><div id="stageMedia"></div><div id="stageInfo">
<button id="close">✕ Fechar</button><button id="delSel">Marcar para usar</button>
<a id="open" target="_blank">↗ Abrir arquivo</a><span id="pos"></span></div></div>
<button class="nav" id="next">›</button></div>
<script>
const DATA=__DATA__;
const CATS={praia:'Praia',humano_avatar:'Humano/Avatar',boneco_palito:'Boneco de palito',outro_desenho:'Outro desenho',revisar:'Revisar'};
const SUBS=__SUBS__;
let tab='video',cat='todos',sub='',query='',view=[],idx=0;
const selected=new Set();
document.getElementById('resumo').textContent=Object.entries(__CATS__).map(([k,v])=>v+' '+k).join('  |  ');
function render(){
  view=DATA.filter(x=>x.kind===tab&&
    (cat==='todos'||(cat==='novo'&&!x.usado_v7)||(cat==='usado'&&x.usado_v7)||(cat!=='novo'&&cat!=='usado'&&x.category===cat))&&
    (!sub||x.subcategory===sub)&&
    (!query||(x.aria+' '+x.name+' '+x.account+' '+x.scene).toLowerCase().includes(query)));
  const g=document.getElementById('grid');g.innerHTML='';
  for(const x of view){
    const c=document.createElement('div');c.className='card';
    const img=x.thumb?'<img src="'+x.thumb+'" loading="lazy">':'<span>sem miniatura</span>';
    const badge=x.category==='praia'?'':(' '+x.category.replace('_',' '));
    c.innerHTML='<div class="thumb">'+img+(x.kind==='video'?'<span class="play">▶</span>':'')+'</div>'+
      '<div class="body"><div class="desc">'+(x.aria||x.name)+'</div>'+
      '<div class="meta"><span class="badge '+x.category+'">'+(x.subcategory||CATS[x.category]||x.category)+badge+'</span><span>'+x.account+'</span></div>'+
      '<div class="meta"><a href="'+x.relative+'" target="_blank">↗ abrir</a><span>'+
      (x.usado_v7?'♻️ v7':'🆕 novo')+'</span></div>'+
      '<label><input type="checkbox" '+(selected.has(x.path)?'checked':'')+' data-path="'+x.path+'"> usar no vídeo</label></div>';
    c.onclick=e=>{if(e.target.tagName!=='INPUT'&&e.target.tagName!=='A')openModal(x)};
    g.appendChild(c);
  }
  document.getElementById('count').textContent=view.length+' itens';
  document.getElementById('selCount').textContent=' | '+selected.size+' selecionados';
  const s=document.getElementById('subs');s.innerHTML='';
  if(cat==='praia'){
    for(const k of Object.keys(SUBS)){
      const b=document.createElement('button');b.className='sub'+(sub===k?' on':'');
      b.textContent=k+' ('+SUBS[k]+')';b.onclick=()=>{sub=sub===k?'':k;render()};s.appendChild(b);
    }
  }
}
function openModal(x){idx=view.indexOf(x);show();document.getElementById('modal').classList.add('show')}
function show(){
  const x=view[idx];if(!x)return;
  document.getElementById('stageMedia').innerHTML=x.kind==='video'?
    '<video id="mp" src="'+x.relative+'" controls autoplay playsinline style="max-width:90vw;max-height:70vh"></video>':
    '<img id="mp" src="'+x.relative+'" style="max-width:90vw;max-height:70vh">';
  document.getElementById('open').href=x.relative;
  document.getElementById('pos').textContent=(idx+1)+' / '+view.length+' — '+(x.aria||x.name);
  document.getElementById('delSel').textContent=selected.has(x.path)?'✓ Selecionado':'Marcar para usar';
}
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));b.classList.add('on');tab=b.dataset.tab;sub='';render()});
document.querySelectorAll('.chip').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('.chip').forEach(t=>t.classList.remove('on'));b.classList.add('on');cat=b.dataset.cat;sub='';render()});
document.getElementById('q').oninput=e=>{query=e.target.value.toLowerCase();render()};
document.getElementById('close').onclick=()=>document.getElementById('modal').classList.remove('show');
document.getElementById('prev').onclick=()=>{idx=(idx-1+view.length)%view.length;show()};
document.getElementById('next').onclick=()=>{idx=(idx+1)%view.length;show()};
document.getElementById('delSel').onclick=()=>{const p=view[idx].path;selected.has(p)?selected.delete(p):selected.add(p);show();render()};
document.addEventListener('change',e=>{if(e.target.dataset.path){e.target.checked?selected.add(e.target.dataset.path):selected.delete(e.target.dataset.path);
  document.getElementById('selCount').textContent=' | '+selected.size+' selecionados'}});
document.addEventListener('keydown',e=>{if(!document.getElementById('modal').classList.contains('show'))return;
  if(e.key==='ArrowLeft')document.getElementById('prev').click();
  if(e.key==='ArrowRight')document.getElementById('next').click();
  if(e.key==='Escape')document.getElementById('close').click()});
render();
</script></body></html>'''
    tpl = (tpl.replace('__DATA__', payload)
              .replace('__SUBS__', json.dumps(dict(subs), ensure_ascii=False))
              .replace('__CATS__', json.dumps(dict(cats), ensure_ascii=False)))
    (OUT / 'index.html').write_text(tpl, encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
