import asyncio
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.flow_accounts import ensure_account_cdp, load_accounts_config  # noqa: E402
from core.flow_continuity import configure_flow_mode  # noqa: E402

async def main():
    cfg = load_accounts_config()
    acc = next(a for a in cfg["accounts"] if a["id"] == "acc_2")
    cdp = ensure_account_cdp(acc)
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(cdp, timeout=15000)
        ctx = b.contexts[0]
        pg = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or await ctx.new_page()
        await pg.goto(acc.get("project_url") or "https://flow.google.com/", wait_until="domcontentloaded", timeout=40000)
        await pg.wait_for_timeout(2500)
        for count in ("x10", "x8", "x4", "x1"):
            try:
                summary = await configure_flow_mode(pg, kind="Imagem", aspect="16:9",
                                                    model_hint="Nano Banana 2.1", count=count)
                print(f"SUCESSO count={count}: {summary}")
                break
            except Exception as exc:
                print(f"FALHA count={count}: {str(exc)[:220]}")
        await b.close()

asyncio.run(main())
