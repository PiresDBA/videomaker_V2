# -*- coding: utf-8 -*-
"""Publica o episodio aprovado no YouTube PT-BR (todo publico).

So publica se a auditoria final estiver aprovada e o MP4 16:9 existir.
Nao publica Shorts (o episodio atual e somente 16:9).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.youtube_publisher import publish_episode_youtube_pt  # noqa: E402


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "primeiro-dia-de-praia-v7"
    proj = ROOT / "projects" / slug
    out = proj / "output" / f"{slug}_16x9.mp4"
    srt = proj / "output" / f"{slug}.srt"
    script = json.loads((proj / "artifacts" / "script_v2.json").read_text(encoding="utf-8"))
    audit = json.loads((proj / "artifacts" / "final_audit_report.json").read_text(encoding="utf-8"))

    if not audit.get("approved"):
        print(f"[publicar] AUDITORIA NAO APROVADA ({audit.get('issues_count')} problemas). Abortando.", flush=True)
        return 2
    if not out.is_file():
        print(f"[publicar] MP4 ausente: {out}", flush=True)
        return 2

    hero = next((proj / "assets" / "images").glob(f"{script['scenes'][0]['scene_id']}_p1.jpg"), None)
    print(f"[publicar] {out.name} | srt={srt.exists()} | thumb={hero.name if hero else 'auto'}", flush=True)
    rec = publish_episode_youtube_pt(
        proj_dir=proj,
        script_data=script,
        video_mp4=out,
        srt_path=srt if srt.exists() else None,
        hero_image=hero,
        privacy="public",
    )
    print(f"[publicar] PUBLICADO: {rec['url']}", flush=True)
    print(f"[publicar] titulo: {rec['title']}", flush=True)
    print(f"[publicar] MadeForKids={rec['selfDeclaredMadeForKids']} | thumbnail={rec['thumbnail_uploaded']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
