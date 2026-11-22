# -*- coding: utf-8 -*-
"""Lista TODAS as vozes pt-BR Chirp 3 HD disponiveis na conta (GET, nao consome chars)."""
import json, sys, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.voice_studio import _get_chirp3_auth_headers

h = _get_chirp3_auth_headers()
url = "https://texttospeech.googleapis.com/v1/voices?languageCode=pt-BR"
r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60)
d = json.loads(r.read().decode())
hd = [v for v in d.get("voices", []) if "Chirp3-HD" in v["name"]]
print(f"Total pt-BR Chirp3-HD: {len(hd)}")
for v in hd:
    gender = v.get("voiceGender") or v.get("gender") or "?"
    print(f"  {v['name']:38s} {gender}")
Path("work/teste_chirp3/voices_list.json").write_text(json.dumps(hd, indent=2, ensure_ascii=False), encoding="utf-8")
