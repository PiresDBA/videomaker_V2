import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.voice_studio import _voice_studio_cli, validate_audio_with_whisper  # noqa: E402

BASE = "Eita! A areia me mordeu! Está entrando entre os meus dedinhos e fazendo {pal}, Frida!"
CANDIDATAS = ["cócegas", "có-ce-gas", "cocegas", "cosquinhas", "có ze gas", "có-ze-gas"]
EXPECTED = BASE.format(pal="cócegas")

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    for i, pal in enumerate(CANDIDATAS):
        out = td / f"c{i}.wav"
        text = BASE.format(pal=pal)
        r = subprocess.run(
            [_voice_studio_cli(), "speak", "--voice", "Luninha", "--language", "Portuguese (Brazil)",
             "-o", str(out), "--overwrite", text],
            capture_output=True, encoding="utf-8", errors="replace", timeout=300,
        )
        if r.returncode != 0 or not out.exists():
            print(pal, "FALHOU", (r.stderr or "")[:100])
            continue
        res = validate_audio_with_whisper(out, EXPECTED, min_similarity=0.0)
        print(f"{pal:<12} -> sim={res['similarity']:.3f} | ouviu='{res['heard_text']}'")
