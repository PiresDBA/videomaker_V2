# -*- coding: utf-8 -*-
"""Envia thumbnail viral para o episodio ja publicado (a capa automatica falhou)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.youtube_publisher import (  # noqa: E402
    generate_viral_pt_thumbnail,
    resolve_pt_credentials,
    SCOPES,
)


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "primeiro-dia-de-praia-v7"
    proj = ROOT / "projects" / slug
    art = proj / "artifacts" / "youtube_publish_pt.json"
    if not art.exists():
        print("[thumb] episodio ainda nao publicado")
        return 2
    receipt = json.loads(art.read_text(encoding="utf-8"))
    vid = receipt["video_id"]

    hero = ROOT / "projects" / "primeiro-dia-de-praia-v5" / "assets" / "images" / "sc_06_p1.jpg"
    if not hero.exists():
        print(f"[thumb] imagem de capa ausente: {hero}")
        return 2
    thumbs = proj / "output" / "thumbs"
    thumbs.mkdir(parents=True, exist_ok=True)
    thumb = thumbs / "thumb_viral_pt.jpg"
    generate_viral_pt_thumbnail(hero, thumb, main_hook="SALSICHA VS MAR",
                                badge_text="VOCÊ NÃO VAI ACREDITAR!")

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    cs, tk = resolve_pt_credentials()
    creds = Credentials.from_authorized_user_file(str(tk), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        tk.write_text(creds.to_json(), encoding="utf-8")
    service = build("youtube", "v3", credentials=creds)
    service.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
    receipt["thumbnail"] = str(thumb)
    receipt["thumbnail_uploaded"] = True
    art.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[thumb] enviada para https://youtu.be/{vid}: {thumb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
