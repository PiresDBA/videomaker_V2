# -*- coding: utf-8 -*-
"""Relatorio da CONTINUACAO: todo material de praia gerado que NAO entrou no v7.

Criterio do usuario (2026-11-24): nao ha prioridade para imagens aprovadas —
TODAS as imagens/videos gerados com tema de praia serao aproveitados no novo
episodio. Este relatorio relateia exatamente o que ficou de fora do ultimo
video, com descricao, conta e arquivo. Material de outro cenario fica numa
secao a parte, so para conferencia.

Uso: python work/relatorio_continuacao_praia.py [slug]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import FFMPEG_EXE  # noqa: E402
from core.delivery_audit import (  # noqa: E402
    BLACKLIST_PATH, sha256, signature, sim, theme_of,
)

REF = ROOT / "assets" / "reference" / "primeiro-dia-de-praia"
FLOW = REF / "flow_all"
HARVEST = REF / "analise_v2_all.json"
TMP = ROOT / "work" / "_continuacao_frames"

# Palavras que identificam OUTRO cenario (fora do universo praia).
OFF = (
    r"spaceship|park|grass|bathtub|bath|pet shop|hallway|car|bird|pigeon|"
    r"\bants?\b|backpack|forest|trophy|living room|sofa|snow|mountain|street|"
    r"bedroom|kitchen|butterfly|cat|fountain|daisy|bicycle|skater|"
    r"motion graphics|stick\s?figure|stickman|motion graphic|vitamin|biscoito|bone|"
    r"kitten|puppy grooming|cliff top|couch|pillow|bed |oak|tree|biscuit|"
    r"cookie|duck|flower|garden|toy|treat|track|hill|rug|carpet|window|"
    r"lighthouse|smartphone|\bphone\b|studio|\bmap\b|fork path|spear|"
    r"\bclock\b|question mark|in room|\broom\b"
)
# Praia / mar / areia em PT e EN.
BEACH = (
    r"beach|praia|ocean|sea|wave|onda|sand|areia|shell|concha|castle|castelo|"
    r"water|agua|wet|molh|foam|espuma|surf|bucket|balde|towel|toalha|"
    r"umbrella|guarda-sol|sunset|por do sol|dune|duna|shore|costa|seaside|"
    r"swim|flutu|maré|mare|cochilo|waving|acen"
)


def _meta() -> dict[str, dict[str, Any]]:
    if not HARVEST.exists():
        return {}
    return {str(x.get("path", "")): x for x in json.loads(HARVEST.read_text(encoding="utf-8"))
            if isinstance(x, dict)}


def _is_beach(meta: dict[str, Any], path: Path) -> bool:
    text = f"{meta.get('aria', '')} {meta.get('scene', '')} {path.stem}".lower()
    if re.search(BEACH, text) and not re.search(OFF, text):
        return True
    if re.search(OFF, text):
        return False
    # Sem descricao confiavel: foi gerado dentro do projeto da praia.
    return True


def _desc(meta: dict[str, Any], path: Path) -> str:
    aria = str(meta.get("aria") or "").strip()
    scene = str(meta.get("scene") or "").strip()
    if aria:
        return f"{aria} [{scene}]" if scene else aria
    return path.stem


def _dur(video: Path) -> float:
    ffprobe = Path(FFMPEG_EXE).with_name("ffprobe.exe")
    r = subprocess.run([str(ffprobe), "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(video)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _video_sigs(video: Path, key: str, n: int = 3) -> list:
    TMP.mkdir(parents=True, exist_ok=True)
    out = []
    d = _dur(video)
    for i in range(n):
        p = TMP / f"{key}_{i}.png"
        r = subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{d * (i + 0.5) / n:.2f}",
                            "-i", str(video), "-frames:v", "1", str(p)], capture_output=True)
        if r.returncode == 0 and p.exists():
            out.append(signature(p))
    return out


def _unique(files: list[Path]) -> list[Path]:
    seen, out = set(), []
    for p in sorted(files):
        h = sha256(p)
        if h not in seen:
            seen.add(h)
            out.append(p)
    return out


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "primeiro-dia-de-praia-v7"
    proj = ROOT / "projects" / slug
    meta = _meta()
    bl = json.loads(BLACKLIST_PATH.read_text(encoding="utf-8")) if BLACKLIST_PATH.exists() else {}
    blocked_img = set(bl.get("sha256", []))
    blocked_vid = set(bl.get("video_sha256", []))

    used_imgs = sorted((proj / "assets" / "images").glob("*.jpg"))
    used_vids = sorted((proj / "assets" / "videos").glob("*.mp4"))
    used_img_sha = {sha256(p) for p in used_imgs}
    used_vid_sha = {sha256(p) for p in used_vids}
    uniq_used_img: dict[str, Any] = {}
    for p in used_imgs:
        uniq_used_img.setdefault(sha256(p), signature(p))
    used_sigs_img = list(uniq_used_img.values())
    used_sigs_vid = {p.stem: _video_sigs(p, p.stem) for p in used_vids}

    imgs = _unique(list(FLOW.glob("acc_*/images/*.jpg")))
    vids = _unique(list(FLOW.glob("acc_*/videos/*.mp4")))

    img_rows, vid_rows = [], []
    for p in imgs:
        m = meta.get(str(p), {})
        h = sha256(p)
        beach = _is_beach(m, p)
        if h in used_img_sha:
            status, best = "usado", 1.0
        else:
            s = signature(p)
            best = max((sim(s, u) for u in used_sigs_img), default=0.0)
            status = "usado-processado" if best >= 0.92 else (
                "vetado" if h in blocked_img else "nao-usado")
        img_rows.append({"path": p, "account": p.parent.parent.name, "desc": _desc(m, p),
                         "beach": beach, "status": status, "sim": best,
                         "theme": theme_of(f"{_desc(m, p)}"),
                         "scene": str(m.get("scene") or "")})

    for p in vids:
        m = meta.get(str(p), {})
        h = sha256(p)
        beach = _is_beach(m, p)
        if h in used_vid_sha:
            status, best = "usado", 1.0
            nearest = ""
        else:
            sigs = _video_sigs(p, p.stem[:10])
            best, nearest = 0.0, ""
            for vid, refs in used_sigs_vid.items():
                for a in sigs:
                    for b in refs:
                        s = sim(a, b)
                        if s > best:
                            best, nearest = s, vid
            status = "usado-reencode" if best >= 0.86 else (
                "vetado" if h in blocked_vid else "nao-usado")
        vid_rows.append({"path": p, "account": p.parent.parent.name, "desc": _desc(m, p),
                         "beach": beach, "status": status, "sim": best,
                         "duration": round(_dur(p), 2), "nearest": nearest,
                         "theme": theme_of(f"{_desc(m, p)}")})

    beach_i_un = [r for r in img_rows if r["beach"] and r["status"] == "nao-usado"]
    beach_v_un = [r for r in vid_rows if r["beach"] and r["status"] == "nao-usado"]
    off_i = [r for r in img_rows if not r["beach"]]
    off_v = [r for r in vid_rows if not r["beach"]]

    L: list[str] = [
        "# Continuação — material de praia que NÃO entrou no último vídeo",
        "",
        "Critério: **todas** as imagens e vídeos gerados com tema de praia serão aproveitados.",
        "Não há distinção entre aprovados e não aprovados. Itens de outros cenários "
        "(parque, banheira, nave, passarinho etc.) ficam só na seção de conferência.",
        "Duplicatas exatas (mesmo SHA dentro do harvest) contam uma vez.",
        "",
        "## Resumo",
        "",
        "| Tipo | Gerados (arquivos) | Únicos | Da praia | Já usados | Da praia e NÃO usados | Outro cenário | Vetados |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| Imagens | {len(list(FLOW.glob('acc_*/images/*.jpg')))} | {len(img_rows)} | "
        f"{sum(1 for r in img_rows if r['beach'])} | "
        f"{sum(1 for r in img_rows if r['status'].startswith('usado'))} | {len(beach_i_un)} | "
        f"{len(off_i)} | {sum(1 for r in img_rows if r['status'] == 'vetado')} |",
        f"| Vídeos | {len(list(FLOW.glob('acc_*/videos/*.mp4')))} | {len(vid_rows)} | "
        f"{sum(1 for r in vid_rows if r['beach'])} | "
        f"{sum(1 for r in vid_rows if r['status'].startswith('usado'))} | {len(beach_v_un)} | "
        f"{len(off_v)} | {sum(1 for r in vid_rows if r['status'] == 'vetado')} |",
        "",
        "## Imagens DE PRAIA que não entraram no v7 (para a continuação)",
        "",
        "| Conta | Arquivo | Descrição | Cena de origem | Tema | Sim. c/ usada |",
        "| --- | --- | --- | --- | --- | ---: |",
    ]
    for r in beach_i_un:
        L.append(f"| {r['account']} | `{r['path'].name}` | {r['desc']} | {r['scene']} | "
                 f"{r['theme']} | {r['sim']:.2f} |")
    L += [
        "",
        "## Vídeos DE PRAIA que não entraram no v7 (para a continuação)",
        "",
        "| Conta | Arquivo | Descrição | Cena | Duração | Sim. c/ usado |",
        "| --- | --- | --- | --- | ---: | ---: |",
    ]
    for r in beach_v_un:
        L.append(f"| {r['account']} | `{r['path'].name}` | {r['desc']} | {r['scene'] if 'scene' in r else ''} | "
                 f"{r['duration']}s | {r['sim']:.2f} |")
    L += [
        "",
        "## Já usados no v7 (referência)",
        "",
        "| Tipo | Arquivo | Descrição |",
        "| --- | --- | --- |",
    ]
    for r in [x for x in img_rows if x["status"].startswith("usado")]:
        L.append(f"| imagem | `{r['path'].name}` | {r['desc']} |")
    for r in [x for x in vid_rows if x["status"].startswith("usado")]:
        L.append(f"| vídeo | `{r['path'].name}` | {r['desc']} |")
    L += [
        "",
        "## Fora da praia (não usar na continuação)",
        "",
        "| Tipo | Arquivo | Descrição |",
        "| --- | --- | --- |",
    ]
    for r in off_i:
        L.append(f"| imagem | `{r['path'].name}` | {r['desc']} |")
    for r in off_v:
        L.append(f"| vídeo | `{r['path'].name}` | {r['desc']} |")
    L += [
        "",
        "## Vetados (não usar)",
        "",
        "| Tipo | Arquivo | Descrição |",
        "| --- | --- | --- |",
    ]
    for r in [x for x in img_rows + vid_rows if x["status"] == "vetado"]:
        L.append(f"| {r['path'].suffix[1:]} | `{r['path'].name}` | {r['desc']} |")
    L += [""]

    out = ROOT / "work" / "relatorio_continuacao_praia.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"[continuacao] {out}")
    print(f"[continuacao] imagens de praia nao usadas: {len(beach_i_un)} | "
          f"videos de praia nao usados: {len(beach_v_un)}")
    print(f"[continuacao] fora da praia: {len(off_i)} imagens, {len(off_v)} videos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
