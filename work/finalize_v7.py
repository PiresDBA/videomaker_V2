# -*- coding: utf-8 -*-
"""Finaliza o episodio v7 apos o TTS: pacing -> imagens -> montagem -> auditoria.

Nao pula nenhuma porta: `work/assemble_only.py` chama o mesmo `run_final_audit`
do pipeline e move o MP4 para `output/_rejected/` se a auditoria reprovar.

Uso: python work/finalize_v7.py [slug]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "primeiro-dia-de-praia-v7"
    py = sys.executable
    steps = [
        ("PACING", [py, str(ROOT / "work" / "build_v7.py"), "--stage", "pacing", slug]),
        ("IMAGENS", [py, str(ROOT / "work" / "build_v7.py"), "--stage", "images", slug]),
        ("MONTAGEM + AUDITORIA", [py, str(ROOT / "work" / "assemble_only.py"), slug]),
        ("FOLHAS DE CONTATO", [py, str(ROOT / "work" / "audit_fino_sheets.py"), slug]),
    ]
    for name, cmd in steps:
        print(f"\n[v7] === {name} ===", flush=True)
        r = subprocess.run(cmd, cwd=str(ROOT))
        if r.returncode != 0:
            print(f"[v7] FALHOU em {name} (exit={r.returncode})", flush=True)
            return r.returncode
    print("\n[v7] CONCLUIDO (montagem aprovada pela porta de entrega).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
