# -*- coding: utf-8 -*-
"""Atribuicao deterministica de imagens aprovadas as cenas (anti-repeticao).

Correcao da causa-raiz do v6: o distribuidor antigo escolhia sempre a imagem de
maior score e, com empate, a primeira por nome — a mesma foto ("Frida apontando
ao por do sol") caiu em 11 cenas. Aqui cada cena recebe UMA imagem base, com:

  * cota global de cenas por imagem (MAX_SCENE_REUSE);
  * proibicao de repetir a imagem em cenas vizinhas;
  * casamento semantico (tema da narracao x tema da imagem + palavras em comum);
  * blacklist por SHA (imagens vetadas pelo usuario nunca entram);
  * cena com video Veo nao consome imagem (o video e o visual da cena).

Todas as partes de uma cena usam a MESMA imagem base; o movimento vem do Ken
Burns + dissolve longo (slow motion), nunca de um flipbook de fotos diferentes.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from core.delivery_audit import (
    INDEX_PATH,
    clip_has_video,
    load_blacklist,
    sha256,
    theme_of,
    tokens,
)

DEFAULT_MAX_REUSE = 2


def load_catalog(index_path: Path = INDEX_PATH, blacklist: set[str] | None = None) -> list[dict[str, Any]]:
    """Carrega o pool aprovado como catalogo de candidatos (sem vetados)."""
    if not index_path.exists():
        from core.delivery_audit import build_approved_index

        build_approved_index()
    data = json.loads(index_path.read_text(encoding="utf-8"))
    blocked = blacklist if blacklist is not None else load_blacklist()
    out: list[dict[str, Any]] = []
    for row in data.get("images", []):
        if row.get("sha256") in blocked:
            continue
        p = Path(row.get("path", ""))
        if not p.exists():
            continue
        out.append({
            "sha": row["sha256"],
            "name": row.get("name", p.name),
            "path": p,
            "theme": row.get("theme") or "geral",
            "tokens": set(row.get("keywords") or []),
        })
    return out


def _score(
    entry: dict[str, Any],
    theme: str,
    words: set[str],
    uses: int,
    prev_sha: str | None,
    max_reuse: int,
) -> float:
    score = 0.0
    if entry["theme"] == theme:
        score += 6.0
    elif theme != "geral" and entry["theme"] == "geral":
        score += 0.8
    score += len(words & entry["tokens"]) * 0.30
    score -= uses * 3.2                      # espalha o uso pelo pool
    if uses >= max_reuse:
        score -= 100.0                       # cota estourada
    if prev_sha and entry["sha"] == prev_sha:
        score -= 60.0                        # nunca em cena vizinha
    return score


def assign_images(
    proj_dir: Path,
    pacing: list[dict[str, Any]],
    images_dir: Path,
    index_path: Path = INDEX_PATH,
    blacklist_path: Path | None = None,
    max_reuse: int = DEFAULT_MAX_REUSE,
    preferred: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Escolhe 1 imagem por cena e materializa `<clip_id>.jpg` para todas as partes.

    `preferred` mapeia `scene_id -> nome do arquivo do pool`. Quando a cena tem
    uma imagem curada (roteiro escrito para aquela foto), ela tem prioridade —
    desde que nao esteja vetada e nao repita cena vizinha.
    """
    blacklist = load_blacklist(blacklist_path) if blacklist_path else load_blacklist()
    catalog = load_catalog(index_path, blacklist)
    if not catalog:
        raise RuntimeError("pool aprovado vazio: nada para atribuir")

    scenes: dict[str, list[dict[str, Any]]] = {}
    for clip in pacing:
        scenes.setdefault(clip["scene_id"], []).append(clip)

    images_dir.mkdir(parents=True, exist_ok=True)
    for old in images_dir.glob("*.jpg"):
        old.unlink()

    used_scenes: dict[str, list[str]] = {}
    assignment: dict[str, dict[str, Any]] = {}
    prev_sha: str | None = None
    prev_theme: str | None = None

    for sid in sorted(scenes):
        clips = scenes[sid]
        if any(clip_has_video(c, images_dir) for c in clips):
            assignment[sid] = {"image": None, "reason": "video"}
            prev_sha = None
            continue

        sample = " ".join(
            str(c.get("text", "")) + " " + str(c.get("visual_action", "")) + " " + str(c.get("location", ""))
            for c in clips[:2]
        )
        theme = theme_of(sample)
        words = tokens(sample)

        preferred_entry = None
        if preferred and sid in preferred:
            wanted = str(preferred[sid])
            preferred_entry = next((e for e in catalog if e["name"] == wanted), None)
            if preferred_entry and preferred_entry["sha"] == prev_sha:
                preferred_entry = None  # nunca repetir em cena vizinha
            if preferred_entry and len(used_scenes.get(preferred_entry["sha"], [])) >= max_reuse:
                preferred_entry = None

        ranked = sorted(
            catalog,
            key=lambda e: (
                -_score(e, theme, words, len(used_scenes.get(e["sha"], [])), prev_sha, max_reuse),
                e["sha"],
            ),
        )
        # fallback: se o pool inteiro estourou cota, libera a menos usada (nunca a vizinha)
        chosen = preferred_entry or ranked[0]
        if len(used_scenes.get(chosen["sha"], [])) >= max_reuse:
            free = [e for e in ranked if e["sha"] != prev_sha]
            free.sort(key=lambda e: (len(used_scenes.get(e["sha"], [])), e["sha"]))
            chosen = free[0]

        used_scenes.setdefault(chosen["sha"], []).append(sid)
        assignment[sid] = {
            "image": chosen["name"],
            "sha256": chosen["sha"],
            "theme_scene": theme,
            "theme_image": chosen["theme"],
            "curated": bool(preferred_entry),
        }
        for clip in clips:
            shutil.copy2(chosen["path"], images_dir / f"{clip['clip_id']}.jpg")
        prev_sha = chosen["sha"]
        prev_theme = theme

    payload = {
        "version": 1,
        "max_reuse": max_reuse,
        "pool_size": len(catalog),
        "scenes": assignment,
        "reuse": {sha: sids for sha, sids in sorted(used_scenes.items())},
    }
    out = proj_dir / "artifacts" / "image_assignment.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
