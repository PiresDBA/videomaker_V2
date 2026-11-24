# -*- coding: utf-8 -*-
"""Zera xfade_duration dos clips de burst no pacing (evita colapso da timeline no xfade)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    slugs = sys.argv[1:] or ["primeiro-dia-de-praia-2", "primeiro-dia-de-praia-v6"]
    for slug in slugs:
        p = ROOT / "projects" / slug / "artifacts" / "pacing_plan_v2.json"
        if not p.exists():
            print(f"[fix] {slug}: sem pacing", flush=True)
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        fixed = 0
        for c in data:
            if (c.get("burst_from") or c.get("burst")) and float(c.get("xfade_duration") or 0) > 0:
                c["xfade_duration"] = 0.0
                fixed += 1
        if fixed:
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[fix] {slug}: {fixed} clips de burst com xfade zerado", flush=True)


if __name__ == "__main__":
    main()
