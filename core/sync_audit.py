# -*- coding: utf-8 -*-
"""Auditoria de SINCRONIA NARRACAO x VISUAL para episodios que REUTILIZAM midia.

Historico / bug que motivou este modulo:
  Na Parte 2 da praia, a narracao falava de "gaivota Guga roubando biscoito"
  enquanto o video mostrava "cachorro lambendo areia" — porque a midia foi
  atribuida por rodizio mecanico e NENHUMA checagem semantica rodava. O
  pipeline que GERA do zero tem o scene_auditor (Vision) para casar cena x
  imagem, mas no caminho de REUTILIZACAO (--skip-images/--skip-veo) essa
  checagem nao roda, deixando o video sair "sem pe nem cabeca".

Este modulo fecha o buraco, sem depender de Vision: exige um manifesto de midia
com DESCRICOES por cena (artifacts/media_assignment.json) e audita:
  1. COBERTURA DE PERSONAGEM: personagem secundario (ex.: Guga) que aparece na
     narracao de N cenas deve aparecer visualmente em pelo menos 1 delas.
  2. ALINHAMENTO DE ANCORA: quando a fala cita uma ancora forte (gaivota,
     biscoito, castelo, concha, balde, toalha, protetor), a midia designada
     precisa conter essa ancora (ou sinonimo) — senao e reprovada.

Formato do manifesto (escrito por quem prepara a midia):
{
  "sc_01": {"video": "sc_01.mp4", "video_desc": "Puppy shaking sand on beach",
            "image": "sc_01_p1.jpg", "image_desc": "..."},
  ...
}
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

# Grupos de sinonimos PT/EN para ancoras e especies. Ordem = prioridade de "ancora forte".
ANCHOR_SYNSETS: tuple[tuple[str, frozenset[str]], ...] = (
    ("gaivota", frozenset({"gaivota", "seagull", "gull", "guga", "gaivotinha"})),
    ("biscoito", frozenset({"biscoito", "cookie", "biscuit", "bolacha", "biscoitinho"})),
    ("castelo", frozenset({"castelo", "castle", "castelinho"})),
    ("concha", frozenset({"concha", "shell", "conchinha", "seashell"})),
    ("balde", frozenset({"balde", "bucket", "baldinho", "pá", "pa"})),
    ("toalha", frozenset({"toalha", "towel", "toalhinha"})),
    ("protetor", frozenset({"protetor", "sunscreen", "creme", "bloqueador"})),
    ("passaro", frozenset({"passaro", "passarinho", "pássaro", "bird", "pigeon",
                           "seagull", "gaivota", "gull"})),
    ("onda", frozenset({"onda", "wave", "ocean", "mar", "sea", "agua", "água",
                        "water", "ondinha", "espuma", "foam"})),
    ("areia", frozenset({"areia", "sand", "areinha"})),
)

# Ancoras "fortes" = se citadas na fala, a midia precisa conter a mesma ancora.
# "gaivota"/"passaro" ficam FORA: cena de perseguicao narra a gaivota mas mostra o
# cachorro correndo (legitimo) — a presenca da gaivota e garantida pela COBERTURA.
STRONG_ANCHORS = ("biscoito", "castelo", "concha", "balde", "toalha", "protetor")


def _norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFKD", (s or "").lower())
                    .encode("ascii", "ignore").decode("ascii").split())


def _synsets(text: str) -> set[str]:
    hay = _norm(text)
    found: set[str] = set()
    for name, words in ANCHOR_SYNSETS:
        for w in words:
            if re.search(rf"\b{re.escape(w)}\b", hay):
                found.add(name)
                break
    return found


def _media_desc_for(assignment: dict[str, Any]) -> str:
    return " ".join(filter(None, (
        str(assignment.get("video_desc") or ""),
        str(assignment.get("image_desc") or ""),
    )))


def audit_narration_sync(proj_dir: Path, script_data: dict[str, Any]) -> list[str]:
    """Retorna lista de problemas de sincronia narracao x visual (fail-closed)."""
    manifest_path = proj_dir / "artifacts" / "media_assignment.json"
    if not manifest_path.exists():
        return ["media_assignment.json ausente: nao e possivel auditar narracao x visual "
                "(gere o manifesto ao preparar a midia reutilizada)"]

    try:
        assignment = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"media_assignment.json invalido: {exc}"]

    issues: list[str] = []
    scenes = script_data.get("scenes") or []
    sec_chars = script_data.get("secondary_characters") or []

    # 1. Cobertura de personagem secundario.
    for sec in sec_chars:
        cname = str(sec.get("name") or "").strip()
        if not cname:
            continue
        cdesc = str(sec.get("description") or "").strip()
        c_syn = _synsets(f"{cname} {cdesc}")
        # cenas em que o personagem e citado
        cited = [s for s in scenes if cname.lower() in _norm(s.get("text", ""))
                 or (c_syn and (c_syn & _synsets(s.get("text", ""))))]
        if not cited:
            continue
        shown = 0
        for s in cited:
            m = assignment.get(s["scene_id"]) or {}
            m_syn = _synsets(_media_desc_for(m))
            if (cname.lower() in _norm(_media_desc_for(m))) or (c_syn and (c_syn & m_syn)):
                shown += 1
        if shown == 0:
            issues.append(
                f"personagem '{cname}' e narrado em {len(cited)} cena(s) mas NAO aparece "
                f"em nenhuma midia designada (cobertura zero)"
            )

    # 2. Alinhamento de ancora forte por cena.
    for s in scenes:
        sid = s["scene_id"]
        m = assignment.get(sid)
        if not m or not _media_desc_for(m):
            issues.append(f"cena {sid}: sem midia designada no manifesto")
            continue
        # A sincronia e sobre o que e FALADO (text) x o que e MOSTRADO (midia).
        # visual_action descreve a intencao da cena; nao entra na ancora.
        talk = str(s.get('text', ''))
        talk_syn = _synsets(talk)
        media_syn = _synsets(_media_desc_for(m))
        for anchor in STRONG_ANCHORS:
            if anchor in talk_syn and anchor not in media_syn:
                issues.append(
                    f"cena {sid}: a fala cita '{anchor}' mas a midia designada "
                    f"('{_media_desc_for(m)[:60]}') nao contem essa ancora"
                )
                break  # uma por cena basta

    return issues
