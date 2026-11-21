# -*- coding: utf-8 -*-
"""Gerenciador de multiplas contas do Google Flow com failover automatico (50 creditos/dia por conta) e clone de personagens."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from config import BASE_DIR, VENDOR_DIR
from core.flow_continuity import (
    DEFAULT_FLOW_PROJECT_URL,
    attach_reference_from_plus,
    clear_attached_chips,
    configure_flow_mode,
    ensure_direct_mode,
    generate_flow_image,
    generate_flow_video,
)

FLOW_ACCOUNTS_CONFIG = BASE_DIR / "flow_accounts.json"
FLOW_ACCOUNTS_EXAMPLE = BASE_DIR / "flow_accounts.example.json"
FLOW_ACCOUNTS_STATE = BASE_DIR / "flow_accounts_state.json"
FLOW_LEARNED_SESSIONS = BASE_DIR / "flow_learned_sessions.json"
CHARACTERS_REF_DIR = BASE_DIR / "assets" / "reference" / "characters"
DEFAULT_CHROME_EXE = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

QUOTA_ERROR_MARKERS = (
    "créditos insuficientes",
    "creditos insuficientes",
    "sem créditos",
    "sem creditos",
    "out of credits",
    "insufficient credits",
    "fazer upgrade",
    "upgrade to",
    "limite diário",
    "limite diario",
    "daily limit",
    "quota",
)


def _today_str() -> str:
    return dt.date.today().isoformat()


def default_accounts_config() -> dict[str, Any]:
    if FLOW_ACCOUNTS_EXAMPLE.exists():
        return json.loads(FLOW_ACCOUNTS_EXAMPLE.read_text(encoding="utf-8"))
    return {
        "max_credits_per_account_per_day": 50,
        "credits_per_veo_lite_8s": 10,
        "accounts": [
            {
                "id": f"acc_{i}",
                "label": f"Conta Google {i}",
                "cdp_port": 18799 + i,
                "profile_dir": (
                    str(BASE_DIR / ".chrome-flow-accounts" / f"acc_{i}")
                    if (BASE_DIR / ".chrome-flow-accounts" / f"acc_{i}").exists() or i != 1
                    else r"C:\videomaker\.chrome-gemini-profile"
                ),
                "project_url": DEFAULT_FLOW_PROJECT_URL if i == 1 else "",
                "enabled": True,
            }
            for i in range(1, 6)
        ],
    }


def load_accounts_config() -> dict[str, Any]:
    if FLOW_ACCOUNTS_CONFIG.exists():
        return json.loads(FLOW_ACCOUNTS_CONFIG.read_text(encoding="utf-8"))
    cfg = default_accounts_config()
    save_accounts_config(cfg)
    return cfg


def save_accounts_config(cfg: dict[str, Any]) -> None:
    FLOW_ACCOUNTS_CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def load_accounts_state() -> dict[str, Any]:
    today = _today_str()
    if FLOW_ACCOUNTS_STATE.exists():
        st = json.loads(FLOW_ACCOUNTS_STATE.read_text(encoding="utf-8"))
    else:
        st = {"date": today, "accounts": {}}
    if st.get("date") != today:
        # Novo dia: cota diaria do Flow reinicia (50 creditos/conta/dia)
        for acc_st in st.get("accounts", {}).values():
            acc_st["credits_used_today"] = 0
            acc_st["videos_used_today"] = 0
            acc_st["exhausted_today"] = False
        st["date"] = today
        save_accounts_state(st)
    return st


def save_accounts_state(st: dict[str, Any]) -> None:
    FLOW_ACCOUNTS_STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def cdp_is_alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2):
            return True
    except Exception:
        return False


def launch_account_chrome_blocking_daemon(account: dict[str, Any]) -> subprocess.Popen:
    """Abre instancia Chrome dedicada ao perfil/porta da conta sem matar janelas existentes."""
    prof = Path(account["profile_dir"])
    prof.mkdir(parents=True, exist_ok=True)
    port = int(account["cdp_port"])
    daemon_py = VENDOR_DIR / "chrome_cdp_daemon.py"
    return subprocess.Popen(
        [sys.executable, str(daemon_py), str(prof), str(port)],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )


def ensure_account_cdp(account: dict[str, Any], wait_s: int = 18) -> str:
    port = int(account["cdp_port"])
    if not cdp_is_alive(port):
        launch_account_chrome_blocking_daemon(account)
        t0 = time.time()
        while time.time() - t0 < wait_s:
            if cdp_is_alive(port):
                break
            time.sleep(1.0)
    if not cdp_is_alive(port):
        raise RuntimeError(f"Chrome CDP na porta {port} ({account['id']}) nao respondeu.")
    return f"http://127.0.0.1:{port}"


def mark_account_usage(account_id: str, credits_delta: int = 10, exhausted: bool = False, email: str = "") -> dict[str, Any]:
    st = load_accounts_state()
    rec = st.setdefault("accounts", {}).setdefault(
        account_id,
        {"credits_used_today": 0, "videos_used_today": 0, "exhausted_today": False, "email": ""},
    )
    rec["credits_used_today"] = int(rec.get("credits_used_today", 0)) + credits_delta
    if credits_delta > 0:
        rec["videos_used_today"] = int(rec.get("videos_used_today", 0)) + 1
    if exhausted:
        rec["exhausted_today"] = True
    if email:
        rec["email"] = email
    save_accounts_state(st)
    return rec


def get_next_available_accounts(ignore_soft_daily_cap: bool = False) -> list[dict[str, Any]]:
    cfg = load_accounts_config()
    st = load_accounts_state()
    max_cr = int(cfg.get("max_credits_per_account_per_day", 50))
    cost = int(cfg.get("credits_per_veo_lite_8s", 10))
    candidates: list[dict[str, Any]] = []
    for acc in cfg.get("accounts", []):
        if not acc.get("enabled", True):
            continue
        rec = st.get("accounts", {}).get(acc["id"], {})
        if rec.get("exhausted_today"):
            continue
        if (not ignore_soft_daily_cap) and (int(rec.get("credits_used_today", 0)) + cost > max_cr):
            continue
        candidates.append({**acc, "state": rec})
    return candidates


def is_quota_error_text(txt: str) -> bool:
    low = (txt or "").lower()
    return any(m in low for m in QUOTA_ERROR_MARKERS)


async def detect_logged_email(page) -> str:
    try:
        lbl = await page.evaluate("""() => {
            const el = document.querySelector('a[aria-label*="@"], button[aria-label*="@"], [aria-label*="@gmail.com"], [aria-label*="Conta do Google:"]');
            return el ? (el.getAttribute('aria-label') || '') : '';
        }""")
        if "@" in lbl:
            for part in lbl.replace("(", " ").replace(")", " ").split():
                if "@" in part:
                    return part.strip()
        return ""
    except Exception:
        return ""


async def check_needs_google_login(page) -> bool:
    url = (page.url or "").lower()
    if "accounts.google.com" in url and "servicelogin" in url:
        return True
    try:
        sign_btn = page.locator('a:has-text("Entrar"), button:has-text("Entrar"), a:has-text("Sign in"), button:has-text("Sign in")').first
        if await sign_btn.count() and await sign_btn.is_visible():
            email = await detect_logged_email(page)
            return not bool(email)
    except Exception:
        pass
    return False


def normalize_project_url(url: str) -> str:
    """Extrai URL raiz do projeto Flow removendo subrotas como /character."""
    m = re.search(r"(https://flow\.google\.com(?:/u/\d+)?/project/[0-9a-fA-F-]+)", url or "")
    return m.group(1) if m else ""


async def _accept_usage_rights_modal(page) -> bool:
    """Aceita automaticamente o aviso 'Direitos de uso desta imagem' (Concordo) no 1o upload."""
    try:
        pane = page.locator('.cdk-overlay-pane:has-text("Direitos de uso"), .cdk-overlay-pane:has-text("usage rights")').last
        if await pane.count() and await pane.is_visible():
            agree = pane.locator('button:has-text("Concordo"), button:has-text("I agree"), button:has-text("Agree"), button:has-text("Accept")').last
            if await agree.count() and await agree.is_visible():
                await agree.click(timeout=4000)
                await page.wait_for_timeout(1200)
                return True
    except Exception:
        pass
    return False


async def _ensure_project_canvas_url(page) -> None:
    """Retorna da tela /character para a raiz do projeto quando necessario."""
    await _accept_usage_rights_modal(page)
    if "/character" not in (page.url or ""):
        return
    back = page.locator('button[aria-label="Voltar"]').first
    try:
        if await back.count() and await back.is_visible():
            await back.click(timeout=3000)
            await page.wait_for_timeout(1500)
    except Exception:
        pass
    if "/character" in (page.url or ""):
        base = normalize_project_url(page.url)
        if base:
            await page.goto(base, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(2000)


async def ensure_flow_project(page, account: dict[str, Any], cfg: dict[str, Any]) -> str:
    """Abre o projeto Flow da conta (ou cria um novo projeto limpo automaticamente)."""
    proj_url = normalize_project_url(account.get("project_url") or "") or (account.get("project_url") or "").strip()
    if proj_url:
        if normalize_project_url(page.url) != normalize_project_url(proj_url) or "/character" in (page.url or ""):
            await page.goto(proj_url, wait_until="domcontentloaded", timeout=35000)
            await page.wait_for_timeout(3000)
        return proj_url

    await page.goto("https://flow.google.com/", wait_until="domcontentloaded", timeout=35000)
    await page.wait_for_timeout(3000)
    if await check_needs_google_login(page):
        raise RuntimeError(f"Conta {account['id']} precisa fazer login no Google Flow (porta {account['cdp_port']}).")

    # Tenta abrir o projeto mais recente existente ou criar 'Novo projeto'
    links = await page.evaluate(
        "() => Array.from(document.querySelectorAll('a[href*=\"/project/\"]')).map(a => a.getAttribute('href'))"
    )
    if links:
        target = links[0] if links[0].startswith("http") else f"https://flow.google.com{links[0]}"
        await page.goto(target, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2500)
    else:
        new_btn = page.locator('button:has-text("Novo projeto"), a:has-text("Novo projeto"), button:has-text("New project")').first
        if await new_btn.count():
            await new_btn.click(timeout=8000)
            await page.wait_for_timeout(3500)
    final_url = normalize_project_url(page.url) or page.url
    if "/project/" in final_url:
        for row in cfg.get("accounts", []):
            if row["id"] == account["id"]:
                row["project_url"] = final_url
                account["project_url"] = final_url
                save_accounts_config(cfg)
                break
    return final_url


async def upload_media_to_flow(page, media_path: Path) -> bool:
    """Envia imagem/referencia local para a biblioteca do projeto Flow sem travar em timeouts longos."""
    if not media_path.exists():
        return False
    try:
        await _ensure_project_canvas_url(page)
        await ensure_direct_mode(page)

        file_inp = page.locator('input[type="file"]').first
        up_btn_sel = (
            '.cdk-overlay-pane :is(button,[role="menuitem"]):has-text("upload"), '
            '.cdk-overlay-pane :is(button,[role="menuitem"]):has-text("Enviar"), '
            '.cdk-overlay-pane :is(button,[role="menuitem"]):has-text("Fazer upload"), '
            ':is(button,[role="menuitem"]):has-text("Fazer upload")'
        )
        up_btn = page.locator(up_btn_sel).first

        if not await file_inp.count():
            menu_add = page.locator('button[aria-label="Menu para adicionar arquivos"]').first
            if await menu_add.count() and await menu_add.is_visible():
                await menu_add.click(timeout=4000)
                await page.wait_for_timeout(700)

        if not await file_inp.count() and not await up_btn.count():
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(250)
            add_btn = page.locator('button[aria-label="Adicionar elementos à caixa de comando"]').first
            if await add_btn.count() and await add_btn.is_visible():
                await add_btn.click(timeout=5000)
                await page.wait_for_timeout(800)
                env_tab = page.locator('.cdk-overlay-pane :is(button,[role="tab"]):has-text("Envios")').first
                if await env_tab.count():
                    await env_tab.click(timeout=4000)
                    await page.wait_for_timeout(600)

        if await file_inp.count():
            await file_inp.set_input_files(str(media_path))
        elif await up_btn.count():
            async with page.expect_file_chooser(timeout=5000) as fc:
                await up_btn.click(timeout=5000)
            chooser = await fc.value
            await chooser.set_files(str(media_path))
        else:
            await page.keyboard.press("Escape")
            return False

        await page.wait_for_timeout(1200)
        await _accept_usage_rights_modal(page)
        await page.wait_for_timeout(1200)
        for _ in range(20):
            try:
                body_txt = await page.locator("body").inner_text()
            except Exception:
                body_txt = ""
            if not re.search(r"(?:image|enviando|uploading|\b)\s*\d{1,2}%", body_txt, re.IGNORECASE):
                break
            await page.wait_for_timeout(1000)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)
        return True
    except Exception as exc:
        print(f"  [FlowUpload] Aviso ao enviar '{media_path.name}': {exc}", flush=True)
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        return False


async def check_characters_present(page, required: tuple[str, ...] = ("Frida", "Luna")) -> dict[str, bool]:
    """Verifica na aba Personagens (+) quais personagens ja existem na conta/projeto atual."""
    try:
        await _ensure_project_canvas_url(page)
        await ensure_direct_mode(page)
        add_btn = page.locator('button[aria-label="Adicionar elementos à caixa de comando"]').first
        if not await add_btn.count() or not await add_btn.is_visible():
            return {name: False for name in required}
        await add_btn.click(timeout=6000)
        await page.wait_for_timeout(800)
        tab = page.locator('.cdk-overlay-pane button:has-text("Personagens"), .cdk-overlay-pane [role="tab"]:has-text("Personagens")').first
        if await tab.count():
            await tab.click(timeout=5000)
            await page.wait_for_timeout(600)
        opts = await page.evaluate(
            "() => Array.from(document.querySelectorAll('.cdk-overlay-pane [role=\"option\"]')).map(e => (e.innerText || '').trim().split('\\n')[0].trim())"
        )
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
        found_set = {x.lower() for x in opts if x}
        return {name: (name.lower() in found_set) for name in required}
    except Exception as exc:
        print(f"  [FlowChars] Aviso ao checar personagens: {exc}", flush=True)
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        return {name: False for name in required}


async def inspect_all_accounts_status() -> list[dict[str, Any]]:
    """Lista status real (CDP, login Google, e-mail, creditos usados hoje, Frida/Luna) das contas."""
    from playwright.async_api import async_playwright

    cfg = load_accounts_config()
    st = load_accounts_state()
    rows = []
    for acc in cfg.get("accounts", []):
        port = int(acc["cdp_port"])
        rec = st.get("accounts", {}).get(acc["id"], {})
        info: dict[str, Any] = {
            "id": acc["id"],
            "label": acc.get("label", ""),
            "port": port,
            "cdp_alive": cdp_is_alive(port),
            "logged_in": False,
            "email": rec.get("email", ""),
            "credits_used_today": int(rec.get("credits_used_today", 0)),
            "credits_remaining_est": max(0, int(cfg.get("max_credits_per_account_per_day", 50)) - int(rec.get("credits_used_today", 0))),
            "exhausted_today": bool(rec.get("exhausted_today", False)),
            "project_url": acc.get("project_url", ""),
            "characters": {},
        }
        if info["cdp_alive"]:
            try:
                async with async_playwright() as pw:
                    b = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=8000)
                    ctx = b.contexts[0]
                    pg = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or await ctx.new_page()
                    if "flow.google.com" not in (pg.url or ""):
                        await pg.goto("https://flow.google.com/", wait_until="domcontentloaded", timeout=25000)
                        await pg.wait_for_timeout(2000)
                    need_login = await check_needs_google_login(pg)
                    info["logged_in"] = not need_login
                    email = await detect_logged_email(pg)
                    if email:
                        info["email"] = email
                        mark_account_usage(acc["id"], credits_delta=0, email=email)
                    norm_proj = normalize_project_url(info["project_url"]) or info["project_url"]
                    if info["logged_in"] and norm_proj:
                        if normalize_project_url(pg.url) != norm_proj or "/character" in (pg.url or ""):
                            await pg.goto(norm_proj, wait_until="domcontentloaded", timeout=25000)
                            await pg.wait_for_timeout(2000)
                        info["characters"] = await check_characters_present(pg)
                    await b.close()
            except Exception as exc:
                info["error"] = str(exc)[:140]
        rows.append(info)
    return rows


async def generate_video_with_failover(
    prompt: str,
    out_mp4: Path,
    characters: tuple[str, ...] = ("Frida", "Luna"),
    keyframe_path: Path | None = None,
    keyframe_aria_on_acc1: str = "",
    preferred_account_id: str = "",
    script_data: dict[str, Any] | None = None,
    proj_dir: Path | None = None,
) -> dict[str, Any]:
    """Gera video Veo 3.1 Lite (8s, 10 creditos) fazendo failover automatico entre as contas cadastradas."""
    from playwright.async_api import async_playwright

    cfg = load_accounts_config()
    candidates = get_next_available_accounts(ignore_soft_daily_cap=True)
    if preferred_account_id:
        candidates.sort(key=lambda a: 0 if a["id"] == preferred_account_id else 1)

    if not candidates:
        raise RuntimeError("Nenhuma conta Google Flow configurada com creditos disponiveis hoje.")

    sec_portrait_dir = (proj_dir / "assets" / "characters") if proj_dir else (CHARACTERS_REF_DIR / "episode_portraits")
    last_err: Exception | None = None
    for acc in candidates:
        port = int(acc["cdp_port"])
        if not cdp_is_alive(port):
            print(f"[FlowFailover] CDP :{port} ({acc['id']}) offline; pulando para proxima conta.", flush=True)
            continue

        async with async_playwright() as pw:
            b = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=10000)
            try:
                ctx = b.contexts[0]
                page = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or await ctx.new_page()
                await page.set_viewport_size({"width": 1600, "height": 920})
                await ensure_flow_project(page, acc, cfg)

                if await check_needs_google_login(page):
                    print(f"[FlowFailover] {acc['id']} deslogada; tentando proxima conta.", flush=True)
                    continue

                email = await detect_logged_email(page)
                # Verifica e garante Frida, Luna e personagens secundarios nesta conta antes do Veo
                present = await check_characters_present(page, required=characters)
                missing_chars = [c for c, ok in present.items() if not ok]
                if missing_chars:
                    try:
                        await ensure_story_characters_created(
                            page,
                            script_data or {},
                            acc.get("project_url") or page.url,
                            portrait_dir=sec_portrait_dir,
                        )
                        present = await check_characters_present(page, required=characters)
                        missing_chars = [c for c, ok in present.items() if not ok]
                    except Exception as char_exc:
                        print(f"[FlowFailover] Aviso ao criar personagens em {acc['id']}: {char_exc}", flush=True)

                # Anexa keyframe e eventuais retratos de fallback para personagens ausentes
                ref_imgs: list[str] = []
                if acc["id"] == "acc_1" and keyframe_aria_on_acc1:
                    ref_imgs.append(keyframe_aria_on_acc1)
                elif keyframe_path and keyframe_path.exists():
                    if await upload_media_to_flow(page, keyframe_path):
                        ref_imgs.append(keyframe_path.name)

                if any(mc.lower() in ("frida", "luna") for mc in missing_chars):
                    sheet = BASE_DIR / "assets" / "reference" / "frida_luna_reference.jpg"
                    if sheet.exists() and await upload_media_to_flow(page, sheet):
                        ref_imgs.append(sheet.name)
                for mc in missing_chars:
                    if mc.lower() in ("frida", "luna"):
                        continue
                    safe_slug = re.sub(r"[^a-z0-9]+", "_", mc.lower()).strip("_") or "personagem"
                    sec_port = sec_portrait_dir / f"{safe_slug}_portrait.jpg"
                    if sec_port.exists() and await upload_media_to_flow(page, sec_port):
                        ref_imgs.append(sec_port.name)
                if missing_chars:
                    print(
                        f"[FlowFailover] {acc['id']} sem personagens na aba ({missing_chars}); "
                        f"retratos/folha + keyframe enviados para manter continuidade.",
                        flush=True,
                    )

                try:
                    # Confere se UI ja mostra sem creditos antes de enviar
                    res = await generate_flow_video(
                        page,
                        prompt=prompt,
                        out_mp4=out_mp4,
                        characters=tuple(c for c in characters if present.get(c, False)),
                        ref_images=tuple(ref_imgs[:3]),
                        video_submode="Elementos",
                        wait_s=360,
                    )
                    usage = mark_account_usage(acc["id"], credits_delta=10, email=email)
                    res["account_id"] = acc["id"]
                    res["account_email"] = email
                    res["credits_used_today"] = usage["credits_used_today"]
                    return res
                except Exception as exc:
                    err_txt = str(exc)
                    # Confere texto visivel na pagina por aviso de creditos esgotados
                    body_low = (await page.evaluate("() => (document.body && document.body.innerText || '').slice(0, 1800)")).lower()
                    if is_quota_error_text(err_txt) or is_quota_error_text(body_low):
                        print(f"[FlowFailover] Cota esgotada em {acc['id']} ({email}); alternando para proxima conta...", flush=True)
                        mark_account_usage(acc["id"], credits_delta=0, exhausted=True, email=email)
                        last_err = exc
                        continue
                    raise
            finally:
                await b.close()

    raise RuntimeError(f"Todas as contas Flow disponíveis falharam ou esgotaram 50 créditos hoje: {last_err}")


_LEARN_CLICK_HOOK_JS = """() => {
  if (window.__vmLearnInstalled) return;
  window.__vmLearnInstalled = true;
  window.__vmLearnedClicks = window.__vmLearnedClicks || [];
  document.addEventListener('click', (ev) => {
    const el = ev.target && ev.target.closest ? ev.target.closest('button,a,[role="button"],[role="option"],[role="menuitem"]') : ev.target;
    if (!el) return;
    window.__vmLearnedClicks.push({
      ts: Date.now(),
      url: location.href,
      tag: el.tagName || '',
      role: el.getAttribute ? (el.getAttribute('role') || '') : '',
      aria: el.getAttribute ? (el.getAttribute('aria-label') || '') : '',
      text: (el.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 80)
    });
  }, true);
}"""


def _load_learned_sessions() -> dict[str, Any]:
    if FLOW_LEARNED_SESSIONS.exists():
        return json.loads(FLOW_LEARNED_SESSIONS.read_text(encoding="utf-8"))
    return {"sessions": {}}


def _save_learned_sessions(data: dict[str, Any]) -> None:
    FLOW_LEARNED_SESSIONS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


async def attach_click_recorder(page) -> None:
    try:
        await page.add_init_script(_LEARN_CLICK_HOOK_JS)
        await page.evaluate(_LEARN_CLICK_HOOK_JS)
    except Exception:
        pass


async def create_character_in_flow(
    page,
    name: str,
    portrait_path: Path,
    personality: str,
    project_url: str,
) -> bool:
    """Cria nativamente o personagem (Frida/Luna) na rota /character da conta Flow."""
    if not portrait_path.exists():
        return False
    base_proj = normalize_project_url(project_url or page.url)
    if not base_proj:
        return False

    char_url = f"{base_proj}/character"
    try:
        await page.goto(char_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        np_btn = page.locator(':is(button,[role="button"],a):has-text("Novo personagem")').last
        if await np_btn.count() and await np_btn.is_visible():
            await np_btn.click(timeout=4000)
            await page.wait_for_timeout(1200)
        elif not await page.locator('button:has-text("Enviar"), input[aria-label="Nome do personagem"]').count():
            nav_char = page.locator('button:has-text("accessibility_new"), a:has-text("Personagens")').first
            if await nav_char.count() and await nav_char.is_visible():
                await nav_char.click(timeout=4000)
                await page.wait_for_timeout(1000)
            if await np_btn.count() and await np_btn.is_visible():
                await np_btn.click(timeout=4000)
                await page.wait_for_timeout(1200)

        up = page.locator('button:has-text("Enviar")').first
        if await up.count():
            try:
                async with page.expect_file_chooser(timeout=6000) as fc:
                    await up.click(timeout=5000)
                ch = await fc.value
                await ch.set_files(str(portrait_path))
            except Exception:
                fi = page.locator('input[type="file"]').first
                if await fi.count():
                    await fi.set_input_files(str(portrait_path))
            await page.wait_for_timeout(1200)
            await _accept_usage_rights_modal(page)
            await page.wait_for_timeout(1200)
            for _ in range(25):
                try:
                    body_txt = await page.locator("body").inner_text()
                except Exception:
                    body_txt = ""
                if not re.search(r"(?:image|enviando|uploading|\b)\s*\d{1,2}%", body_txt, re.IGNORECASE):
                    break
                await page.wait_for_timeout(1000)

        await _accept_usage_rights_modal(page)
        name_inp = page.locator('input[aria-label="Nome do personagem"], input[placeholder*="Nome do personagem"]').first
        if await name_inp.count():
            await name_inp.click(timeout=4000)
            await name_inp.fill(name)
            await page.wait_for_timeout(300)

        pers_inp = page.locator('textarea[aria-label="Personalidade do personagem"], textarea[placeholder*="Descreva"]').first
        if await pers_inp.count():
            await pers_inp.fill(personality)
            await page.wait_for_timeout(300)

        done_btn = page.locator('button:has-text("Concluir")').first
        if await done_btn.count():
            for _ in range(12):
                try:
                    if not await done_btn.is_disabled():
                        break
                except Exception:
                    break
                await page.wait_for_timeout(1000)
            await done_btn.click(timeout=6000)
            await page.wait_for_timeout(3000)
            print(f"  [FlowChars] Personagem '{name}' criado na conta!", flush=True)
            return True
        return False
    except Exception as exc:
        print(f"  [FlowChars] Aviso ao criar '{name}': {exc}", flush=True)
        return False
    finally:
        try:
            if normalize_project_url(page.url) != base_proj or "/character" in (page.url or ""):
                await page.goto(base_proj, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)
        except Exception:
            pass


async def ensure_all_characters_created(page, project_url: str) -> dict[str, bool]:
    """Garante Frida e Luna criados na aba Personagens desta conta Flow."""
    present = await check_characters_present(page, required=("Frida", "Luna"))
    specs = {
        "Frida": (
            CHARACTERS_REF_DIR / "frida_portrait.jpg",
            "Cachorrinha buldogue fêmea jovem (idade de criança/pré-adolescente, máximo 1 ano de vida, equivalente a uma criança de 6 a 10 anos em desenho animado 3D Disney Pixar, idêntica ao avatar oficial; nunca cachorra velha/adulta pesada e nunca cachorro real fotorrealista), traços graciosos e infantis, olhos grandes brilhantes expressivos com cílios longos, pelagem caramelo-dourada macia estilizada, coleira de pérolas brancas com pingente dourado de patinha e pequeno brinco de pérola.",
        ),
        "Luna": (
            CHARACTERS_REF_DIR / "luna_portrait.jpg",
            "Cachorrinha salsicha dachshund fêmea jovem (idade de criança/pré-adolescente, máximo 1 ano de vida, equivalente a uma criança de 6 a 10 anos em desenho animado 3D Disney Pixar, idêntica ao avatar oficial; nunca cachorra velha/adulta e nunca cachorro real fotorrealista), traços graciosos, delicados e infantis, olhos grandes brilhantes expressivos com cílios longos, pelagem marrom-chocolate estilizada com marcas caramelo, duas correntes douradas finas com pingentes de coração.",
        ),
    }
    for cname, (p_path, desc) in specs.items():
        if not present.get(cname):
            ok = await create_character_in_flow(page, cname, p_path, desc, project_url)
            present[cname] = ok
    return present


async def ensure_story_characters_created(
    page,
    script_data: dict[str, Any],
    project_url: str,
    portrait_dir: Path | None = None,
) -> dict[str, bool]:
    """Cria Frida, Luna e todo personagem secundario recorrente do roteiro na aba Personagens (retrato isolado por episodio)."""
    present = await ensure_all_characters_created(page, project_url)
    sec_portrait_dir = Path(portrait_dir) if portrait_dir else (CHARACTERS_REF_DIR / "episode_portraits")
    sec_portrait_dir.mkdir(parents=True, exist_ok=True)
    for sec in script_data.get("secondary_characters") or []:
        cname = str(sec.get("name") or "").strip()
        cdesc = str(sec.get("description") or "").strip()
        if not cname:
            continue
        cur = await check_characters_present(page, required=(cname,))
        if cur.get(cname):
            present[cname] = True
            continue
        safe_slug = re.sub(r"[^a-z0-9]+", "_", cname.lower()).strip("_") or "personagem"
        portrait = sec_portrait_dir / f"{safe_slug}_portrait.jpg"
        if not portrait.exists() and cdesc:
            try:
                await generate_flow_image(
                    page,
                    prompt=(
                        f"Single stylized 3D Disney Pixar animated character portrait centered on soft neutral studio background, "
                        f"friendly appealing child-like cartoon expression, clear silhouette, NOT realistic: {cdesc}"
                    ),
                    out_jpg=portrait,
                    characters=(),
                    wait_s=130,
                )
            except Exception as exc:
                print(f"  [FlowChars] Aviso ao gerar retrato 0-cred para '{cname}': {exc}", flush=True)
        ok = False
        if portrait.exists():
            ok = await create_character_in_flow(page, cname, portrait, cdesc or cname, project_url)
        present[cname] = ok

    # Regra de Objeto-como-Personagem: todo story_prop recorrente deste episodio vira personagem no Flow
    for pr in script_data.get("story_props") or []:
        pname = str(pr.get("name") or "").strip()
        pdesc = str(pr.get("description") or "").strip()
        if not pname:
            continue
        cur = await check_characters_present(page, required=(pname,))
        if cur.get(pname):
            present[pname] = True
            continue
        safe_slug = re.sub(r"[^a-z0-9]+", "_", pname.lower()).strip("_") or "objeto"
        portrait = sec_portrait_dir / f"{safe_slug}_portrait.jpg"
        if not portrait.exists() and pdesc:
            try:
                await generate_flow_image(
                    page,
                    prompt=(
                        f"Single 3D animated cartoon prop object centered on a clean soft neutral studio background, "
                        f"crisp studio lighting, full object clearly visible and isolated: {pdesc}"
                    ),
                    out_jpg=portrait,
                    characters=(),
                    wait_s=130,
                )
            except Exception as exc:
                print(f"  [FlowChars] Aviso ao gerar retrato de objeto '{pname}': {exc}", flush=True)
        ok = False
        if portrait.exists():
            ok = await create_character_in_flow(page, pname, portrait, pdesc or pname, project_url)
        present[pname] = ok
    return present


async def capture_learned_session(account_id: str, auto_seed_refs: bool = True) -> dict[str, Any]:
    """Lê a sessão atual aberta na conta (e-mail, projeto Flow, personagens, cliques aprendidos) e guarda para uso contínuo."""
    from playwright.async_api import async_playwright

    cfg = load_accounts_config()
    acc = next((a for a in cfg.get("accounts", []) if a["id"] == account_id), None)
    if acc is None:
        raise ValueError(f"Conta desconhecida: {account_id}")
    port = int(acc["cdp_port"])
    if not cdp_is_alive(port):
        raise RuntimeError(f"CDP da conta {account_id} (porta {port}) nao esta ativo.")

    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=10000)
        ctx = b.contexts[0]
        page = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or ctx.pages[-1]
        if "flow.google.com" not in (page.url or ""):
            await page.goto("https://flow.google.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

        need_login = await check_needs_google_login(page)
        email = await detect_logged_email(page)
        try:
            clicks = await page.evaluate("() => window.__vmLearnedClicks || []")
        except Exception:
            clicks = []

        proj_url = normalize_project_url(page.url) or normalize_project_url(acc.get("project_url") or "")
        if (not need_login) and not proj_url:
            proj_url = await ensure_flow_project(page, acc, cfg)
            proj_url = normalize_project_url(proj_url) or proj_url

        present_chars: dict[str, bool] = {}
        seeded_files: list[str] = []
        if not need_login and proj_url:
            if normalize_project_url(page.url) != proj_url or "/character" in (page.url or ""):
                await page.goto(proj_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)
            if auto_seed_refs:
                try:
                    present_chars = await ensure_all_characters_created(page, proj_url)
                except Exception as exc:
                    print(f"  [Learn] Aviso personagens em {account_id}: {exc}", flush=True)
                try:
                    sheet = BASE_DIR / "assets" / "reference" / "frida_luna_reference.jpg"
                    if sheet.exists() and await upload_media_to_flow(page, sheet):
                        seeded_files.append(sheet.name)
                except Exception as exc:
                    print(f"  [Learn] Aviso upload folha em {account_id}: {exc}", flush=True)
            else:
                present_chars = await check_characters_present(page)

        await b.close()

    # Persiste sessao aprendida
    if email or proj_url:
        for row in cfg.get("accounts", []):
            if row["id"] == account_id:
                if proj_url:
                    row["project_url"] = proj_url
                if email:
                    row["label"] = f"{account_id} ({email})"
                row["enabled"] = True
                save_accounts_config(cfg)
                break
        mark_account_usage(account_id, credits_delta=0, exhausted=False, email=email)

    learned = _load_learned_sessions()
    entry = {
        "account_id": account_id,
        "email": email,
        "logged_in": not need_login,
        "project_url": proj_url,
        "characters": present_chars,
        "seeded_refs": seeded_files,
        "clicks": clicks[-60:],
        "saved_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    learned.setdefault("sessions", {})[account_id] = entry
    _save_learned_sessions(learned)
    return entry


async def interactive_learn_accounts_wizard(account_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Modo de aprendizado guiado conta a conta: você navega/loga em uma sessão, nós aprendemos e salvamos, depois pedimos a próxima."""
    from playwright.async_api import async_playwright

    cfg = load_accounts_config()
    targets = [
        a for a in cfg.get("accounts", [])
        if (account_ids is None and a["id"] != "acc_1") or (account_ids and a["id"] in account_ids)
    ]
    results: list[dict[str, Any]] = []
    for idx, acc in enumerate(targets, 1):
        print(f"\n================ SESSÃO {idx}/{len(targets)}: {acc['id']} (porta {acc['cdp_port']}) ================")
        cdp = ensure_account_cdp(acc)
        async with async_playwright() as pw:
            b = await pw.chromium.connect_over_cdp(cdp, timeout=10000)
            ctx = b.contexts[0]
            page = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or await ctx.new_page()
            await attach_click_recorder(page)
            if "flow.google.com" not in (page.url or ""):
                await page.goto("https://flow.google.com/", wait_until="domcontentloaded", timeout=30000)
            await b.close()

        print(f"1) Janela Chrome aberta para '{acc['id']}' em {cdp}.")
        print("2) Faca login na sua conta Google Flow, navegue ate um projeto (ou crie um Novo Projeto) e, se desejar, abra os personagens.")
        ans = input("3) Quando terminar esta secao, pressione [ENTER] para aprender e guardar (ou digite 'pular'/'sair'): ").strip().lower()
        if ans == "sair":
            break
        if ans == "pular":
            continue
        try:
            rec = await capture_learned_session(acc["id"], auto_seed_refs=True)
            print(
                f"[APRENDIDO] {acc['id']} | login={'OK' if rec['logged_in'] else 'PENDENTE'} | "
                f"email={rec['email'] or '-'} | projeto={rec['project_url'] or '-'} | cliques={len(rec['clicks'])}"
            )
            results.append(rec)
        except Exception as exc:
            print(f"[ERRO AO APRENDER {acc['id']}] {exc} (continuando para a proxima conta)", flush=True)
    return results
