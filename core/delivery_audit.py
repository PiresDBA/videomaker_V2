# -*- coding: utf-8 -*-
"""Porta de entrega obrigatoria (Regras 9 e 13 do CONTRATO_MOTOR_V2.md).

Nenhum video e entregue sem passar por aqui. A auditoria e LOCAL e deterministica:
nao depende de Vision API, entao nao pode falhar por cota/rede e nao pode ser
burlada por atalho de montagem.

Verificacoes:
  1. WHITELIST: toda imagem usada no projeto tem SHA256 igual a uma imagem aprovada
     (v5 + v6), catalogada em assets/reference/primeiro-dia-de-praia/approved_images.json.
     -> Pega na origem a contaminacao por colheita velha (astronauta, galinha, parque).
  2. FRAME x CENA: extrai 1 frame por cena do MP4 final e exige similaridade com
     alguma imagem/videos designados para aquela cena (fail-closed).
  3. RAJADA: fractions consecutivos de burst nao podem ser quasi identicos
     (0.98 = micro-zoom de uma unica foto => "tremendo dos lados").
  4. DESPEDIDA/CTA: ultimo frame deve bater com a referencia aprovada de CTA.
  5. CONTATO: salva folhas de contato para conferencia humana.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
ROOT = ROOT_DIR
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
from config import FFMPEG_EXE  # noqa: E402

REF_DIR = ROOT / "assets" / "reference" / "primeiro-dia-de-praia"
INDEX_PATH = REF_DIR / "approved_images.json"
CTA_REF_PATH = REF_DIR / "cta_final_ref.jpg"
CTA_REF_ALT = REF_DIR / "cta_final_v5_ref.jpg"  # despedida alternativa aprovada (v5)
APPROVED_SOURCES = (
    ROOT / "projects" / "primeiro-dia-de-praia-v5" / "assets" / "images",
    ROOT / "projects" / "primeiro-dia-de-praia-v6" / "assets" / "images",
)
SIM_MIN = 0.68          # abaixo disso: frame nao corresponde a cena
BURST_MAX_SIM = 0.96    # acima disso: rajada "tremendo" (frames identicos)
CTA_MIN_SIM = 0.62      # abaixo disso: despedida/CTA ausente


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_approved_index() -> dict[str, Any]:
    """ gere o indice de imagens aprovadas (v5 + v6). Chamado uma vez e versionado. """
    images: list[dict[str, str]] = []
    seen: set[str] = set()
    for base in APPROVED_SOURCES:
        if not base.exists():
            continue
        for p in sorted(base.glob("*.jpg")):
            h = sha256(p)
            if h in seen:
                continue
            seen.add(h)
            images.append({
                "sha256": h,
                "name": p.name,
                "source": base.parent.parent.name,
                "path": str(p),
            })
    payload = {"version": 1, "source": "v5 aprovado + v6 tematico", "images": images}
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_approved_index() -> set[str]:
    if not INDEX_PATH.exists():
        build_approved_index()
    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return {r["sha256"] for r in data.get("images", [])}


def signature(path: Path, size: int = 32) -> tuple[list[float], list[float]]:
    """Assinatura robusta a crop/Ken Burns: pixels normalizados + histograma HSV."""
    im = Image.open(path).convert("RGB").resize((size, size), Image.Resampling.BILINEAR)
    px = list(im.getdata())
    flat: list[float] = []
    hist = [0.0] * 25
    for r, g, b in px:
        flat += [r / 255.0, g / 255.0, b / 255.0]
        mx, mn = max(r, g, b), min(r, g, b)
        d = mx - mn
        if d == 0:
            h = 0
        elif mx == r:
            h = ((g - b) / d) % 6
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        hb = min(11, int(h * 2))
        sb = min(1, int(mx / 128))
        vb = min(1, int(mx / 128))
        hist[hb * 2 + sb + vb] += 1
    n = float(len(px))
    return flat, [v / n for v in hist]


def sim(a: tuple[list[float], list[float]], b: tuple[list[float], list[float]]) -> float:
    fa, ha = a
    fb, hb = b
    ma = sum(fa) / len(fa)
    mb = sum(fb) / len(fb)
    num = sum((x - ma) * (y - mb) for x, y in zip(fa, fb))
    da = math.sqrt(sum((x - ma) ** 2 for x in fa))
    db = math.sqrt(sum((y - mb) ** 2 for y in fb))
    corr = num / (da * db) if da and db else 0.0
    hc = sum(math.sqrt(x * y) for x, y in zip(ha, hb))
    return 0.5 * max(0.0, corr) + 0.5 * hc


def _extract(video: Path, t: float, out: Path) -> Path | None:
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video),
         "-frames:v", "1", str(out)],
        capture_output=True,
    )
    return out if r.returncode == 0 and out.exists() else None


def _dur(video: Path) -> float:
    ffprobe = Path(FFMPEG_EXE).with_name("ffprobe.exe")
    r = subprocess.run(
        [str(ffprobe), "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(video)], capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def check_whitelist(images_dir: Path, approved: set[str]) -> list[str]:
    """Retorna os nomes de arquivos de imagem que NAO estao no pool aprovado."""
    if not images_dir.exists():
        return []
    return [p.name for p in sorted(images_dir.glob("*.jpg")) if sha256(p) not in approved]


def audit_delivery(
    proj_dir: Path,
    out_16_9: Path,
    visual_clips: list[dict[str, Any]],
    images_dir: Path,
    strict: bool = True,
) -> dict[str, Any]:
    """ Audita o MP4 final. Retorna {'approved','issues','scenes',...} e grava relatorio. """
    issues: list[str] = []
    details: list[dict[str, Any]] = []
    work = proj_dir / "work" / "delivery_audit"
    work.mkdir(parents=True, exist_ok=True)

    if not out_16_9.exists() or out_16_9.stat().st_size < 1000:
        return {"approved": False, "issues": [f"video final ausente: {out_16_9}"],
                "scenes": [], "report_path": ""}

    # 1. WHITELIST deterministica
    approved = load_approved_index()
    bad = check_whitelist(images_dir, approved)
    if bad:
        issues.append(
            f"whitelist: {len(bad)} imagem(ns) fora do pool aprovado "
            f"(ex.: {', '.join(bad[:4])}) — colheita velha contaminada"
        )

    # agrupa clips por cena
    scenes: dict[str, list[dict[str, Any]]] = {}
    for c in visual_clips:
        scenes.setdefault(c["scene_id"], []).append(c)

    videos_dir = images_dir.parent / "videos"
    scene_frames: dict[str, Path] = {}

    # 2. FRAME x CENA (fail-closed)
    for sid in sorted(scenes):
        clips = scenes[sid]
        p1 = next((c for c in clips if c["clip_id"].endswith("_p1")), clips[0])
        t = (float(p1.get("start") or 0) + float(p1.get("end") or 0)) / 2
        frame = _extract(out_16_9, t, work / f"{sid}.png")
        if frame is None:
            issues.append(f"cine {sid}: nao foi possivel extrair frame em t={t:.2f}s")
            continue
        scene_frames[sid] = frame

        # referencias da cena: imagens designadas + videos da cena
        refs: list[Path] = [images_dir / f"{c['clip_id']}.jpg" for c in clips]
        refs = [p for p in refs if p.exists()]
        vids = sorted(videos_dir.glob(f"{sid}*.mp4")) if videos_dir.exists() else []
        for v in vids[:3]:
            rv = _extract(v, min(2.0, max(0.3, _dur(v) * 0.3)), work / f"ref_{sid}_{v.stem}.png")
            if rv:
                refs.append(rv)
        if not refs:
            issues.append(f"cena {sid}: sem imagens/videos de referencia")
            continue
        fsig = signature(frame)
        best = max((sim(fsig, signature(r)), r.name) for r in refs)
        details.append({"scene": sid, "t": round(t, 2), "best_sim": round(best[0], 3),
                        "ref": best[1], "n_refs": len(refs), "has_video": bool(vids)})
        if best[0] < SIM_MIN:
            issues.append(
                f"cena {sid}: frame renderizado nao bate com a cena "
                f"(sim={best[0]:.3f} < {SIM_MIN}; ref={best[1]})"
            )

    # 3. RAJADA (frames quasi identicos = micro-zoom / tremidacao)
    for sid, clips in scenes.items():
        bursts = [c for c in clips if "_b_" in c["clip_id"]]
        if len(bursts) < 4:
            continue
        b0, b1 = bursts[0], bursts[-1]
        t0 = float(b0.get("start") or 0)
        t1 = float(b1.get("end") or t0 + 1.3)
        frames: list[Path] = []
        for i in range(8):
            t = t0 + (t1 - t0) * i / 8
            f = _extract(out_16_9, t, work / f"burst_{sid}_{i}.png")
            if f:
                frames.append(f)
        if len(frames) >= 5:
            vals = [sim(signature(a), signature(b)) for a, b in zip(frames, frames[1:])]
            mean = sum(vals) / len(vals)
            details.append({"scene": sid, "burst_mean_sim": round(mean, 4)})
            if mean > BURST_MAX_SIM:
                issues.append(
                    f"cena {sid}: rajada tremendo — {len(frames)} frames com "
                    f"similaridade media {mean:.3f} > {BURST_MAX_SIM} (micro-zoom de 1 foto)"
                )

    # 4. DESPEDIDA / CTA
    total = _dur(out_16_9)
    final_frame = _extract(out_16_9, max(0.0, total - 0.5), work / "final.png")
    refs = [p for p in (CTA_REF_PATH, CTA_REF_ALT) if p.exists()]
    if final_frame and refs:
        fsig = signature(final_frame)
        fsim, fname = max((sim(fsig, signature(p)), p.name) for p in refs)
        details.append({"final_sim": round(fsim, 3), "final_ref": fname})
        if fsim < CTA_MIN_SIM:
            issues.append(
                f"despedida/CTA: ultimo frame nao bate com nenhuma despedida aprovada "
                f"(melhor sim={fsim:.3f} < {CTA_MIN_SIM})"
            )
    elif not refs:
        issues.append("referencias de CTA ausentes: " + str(CTA_REF_PATH))

    # 5. folhas de contato (evidencia humana)
    ordered = [scene_frames[s] for s in sorted(scene_frames)]
    for page in range(0, len(ordered), 12):
        chunk = ordered[page:page + 12]
        cols, tw, th = 3, 400, 225
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * th), (18, 18, 22))
        for i, f in enumerate(chunk):
            im = Image.open(f).convert("RGB")
            im.thumbnail((tw, th))
            sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
        sheet.save(work / f"contato_{page // 12 + 1}.jpg", quality=85)

    report = {
        "approved": len(issues) == 0,
        "strict": strict,
        "issues_count": len(issues),
        "issues": issues,
        "whitelist_size": len(approved),
        "frames_checked": len(scene_frames),
        "details": details,
        "contact_sheets": sorted(p.name for p in work.glob("contato_*.jpg")),
        "video": str(out_16_9),
    }
    report_path = proj_dir / "artifacts" / "delivery_audit_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Porta de entrega obrigatoria (auditoria visual local).")
    ap.add_argument("slug", nargs="?", default="primeiro-dia-de-praia-v6")
    ap.add_argument("--build-index", action="store_true", help="regera indice de imagens aprovadas")
    args = ap.parse_args()
    if args.build_index:
        idx = build_approved_index()
        print(f"[delivery-audit] indice: {len(idx['images'])} imagens aprovadas -> {INDEX_PATH}")
        return 0
    root = ROOT
    proj = root / "projects" / args.slug
    video = proj / "output" / f"{args.slug}_16x9.mp4"
    pacing = json.loads((proj / "artifacts" / "pacing_plan_v2.json").read_text(encoding="utf-8"))
    rep = audit_delivery(proj, video, pacing, proj / "assets" / "images")
    print(f"[delivery-audit] APPROVED={rep['approved']} | issues={rep['issues_count']} | frames={rep['frames_checked']}")
    for it in rep["issues"][:30]:
        print("  [FAIL]", it)
    print("[delivery-audit] relatorio:", rep.get("report_path"))
    return 0 if rep["approved"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
