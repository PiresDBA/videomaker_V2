# -*- coding: utf-8 -*-
"""Colhe TODOS os videos e imagens das 5 contas Flow para um diretorio de referencia unico.

Nao roda Vision QA (isso e o que custava ~1h). Apenas download + manifesto.
"""
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.flow_accounts import cdp_is_alive, ensure_account_cdp, load_accounts_config  # noqa: E402
from scripts.recover_flow_media import _harvest_account_tiles  # noqa: E402

OUT = ROOT / "assets" / "reference" / "primeiro-dia-de-praia" / "flow_all"
MANIFEST = OUT / "harvest_manifest.json"


def main() -> int:
    cfg = load_accounts_config()
    OUT.mkdir(parents=True, exist_ok=True)
    all_items: list[dict] = []
    status: dict[str, dict] = {}

    for acc in cfg.get("accounts", []):
        aid = str(acc.get("id") or "acc?")
        port = int(acc.get("cdp_port") or 0)
        if not cdp_is_alive(port):
            try:
                url = ensure_account_cdp(acc)
                print(f"[Harvest] {aid} CDP iniciado em {url}", flush=True)
            except Exception as exc:
                print(f"[Harvest] {aid} falhou ao iniciar CDP: {exc}", flush=True)
                status[aid] = {"ok": False, "error": str(exc)[:180]}
                continue
        acc_dir = OUT / aid
        print(f"[Harvest] {aid} coletando todos os projetos...", flush=True)
        try:
            items = asyncio.run(_harvest_account_tiles(acc, cfg, acc_dir, include_images=True))
            all_items.extend(items)
            status[aid] = {
                "ok": True,
                "videos": sum(1 for i in items if i["kind"] == "video"),
                "images": sum(1 for i in items if i["kind"] == "image"),
            }
            print(f"[Harvest] {aid}: {status[aid]['videos']} videos, {status[aid]['images']} imagens", flush=True)
        except Exception as exc:
            print(f"[Harvest] {aid} erro: {exc}", flush=True)
            status[aid] = {"ok": False, "error": str(exc)[:180]}

    payload = {
        "harvested_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(OUT),
        "accounts": status,
        "total_videos": sum(1 for i in all_items if i["kind"] == "video"),
        "total_images": sum(1 for i in all_items if i["kind"] == "image"),
        "items": all_items,
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Harvest] FINAL: {payload['total_videos']} videos + {payload['total_images']} imagens -> {OUT}", flush=True)
    print(f"[Harvest] Manifesto: {MANIFEST}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
