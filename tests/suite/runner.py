# -*- coding: utf-8 -*-
"""Runner do catalogo de testes: lista, verifica e executa scripts catalogados.

Uso:
  python tests/suite/runner.py --list
  python tests/suite/runner.py --check
  python tests/suite/runner.py --run unit_all
  python tests/suite/runner.py --category voz
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("manifest.json")


def _load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _entries(data: dict, category: str = "") -> list[dict]:
    items = data.get("entries", [])
    return [e for e in items if not category or e.get("category") == category]


def main() -> int:
    ap = argparse.ArgumentParser(description="Catalogo de testes do Videomaker v2")
    ap.add_argument("--list", action="store_true", help="Lista todos os testes catalogados")
    ap.add_argument("--check", action="store_true", help="Verifica quais arquivos catalogados existem")
    ap.add_argument("--run", default="", help="Executa um teste pelo id")
    ap.add_argument("--category", default="", help="Filtra por categoria (voz, audio, roteiro, imagem, video, nucleo)")
    args = ap.parse_args()

    data = _load()
    items = _entries(data, args.category)

    if args.run:
        hit = next((e for e in data["entries"] if e["id"] == args.run), None)
        if not hit:
            print(f"Teste desconhecido: {args.run}", file=sys.stderr)
            return 2
        path = ROOT / hit["path"]
        if not path.exists():
            print(f"Arquivo ausente: {path}", file=sys.stderr)
            return 2
        cmd = [sys.executable, str(path)] + sys.argv[sys.argv.index("--run") + 2:]
        print(f"[suite] {hit['id']} -> {' '.join(cmd)}", flush=True)
        return subprocess.call(cmd, cwd=str(ROOT))

    if args.check or args.list or args.category:
        missing = [e for e in items if not (ROOT / e["path"]).exists()]
        if args.list or args.category:
            for e in items:
                mark = "OK" if (ROOT / e["path"]).exists() else "FALTA"
                flags = ("[modifica]" if e.get("mutating") else "") + (" [credenciais]" if e.get("credentials") else "")
                print(f"  {e['id']:<22} {mark:<5} {e['category']:<8} {e['purpose'][:72]}{flags}")
        print(f"\nTotal: {len(items)} catalogados | {len(missing)} ausentes")
        return 1 if (args.check and missing) else 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
