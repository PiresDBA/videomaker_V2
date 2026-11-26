# -*- coding: utf-8 -*-
"""Publica 2 Shorts de cada video da praia (01_hook + 02_storybook), linkados ao principal."""
import json, sys, urllib.request, base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.youtube_publisher import resolve_pt_credentials, SCOPES
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

_, tk = resolve_pt_credentials()
creds = Credentials.from_authorized_user_file(str(tk), SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request()); tk.write_text(creds.to_json(), encoding="utf-8")
yt = build("youtube", "v3", credentials=creds)

PROJETOS = [
    ("primeiro-dia-de-praia-v7", "https://youtu.be/oR7Z4NMsFgM",
     "O Primeiro Dia de Praia da Frida e da Luna!\n\nEpisodio completo: https://youtu.be/oR7Z4NMsFgM\n\n#Shorts #cachorros #fridaeluna #praia #humorpets"),
    ("primeiro-dia-de-praia-parte2", "https://youtu.be/ZKiQg1ideAs",
     "A Praia Parte 2: o Biscoito Roubado!\n\nEpisodio completo: https://youtu.be/ZKiQg1ideAs\n\n#Shorts #cachorros #fridaeluna #praia #humorpets"),
]
TITULOS = {
    "01_hook": "Olha s\u00f3 o que rolou na praia! Frida e Luna #Shorts",
    "02_storybook": "A confus\u00e3o na areia: Frida e Luna #Shorts",
}
resultados = []
for slug, main_url, desc in PROJETOS:
    proj = Path("projects") / slug
    for name in ("01_hook", "02_storybook"):
        video = proj / "output" / f"{slug}_short_{name}.mp4"
        if not video.exists():
            print("FALTA:", video); continue
        body = {
            "snippet": {"title": TITULOS[name], "description": desc + "\n\n" + main_url,
                        "tags": ["Shorts", "cachorros", "fridaeluna", "praia", "humorpets"]},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        }
        r = yt.videos().insert(part="snippet,status", body=body,
                               media_body=MediaFileUpload(str(video), chunksize=-1, resumable=True)).execute()
        url = f"https://youtube.com/shorts/{r['id']}"
        print(f"PUBLICADO {slug} {name}: {url}")
        resultados.append({"proj": slug, "name": name, "url": url, "id": r["id"]})
Path("projects/primeiro-dia-de-praia-parte2/artifacts/youtube_shorts_praia.json").write_text(
    json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
print("TOTAL:", len(resultados))
