# -*- coding: utf-8 -*-
"""Gera listas com hiperlinks clicaveis e atualiza o relatorio de continuacao."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'work' / 'selecao_continuacao'
items = json.loads((OUT / 'dados.json').read_text(encoding='utf-8'))


def link(p: Path, label: str) -> str:
    return f"[▶ {label}]({p.as_uri()})"


def write_list(kind: str, title: str, filename: str) -> None:
    rows = [x for x in items if x['category'] == 'praia' and x['kind'] == kind]
    lines = [f'# {title}', '',
             f'Total: **{len(rows)}** itens de praia para a continuação.', '',
             '| # | Descrição | Categoria | Arquivo (clique para abrir) |',
             '| ---: | --- | --- | --- |']
    for i, x in enumerate(rows, 1):
        p = OUT / x['relative']
        label = x['name']
        lines.append(f"| {i} | {x['aria'] or x['name']} | {x['subcategory']} | {link(p, label)} |")
    lines.append('')
    (OUT / filename).write_text('\n'.join(lines), encoding='utf-8')


write_list('video', 'Vídeos de praia — clicáveis', 'lista_videos_praia.md')
write_list('imagem', 'Fotos de praia — clicáveis', 'lista_fotos_praia.md')

cats = Counter(x['category'] for x in items)
subs = Counter(x['subcategory'] for x in items if x['category'] == 'praia')
vids = [x for x in items if x['category'] == 'praia' and x['kind'] == 'video']
imgs = [x for x in items if x['category'] == 'praia' and x['kind'] == 'imagem']
rep = ROOT / 'work' / 'relatorio_continuacao_praia.md'
rep.write_text('\n'.join([
    '# Continuação — separação do material gerado (versão 2 da praia)', '',
    'O inventário anterior (57 "vídeos de praia") estava **errado**: arquivos sem descrição '
    'foram contados como praia por padrão. A conferência quadro a quadro mostrou que a maioria '
    'era parque, obstáculos, motion graphics e o avatar (homem falando à câmera).', '',
    '## Contagem real por categoria', '',
    '| Categoria | Imagens | Vídeos | Total |',
    '| --- | ---: | ---: | ---: |',
    *[f"| {c} | {sum(1 for x in items if x['category']==c and x['kind']=='imagem')} "
      f"| {sum(1 for x in items if x['category']==c and x['kind']=='video')} "
      f"| {cats[c]} |" for c in ('praia', 'humano_avatar', 'boneco_palito', 'outro_desenho', 'revisar', 'defeitos')],
    '',
    f'**Praia utilizável: {len(imgs)} fotos e {len(vids)} vídeos** '
    f'(inclui a gaivota branca Guga roubando o biscoito da Luna).', '',
    '## Praia por subcategoria (filtros do carrossel)', '',
    '| Subcategoria | Itens |', '| --- | ---: |',
    *[f'| {k} | {v} |' for k, v in sorted(subs.items())], '',
    '## Arquivos', '',
    '- Carrossel com filtros: `work/selecao_continuacao/index.html` (abrir com `work/abrir_carrossel.bat`)',
    '- Vídeos clicáveis: `work/selecao_continuacao/lista_videos_praia.md`',
    '- Fotos clicáveis: `work/selecao_continuacao/lista_fotos_praia.md`',
    '- Dados completos: `work/selecao_continuacao/dados.json`', '',
]), encoding='utf-8')
print('listas e relatorio atualizados')
print('praia:', len(imgs), 'fotos,', len(vids), 'videos')
print('categorias:', dict(cats))
