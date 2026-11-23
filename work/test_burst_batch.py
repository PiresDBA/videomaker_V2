import asyncio
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.burst_montage import build_burst_prompt  # noqa: E402
from core.flow_accounts import ensure_account_cdp, load_accounts_config  # noqa: E402
from core.flow_continuity import generate_flow_image_batch  # noqa: E402

scene = {
    "scene_id": "sc_18",
    "visual_action": "A gaivota Guga mergulha do céu em direção ao biscoito na toalha, Frida observa arregalada",
    "location": "Praia ensolarada com toalha e areia",
    "characters": ["Frida", "Guga"],
}
ref = ROOT / "projects" / "primeiro-dia-de-praia-v5" / "assets" / "images" / "sc_18_p1.jpg"
out = ROOT / "assets" / "reference" / "primeiro-dia-de-praia" / "teste_burst_gaivota"

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
        await pg.wait_for_timeout(6000)
        prompt = build_burst_prompt(scene, n=10)
        print("PROMPT (primeiras linhas):", prompt[:400], flush=True)
        saved = await generate_flow_image_batch(
            pg, prompt, out, n=10,
            ref_images=(str(ref),) if ref.exists() else (),
            wait_s=600,
        )
        print(json.dumps({"salvas": len(saved), "arquivos": [Path(s["path"]).name for s in saved]}, ensure_ascii=False, indent=2))
        await b.close()

asyncio.run(main())
