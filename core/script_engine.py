# -*- coding: utf-8 -*-
"""Geracao e validacao rigorosa de roteiros 3 atos com dialogo Frida x Luna e direcao emocional."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from config import ENV_FILE, SCRIPT_MAX_WORDS, SCRIPT_MIN_WORDS, VENDOR_DIR

sys.path.insert(0, str(VENDOR_DIR))
from env_keys import load_env_key  # noqa: E402

VALID_SPEAKERS = ("narrador", "frida", "luna", "secundario")
VALID_AVATAR_MODES = ("auto", "frida", "luna", "duo", "none")

BANNED_OPENING_PATTERNS = (
    r"^\s*(?:bom\s+dia|boa\s+tarde|boa\s+noite)\b",
    r"\b(?:sejam?\s+bem[- ]vind[oa]s?|bem[- ]vindo\s+ao\s+canal)\b",
    r"^\s*(?:oi[eê]?,?\s*(?:pessoal|amiguinhos|galera|gente|fam[íi]lia)|ol[áa],?\s*(?:amiguinhos|pessoal|galera|fam[íi]lia))\b",
    r"\b(?:deixe\s+seu\s+like|se\s+inscrev[ae]|inscreva[- ]se|curta\s+o\s+v[íi]deo)\b",
)

CTA_PATTERNS = (
    r"\b(?:like|joinha|inscrev|curta\s+o\s+v[íi]deo|compartilh|sininho)\b",
)

SYSTEM_PROMPT = """Você é um roteirista premiado de animações infantis e YouTube storytelling, escrevendo em português do Brasil natural, emocionante e totalmente acentuado.

Escreva uma história ORIGINAL de 3 a 4 minutos para o canal "Frida e Luna" no formato DINÂMICO DE DUPLA (Frida e Luna comentando e vivendo a história juntas, com o Narrador conduzindo apenas as viradas de ação).

REGRAS OBRIGATÓRIAS DE RETENÇÃO, EMOÇÃO E ESTRUTURA:
1. CONTAGEM ESTRITA DE PALAVRAS: a soma total de palavras do campo "text" de todas as cenas DEVE ficar entre 450 e 550 palavras.
2. GANCHO IMEDIATO (0-5s): É PROIBIDO começar com saudações ("Bom dia", "Oi pessoal", "Sejam bem-vindos", etc.). A cena 1 já abre dentro da ação/surpresa nos primeiros 5 segundos.
3. DIÁLOGO VIVO FRIDA x LUNA: Divida a narrativa em bate-bola ágil entre Frida (doce, calma, sensata) e Luna (agitada, curiosa, dramática), usando o Narrador só para pontes de ação. Evite blocos longos de monólogo.
4. OPEN LOOPS E 3 ATOS COM CONFLITO REAL:
   - Ato 1 (act=1): Gancho explosivo + objetivo/mistério + pequeno gancho de curiosidade no fim do ato.
   - Ato 2 (act=2): Conflito entre Frida e Luna, obstáculos crescentes, virada inesperada.
   - Ato 3 (act=3): Clímax, resolução emocionante, moral rápida em 1 frase e CTA apenas na ÚLTIMA cena (<= 20 palavras).
5. DIREÇÃO EMOCIONAL E AVATAR: Toda cena DEVE trazer:
   - "emotion_direction": instrução curta de emoção vocal em português (ex.: "sussurrando com medo e curiosidade", "explodindo de empolgação", "indignada e dramática", "sorrindo aliviada").
   - "avatar_mode": "frida", "luna", "duo" (troca/reação entre as duas) ou "none" (cena de ação pura em tela cheia).
6. CENAS CURTAS E PORTUGUÊS LIMPO: 1 a 2 frases curtas por cena (12 a 26 palavras). Zero risadas escritas ("Hahaha", "kkkk") e acentuação perfeita ("cães", "já", "céu", "é", "patinha", "passarinhos", "coro", "piadas").
7. CENÁRIO CONSISTENTE: Defina "location" em TODA cena preservando continuidade geográfica lógica.
8. IDADE E ESTILO DOS PERSONAGENS (PADRÃO CRIANÇA / AVATAR 3D DISNEY-PIXAR): Em TODA descrição de "visual_action", descreva Frida e Luna com aparência jovem de criança/pré-adolescente (filhotes jovens de até 1 ano no máximo, equivalentes a crianças de 5 a 10 anos em animação 3D Disney/Pixar, fiéis ao avatar oficial: graciosas, olhos grandes expressivos, traços arredondados de desenho animado — NUNCA cães adultos/velhos nem cães reais fotorrealistas; use versão bebê recém-nascido apenas se a cena for explicitamente um flashback de quando eram bebês).
9. CONTINUIDADE DE PERSONAGENS SECUNDÁRIOS: Sempre que houver outro personagem recorrente na história (ex.: gato Pingo, pombo, esquilo, outro cão), declare-o na lista de topo "secondary_characters": [{"name": "NomeCurto", "description": "Descrição visual 3D Disney/Pixar completa e fixa do personagem (espécie, cor exata da pelagem/penas, olhos, acessório)"}] e inclua o campo "characters": ["Frida", "Luna", "NomeCurto"] em TODA cena em que ele aparecer, repetindo suas características físicas em "visual_action".

FORMATO DE SAÍDA (APENAS JSON puro, sem markdown):
{
  "title": "Título curto <= 55 caracteres com curiosidade",
  "thumb_hook": "2 A 3 PALAVRAS",
  "description": "Descrição curta otimizada para YouTube",
  "tags": ["frida e luna", "historia infantil"],
  "target_minutes": 3.5,
  "scenes": [
    {
      "scene_id": "sc_01",
      "act": 1,
      "speaker": "narrador | frida | luna | secundario",
      "emotion_direction": "tom energético de abertura",
      "text": "1 ou 2 frases curtas.",
      "location": "Exact scene environment",
      "visual_action": "Concrete expressive 3D visual action",
      "sfx": "whoosh_fast/crisp ou termo curto ingles ou null",
      "avatar_mode": "frida | luna | duo | none"
    }
  ]
}
"""


def count_total_words(script_data: dict[str, Any]) -> int:
    """Conta o total de palavras faladas em todas as cenas do roteiro."""
    return sum(len((s.get("text") or "").split()) for s in script_data.get("scenes", []))


def _infer_avatar_mode(sc: dict[str, Any], spk: str) -> str:
    explicit = str(sc.get("avatar_mode") or "").strip().lower()
    if explicit in VALID_AVATAR_MODES and explicit != "auto":
        return explicit
    if sc.get("avatar_pip") is False:
        return "none"
    if spk in ("frida", "luna"):
        return spk
    if sc.get("avatar_pip") is True:
        return "frida"
    return "none"


def normalize_script_records(data: dict[str, Any]) -> dict[str, Any]:
    """Normaliza schema do roteiro garantindo campos de emocao, duo, avatar e personagens secundarios."""
    sec_chars_in = data.get("secondary_characters") or []
    sec_chars_out: list[dict[str, str]] = []
    sec_names: list[str] = []
    for item in sec_chars_in:
        if isinstance(item, dict) and str(item.get("name") or "").strip():
            cname = " ".join(str(item["name"]).split())
            cdesc = " ".join(str(item.get("description") or "").split())
            sec_chars_out.append({"name": cname, "description": cdesc})
            sec_names.append(cname)

    raw_scenes = data.get("scenes", [])
    scenes_out = []
    for idx, sc in enumerate(raw_scenes, 1):
        sid = str(sc.get("scene_id") or f"sc_{idx:02d}").strip()
        spk = str(sc.get("speaker") or "narrador").strip().lower()
        if spk not in VALID_SPEAKERS:
            spk = "narrador"
        act = sc.get("act")
        if act not in (1, 2, 3):
            ratio = idx / max(1, len(raw_scenes))
            act = 1 if ratio <= 0.28 else (2 if ratio <= 0.72 else 3)

        avatar_mode = _infer_avatar_mode(sc, spk)
        emotion_dir = " ".join(str(sc.get("emotion_direction") or "").split())
        if not emotion_dir:
            emotion_dir = {
                "frida": "doce, calorosa e expressiva",
                "luna": "rápida, animada e curiosa",
                "secundario": "teatral e divertida",
            }.get(spk, "narrativa viva e envolvente")

        txt_clean = " ".join(str(sc.get("text") or "").split())
        act_clean = " ".join(str(sc.get("visual_action") or "").split())
        raw_chars = sc.get("characters")
        if isinstance(raw_chars, list) and raw_chars:
            chars = [" ".join(str(c).split()) for c in raw_chars if str(c).strip()]
        else:
            hay_c = f"{txt_clean} {act_clean}".lower()
            chars = []
            for main_c in ("Frida", "Luna"):
                if main_c.lower() in hay_c or spk == main_c.lower():
                    chars.append(main_c)
            for sname in sec_names:
                if sname.lower() in hay_c and sname not in chars:
                    chars.append(sname)
            if not chars:
                chars = ["Frida", "Luna"]

        scenes_out.append({
            "scene_id": sid,
            "act": int(act),
            "speaker": spk,
            "emotion_direction": emotion_dir,
            "text": txt_clean,
            "location": " ".join(str(sc.get("location") or "").split()),
            "visual_action": act_clean,
            "sfx": sc.get("sfx") if sc.get("sfx") else None,
            "avatar_mode": avatar_mode,
            "avatar_pip": avatar_mode != "none",
            "characters": chars,
        })

    title = " ".join(str(data.get("title") or "Frida e Luna").split())
    out = {
        "title": title,
        "thumb_hook": " ".join(str(data.get("thumb_hook") or "ELAS FALARAM?!").split()).upper(),
        "description": " ".join(str(data.get("description") or title).split()),
        "tags": list(data.get("tags") or ["frida e luna", "cachorros falantes", "animacao 3d"]),
        "target_minutes": float(data.get("target_minutes") or 3.5),
        "secondary_characters": sec_chars_out,
        "scenes": scenes_out,
    }
    return out


def validate_script_schema(
    data: dict[str, Any],
    min_words: int = SCRIPT_MIN_WORDS,
    max_words: int = SCRIPT_MAX_WORDS,
) -> list[str]:
    """Valida schema, 3 atos, gancho sem saudacao, CTA no fim, dialogo e palavras."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["roteiro nao e um objeto JSON"]

    title = (data.get("title") or "").strip()
    if not title:
        errors.append("campo 'title' ausente ou vazio")

    scenes = data.get("scenes")
    if not isinstance(scenes, list) or len(scenes) < 6:
        errors.append("campo 'scenes' precisa ter ao menos 6 cenas curtas")
        return errors

    seen_ids: set[str] = set()
    acts_seen: list[int] = []
    required_keys = ("scene_id", "speaker", "text", "location", "visual_action")

    for idx, sc in enumerate(scenes):
        if not isinstance(sc, dict):
            errors.append(f"cena[{idx}] invalida (esperado objeto)")
            continue
        for k in required_keys:
            if not str(sc.get(k) or "").strip():
                errors.append(f"cena[{idx}] ({sc.get('scene_id', '?')}) sem campo obrigatorio '{k}'")
        if "sfx" not in sc:
            errors.append(f"cena[{idx}] ({sc.get('scene_id', '?')}) sem chave 'sfx'")

        sid = str(sc.get("scene_id") or "").strip()
        if sid in seen_ids:
            errors.append(f"scene_id duplicado: '{sid}'")
        seen_ids.add(sid)

        spk = str(sc.get("speaker") or "").strip().lower()
        if spk not in VALID_SPEAKERS:
            errors.append(f"cena '{sid}': speaker invalido '{spk}' (use {VALID_SPEAKERS})")

        act = sc.get("act")
        if act not in (1, 2, 3):
            errors.append(f"cena '{sid}': act invalido '{act}' (esperado 1, 2 ou 3)")
        else:
            acts_seen.append(act)

        txt = (sc.get("text") or "").strip()
        if re.search(r"\b(?:hahaha+|kkkk+|rsrs+)\b", txt, re.I):
            errors.append(f"cena '{sid}': contem risada escrita proibida")

        if idx == 0:
            for pat in BANNED_OPENING_PATTERNS:
                if re.search(pat, txt, re.I):
                    errors.append(f"cena '{sid}' (abertura): contem saudacao/CTA proibido nos primeiros 5s")
                    break

        if idx < len(scenes) - 1:
            for pat in CTA_PATTERNS:
                if re.search(pat, txt, re.I):
                    errors.append(f"cena '{sid}': CTA (like/inscricao) fora da cena final")
                    break

    if acts_seen:
        if set(acts_seen) != {1, 2, 3}:
            errors.append(f"roteiro deve cobrir os 3 atos (encontrados: {sorted(set(acts_seen))})")
        if acts_seen != sorted(acts_seen):
            errors.append("ordem dos atos fora de sequencia (esperado 1 -> 2 -> 3)")

    total_words = count_total_words(data)
    if total_words < min_words or total_words > max_words:
        errors.append(
            f"total de palavras ({total_words}) fora do limite obrigatorio ({min_words}..{max_words})"
        )
    return errors


def extract_json_object(raw_text: str) -> dict[str, Any]:
    """Extrai o objeto JSON estruturado da resposta de texto do LLM."""
    decoder = json.JSONDecoder()
    best: dict[str, Any] | None = None
    for m in re.finditer(r'\{\s*"title"', raw_text):
        try:
            obj, _ = decoder.raw_decode(raw_text[m.start():])
        except Exception:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("scenes"), list):
            if best is None or len(obj["scenes"]) >= len(best["scenes"]):
                best = obj
    if best is not None:
        return best
    s = raw_text.find("{")
    e = raw_text.rfind("}")
    if s == -1 or e <= s:
        raise ValueError("Nenhum objeto JSON valido encontrado na resposta.")
    return json.loads(raw_text[s:e + 1])


def _get_google_keys() -> list[str]:
    names = ["GOOGLE_TTS_API_KEY"] + [f"GOOGLE_TTS_API_KEY_{i}" for i in range(1, 21)] + ["GEMINI_API_KEY"]
    keys = []
    for n in names:
        val = (load_env_key(n, ENV_FILE) or os.environ.get(n) or "").strip()
        if val and val not in keys:
            keys.append(val)
    return keys


def _call_gemini_text_api(prompt: str, model: str = "gemini-3-flash-preview") -> str:
    keys = _get_google_keys()
    if not keys:
        raise RuntimeError("Nenhuma chave Google/Gemini encontrada no .env interno.")
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.75, "responseMimeType": "application/json"},
    }).encode("utf-8")
    last_err: Exception | None = None
    for key in keys:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(key)}"
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            cands = data.get("candidates") or []
            parts = cands[0].get("content", {}).get("parts", []) if cands else []
            txt = "\n".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()
            if txt:
                return txt
        except Exception as exc:
            last_err = exc
    raise RuntimeError(f"Gemini Text API falhou em todas as chaves: {last_err}")


def generate_script(
    theme_prompt: str,
    out_path: Path,
    wait_s: int = 120,
    max_attempts: int = 3,
    min_words: int = SCRIPT_MIN_WORDS,
    max_words: int = SCRIPT_MAX_WORDS,
) -> dict[str, Any]:
    """Gera roteiro via Gemini API (com fallback para gemini_fetch.py web) validando schema."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    feedback = ""
    fetch = VENDOR_DIR / "gemini_fetch.py"

    for attempt in range(1, max_attempts + 1):
        prompt = f"{SYSTEM_PROMPT}\n\nMETA DE PALAVRAS DO ROTEIRO: entre {min_words} e {max_words} palavras.\nTEMA DO EPISÓDIO: {theme_prompt}"
        if feedback:
            prompt += f"\n\nCORREÇÃO OBRIGATÓRIA DA TENTATIVA ANTERIOR:\n{feedback}"

        raw = ""
        try:
            raw = _call_gemini_text_api(prompt)
        except Exception as api_exc:
            if fetch.exists():
                cmd = [
                    sys.executable, str(fetch),
                    "--kind", "text",
                    "--prompt", prompt,
                    "--name", f"script_v2_try{attempt}",
                    "--out-dir", str(out_path.parent),
                    "--wait", str(wait_s),
                ]
                subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
                md_files = sorted(out_path.parent.glob(f"script_v2_try{attempt}*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
                if md_files:
                    raw = md_files[0].read_text(encoding="utf-8", errors="replace")
                else:
                    feedback = f"API ({api_exc}) e Gemini Web falharam."
                    continue
            else:
                feedback = str(api_exc)
                continue

        try:
            parsed = normalize_script_records(extract_json_object(raw))
        except Exception as exc:
            feedback = f"JSON invalido ({exc}). Responda somente JSON valido."
            continue

        errs = validate_script_schema(parsed, min_words=min_words, max_words=max_words)
        if not errs:
            out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
            return parsed
        feedback = "; ".join(errs)

    raise RuntimeError(f"Falha ao gerar roteiro valido apos {max_attempts} tentativas: {feedback}")
