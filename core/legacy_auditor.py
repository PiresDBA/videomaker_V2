# -*- coding: utf-8 -*-
"""Auditor e importador de projetos legados (para processar os 30+ videos no motor v2)."""
from __future__ import annotations

import base64
import json
import re
import shutil
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image

from config import ENV_FILE
from core.media_studio import detect_split_collage, fit_aspect_jpeg
from core.script_engine import (
    SYSTEM_PROMPT,
    _call_gemini_text_api,
    _get_google_keys,
    extract_json_object,
    normalize_script_records,
    validate_script_schema,
)
from vendor.env_keys import load_env_key  # noqa: E402


def audit_image_with_vision(
    image_path: Path,
    expected_location: str,
    expected_action: str,
    model: str = "gemini-3-flash-preview",
    expected_narration: str = "",
    fail_closed: bool = False,
) -> dict[str, Any]:
    """Compara uma imagem real com a cena/cenario/narracao esperados usando Gemini Vision."""
    keys = _get_google_keys()
    if not keys:
        return {"checked": False, "ok": not fail_closed, "reason": "sem chave Google para Vision"}

    b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    prompt = (
        "Audit this animated cartoon frame against its intended scene.\n"
        + (f'Spoken Narration (Portuguese): "{expected_narration}"\n' if expected_narration else "")
        + f"Expected environment/location: {expected_location}\n"
        f"Expected visual action: {expected_action}\n"
        "Character Canon: Frida is a fawn golden-tan young English bulldog puppy with white pearl necklace (NEVER black-and-white spotted, NEVER Golden Retriever); "
        "Luna is a chocolate-brown miniature dachshund puppy with tan markings (NEVER Cocker Spaniel).\n"
        "Respond ONLY in JSON with keys: "
        '{"matches_location": bool, "matches_action": bool, "has_collage_or_split": bool, "has_visible_text": bool, "reason": "short summary"}'
    )
    payload = json.dumps({
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inlineData": {"mimeType": mime, "data": b64}},
            ]
        }],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }).encode("utf-8")

    for key in keys[:4]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(key)}"
        )
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            txt = data["candidates"][0]["content"]["parts"][0]["text"]
            res = json.loads(txt)
            ok = (
                bool(res.get("matches_location", True))
                and bool(res.get("matches_action", True))
                and not bool(res.get("has_collage_or_split", False))
                and not bool(res.get("has_visible_text", False))
            )
            res["checked"] = True
            res["ok"] = ok
            return res
        except Exception:
            continue
    return {"checked": False, "ok": not fail_closed, "reason": "vision timeout/erro"}


def _collect_legacy_images(legacy_dir: Path) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    dirs = [
        legacy_dir / "assets" / "images" / "gemini",
        legacy_dir / "assets" / "images",
        legacy_dir / "scenes" / "pt",
    ]
    found: list[Path] = []
    seen: set[Path] = set()
    for d in dirs:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix.lower() in exts and p not in seen:
                seen.add(p)
                found.append(p)
    return found


def scan_legacy_project(legacy_dir: Path) -> dict[str, Any]:
    """Audita completamente uma pasta de video legado sem alterar nenhum arquivo."""
    script_p = legacy_dir / "artifacts" / "script.json"
    words = 0
    sections_n = 0
    title = legacy_dir.name
    bad_opening = False
    laughs = 0

    if script_p.exists():
        data = json.loads(script_p.read_text(encoding="utf-8", errors="replace"))
        title = data.get("title") or title
        secs = data.get("sections") or data.get("scenes") or []
        sections_n = len(secs)
        full_txt = " ".join(str(s.get("text") or "") for s in secs)
        words = len(full_txt.split())
        laughs = len(re.findall(r"\b(?:hahaha+|kkkk+|rsrs+)\b", full_txt, re.I))
        if secs:
            intro_txt = " ".join(str(s.get("text") or "") for s in secs[:2])
            intro_labels = " ".join(str(s.get("id") or "") + " " + str(s.get("label") or "") for s in secs[:2])
            bad_opening = bool(
                re.search(r"bom dia|boa tarde|bem[- ]vind|oi[, ]+pessoal|amiguinhos|nosso canal|vamos descobrir", intro_txt, re.I)
                or re.search(r"introdu|apresenta", intro_labels, re.I)
            )

    imgs = _collect_legacy_images(legacy_dir)
    usable_imgs: list[str] = []
    collage_imgs: list[str] = []
    corrupt_imgs: list[str] = []
    for p in imgs:
        try:
            with Image.open(p) as im:
                w, h = im.size
            if w < 640 or h < 360:
                corrupt_imgs.append(p.name)
                continue
            if detect_split_collage(p) > 1:
                collage_imgs.append(p.name)
            else:
                usable_imgs.append(str(p))
        except Exception:
            corrupt_imgs.append(p.name)

    has_short = any((legacy_dir / "output").glob("*short*")) if (legacy_dir / "output").exists() else False
    return {
        "project": legacy_dir.name,
        "path": str(legacy_dir),
        "title": title,
        "has_script": script_p.exists(),
        "sections": sections_n,
        "words": words,
        "needs_script_condense": words < 420 or words > 600 or bad_opening or laughs > 0,
        "bad_opening": bad_opening,
        "written_laughs": laughs,
        "images_total": len(imgs),
        "images_usable": len(usable_imgs),
        "images_collage": len(collage_imgs),
        "images_corrupt": len(corrupt_imgs),
        "usable_paths": usable_imgs,
        "has_short_9_16": has_short,
        "recommended_actions": [
            a for a, cond in (
                ("condensar_roteiro_3_atos_frida_luna", words > 600 or words < 420),
                ("remover_saudacao_inicial", bad_opening),
                ("remover_risadas_escritas", laughs > 0),
                ("recriar_imagens_colagem_ou_faltantes", len(usable_imgs) < 18 or len(collage_imgs) > 0),
                ("gerar_tts_emocional_prosodia", True),
                ("adicionar_dual_avatar_e_short_motion", not has_short),
            ) if cond
        ],
    }


def batch_scan_legacy_root(root_dir: Path) -> list[dict[str, Any]]:
    """Lista e audita todos os projetos de video legados em um diretorio (ex.: E:\\videos)."""
    results = []
    for sub in sorted(root_dir.iterdir()):
        if not sub.is_dir():
            continue
        if sub.name in ("videomaker_v2", "scripts", "Referencia", "thumbnails", "ui", "server", "artifacts", "auditoria", "logs", ".venv"):
            continue
        if (sub / "artifacts" / "script.json").exists() or (sub / "project.json").exists():
            results.append(scan_legacy_project(sub))
    return results


def import_and_upgrade_legacy(
    legacy_dir: Path,
    target_proj_dir: Path,
    reuse_clean_images: bool = True,
    vision_filter: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """Converte um projeto legado para v2: reescreve roteiro em 3 atos e so reaproveita imagens aprovadas na visao."""
    report = scan_legacy_project(legacy_dir)
    script_p = legacy_dir / "artifacts" / "script.json"
    if not script_p.exists():
        raise FileNotFoundError(f"script.json nao encontrado em {legacy_dir}")

    legacy_raw = json.loads(script_p.read_text(encoding="utf-8", errors="replace"))
    legacy_title = legacy_raw.get("title") or legacy_dir.name
    legacy_secs = legacy_raw.get("sections") or legacy_raw.get("scenes") or []
    summary_text = "\n".join(
        f"- {s.get('section_id', '')}: {str(s.get('text') or '')[:260]}"
        for s in legacy_secs[:24]
    )

    out_script = target_proj_dir / "artifacts" / "script_v2.json"
    out_script.parent.mkdir(parents=True, exist_ok=True)
    if force or not out_script.exists():
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"ADAPTE E MELHORE ESTA HISTÓRIA EXISTENTE DO CANAL ('{legacy_title}') PARA O FORMATO V2 DE ALTA RETENÇÃO (OBRIGATÓRIO: ENTRE 450 E 550 PALAVRAS NO TOTAL, 3 ATOS, DIÁLOGO VIVO FRIDA x LUNA, COM 'story_props' PARA OBJETOS RECORRENTES E 'secondary_characters' SE HOUVER OUTROS PERSONAGENS).\n"
            f"IMPORTANTE: Frida é uma buldogue inglesa caramelo-dourada de colar de pérolas (NUNCA Golden Retriever, nunca preta/branca manchada); Luna é uma dachshund salsicha marrom-chocolate de correntinhas douradas (NUNCA Cocker Spaniel).\n"
            f"BASE DA HISTÓRIA:\n{summary_text}"
        )
        raw_resp = _call_gemini_text_api(prompt)
        parsed = normalize_script_records(extract_json_object(raw_resp))
        errs = validate_script_schema(parsed)
        for _retry in range(2):
            if not errs:
                break
            raw_resp = _call_gemini_text_api(prompt + f"\n\nCORRIJA EXATAMENTE ESTES ERROS: {'; '.join(errs)}")
            parsed = normalize_script_records(extract_json_object(raw_resp))
            errs = validate_script_schema(parsed)
        out_script.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        parsed = normalize_script_records(json.loads(out_script.read_text(encoding="utf-8")))

    reused = 0
    if reuse_clean_images and report["usable_paths"]:
        images_dir = target_proj_dir / "assets" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        usable = [Path(p) for p in report["usable_paths"]]
        # Mapeia sequencialmente as imagens limpas que passarem na auditoria visual para p1 das cenas
        for idx, sc in enumerate(parsed.get("scenes", [])):
            if idx >= len(usable):
                break
            src_im = usable[idx]
            dst_im = images_dir / f"{sc['scene_id']}_p1.jpg"
            if not force and dst_im.exists():
                continue
            if vision_filter:
                v = audit_image_with_vision(
                    src_im,
                    sc["location"],
                    sc["visual_action"],
                    expected_narration=sc.get("text", ""),
                    fail_closed=True,
                )
                if not v.get("ok", False):
                    continue
            fit_aspect_jpeg(src_im, dst_im)
            reused += 1

    return {"audit": report, "script_v2_path": str(out_script), "images_reused": reused}
