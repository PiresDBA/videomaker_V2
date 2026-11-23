import asyncio
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.flow_accounts import ensure_account_cdp, load_accounts_config  # noqa: E402


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
        await pg.wait_for_timeout(10000)
        print("BODY:", (await pg.evaluate("() => document.body.innerText"))[:600])
        data = await pg.evaluate("""() => {
          const out = [];
          document.querySelectorAll('button, [role="button"], [contenteditable="true"], textarea').forEach((e, i) => {
            const r = e.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) return;
            out.push({
              i, tag: e.tagName,
              aria: e.getAttribute('aria-label') || '',
              title: e.getAttribute('title') || '',
              txt: (e.innerText || '').trim().slice(0, 60),
              html: e.outerHTML.slice(0, 220),
              x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)
            });
          });
          return out;
        }""")
        print("URL:", pg.url)
        print("VIEWPORT:", await pg.evaluate("() => [innerWidth, innerHeight]"))
        print("TOTAL:", len(data))
        keys = ("agent", "agente", "spark", "auto_awesome", "modo", "✨", "enviar", "prompt", "criar", "gerar")
        hits = [o for o in data if any(k in (o["aria"] + " " + o["txt"] + " " + o["html"]).lower() for k in keys)]
        print("HITS:", len(hits))
        print(json.dumps(hits[-30:], ensure_ascii=False, indent=1)[:14000])
        print("BOTTOM:", json.dumps([o for o in data if o["y"] > 780], ensure_ascii=False, indent=1)[:8000])
        await b.close()

asyncio.run(main())
