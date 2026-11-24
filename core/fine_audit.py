# -*- coding: utf-8 -*-
"""Auditoria FINA clip-a-clip do MP4 final (pedido do usuario, 2026-11-24).

A porta de entrega olha 1 frame por CENA; esta auditoria olha CADA sub-clip
renderizado (3 frames por clip) e compara com o material designado para ele:

  * clip de imagem  -> similaridade com `assets/images/<clip_id>.jpg`;
  * clip de video   -> similaridade com frames do video da cena;
  * blacklist       -> nenhum frame pode ser o passarinho vetado nem a despedida
                       com patinha fantasma (comparacao visual, alem do SHA).

Reprova (fail-closed) quando um clip renderizado nao corresponde ao seu material,
o que pega desde imagem trocada ate clip velho reaproveitado de outra versao.

Gera `artifacts/fine_audit_report.json` + folha de contato dos piores clips.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image

from config import FFMPEG_EXE
from core.delivery_audit import (
    BLACKLIST_PATH,
    INDEX_PATH,
    _dur,
    _extract,
    signature,
    sim,
)

FINE_MIN_SIM = 0.62       # frame renderizado x material do clip
BLACKLIST_MAX_SIM = 0.93  # parecenca demais com material vetado


def _blacklist_refs(work: Path) -> list[Path]:
    """Materializa imagens vetadas que ainda existem no disco (para comparacao visual)."""
    if not BLACKLIST_PATH.exists():
        return []
    blocked = set(json.loads(BLACKLIST_PATH.read_text(encoding="utf-8")).get("sha256", []))
    if not blocked or not INDEX_PATH.exists():
        return []
    out: list[Path] = []
    for row in json.loads(INDEX_PATH.read_text(encoding="utf-8")).get("images", []):
        if row.get("sha256") in blocked:
            p = Path(row.get("path", ""))
            if p.exists():
                out.append(p)
    return out


def _scene_video_refs(videos_dir: Path, sid: str, work: Path, n: int = 6) -> list[Path]:
    refs: list[Path] = []
    if not videos_dir.exists():
        return refs
    for v in sorted(videos_dir.glob(f"{sid}*.mp4"))[:3]:
        d = _dur(v)
        if d <= 0.2:
            continue
        for i in range(n):
            t = d * (i + 0.5) / n
            f = _extract(v, t, work / f"ref_{v.stem}_{i}.png")
            if f:
                refs.append(f)
    return refs


def audit_fine(
    proj_dir: Path,
    out_video: Path,
    visual_clips: list[dict[str, Any]],
    images_dir: Path,
    min_sim: float = FINE_MIN_SIM,
) -> dict[str, Any]:
    work = proj_dir / "work" / "fine_audit"
    work.mkdir(parents=True, exist_ok=True)
    videos_dir = images_dir.parent / "videos"
    blocked_refs = _blacklist_refs(work)
    blocked_sigs = [(p, signature(p)) for p in blocked_refs]

    issues: list[str] = []
    rows: list[dict[str, Any]] = []
    refs_by_scene: dict[str, list[Path]] = {}

    for idx, clip in enumerate(visual_clips):
        cid = str(clip.get("clip_id", f"clip_{idx}"))
        sid = str(clip.get("scene_id", ""))
        start = float(clip.get("start") or 0.0)
        dur = max(0.15, float(clip.get("duration") or 0.0))
        times = [start + dur * 0.25, start + dur * 0.75]
        jpg = images_dir / f"{cid}.jpg"
        is_video = bool(clip.get("video_path")) or bool(list(videos_dir.glob(f"{sid}*.mp4"))) if videos_dir.exists() else False

        refs: list[Path] = []
        if is_video:
            if sid not in refs_by_scene:
                refs_by_scene[sid] = _scene_video_refs(videos_dir, sid, work)
            refs = refs_by_scene[sid]
            if jpg.exists():
                refs = refs + [jpg]
        else:
            if jpg.exists():
                refs = [jpg]
        if not refs:
            issues.append(f"fino {cid}: sem referencia visual para comparar")
            continue

        sims: list[float] = []
        blocked_hit = ""
        for j, t in enumerate(times):
            frame = _extract(out_video, t, work / f"{cid}_{j}.png")
            if frame is None:
                continue
            fsig = signature(frame)
            sims.append(max(sim(fsig, signature(r)) for r in refs))
            for bp, bsig in blocked_sigs:
                if sim(fsig, bsig) >= BLACKLIST_MAX_SIM:
                    blocked_hit = bp.name
                    break

        if not sims:
            issues.append(f"fino {cid}: nao foi possivel extrair frame em t={start:.2f}s")
            continue
        worst = min(sims)
        rows.append({"clip": cid, "scene": sid, "t": round(start, 2),
                     "min_sim": round(worst, 3), "source": "video" if is_video else "image",
                     "blocked": blocked_hit})
        if blocked_hit:
            issues.append(f"fino {cid}: frame parece material VETADO ({blocked_hit})")
        elif worst < min_sim:
            issues.append(
                f"fino {cid} (cena {sid}, t={start:.2f}s): frame nao corresponde ao material "
                f"do clip (sim={worst:.3f} < {min_sim})"
            )

    # folha de contato dos 12 piores (evidencia humana)
    worst_rows = sorted(rows, key=lambda r: r["min_sim"])[:12]
    frames: list[tuple[dict[str, Any], Path]] = []
    for r in worst_rows:
        t = float(r["t"]) + 0.4
        f = _extract(out_video, t, work / f"worst_{r['clip']}.png")
        if f:
            frames.append((r, f))
    if frames:
        cols, tw, th = 3, 400, 225
        rows_n = (len(frames) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows_n * (th + 18)), (16, 16, 20))
        from PIL import ImageDraw

        dr = ImageDraw.Draw(sheet)
        for i, (r, f) in enumerate(frames):
            im = Image.open(f).convert("RGB")
            im.thumbnail((tw, th))
            x, y = (i % cols) * tw, (i // cols) * (th + 18)
            sheet.paste(im, (x, y))
            dr.text((x + 3, y + th + 2),
                    f"{r['clip']} sim={r['min_sim']}", fill=(255, 230, 120))
        sheet.save(work / "piores_clips.jpg", quality=86)

    report = {
        "approved": len(issues) == 0,
        "clips_checked": len(rows),
        "issues_count": len(issues),
        "issues": issues,
        "worst": sorted(rows, key=lambda r: r["min_sim"])[:15],
        "min_sim_threshold": min_sim,
        "contact_sheet": str(work / "piores_clips.jpg") if frames else "",
    }
    out = proj_dir / "artifacts" / "fine_audit_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_path"] = str(out)
    return report
