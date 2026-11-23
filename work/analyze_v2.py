# -*- coding: utf-8 -*-
"""Classificacao revisada: hash exato + pHash + histograma de cor, com shortlist visual."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import FFMPEG_EXE  # noqa: E402

REF = ROOT / "assets" / "reference" / "primeiro-dia-de-praia"
MAN = REF / "flow_all" / "harvest_manifest.json"
FINAL = ROOT / "projects" / "primeiro-dia-de-praia-v5"
SHEET = REF / "CANDIDATOS.jpg"
OUT_JSON = REF / "analise_v2.json"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


DCT = np.cos(np.pi * (2 * np.arange(32)[None, :] + 1) * np.arange(32)[:, None] / 64.0)
DCT[0] *= 1 / np.sqrt(2)


def sig(im: Image.Image) -> tuple[str, np.ndarray]:
    a = np.asarray(im.convert("L").resize((32, 32), Image.LANCZOS), dtype=float)
    d = DCT @ a @ DCT.T
    b = d[:8, :8].copy()
    med = np.median(b[1:])
    ph = "".join("1" if v > med else "0" for v in b.reshape(-1))
    small = im.convert("RGB").resize((64, 64))
    arr = np.asarray(small, dtype=float) / 255.0
    hists = []
    for c in range(3):
        h, _ = np.histogram(arr[:, :, c], bins=8, range=(0, 1))
        hists.append(h / h.sum())
    return ph, np.concatenate(hists)


def frame(path: Path, kind: str) -> Image.Image:
    if kind == "image":
        return Image.open(path).convert("RGB")
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "f.jpg"
        subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-ss", "1", "-i", str(path), "-vframes", "1", str(f)], check=True, timeout=60)
        return Image.open(f).convert("RGB")


def ham(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b))


def main() -> int:
    data = json.loads(MAN.read_text(encoding="utf-8"))
    used = sorted((FINAL / "assets" / "images").glob("*.jpg")) + sorted((FINAL / "assets" / "videos").glob("*.mp4"))
    used_hash = {sha(p) for p in used}
    refs = []
    for p in used:
        try:
            ph, hi = sig(frame(p, "image" if p.suffix == ".jpg" else "video"))
            refs.append((p.stem, ph, hi))
        except Exception:
            pass

    rows = []
    for it in data["items"]:
        p = Path(it["path"])
        if not p.exists():
            continue
        try:
            ph, hi = sig(frame(p, it["kind"]))
        except Exception:
            continue
        exact = sha(p) in used_hash
        best = ("?", 99, 99.0)
        for sid, rph, rhi in refs:
            dph = ham(ph, rph)
            dhi = float(np.abs(hi - rhi).sum())
            score = dph + dhi * 6.0
            if score < best[1] + best[2]:
                best = (sid, dph, dhi)
        sid, dph, dhi = best
        if exact:
            cls = "usado"
        elif dph <= 2 and dhi <= 0.12:
            cls = "duplicata_reencode"
        elif dhi <= 0.70 and dph <= 26:
            cls = "candidato"
        else:
            cls = "fora_tema"
        rows.append({**it, "sha": sha(p), "scene": sid, "dph": dph, "dhi": round(dhi, 3), "class": cls})

    cand = [r for r in rows if r["class"] == "candidato"]
    # dedup por conteudo e por assinatura visual
    seen_hash, seen_sig, uniq = set(), set(), []
    for r in sorted(cand, key=lambda x: (x["dph"] + x["dhi"] * 6)):
        if r["sha"] in seen_hash or (r["dph"], r["dhi"]) in seen_sig:
            continue
        seen_hash.add(r["sha"])
        seen_sig.add((r["dph"], r["dhi"]))
        uniq.append(r)

    by_scene = defaultdict(list)
    for r in uniq:
        by_scene[r["scene"]].append(r)

    lines = [
        "# Auditoria de aproveitamento (revisada) — primeiro dia de praia",
        "",
        f"- Colhidos: **{data['total_videos']} vídeos + {data['total_images']} imagens** nas 5 contas",
        f"- Já usados (hash exato): **{sum(1 for r in rows if r['class'] == 'usado')}**",
        f"- Cópias reencodadas do que já entrou: **{sum(1 for r in rows if r['class'] == 'duplicata_reencode')}**",
        f"- **Candidatos novos deduplicados: {len(uniq)}** (brutos: {len(cand)})",
        f"- Fora do tema: **{sum(1 for r in rows if r['class'] == 'fora_tema')}**",
        "",
        "Pasta: `assets/reference/primeiro-dia-de-praia/flow_all/{acc}/{videos,images}`",
        "",
        "## Candidatos por cena (dph = distância de forma, dhi = distância de cor)",
        "",
    ]
    for sid in sorted(by_scene):
        lines.append(f"### {sid} — {len(by_scene[sid])}")
        for r in by_scene[sid][:12]:
            lines.append(f"- `{r['kind']}` dph={r['dph']} dhi={r['dhi']} `{r['path']}`")
        lines.append("")
    (REF / "APROVEITAMENTO.md").write_text("\n".join(lines), encoding="utf-8")

    # Relatorio especifico de imagens geradas x nao usadas
    imgs = [r for r in rows if r["kind"] == "image"]
    img_lines = [
        "# Imagens geradas que nao entraram no episodio — primeiro dia de praia",
        "",
        f"- Imagens colhidas nas 5 contas: **{len(imgs)}**",
        f"- Usadas no vídeo final (hash exato): **{sum(1 for r in imgs if r['class'] == 'usado')}**",
        f"- Copias reencodadas das que ja entraram: **{sum(1 for r in imgs if r['class'] == 'duplicata_reencode')}**",
        f"- Candidatas novas (dedup): **{sum(1 for r in imgs if r['class'] == 'candidato')}**",
        f"- Fora do tema / outros episodios: **{sum(1 for r in imgs if r['class'] == 'fora_tema')}**",
        "",
        "## Como classificar",
        "",
        "- `usado`: SHA256 identico ao arquivo em `projects/primeiro-dia-de-praia-v5/assets/images`.",
        "- `duplicata_reencode`: mesma cena do que entrou, so com another encoding/crop (pHash<=2 e cor<=0,12). Nao agrega.",
        "- `candidato`: cena parecida mas enquadramento/elementos diferentes — pode entrar como sub-clip extra.",
        "- `fora_tema`: parque, campeonato, stick figures, humanos, model sheets etc. de outros episodios.",
        "",
        "## Candidatas novas por cena",
        "",
    ]
    for sid in sorted({r["scene"] for r in imgs if r["class"] == "candidato"}):
        sel = [r for r in imgs if r["class"] == "candidato" and r["scene"] == sid]
        img_lines.append(f"### {sid} ({len(sel)})")
        for r in sel[:10]:
            img_lines.append(f"- dph={r['dph']} dhi={r['dhi']} `{r['path']}`")
        img_lines.append("")
    img_lines += [
        "## Reprovações registradas durante a producao (por cena)",
        "",
        "- `sc_10_p1` tentativa 1: reproducao da cena mostrava **Yorkshire no lugar da Luna** e **texto legivel no tubo** → reprovada e regenerada; a versao aprovada esta no vídeo final.",
        "- Na pre-varredura das 5 contas, centenas de imagens de **outros episodios** foram reprovadas por: cenario de parque/jardim em vez de praia, terceiro cao (Chihuahua) fora do elenco, Frida sem colar de perolas, Luna sem corrente de coracao, colagens/model sheets, stick figures e presenca de humanos.",
        "",
        "Pasta de referencia: `assets/reference/primeiro-dia-de-praia/flow_all/{acc}/{videos,images}`",
    ]
    (REF / "IMAGENS_NAO_USADAS.md").write_text("\n".join(img_lines), encoding="utf-8")
    (REF / "analise_v2_all.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # contact sheet dos candidatos
    if uniq:
        tw, th, cols = 220, 150, 6
        sheet = Image.new("RGB", (cols * tw, ((len(uniq) + cols - 1) // cols) * (th + 26)), (245, 245, 245))
        dr = ImageDraw.Draw(sheet)
        for i, r in enumerate(uniq[:60]):
            im = frame(Path(r["path"]), r["kind"])
            im.thumbnail((tw, th))
            x, y = (i % cols) * tw, (i // cols) * (th + 26)
            sheet.paste(im, (x + (tw - im.width) // 2, y))
            dr.text((x + 2, y + th + 2), f"{r['scene']} {r['kind'][:1]} d{r['dph']}/{r['dhi']}", fill=(0, 0, 0))
        sheet.save(SHEET, quality=88)

    summary = {
        "harvested": f"{data['total_videos']} videos + {data['total_images']} imagens",
        "used": sum(1 for r in rows if r["class"] == "usado"),
        "dup": sum(1 for r in rows if r["class"] == "duplicata_reencode"),
        "candidates": len(uniq),
        "off_theme": sum(1 for r in rows if r["class"] == "fora_tema"),
        "by_scene": {s: len(v) for s, v in sorted(by_scene.items())},
        "sheet": str(SHEET),
    }
    OUT_JSON.write_text(json.dumps({"summary": summary, "candidates": uniq}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
