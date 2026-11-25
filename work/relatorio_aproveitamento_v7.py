# -*- coding: utf-8 -*-
"""Relatorio de aproveitamento do projeto "primeiro dia de praia" (v7 final).

Compara TUDO que foi gerado no Flow (imagens/videos) com o que entrou no MP4
final, deduplica por SHA e por assinatura visual (para versoes processadas),
e escreve `work/relatorio_aproveitamento_v7.md` com a descricao de cada item
gerado que NAO foi usado.

Uso: python work/relatorio_aproveitamento_v7.py [slug]
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import FFMPEG_EXE  # noqa: E402
from core.delivery_audit import (  # noqa: E402
    BLACKLIST_PATH,
    sha256,
    signature,
    sim,
    theme_of,
)

REF = ROOT / "assets" / "reference" / "primeiro-dia-de-praia"
FLOW = REF / "flow_all"
HARVEST = REF / "analise_v2_all.json"
SIM_IMAGE = 0.92       # mesma foto, crop/resize/reencode
SIM_VIDEO = 0.86       # mesmo clipe, reencode
TMP = ROOT / "work" / "_inventory_frames"


def _meta() -> dict[str, dict[str, Any]]:
    if not HARVEST.exists():
        return {}
    data = json.loads(HARVEST.read_text(encoding="utf-8"))
    return {str(x.get("path", "")): x for x in data if isinstance(x, dict)}


def _frame_sigs(video: Path, sid: str, n: int = 3) -> list:
    TMP.mkdir(parents=True, exist_ok=True)
    out: list = []
    dur = _dur(video)
    if dur <= 0.2:
        return out
    for i in range(n):
        t = dur * (i + 0.5) / n
        p = TMP / f"{sid}_{i}.png"
        r = subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{t:.2f}",
                            "-i", str(video), "-frames:v", "1", str(p)], capture_output=True)
        if r.returncode == 0 and p.exists():
            out.append(signature(p))
    return out


def _dur(video: Path) -> float:
    ffprobe = Path(FFMPEG_EXE).with_name("ffprobe.exe")
    r = subprocess.run([str(ffprobe), "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(video)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _describe(meta: dict[str, Any], path: Path) -> str:
    aria = str(meta.get("aria") or "").strip()
    scene = str(meta.get("scene") or "").strip()
    if aria:
        return f"{aria} [{scene}]" if scene else aria
    return path.stem


def _rows_images(used_sigs: list, used_sha: set[str], meta: dict[str, dict[str, Any]],
                 blocked: set[str]) -> tuple[list[dict[str, Any]], dict[str, Counter]]:
    files = sorted(FLOW.glob("acc_*/images/*.jpg"))
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    stats: dict[str, Counter] = {"status": Counter(), "theme": Counter()}
    for p in files:
        h = sha256(p)
        m = meta.get(str(p), {})
        desc = _describe(m, p)
        theme = theme_of(f"{desc} {p.stem}")
        if h in seen:
            continue  # duplicata exata dentro do proprio harvest
        seen.add(h)
        if h in used_sha:
            status = "usado-exato"
        elif h in blocked:
            status = "vetado-blacklist"
        else:
            s = signature(p)
            best = max((sim(s, u) for u in used_sigs), default=0.0)
            status = "usado-processado" if best >= SIM_IMAGE else "nao-usado"
        stats["status"][status] += 1
        if status == "nao-usado":
            stats["theme"][theme] += 1
        rows.append({"sha": h, "path": str(p.relative_to(ROOT)), "account": p.parent.parent.name,
                     "description": desc, "theme": theme, "status": status,
                     "harvest_class": str(m.get("class") or ""),
                     "scene": str(m.get("scene") or "")})
    return rows, stats


def _rows_videos(used_sigs: dict[str, list], used_sha: set[str],
                 meta: dict[str, dict[str, Any]], blocked_vid: set[str]
                 ) -> tuple[list[dict[str, Any]], dict[str, Counter]]:
    files = sorted(FLOW.glob("acc_*/videos/*.mp4"))
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    stats: dict[str, Counter] = {"status": Counter(), "theme": Counter()}
    for p in files:
        h = sha256(p)
        m = meta.get(str(p), {})
        desc = _describe(m, p)
        theme = theme_of(f"{desc} {p.stem}")
        if h in seen:
            continue
        seen.add(h)
        if h in used_sha:
            status = "usado-exato"
        elif h in blocked_vid:
            status = "vetado-blacklist"
        else:
            sigs = _frame_sigs(p, p.stem[:8])
            best, best_id = 0.0, ""
            for vid_id, ref_sigs in used_sigs.items():
                for a in sigs:
                    for b in ref_sigs:
                        s = sim(a, b)
                        if s > best:
                            best, best_id = s, vid_id
            status = "usado-reencode" if best >= SIM_VIDEO else "nao-usado"
        stats["status"][status] += 1
        if status == "nao-usado":
            stats["theme"][theme] += 1
        rows.append({"sha": h, "path": str(p.relative_to(ROOT)),
                     "account": p.parent.parent.name, "description": desc,
                     "duration": round(_dur(p), 2), "theme": theme, "status": status,
                     "harvest_class": str(m.get("class") or ""),
                     "nearest": best_id if status == "usado-reencode" else ""})
    return rows, stats


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "primeiro-dia-de-praia-v7"
    proj = ROOT / "projects" / slug
    meta = _meta()
    blacklist = json.loads(BLACKLIST_PATH.read_text(encoding="utf-8")) if BLACKLIST_PATH.exists() else {}
    blocked_img = set(blacklist.get("sha256", []))
    blocked_vid = set(blacklist.get("video_sha256", []))

    used_imgs = sorted((proj / "assets" / "images").glob("*.jpg"))
    used_vids = sorted((proj / "assets" / "videos").glob("*.mp4"))
    used_img_sha = {sha256(p) for p in used_imgs}
    used_vid_sha = {sha256(p) for p in used_vids}
    uniq: dict[str, Any] = {}
    for p in used_imgs:
        uniq.setdefault(sha256(p), signature(p))
    used_sigs_img = list(uniq.values())
    used_sigs_vid = {p.stem: _frame_sigs(p, p.stem[:8]) for p in used_vids}

    img_rows, img_stats = _rows_images(used_sigs_img, used_img_sha, meta, blocked_img)
    vid_rows, vid_stats = _rows_videos(used_sigs_vid, used_vid_sha, meta, blocked_vid)

    lines: list[str] = [
        "# Relatorio de aproveitamento — primeiro dia de praia (v7 final)",
        "",
        "Comparacao entre tudo que foi gerado no Flow e o que realmente entrou no MP4 final.",
        "Duplicatas exatas (mesmo SHA dentro do harvest) contam uma unica vez.",
        "",
        "## Resumo",
        "",
        "| Tipo | Gerados (arquivos) | Gerados (unicos) | Usados | Nao usados | Vetados |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    img_total_files = len(list(FLOW.glob("acc_*/images/*.jpg")))
    vid_total_files = len(list(FLOW.glob("acc_*/videos/*.mp4")))
    i_used = img_stats["status"]["usado-exato"] + img_stats["status"]["usado-processado"]
    v_used = vid_stats["status"]["usado-exato"] + vid_stats["status"]["usado-reencode"]
    lines += [
        f"| Imagens | {img_total_files} | {len(img_rows)} | {i_used} | "
        f"{img_stats['status']['nao-usado']} | {img_stats['status']['vetado-blacklist']} |",
        f"| Videos | {vid_total_files} | {len(vid_rows)} | {v_used} | "
        f"{vid_stats['status']['nao-usado']} | {vid_stats['status']['vetado-blacklist']} |",
        "",
        "Status das imagens unicas: " + ", ".join(f"{k}={v}" for k, v in sorted(img_stats["status"].items())),
        "Status dos videos unicos: " + ", ".join(f"{k}={v}" for k, v in sorted(vid_stats["status"].items())),
        "",
        f"Imagens usadas no final: **{len(used_img_sha)}** imagens distintas "
        f"({len(used_imgs)} arquivos de clip). Videos usados no final: **{len(used_vids)}** "
        "(15 do Flow + 1 despedida composta).",
        "",
        "Temas das imagens nao usadas: " + ", ".join(f"{k}={v}" for k, v in img_stats["theme"].most_common()),
        "Temas dos videos nao usados: " + ", ".join(f"{k}={v}" for k, v in vid_stats["theme"].most_common()),
        "",
        "## Imagens geradas que NAO foram usadas",
        "",
        "| Conta | Arquivo | Descricao (Flow) | Tema | Classe colheita |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in [x for x in img_rows if x["status"] == "nao-usado"]:
        lines.append(f"| {r['account']} | `{Path(r['path']).name}` | {r['description']} | "
                     f"{r['theme']} | {r['harvest_class']} |")
    lines += [
        "",
        "## Imagens usadas no final",
        "",
        "| Conta | Arquivo | Descricao | Status |",
        "| --- | --- | --- | --- |",
    ]
    for r in [x for x in img_rows if x["status"].startswith("usado")]:
        lines.append(f"| {r['account']} | `{Path(r['path']).name}` | {r['description']} | {r['status']} |")
    lines += [
        "",
        "## Videos gerados que NAO foram usados",
        "",
        "| Conta | Arquivo | Descricao (Flow) | Dur. | Tema | Classe colheita |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for r in [x for x in vid_rows if x["status"] == "nao-usado"]:
        lines.append(f"| {r['account']} | `{Path(r['path']).name}` | {r['description']} | "
                     f"{r['duration']}s | {r['theme']} | {r['harvest_class']} |")
    lines += [
        "",
        "## Videos usados no final",
        "",
        "| Conta | Arquivo | Descricao | Dur. | Status |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for r in [x for x in vid_rows if x["status"].startswith("usado")]:
        lines.append(f"| {r['account']} | `{Path(r['path']).name}` | {r['description']} | "
                     f"{r['duration']}s | {r['status']} |")
    lines += [
        "",
        "## Vetados (blacklist)",
        "",
        "| Tipo | Arquivo | Motivo |",
        "| --- | --- | --- |",
    ]
    for r in [x for x in img_rows if x["status"] == "vetado-blacklist"]:
        lines.append(f"| imagem | `{Path(r['path']).name}` | {r['description']} |")
    for r in [x for x in vid_rows if x["status"] == "vetado-blacklist"]:
        lines.append(f"| video | `{Path(r['path']).name}` | {r['description']} |")
    gitdiff = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--stat", "531cd66..HEAD"],
        capture_output=True, text=True,
    ).stdout.strip()
    lines += [
        "",
        "## Diff de código desde o último render aprovado (commit 531cd66)",
        "",
        "```",
        gitdiff or "(sem alterações)",
        "```",
        "",
        "Evidência: `artifacts/final_audit_report.json`, `artifacts/image_assignment.json`, "
        "`artifacts/pacing_plan_v2.json` e `assets/videos/` do projeto final.",
        "",
    ]

    out = ROOT / "work" / "relatorio_aproveitamento_v7.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[relatorio] {out}")
    print(f"[relatorio] imagens: {len(img_rows)} unicas | "
          f"usadas={i_used} nao-usadas={img_stats['status']['nao-usado']} "
          f"vetadas={img_stats['status']['vetado-blacklist']}")
    print(f"[relatorio] videos: {len(vid_rows)} unicos | "
          f"usados={v_used} nao-usados={vid_stats['status']['nao-usado']} "
          f"vetados={vid_stats['status']['vetado-blacklist']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
