# -*- coding: utf-8 -*-
"""Pesquisa de virais do YouTube por tema e extracao da ESTRUTURA do humor.

NUNCA copia conteudo: titulos, falas, cenas e personagens dos videos encontrados sao usados
apenas como evidencia local (artifacts/viral_research.json). O prompt do roteiro recebe
somente padroes abstratos de comedia (gancho, contraste, escalada, callback, payoff).
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

MIN_VIRAL_VIEWS = 1_000_000
CACHE_MAX_AGE_HOURS = 24

# (regex, nome do sinal, orientacao estrutural em portugues)
_HUMOR_SIGNALS: tuple[tuple[str, str, str], ...] = (
    (r"first\s*time|primeira\s*vez|first\s*encounter|first\s*day|primeiro\s*dia", "first_time",
     "abertura com reacao de primeira vez nos primeiros 3 segundos, sem intro lenta"),
    (r"doesn'?t\s*go\s*as\s*planned|backfire|desastre|plano\s*que\s*da\s*errado|sai\s*todo\s*errado", "plan_backfire",
     "plano esperto que falha tres vezes de formas crescentes"),
    (r"funny|hilarious|engracad|risad|comedy|maluco|loco|haha", "physical_comedy",
     "gag fisico e exagero cartoon em praticamente cada cena"),
    (r"compilation|try\s*not\s*to\s*laugh|compilad|melhores\s*momentos", "rapid_compilation",
     "ritmo de compilacao: gag curto, sem tempo morto entre piadas"),
    (r"surprise|susto|inesperad|surpresa|shock|gigante", "surprise",
     "virada surpreendente com uma pausa curta antes do payoff"),
    (r"reaction|reagind|reacao", "reaction",
     "reacao exagerada de um personagem ao que o outro acabou de fazer"),
    (r"two\s*types|contrast|versus|\bvs\b|dupla|sensat|impulsiv", "contrast",
     "contraste de personalidades entre os personagens como motor do riso"),
    (r"fail|queda|caiu|escorreg|bateu|erro", "fail",
     "queda, escorrego e batida como familia recorrente de gags"),
    (r"dog|cachorr|puppy|filhote|pet", "dog",
     "corpo pequeno, patinhas e orelhas como fonte de comicidade fisica"),
    (r"beach|praia|ocean|mar|onda|areia|sand|water|agua", "setting",
     "cenario amplo com agua/areia para gags fisicos e surpresas"),
    (r"cute|adorable|fofo|fofinho|sweet", "cute",
     "contraste entre fofura e caos para amplificar o riso"),
    (r"run|corr|chase|persegui|fug", "chase",
     "perseguicao rapida como sequencia encadeada de gags"),
)

_FALLBACK_STRUCTURE = {
    "hook": "reacao surpresa e risonha nos primeiros 3 segundos",
    "engine": "contraste entre uma personagem sensata e outra impulsiva",
    "escalation": "um plano esperto que falha tres vezes, cada vez pior",
    "rhythm": "gag fisico, pausa de respiro, gag de palavra, pausa de respiro",
    "callback": "frase de efeito repetida tres vezes em situacoes diferentes",
    "payoff": "final feliz e quente com abraço e moral de uma frase",
}


def parse_view_count(text: str) -> int:
    """Converte contagens do YouTube em inteiro (EN '1.9M views' e PT '6.455.922 visualizações')."""
    if not text:
        return 0
    t = str(text).strip().lower().replace("\xa0", " ")
    t = re.sub(r"visualiza[çc][oõ]es|views?|visualizações", " ", t)
    m = re.search(r"([\d.,]+)\s*(mi|mil|k|m|b)?", t)
    if not m:
        return 0
    num = m.group(1)
    suffix = (m.group(2) or "").strip()
    abbreviated = suffix in ("mi", "mil", "k", "m", "b")
    if "," in num and "." in num:
        if num.rfind(",") > num.rfind("."):
            num = num.replace(".", "").replace(",", ".")
        else:
            num = num.replace(",", "")
    elif "," in num:
        num = num.replace(",", "") if re.search(r",\d{3}$", num) else num.replace(",", ".")
    elif "." in num:
        # "1.9M" e decimal; "6.455.922" / "256.859" (sem sufixo) e separador de milhar
        if not abbreviated:
            num = num.replace(".", "")
    try:
        value = float(num)
    except ValueError:
        return 0
    mult = {"mi": 1_000_000, "mil": 1_000, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(suffix, 1)
    return int(value * mult)


def _extract_yt_initial_data(html: str) -> dict[str, Any] | None:
    dec = json.JSONDecoder()
    for pat in ("var ytInitialData = ", 'window["ytInitialData"] = ', "ytInitialData = "):
        pos = html.find(pat)
        if pos < 0:
            continue
        try:
            obj, _ = dec.raw_decode(html[pos + len(pat):])
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return None


def _walk_videos(node: Any, out: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        v = node.get("videoRenderer")
        if isinstance(v, dict) and v.get("videoId"):
            title = "".join(r.get("text", "") for r in (v.get("title") or {}).get("runs", [])) or str((v.get("title") or {}).get("simpleText", ""))
            views_text = str((v.get("viewCountText") or {}).get("simpleText") or "")
            if not views_text:
                views_text = "".join(r.get("text", "") for r in (v.get("viewCountText") or {}).get("runs", []))
            snips = v.get("detailedMetadataSnippets") or []
            snippet = ""
            if snips:
                snippet = "".join(r.get("text", "") for r in (snips[0].get("snippetText") or {}).get("runs", []))
            out.append({
                "video_id": str(v["videoId"]),
                "title": title.strip(),
                "views_text": views_text,
                "views": parse_view_count(views_text),
                "url": f"https://www.youtube.com/watch?v={v['videoId']}",
                "snippet": snippet.strip()[:400],
            })
        for value in node.values():
            _walk_videos(value, out)
    elif isinstance(node, list):
        for item in node:
            _walk_videos(item, out)


def search_youtube_videos(query: str, timeout: int = 25) -> list[dict[str, Any]]:
    """Busca no YouTube via HTML publico (sem chave de API) e devolve videoId/titulo/views."""
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        html = resp.read().decode("utf-8", "replace")
    data = _extract_yt_initial_data(html)
    if not data:
        return []
    found: list[dict[str, Any]] = []
    _walk_videos(data, found)
    return found


_SYNONYM_GROUPS = {
    "cachorro": ("cachorro", "cachorrinho", "dog", "dogs", "puppy", "puppies", "filhote", "pet", "cão"),
    "praia": ("praia", "beach", "shore", "seaside", "areia", "sand", "mar", "ocean", "sea"),
    "mar": ("mar", "ocean", "sea", "onda", "wave", "beach", "praia"),
    "areia": ("areia", "sand", "beach", "praia"),
    "engracado": ("engracado", "engraçado", "funny", "hilarious", "comedy", "risada"),
    "filhote": ("filhote", "puppy", "puppies", "dog", "cachorro"),
}
_EN_HINT = {
    "cachorro": "dog", "praia": "beach", "mar": "ocean", "areia": "sand",
    "engracado": "funny", "filhote": "puppy", "primeiro": "first", "dia": "day",
}


def _relevance_terms(subjects: list[str]) -> list[str]:
    terms: set[str] = set()
    for s in subjects:
        terms.update(_SYNONYM_GROUPS.get(s, (s,)))
    return sorted(terms)


_SEARCH_STOPWORDS = {
    "muito", "muita", "engracado", "engraçado", "energia", "alegria", "primeiro", "primeira",
    "dia", "historia", "história", "episodio", "episódio", "video", "vídeo", "coisas", "sobre",
    "com", "para", "pela", "pelo", "uns", "umas", "como", "mais", "seu", "sua", "todos",
    "todas", "isso", "esse", "essa", "quando", "onde", "porque", "tem", "sao", "são", "funny",
    "viral", "compilation", "milhoes", "milhões", "visualizacoes", "visualizações", "primeira",
    "vez", "first", "time", "dog", "dogs", "cachorro", "cachorros",
}


_TOPIC_PRIORITY = (
    "praia", "beach", "mar", "ocean", "areia", "sand", "parque", "park", "floresta", "forest",
    "cozinha", "kitchen", "escola", "school", "jardim", "garden", "quintal", "backyard",
    "espaco", "space", "trem", "train", "lua", "moon", "dinossauro", "dinosaur", "piscina", "pool",
)


def theme_subjects(theme_prompt: str) -> list[str]:
    """Palavras-substantivo do tema, usadas tanto na busca quanto no filtro de relevancia."""
    text = str(theme_prompt or "").lower()
    tokens = [t for t in re.findall(r"[a-zà-ÿ]{4,}", text) if t not in _SEARCH_STOPWORDS]
    if any(name in text for name in ("frida", "luna")):
        # Frida e Luna sao cachorras: o publico busca esse termo, nao os nomes do canal
        tokens = [t for t in tokens if t not in ("frida", "luna")]
        if "cachorro" not in tokens:
            tokens.insert(0, "cachorro")
    priority = [t for t in _TOPIC_PRIORITY if t in text]
    ordered = priority + [t for t in tokens if t not in priority]
    return list(dict.fromkeys(ordered))[:4]


def build_queries(theme_prompt: str) -> list[str]:
    """Monta consultas curtas e especiais a partir do tema (prompt inteiro e longo demais para busca)."""
    text = str(theme_prompt or "").lower()
    core = " ".join(theme_subjects(theme_prompt)) or "cachorro engraçado"
    first = "primeira vez" if any(k in text for k in ("primeir", "first")) else ""
    en_core = " ".join(dict.fromkeys(_EN_HINT.get(s, s) for s in theme_subjects(theme_prompt)))
    queries = [
        f"{core} {first} funny viral".strip(),
        f"{core} {first} engraçado milhões de visualizações".strip(),
        f"{en_core} first time funny compilation viral".strip() if en_core else "",
        f"{en_core} first time funny".strip() if en_core else "",
    ]
    seen: set[str] = set()
    out = []
    for q in queries:
        if q.strip() and q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out


def analyze_humor_structure(videos: list[dict[str, Any]]) -> dict[str, Any]:
    """Extrai sinais ESTRUTURAIS do humor a partir de titulos e descricoes (nunca copia conteudo)."""
    counts: dict[str, int] = {}
    hints: dict[str, str] = {}
    for v in videos:
        hay = f"{v.get('title') or ''} {v.get('snippet') or ''}".lower()
        for rx, name, hint in _HUMOR_SIGNALS:
            if re.search(rx, hay, re.I):
                counts[name] = counts.get(name, 0) + 1
                hints[name] = hint
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
    signals = [{"signal": name, "count": n, "structure": hints[name]} for name, n in top]
    structure = dict(_FALLBACK_STRUCTURE)
    # Sinais mais fortes substituem apenas a orientacao correspondente
    for s in signals:
        name = s["signal"]
        if name == "first_time":
            structure["hook"] = s["structure"]
        elif name == "contrast":
            structure["engine"] = s["structure"]
        elif name in ("plan_backfire", "surprise", "setting"):
            structure["escalation"] = s["structure"]
        elif name in ("rapid_compilation", "physical_comedy", "reaction", "chase", "fail"):
            structure["rhythm"] = s["structure"]
        elif name in ("cute", "dog"):
            structure["engine"] = s["structure"]
    return {"signals": signals, "structure": structure}


def research_viral_humor(
    theme_prompt: str,
    cache_path: Path | None = None,
    timeout: int = 25,
    min_views: int = MIN_VIRAL_VIEWS,
) -> dict[str, Any]:
    """Pesquisa virais do tema. Falha de rede NUNCA quebra o pipeline: devolve sugestao de fallback."""
    theme_key = hashlib.sha1(" ".join(str(theme_prompt).split()).lower().encode("utf-8")).hexdigest()[:12]
    if cache_path and cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            ts = datetime.fromisoformat(cached.get("searched_at", ""))
            if cached.get("theme_hash") == theme_key and datetime.now(timezone.utc) - ts < timedelta(hours=CACHE_MAX_AGE_HOURS):
                cached["from_cache"] = True
                return cached
        except Exception:
            pass

    queries = build_queries(theme_prompt)
    all_videos: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for q in queries:
        try:
            for v in search_youtube_videos(q, timeout=timeout):
                all_videos.setdefault(v["video_id"], v)
        except Exception as exc:
            errors.append(str(exc)[:160])

    videos = sorted(all_videos.values(), key=lambda v: v.get("views", 0), reverse=True)
    subjects = theme_subjects(theme_prompt)
    relevance = _relevance_terms(subjects)

    def is_relevant(v: dict[str, Any]) -> bool:
        if not relevance:
            return True
        hay = f"{v.get('title') or ''} {v.get('snippet') or ''}".lower()
        return any(s in hay for s in relevance)

    relevant = [v for v in videos if is_relevant(v)] or videos
    viral = [v for v in relevant if v.get("views", 0) >= min_views]
    analyzed = analyze_humor_structure(viral or relevant)

    suggestion = None
    if not viral:
        parts = [s["structure"] for s in analyzed["signals"][:3]]
        suggestion = "Nenhum vídeo acima de 1M encontrado. " + (
            "Com base nos vídeos do tema encontrados, usar: " + "; ".join(parts) + "."
            if parts else "Sugestão: " + "; ".join(_FALLBACK_STRUCTURE.values()) + "."
        )

    payload: dict[str, Any] = {
        "ok": not errors,
        "from_cache": False,
        "searched_at": datetime.now(timezone.utc).isoformat(),
        "theme": " ".join(str(theme_prompt).split())[:300],
        "theme_hash": theme_key,
        "min_views": min_views,
        "queries": queries,
        "found_viral": bool(viral),
        "viral_count": len(viral),
        "subjects": subjects,
        "relevant_count": len(relevant),
        "videos": [
            {k: v[k] for k in ("video_id", "title", "views", "views_text", "url", "snippet")}
            for v in (viral or relevant)[:8]
        ],
        "humor": analyzed,
        "suggestion": suggestion,
        "errors": errors,
    }
    if cache_path:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    return payload


def build_prompt_section(research: dict[str, Any] | None) -> str:
    """Transforma a pesquisa em instrucao de ESTRUTURA para o roteirista (sem titulos/frases copiados)."""
    if not research:
        return ""
    humor = research.get("humor") or {}
    structure = humor.get("structure") or _FALLBACK_STRUCTURE
    signals = [s.get("structure") for s in (humor.get("signals") or []) if s.get("structure")]
    lines = ["PESQUISA DE VIRAIS DO MESMO TEMA (USE A ESTRUTURA, CRIE CONTEÚDO 100% ORIGINAL):"]
    if research.get("found_viral"):
        lines.append(f"- Encontrei {research.get('viral_count')} vídeos acima de 1 milhão de visualizações no tema.")
    else:
        lines.append(f"- {research.get('suggestion') or 'Nenhum vídeo acima de 1M encontrado; usar a fórmula abaixo.'}")
    if signals:
        lines.append("- Padrões estruturais detectados: " + " | ".join(dict.fromkeys(signals)) + ".")
    lines.append("- Estrutura obrigatória:")
    for key, label in (("hook", "Gancho"), ("engine", "Motor do riso"), ("escalation", "Escalação"),
                       ("rhythm", "Ritmo"), ("callback", "Repetição"), ("payoff", "Desfecho")):
        if structure.get(key):
            lines.append(f"  * {label}: {structure[key]}")
    lines.append(
        "- PROIBIDO copiar títulos, frases, cenas, personagens ou piadas dos vídeos pesquisados. "
        "A pesquisa serve apenas para definir o formato; cada piada deve ser escrita do zero."
    )
    return "\n".join(lines)
