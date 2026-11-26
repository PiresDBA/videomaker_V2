# -*- coding: utf-8 -*-
"""Consulta a YouTube Data API para ver o status REAL dos 4 videos publicados."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.youtube_publisher import resolve_pt_credentials, SCOPES
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ids = ["KttQvaipMAE", "JaMwzIm-OWw", "DABtFA65EBc", "fTWogr6IMqE"]
_, tk = resolve_pt_credentials()
creds = Credentials.from_authorized_user_file(str(tk), SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request()); tk.write_text(creds.to_json(), encoding="utf-8")
yt = build("youtube", "v3", credentials=creds)
r = yt.videos().list(part="id,snippet,status", id=",".join(ids)).execute()
print("encontrados pela API:", r.get("pageInfo", {}).get("totalResults"))
for it in r.get("items", []):
    s = it["snippet"]; st = it["status"]
    print(f"{it['id']:14s} privacidade={st.get('privacyStatus')} | embed={st.get('embeddable')} | titulo={s.get('title','')[:50]!r}")
found = {it["id"] for it in r.get("items", [])}
for i in ids:
    if i not in found:
        print(f"{i:14s} NAO ENCONTRADO (pode ter sido deletado ou nunca existiu)")
