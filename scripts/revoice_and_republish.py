# -*- coding: utf-8 -*-
"""Utilitario autonomo (sem IA) para refazer narracao, remontar 16:9 + 3 Shorts, remover antigos do YouTube e republicar."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.youtube_publisher import SCOPES, resolve_pt_credentials


def _delete_old_youtube_videos(proj_dir: Path) -> None:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    art = proj_dir / "artifacts"
    pub_main = art / "youtube_publish_pt.json"
    pub_shorts = art / "youtube_shorts_publish_pt.json"

    ids_to_delete: list[tuple[str, str]] = []
    if pub_main.is_file():
        d = json.loads(pub_main.read_text(encoding="utf-8"))
        if isinstance(d, dict) and d.get("video_id"):
            ids_to_delete.append(("16:9", str(d["video_id"])))
    if pub_shorts.is_file():
        arr = json.loads(pub_shorts.read_text(encoding="utf-8"))
        if isinstance(arr, list):
            for row in arr:
                if isinstance(row, dict) and row.get("video_id"):
                    ids_to_delete.append((str(row.get("file") or "short"), str(row["video_id"])))

    if not ids_to_delete:
        print("[YouTube] Nenhum video antigo registrado para remover.", flush=True)
        return

    _, tk_path = resolve_pt_credentials()
    creds = Credentials.from_authorized_user_file(str(tk_path), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        tk_path.write_text(creds.to_json(), encoding="utf-8")
    service = build("youtube", "v3", credentials=creds)

    for label, vid in ids_to_delete:
        try:
            service.videos().delete(id=vid).execute()
            print(f"[YouTube] Removido {label}: https://youtu.be/{vid}", flush=True)
        except HttpError as exc:
            if getattr(exc.resp, "status", None) == 404:
                print(f"[YouTube] Ja estava removido ({label}): {vid}", flush=True)
            else:
                print(f"[YouTube] Aviso ao remover {label} ({vid}): {exc}", flush=True)

    ts = int(time.time())
    for p in (pub_main, pub_shorts):
        if p.is_file():
            shutil.move(str(p), str(p.with_name(f"{p.stem}_OLD_deleted_{ts}.json")))


def _run(cmd: list[str]) -> None:
    print("\n>>>", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode != 0:
        raise SystemExit(r.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description="Refaz narracao (Zephyr/Sulafat/Leda), remonta 16:9 + 3 Shorts e republica no YouTube.")
    ap.add_argument("--slug", required=True, help="Nome da pasta dentro de projects/")
    ap.add_argument("--veo-videos", type=int, default=10, help="Quantidade minima de Veo no self_audit (use 0 se episodio legado sem Veo)")
    ap.add_argument("--skip-tts", action="store_true", help="Pula sintese TTS (use se a narracao nova ja foi gerada)")
    ap.add_argument("--skip-render", action="store_true", help="Pula remontagem 16:9 + 3 Shorts (use se ja renderizou)")
    ap.add_argument("--skip-delete-old", action="store_true", help="Nao remove os videos antigos do YouTube")
    ap.add_argument("--skip-publish", action="store_true", help="Nao publica no YouTube (apenas gera/remonta localmente)")
    ap.add_argument("--privacy", default="public", choices=("public", "unlisted", "private"))
    args = ap.parse_args()

    proj_dir = ROOT / "projects" / args.slug
    script_file = proj_dir / "artifacts" / "script_v2.json"
    if not script_file.is_file():
        raise SystemExit(f"Erro: roteiro nao encontrado em {script_file}")

    py = sys.executable
    pipe = str(ROOT / "pipeline_v2.py")

    if not args.skip_tts:
        _run([
            py, "-u", pipe,
            "--slug", args.slug,
            "--script-file", str(script_file),
            "--stage", "tts",
            "--tts-provider", "gemini_emotion",
            "--force",
        ])

    if not args.skip_render:
        cmd_render = [
            py, "-u", pipe,
            "--slug", args.slug,
            "--script-file", str(script_file),
            "--skip-images",
            "--veo-videos", str(args.veo_videos),
        ]
        if args.veo_videos <= 0:
            cmd_render.append("--skip-veo")
        _run(cmd_render)

    if not args.skip_delete_old:
        _delete_old_youtube_videos(proj_dir)

    if not args.skip_publish:
        _run([
            py, "-u", pipe,
            "--slug", args.slug,
            "--script-file", str(script_file),
            "--stage", "publish",
            "--publish-pt",
            "--publish-shorts-pt",
            "--publish-privacy", args.privacy,
        ])

    print(f"\n[OK] Episodio '{args.slug}' concluido!", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
