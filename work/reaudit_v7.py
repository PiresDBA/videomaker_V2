# -*- coding: utf-8 -*-
"""Reexecuta a auditoria final sem re-renderizar (usado apos corrigir metadado do indice)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import TARGET_VEO_VIDEOS  # noqa: E402
from core.self_audit import run_final_audit  # noqa: E402


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "primeiro-dia-de-praia-v7"
    proj = ROOT / "projects" / slug
    out = proj / "output" / f"{slug}_16x9.mp4"
    rejected = proj / "output" / "_rejected" / out.name
    if not out.exists() and rejected.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(rejected), str(out))
        print(f"[reaudit] MP4 restaurado de {rejected}", flush=True)
    artifacts = proj / "artifacts"
    audit = run_final_audit(
        proj_dir=proj,
        script_data=json.loads((artifacts / "script_v2.json").read_text(encoding="utf-8")),
        tts_timings=json.loads((artifacts / "tts_timings_v2.json").read_text(encoding="utf-8")),
        visual_clips=json.loads((artifacts / "pacing_plan_v2.json").read_text(encoding="utf-8")),
        images_dir=proj / "assets" / "images",
        out_16_9=out,
        out_short=None,
        thumbs_dir=proj / "output" / "thumbs",
        vision_check=False,
        min_veo_videos=int(TARGET_VEO_VIDEOS),
    )
    print(f"[reaudit] APPROVED={audit['approved']} | issues={audit['issues_count']}", flush=True)
    for e in audit["issues"][:20]:
        print("  [AUDIT]", e, flush=True)
    if not audit["approved"]:
        dest = proj / "output" / "_rejected"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out), str(dest / out.name))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
