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
from core.logging_manager import log_flow_event
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
# Registro de projetos Flow nomeados por conta: {account_id: {project_name: url}} (Regra 24)
FLOW_PROJECTS_REGISTRY = BASE_DIR / "flow_projects.json"
FLOW_RUNTIME_DIR = BASE_DIR / ".chrome-flow-accounts" / "runtime"
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


def load_flow_projects() -> dict[str, dict[str, str]]:
    """Carrega o registro de projetos nomeados por conta (Regra 24)."""
    if FLOW_PROJECTS_REGISTRY.exists():
        try:
            return json.loads(FLOW_PROJECTS_REGISTRY.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_flow_projects(reg: dict[str, dict[str, str]]) -> None:
    FLOW_PROJECTS_REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")


def get_named_project_url(account_id: str, project_name: str) -> str:
    """Retorna a URL do projeto nomeado para a conta, se ja criado."""
    if not project_name:
        return ""
    return (load_flow_projects().get(account_id) or {}).get(project_name, "")


def register_named_project(account_id: str, project_name: str, url: str) -> None:
    """Registra a URL de um projeto nomeado para reutilizacao futura."""
    if not project_name or not url:
        return
    reg = load_flow_projects()
    reg.setdefault(account_id, {})[project_name] = url
    save_flow_projects(reg)


def episode_project_name(slug: str, script_data: dict[str, Any] | None = None) -> str:
    """Nome legivel do projeto Flow para o episodio/tema (Regra 24).

    Prioriza `flow_project_name` no roteiro; senao deriva do titulo/slug.
    Ex.: 'primeiro-dia-de-praia-2' -> 'Frida na praia'.
    """
    if script_data and script_data.get("flow_project_name"):
        return str(script_data["flow_project_name"]).strip()
    title = str((script_data or {}).get("title") or "").strip()
    if title:
        # Titulos modelo "O MISTERIO DA AREIA...: FRIDA E LUNA NA PRAIA" -> usa o trecho depois de ':'
        tail = title.split(":")[-1].strip()
        if 3 <= len(tail) <= 60 and ("frida" in tail.lower() or "luna" in tail.lower()):
            return tail.title() if tail.isupper() else tail
    if not slug:
        return ""
    s = re.sub(r"[-_]+", " ", slug).strip()
    s = re.sub(r"\bv\d+\b", "", s, flags=re.I)
    s = re.sub(r"\bprimeiro dia de praia\b", "Frida na praia", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    return s.title()


def load_accounts_state() -> dict[str, Any]:
    today = _today_str()
    now_ts = time.time()
    if FLOW_ACCOUNTS_STATE.exists():
        st = json.loads(FLOW_ACCOUNTS_STATE.read_text(encoding="utf-8"))
    else:
        st = {"date": today, "accounts": {}}
    dirty = False
    if st.get("date") != today:
        # Novo dia / ciclo de 24h: as 4 primeiras contas (acc_1..acc_4) renovam 50 creditos cada (200 creditos = 20 videos/dia)
        for acc_id, acc_st in st.get("accounts", {}).items():
            if acc_id != "acc_5":
                acc_st["credits_used_today"] = 0
                acc_st["videos_used_today"] = 0
                acc_st["exhausted_today"] = False
                acc_st.pop("exhausted_at", None)
        st["date"] = today
        dirty = True
    else:
        # Tambem destrava automaticamente qualquer conta primaria (acc_1..acc_4) cujo exhausted_at ja completou 24h (86400s)
        for acc_id, acc_st in st.get("accounts", {}).items():
            if acc_id != "acc_5" and acc_st.get("exhausted_today"):
                ex_at = float(acc_st.get("exhausted_at") or 0.0)
                if ex_at > 0 and (now_ts - ex_at) >= 86400.0:
                    acc_st["credits_used_today"] = 0
                    acc_st["videos_used_today"] = 0
                    acc_st["exhausted_today"] = False
                    acc_st.pop("exhausted_at", None)
                    dirty = True
    if dirty:
        save_accounts_state(st)
    return st


def save_accounts_state(st: dict[str, Any]) -> None:
    FLOW_ACCOUNTS_STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def cdp_is_alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=0.6):
            return True
    except Exception:
        return False


def launch_account_chrome_blocking_daemon(account: dict[str, Any]) -> subprocess.Popen:
    """Abre instancia Chrome dedicada ao perfil/porta da conta sem matar janelas existentes."""
    prof = Path(account["profile_dir"]).resolve()
    prof.mkdir(parents=True, exist_ok=True)
    port = int(account["cdp_port"])
    daemon_py = VENDOR_DIR / "chrome_cdp_daemon.py"
    return subprocess.Popen(
        [sys.executable, str(daemon_py), str(prof), str(port), str(os.getpid())],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )


def _runtime_record_path(port: int) -> Path:
    return FLOW_RUNTIME_DIR / f"port_{int(port)}.json"


def _read_runtime_record(port: int) -> dict[str, Any] | None:
    path = _runtime_record_path(port)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def ensure_account_cdp(
    account: dict[str, Any],
    wait_s: int = 18,
    *,
    purpose: str = "",
    project_name: str = "",
) -> str:
    """Abre somente a conta solicitada, sob demanda, e registra ownership do Chrome."""
    port = int(account["cdp_port"])
    account_id = str(account.get("id") or "")
    if cdp_is_alive(port):
        log_flow_event("cdp_reused", account_id, port=port, purpose=purpose, project=project_name)
        return f"http://127.0.0.1:{port}"

    log_flow_event("opening", account_id, port=port, purpose=purpose, project=project_name)
    try:
        launch_account_chrome_blocking_daemon(account)
    except Exception as exc:
        log_flow_event("open_failed", account_id, port=port, purpose=purpose, error=str(exc))
        raise
    t0 = time.time()
    while time.time() - t0 < wait_s:
        if cdp_is_alive(port):
            break
        time.sleep(1.0)
    if not cdp_is_alive(port):
        error = f"Chrome CDP na porta {port} ({account_id}) nao respondeu."
        log_flow_event("open_failed", account_id, port=port, purpose=purpose, error=error)
        raise RuntimeError(error)
    record = _read_runtime_record(port) or {}
    log_flow_event(
        "opened",
        account_id,
        port=port,
        purpose=purpose,
        project=project_name,
        browser_pid=record.get("browser_pid", ""),
        owned_by_this_process=record.get("owner_pid") == os.getpid(),
    )
    return f"http://127.0.0.1:{port}"


def _process_command_line(pid: int) -> str:
    """Le a linha de comando de um PID para nunca encerrar outro perfil/porta."""
    if os.name == "nt":
        command = [
            "powershell", "-NoProfile", "-Command",
            f"(Get-CimInstance Win32_Process -Filter \"ProcessId = {int(pid)}\").CommandLine",
        ]
        return subprocess.check_output(command, text=True, encoding="utf-8", errors="replace", timeout=8).strip()
    return subprocess.check_output(["ps", "-p", str(int(pid)), "-o", "command="], text=True, timeout=8).strip()


def _runtime_matches_account(record: dict[str, Any], account: dict[str, Any]) -> bool:
    try:
        if int(record.get("port") or 0) != int(account["cdp_port"]):
            return False
        expected_profile = str(Path(account["profile_dir"]).resolve()).lower()
        recorded_profile = str(Path(str(record.get("profile_dir") or "")).resolve()).lower()
        if expected_profile != recorded_profile:
            return False
        cmdline = _process_command_line(int(record["browser_pid"])).replace('"', "").lower()
        port_token = f"--remote-debugging-port={int(account['cdp_port'])}"
        profile_token = f"--user-data-dir={expected_profile}"
        return port_token in cmdline and profile_token in cmdline
    except Exception:
        return False


def release_account_chrome(account: dict[str, Any], *, reason: str = "") -> bool:
    """Fecha apenas Chrome aberto e pertencente a este processo/perfil/porta.

    Sessoes preexistentes ou de outro processo sao sempre preservadas. A checagem
    do lock impede fechar uma conta que outro processo acabou de assumir.
    """
    port = int(account["cdp_port"])
    account_id = str(account.get("id") or "")
    lock_owner = is_flow_account_locked(port)
    if lock_owner:
        log_flow_event("release_skipped", account_id, port=port, reason=reason, locked_by=lock_owner.get("pid"))
        return False
    record = _read_runtime_record(port)
    if not record:
        log_flow_event("release_skipped", account_id, port=port, reason=reason, detail="no_owned_runtime")
        return False
    if int(record.get("owner_pid") or 0) != os.getpid():
        log_flow_event("release_skipped", account_id, port=port, reason=reason, detail="foreign_owner")
        return False
    browser_pid = int(record.get("browser_pid") or 0)
    if browser_pid <= 0 or not _is_pid_alive(browser_pid):
        _runtime_record_path(port).unlink(missing_ok=True)
        log_flow_event("release_skipped", account_id, port=port, reason=reason, detail="browser_already_exited")
        return False
    if not _runtime_matches_account(record, account):
        log_flow_event("release_skipped", account_id, port=port, reason=reason, detail="profile_or_command_mismatch")
        return False

    log_flow_event("releasing", account_id, port=port, reason=reason, browser_pid=browser_pid)
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(browser_pid), "/T", "/F"], capture_output=True, timeout=12)
        else:
            os.kill(browser_pid, 15)
        for _ in range(20):
            if not _is_pid_alive(browser_pid):
                _runtime_record_path(port).unlink(missing_ok=True)
                log_flow_event("released", account_id, port=port, reason=reason, browser_pid=browser_pid)
                return True
            time.sleep(0.25)
        log_flow_event("release_failed", account_id, port=port, reason=reason, browser_pid=browser_pid)
    except Exception as exc:
        log_flow_event("release_failed", account_id, port=port, reason=reason, browser_pid=browser_pid, error=str(exc))
    return False


def release_all_owned_flow_accounts(reason: str = "flow_stage_finished") -> list[str]:
    """Libera os Chrome dedicados abertos pelo processo atual, sem tocar em sessoes alheias."""
    released: list[str] = []
    if not FLOW_RUNTIME_DIR.exists():
        return released
    for record_path in sorted(FLOW_RUNTIME_DIR.glob("port_*.json")):
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
            account = record.get("account") or {}
            if not account:
                account = {
                    "id": record.get("account_id") or record_path.stem,
                    "cdp_port": int(record.get("port") or 0),
                    "profile_dir": record.get("profile_dir") or "",
                }
            if release_account_chrome(account, reason=reason):
                released.append(str(account.get("id") or record_path.stem))
        except Exception:
            continue
    return released


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
        rec["exhausted_at"] = round(time.time(), 2)
    if email:
        rec["email"] = email
    save_accounts_state(st)
    return rec


def get_next_available_accounts(ignore_soft_daily_cap: bool = False) -> list[dict[str, Any]]:
    """
    Para videos Veo 3.1 Lite (10 creditos/video):
    - Prioriza SEMPRE as 4 primeiras contas diarias (acc_1..acc_4: 50 creditos/24h cada = 200 creditos = 20 videos/dia).
    - A ultima conta (acc_5) fica estritamente por ULTIMO como reserva de ultima hipotese, so sendo consumida
      quando as 4 primeiras contas ja esgotaram os 50 creditos do ciclo de 24h.
    """
    cfg = load_accounts_config()
    st = load_accounts_state()
    max_cr = int(cfg.get("max_credits_per_account_per_day", 50))
    cost = int(cfg.get("credits_per_veo_lite_8s", 10))
    primary_daily: list[dict[str, Any]] = []
    last_resort_reserve: list[dict[str, Any]] = []
    from config import FLOW_IMAGE_ACCOUNT_ID

    all_accs = [
        a for a in cfg.get("accounts", [])
        if a.get("enabled", True) and a.get("id") != FLOW_IMAGE_ACCOUNT_ID
    ]
    last_acc_id = all_accs[-1]["id"] if len(all_accs) >= 5 else "acc_5"
    for acc in all_accs:
        rec = st.get("accounts", {}).get(acc["id"], {})
        if rec.get("exhausted_today"):
            continue
        acc_max_cr = int(acc.get("max_credits") or max_cr)
        if (not ignore_soft_daily_cap) and (int(rec.get("credits_used_today", 0)) + cost > acc_max_cr):
            continue
        item = {**acc, "state": rec}
        if acc["id"] == last_acc_id:
            last_resort_reserve.append(item)
        else:
            primary_daily.append(item)
    return primary_daily + last_resort_reserve


def get_image_candidate_accounts() -> list[dict[str, Any]]:
    """Conta UNICA padrao para TODAS as imagens (Regra 24), com fallback so se indisponivel.

    Nano Banana 2.1 = 0 credito. Concentrar numa so conta evita espalhar imagens por
    varias contas/projetos. As demais entram apenas como reserva de emergencia.
    """
    from config import FLOW_IMAGE_ACCOUNT_ID

    cfg = load_accounts_config()
    st = load_accounts_state()
    primary_exhausted: list[dict[str, Any]] = []
    primary_with_video: list[dict[str, Any]] = []
    reserve_last: list[dict[str, Any]] = []
    all_accs = [a for a in cfg.get("accounts", []) if a.get("enabled", True)]
    last_acc_id = all_accs[-1]["id"] if len(all_accs) >= 5 else "acc_5"
    designated: list[dict[str, Any]] = []
    for acc in all_accs:
        rec = st.get("accounts", {}).get(acc["id"], {})
        item = {**acc, "state": rec}
        if acc.get("id") == FLOW_IMAGE_ACCOUNT_ID:
            designated.append(item)
        elif acc["id"] == last_acc_id:
            reserve_last.append(item)
        elif rec.get("exhausted_today"):
            primary_exhausted.append(item)
        else:
            primary_with_video.append(item)
    primary_exhausted.reverse()
    return designated + primary_exhausted + primary_with_video + reserve_last


def get_image_flow_account() -> dict[str, Any]:
    """Conta UNICA e padrao para TODAS as imagens (Regra 24). Nunca gera videos."""
    from config import FLOW_IMAGE_ACCOUNT_ID

    cfg = load_accounts_config()
    for acc in cfg.get("accounts", []):
        if acc.get("id") == FLOW_IMAGE_ACCOUNT_ID and acc.get("enabled", True):
            return acc
    for acc in cfg.get("accounts", []):
        if acc.get("enabled", True):
            return acc
    return {}


def get_video_flow_accounts() -> list[dict[str, Any]]:
    """Contas que geram APENAS videos Veo (Regra 24). Exclui a conta de imagens."""
    from config import FLOW_IMAGE_ACCOUNT_ID

    cfg = load_accounts_config()
    return [
        acc for acc in cfg.get("accounts", [])
        if acc.get("enabled", True) and acc.get("id") != FLOW_IMAGE_ACCOUNT_ID
    ]


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


async def _rename_flow_project(page, name: str) -> bool:
    """Renomeia o projeto Flow aberto via menu 'Mais opcoes' -> 'Renomear' (Regra 24)."""
    try:
        more = page.locator(
            'button[aria-label="Mais opções para o projeto"], '
            'button[aria-label="More options for project"]'
        ).first
        if not await more.count():
            return False
        await more.click(timeout=6000)
        await page.wait_for_timeout(500)
        ren = page.locator(
            '[role="menuitem"]:has-text("Renomear"), [role="menuitem"]:has-text("Rename"), '
            'button:has-text("Renomear"), button:has-text("Rename")'
        ).first
        if not await ren.count():
            await page.keyboard.press("Escape")
            return False
        await ren.click(timeout=6000)
        await page.wait_for_timeout(600)
        ed = page.locator('input[placeholder*="nome" i], input[placeholder*="name" i], [contenteditable="true"]').last
        if await ed.count():
            await ed.fill(name)
        else:
            await page.keyboard.press("Control+A")
            await page.keyboard.type(name)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1200)
        return True
    except Exception:
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        return False


async def ensure_named_flow_project(page, account: dict[str, Any], cfg: dict[str, Any], project_name: str) -> str:
    """Abre (ou cria e renomeia) um projeto Flow nomeado para o episodio/tema (Regra 24)."""
    saved = get_named_project_url(account["id"], project_name)
    if saved:
        try:
            if normalize_project_url(page.url) != normalize_project_url(saved) or "/character" in (page.url or ""):
                await page.goto(saved, wait_until="domcontentloaded", timeout=35000)
                await page.wait_for_timeout(2500)
            if "/project/" in (page.url or ""):
                return normalize_project_url(page.url) or saved
        except Exception:
            pass

    await page.goto("https://flow.google.com/", wait_until="domcontentloaded", timeout=35000)
    await page.wait_for_timeout(3000)
    if await check_needs_google_login(page):
        raise RuntimeError(f"Conta {account['id']} precisa fazer login no Google Flow (porta {account['cdp_port']}).")

    new_btn = page.locator(
        'button:has-text("Novo projeto"), a:has-text("Novo projeto"), '
        'button:has-text("New project"), a:has-text("New project")'
    ).first
    if await new_btn.count():
        try:
            await new_btn.click(timeout=8000)
            await page.wait_for_timeout(3500)
        except Exception as exc:
            print(f"  [FlowProject] AVISO: botao Novo projeto falhou em {account['id']}: {str(exc).splitlines()[0]}; reutilizando projeto existente.", flush=True)
            links = await page.evaluate(
                "() => Array.from(document.querySelectorAll('a[href*=\"/project/\"]')).map(a => a.getAttribute('href'))"
            )
            if links:
                target = links[0] if links[0].startswith("http") else f"https://flow.google.com{links[0]}"
                await page.goto(target, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2500)
            elif account.get("project_url"):
                await page.goto(account["project_url"], wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2500)
    else:
        links = await page.evaluate(
            "() => Array.from(document.querySelectorAll('a[href*=\"/project/\"]')).map(a => a.getAttribute('href'))"
        )
        if links:
            target = links[0] if links[0].startswith("http") else f"https://flow.google.com{links[0]}"
            await page.goto(target, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2500)
        elif account.get("project_url"):
            await page.goto(account["project_url"], wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2500)

    if project_name:
        renamed = await _rename_flow_project(page, project_name)
        print(f"  [FlowProject] Conta {account['id']} -> '{project_name}' ({'renomeado' if renamed else 'nome padrao'})", flush=True)

    final_url = normalize_project_url(page.url) or page.url
    if "/project/" in final_url:
        register_named_project(account["id"], project_name, final_url)
        for row in cfg.get("accounts", []):
            if row["id"] == account["id"]:
                row["project_url"] = final_url
                account["project_url"] = final_url
                save_accounts_config(cfg)
                break
    return final_url


async def ensure_episode_project_on_account(account: dict[str, Any], project_name: str) -> str:
    """Abre o CDP da conta e garante o projeto Flow nomeado do episodio (Regra 24)."""
    from playwright.async_api import async_playwright

    cfg = load_accounts_config()
    cdp = ensure_account_cdp(account)
    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(cdp, timeout=15000)
        try:
            ctx = b.contexts[0]
            pg = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or await ctx.new_page()
            return await ensure_named_flow_project(pg, account, cfg, project_name)
        finally:
            await b.close()


async def ensure_flow_project(page, account: dict[str, Any], cfg: dict[str, Any], project_name: str = "") -> str:
    """Abre o projeto Flow da conta (ou cria um novo projeto limpo automaticamente).

    Se `project_name` for informado, usa/cria um projeto nomeado por episodio (Regra 24).
    """
    if project_name:
        return await ensure_named_flow_project(page, account, cfg, project_name)
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

        if not await file_inp.count() and not await up_btn.count():
            # Segunda tentativa: o overlay pode ter fechado ou trocado de aba entre navegacoes
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(350)
            add_retry = page.locator('button[aria-label="Adicionar elementos à caixa de comando"]').first
            if await add_retry.count() and await add_retry.is_visible():
                await add_retry.click(timeout=4000)
                await page.wait_for_timeout(700)
                env_retry = page.locator(
                    '.cdk-overlay-pane :is(button,[role="tab"]):has-text("Envios")'
                ).first
                if await env_retry.count():
                    await env_retry.click(timeout=4000)
                    await page.wait_for_timeout(600)

        if await file_inp.count():
            await file_inp.set_input_files(str(media_path))
        elif await up_btn.count():
            async with page.expect_file_chooser(timeout=5000) as fc:
                await up_btn.click(timeout=5000)
            chooser = await fc.value
            await chooser.set_files(str(media_path))
        else:
            print(f"  [FlowUpload] AVISO: nenhum campo de upload disponivel para '{media_path.name}'.", flush=True)
            await page.keyboard.press("Escape")
            return False

        await page.wait_for_timeout(1500)
        await _accept_usage_rights_modal(page)
        await page.wait_for_timeout(2500)
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
        for _ in range(2):
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(200)
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
            "() => Array.from(document.querySelectorAll('.cdk-overlay-pane [role=\"option\"]')).flatMap(e => (e.innerText || '').split('\\n').map(s => s.trim()).filter(Boolean))"
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
            "credits_remaining_est": max(0, int(acc.get("max_credits") or cfg.get("max_credits_per_account_per_day", 50)) - int(rec.get("credits_used_today", 0))),
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
    project_name: str = "",
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
    had_non_quota_err = False
    for acc in candidates:
        port = int(acc["cdp_port"])
        account_id = str(acc["id"])
        failure_reason = ""
        success = False
        try:
            with FlowAccountLock(port, slug=(proj_dir.name if proj_dir else "episodio"), kind="video", wait=False):
                # Abertura sequencial: a proxima candidata so e tocada se esta falhar.
                if not cdp_is_alive(port):
                    ensure_account_cdp(acc, purpose="video", project_name=project_name)
                async with async_playwright() as pw:
                    b = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=10000)
                    try:
                        ctx = b.contexts[0]
                        page = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or await ctx.new_page()
                        await page.set_viewport_size({"width": 1600, "height": 920})
                        await ensure_flow_project(page, acc, cfg, project_name=project_name)

                        if await check_needs_google_login(page):
                            failure_reason = "logged_out"
                            print(f"[FlowFailover] {account_id} deslogada; tentando proxima conta.", flush=True)
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
                                    normalize_project_url(page.url) or acc.get("project_url") or page.url,
                                    portrait_dir=sec_portrait_dir,
                                )
                                present = await check_characters_present(page, required=characters)
                                missing_chars = [c for c, ok in present.items() if not ok]
                            except Exception as char_exc:
                                print(f"[FlowFailover] Aviso ao criar personagens em {acc['id']}: {char_exc}", flush=True)

                        # Anexa keyframe e eventuais retratos de fallback para personagens ausentes
                        ref_imgs: list[str] = []
                        keyframe_ready = False
                        if acc["id"] == "acc_1" and keyframe_aria_on_acc1:
                            ref_imgs.append(keyframe_aria_on_acc1)
                            keyframe_ready = True
                        elif keyframe_path and keyframe_path.exists():
                            import hashlib
                            import shutil
                            kf_hash = hashlib.sha1(keyframe_path.read_bytes()).hexdigest()[:6]
                            kf_unique = keyframe_path.parent / f"kf_{kf_hash}_{keyframe_path.name}"
                            try:
                                shutil.copy2(keyframe_path, kf_unique)
                                if await upload_media_to_flow(page, kf_unique):
                                    ref_imgs.append(kf_unique.name)
                                    keyframe_ready = True
                            finally:
                                kf_unique.unlink(missing_ok=True)
                        if keyframe_path and keyframe_path.exists() and not keyframe_ready:
                            failure_reason = "keyframe_failed"
                            print(
                                f"[FlowFailover] {account_id} nao conseguiu anexar o keyframe; "
                                "pulando conta para nao gerar video com morfologia instavel.",
                                flush=True,
                            )
                            continue

                        # Sempre inclui a folha de referencia dupla como ancora visual extra
                        sheet = BASE_DIR / "assets" / "reference" / "frida_luna_reference.jpg"
                        if sheet.exists() and sheet.name not in ref_imgs and await upload_media_to_flow(page, sheet):
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
                            usage = mark_account_usage(account_id, credits_delta=10, email=email)
                            res["account_id"] = account_id
                            res["account_email"] = email
                            res["credits_used_today"] = usage["credits_used_today"]
                            success = True
                            log_flow_event("video_completed", account_id, project=(proj_dir.name if proj_dir else ""), output=str(out_mp4))
                            return res
                        except Exception as exc:
                            err_txt = str(exc)
                            # Confere texto visivel na pagina por aviso de creditos esgotados
                            body_low = ""
                            try:
                                body_low = (await page.evaluate("() => (document.body && document.body.innerText || '').slice(0, 1800)")).lower()
                            except Exception:
                                pass
                            if is_quota_error_text(err_txt) or is_quota_error_text(body_low):
                                failure_reason = "exhausted"
                                print(f"[FlowFailover] Cota esgotada em {account_id} ({email}); alternando para proxima conta...", flush=True)
                                mark_account_usage(account_id, credits_delta=0, exhausted=True, email=email)
                            else:
                                failure_reason = "busy" if ("ocupada" in err_txt.lower() or "busy" in err_txt.lower()) else "generation_failed"
                                print(f"[FlowFailover] Erro de UI/sessao em {account_id} ({email}): {err_txt}; tentando proxima conta...", flush=True)
                                had_non_quota_err = True
                            last_err = exc
                            continue
                    finally:
                        await b.close()
                        if success and not FlowStageWatchdog.is_active_for_current_process():
                            release_account_chrome(acc, reason="video_completed")
        except Exception as exc:
            err_low = str(exc).lower()
            failure_reason = "busy" if any(token in err_low for token in ("em uso", "aguardando liberacao", "ocupada", "busy")) else "attempt_failed"
            had_non_quota_err = True
            last_err = exc
            print(f"[FlowFailover] {account_id} falhou antes/depois da sessao: {exc}; tentando proxima conta...", flush=True)
        finally:
            if failure_reason:
                log_flow_event(
                    failure_reason,
                    account_id,
                    stage="video",
                    project=(proj_dir.name if proj_dir else ""),
                    error=str(last_err or "")[:500],
                )
                release_account_chrome(acc, reason=failure_reason)

    if had_non_quota_err:
        raise RuntimeError(f"Erro transitorio de UI/sessao nas contas Flow disponiveis: {last_err}")
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
    base_proj = normalize_project_url(page.url) or normalize_project_url(project_url)
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
        name_inp = page.locator('input[aria-label="Nome do personagem"], input[placeholder*="Nome"]').first
        for _ in range(12):
            if await name_inp.count() and await name_inp.is_visible():
                break
            await page.wait_for_timeout(1000)
        if not (await name_inp.count() and await name_inp.is_visible()):
            print(f"  [FlowChars] Aviso: campo de nome nao apareceu apos upload para '{name}'", flush=True)
            return False

        await name_inp.click(timeout=4000)
        await name_inp.fill(name)
        await page.wait_for_timeout(300)

        pers_inp = page.locator('textarea[aria-label="Personalidade do personagem"], textarea[placeholder*="Descreva"]').first
        if await pers_inp.count():
            await pers_inp.fill(personality)
            await page.wait_for_timeout(300)

        done_btn = page.locator('button:has-text("Concluir")').first
        if not await done_btn.count():
            print(f"  [FlowChars] Aviso: botao Concluir nao encontrado para '{name}'", flush=True)
            return False
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
            release_account_chrome(acc, reason="learn_account_finished")
            break
        if ans == "pular":
            release_account_chrome(acc, reason="learn_account_skipped")
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
        finally:
            release_account_chrome(acc, reason="learn_account_finished")
    return results


# ==============================================================================
# FLOW STAGE WATCHDOG — Fila FIFO + Heartbeat + Aviso Automatico de Termino
# Impede que 2 processos pipeline_v2 disputem a mesma aba Chrome CDP do Flow
# ==============================================================================
import atexit
import ctypes
import os
import threading

FLOW_WATCHDOG_FILE = BASE_DIR / ".chrome-flow-accounts" / "flow_watchdog_queue.json"
FLOW_ACCOUNT_LOCKS_DIR = BASE_DIR / ".chrome-flow-accounts" / "account_locks"


def _extract_port_from_url_or_int(port_or_url: int | str) -> int:
    if isinstance(port_or_url, int):
        return port_or_url
    m = re.search(r":(\d{4,5})\b", str(port_or_url))
    return int(m.group(1)) if m else int(str(port_or_url) or 0)


def is_flow_account_locked(port_or_url: int | str) -> dict[str, Any] | None:
    """Retorna metadados do processo dono se a conta/porta CDP estiver bloqueada por OUTRO processo vivo."""
    port = _extract_port_from_url_or_int(port_or_url)
    if port <= 0:
        return None
    lfile = FLOW_ACCOUNT_LOCKS_DIR / f"port_{port}.json"
    if not lfile.exists():
        return None
    try:
        data = json.loads(lfile.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        opid = int(data.get("pid") or 0)
        if opid <= 0 or opid == os.getpid():
            return None
        if not _is_pid_alive(opid):
            lfile.unlink(missing_ok=True)
            return None
        return data
    except Exception:
        return None


class FlowAccountLock:
    """
    Lock por conta/porta CDP do Google Flow.
    - Para imagens (wait=False): se a conta estiver em uso por outro processo, falha instantaneamente
      para que o gerador pule imediatamente para outra conta Flow com imagem ilimitada (acc_4/acc_3/acc_2).
    - Para videos (wait=False): registra a ocupacao e tenta a proxima candidata permitida, sem abrir varias contas.
    """

    def __init__(self, port_or_url: int | str, slug: str = "", kind: str = "image", wait: bool = False, max_wait_s: float = 900.0) -> None:
        self.port = _extract_port_from_url_or_int(port_or_url)
        self.slug = str(slug or "episodio")
        self.kind = str(kind or "image")
        self.wait = bool(wait)
        self.max_wait_s = float(max_wait_s)
        self.pid = os.getpid()
        self._lfile = FLOW_ACCOUNT_LOCKS_DIR / f"port_{self.port}.json"
        self._acquired = False

    def acquire(self) -> "FlowAccountLock":
        FLOW_ACCOUNT_LOCKS_DIR.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        logged = False
        while True:
            owner = is_flow_account_locked(self.port)
            if owner is None:
                payload = {
                    "pid": self.pid,
                    "slug": self.slug,
                    "kind": self.kind,
                    "port": self.port,
                    "ts": round(time.time(), 2),
                }
                try:
                    self._lfile.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                    self._acquired = True
                    return self
                except Exception:
                    pass
            if not self.wait:
                o_slug = (owner or {}).get("slug", "?")
                o_pid = (owner or {}).get("pid", "?")
                log_flow_event("busy", f"port_{self.port}", port=self.port, kind=self.kind, owner_pid=o_pid, owner_project=o_slug)
                raise RuntimeError(
                    f"Conta Flow :{self.port} em uso por outro processo ({o_slug}, PID {o_pid}); alternando para outra conta."
                )
            if (time.time() - t0) >= self.max_wait_s:
                raise TimeoutError(f"Timeout aguardando liberacao da conta Flow :{self.port}")
            if not logged and owner:
                log_flow_event("busy", f"port_{self.port}", port=self.port, kind=self.kind, owner_pid=owner.get("pid"), owner_project=owner.get("slug"))
                print(
                    f"  [FlowAccountLock] Conta :{self.port} em uso por '{owner.get('slug')}' (PID {owner.get('pid')}); aguardando liberar...",
                    flush=True,
                )
                logged = True
            time.sleep(3.0)

    def release(self) -> None:
        if not self._acquired:
            return
        try:
            if self._lfile.exists():
                data = json.loads(self._lfile.read_text(encoding="utf-8"))
                if isinstance(data, dict) and int(data.get("pid") or 0) == self.pid:
                    self._lfile.unlink(missing_ok=True)
        except Exception:
            pass
        self._acquired = False

    def __enter__(self) -> "FlowAccountLock":
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


def _is_legacy_process_done_with_flow(cmdline: str) -> bool:
    """Verifica se um processo pipeline_v2 legado ja concluiu a etapa Google Flow e esta apenas renderizando FFmpeg local."""
    try:
        slug = ""
        m_slug = re.search(r"--slug\s+[\"']?([a-zA-Z0-9_-]+)", cmdline or "")
        if m_slug:
            slug = m_slug.group(1).strip()
        else:
            m_leg = re.search(r"--legacy-dir\s+[\"']?([^\"'\s]+)", cmdline or "")
            if m_leg:
                slug = Path(m_leg.group(1).strip()).name.lower()[:44].strip("-")
        if not slug:
            return False
        rep_p = BASE_DIR / "projects" / slug / "artifacts" / "scene_audit_report.json"
        if rep_p.exists():
            rep = json.loads(rep_p.read_text(encoding="utf-8"))
            if isinstance(rep, dict) and rep.get("approved") is True and int(rep.get("scenes_audited") or 0) >= 15:
                return True
    except Exception:
        pass
    return False


def _is_pid_alive(pid: int) -> bool:
    """Verifica se um PID do sistema operacional ainda esta vivo (sub-milissegundo no Windows)."""
    if not pid or pid <= 0:
        return False
    if os.name == "nt":
        try:
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return int(exit_code.value) == STILL_ACTIVE
                return False
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            return False
    else:
        try:
            os.kill(int(pid), 0)
            return True
        except OSError:
            return False


def _detect_untracked_pipeline_processes(exclude_pids: set[int]) -> list[tuple[int, str]]:
    """Detecta processos pipeline_v2.py ja em execucao na maquina que iniciaram antes do Watchdog."""
    if os.name != "nt":
        return []
    try:
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" "
                "| Where-Object { $_.CommandLine -match 'pipeline_v2\\.py' } "
                "| Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress"
            ),
        ]
        out = subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace", timeout=8).strip()
        if not out:
            return []
        rows = json.loads(out)
        if isinstance(rows, dict):
            rows = [rows]
        found: list[tuple[int, str]] = []
        for r in rows or []:
            pid = int(r.get("ProcessId") or 0)
            cmdline = str(r.get("CommandLine") or "")
            if pid <= 0 or pid in exclude_pids:
                continue
            if any(flag in cmdline for flag in ("--flow-accounts-status", "--batch-scan", "--stage publish", "--stage audit")):
                continue
            if _is_legacy_process_done_with_flow(cmdline):
                continue
            found.append((pid, cmdline))
        return found
    except Exception:
        return []


def _read_watchdog_state() -> dict[str, Any]:
    if not FLOW_WATCHDOG_FILE.exists():
        return {"active_owner": None, "queue": [], "last_finished": None}
    for _ in range(5):
        try:
            data = json.loads(FLOW_WATCHDOG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            time.sleep(0.08)
    return {"active_owner": None, "queue": [], "last_finished": None}


def _write_watchdog_state(state: dict[str, Any]) -> None:
    FLOW_WATCHDOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FLOW_WATCHDOG_FILE.with_suffix(f".tmp.{os.getpid()}")
    payload = json.dumps(state, ensure_ascii=False, indent=2)
    for _ in range(6):
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(str(tmp), str(FLOW_WATCHDOG_FILE))
            return
        except Exception:
            time.sleep(0.08)
    try:
        FLOW_WATCHDOG_FILE.write_text(payload, encoding="utf-8")
    except Exception:
        pass
    finally:
        tmp.unlink(missing_ok=True)


class FlowStageWatchdog:
    """
    Watchdog multi-processo com fila FIFO, heartbeat continuo e sinalizacao automatica de termino.
    Quem esta usando o Google Flow mantem heartbeat ativo e, ao concluir a etapa de midia (ou encerrar),
    grava sinalizacao explicita ('finished_and_notified') para o proximo processo continuar imediatamente.
    """

    def __init__(self, slug: str, stage: str = "flow_media", heartbeat_interval_s: float = 4.0, stale_timeout_s: float = 60.0) -> None:
        self.slug = str(slug or "episodio")
        self.stage = str(stage or "flow_media")
        self.pid = os.getpid()
        self.ppid = os.getppid()
        self.heartbeat_interval_s = heartbeat_interval_s
        self.stale_timeout_s = stale_timeout_s
        self._stop_evt = threading.Event()
        self._hb_thread: threading.Thread | None = None
        self._acquired = False

    @classmethod
    def is_active_for_current_process(cls) -> bool:
        """Indica se esta execucao ja detem o Watchdog e pode manter contas abertas."""
        owner = _read_watchdog_state().get("active_owner")
        return isinstance(owner, dict) and int(owner.get("pid") or 0) == os.getpid()

    @classmethod
    def is_busy_by_other(cls) -> bool:
        """Retorna True se outro processo pipeline_v2 vivo estiver atualmente detendo ou na frente da fila do Watchdog."""
        my_pid = os.getpid()
        st = _read_watchdog_state()
        owner = st.get("active_owner")
        if isinstance(owner, dict):
            opid = int(owner.get("pid") or 0)
            if opid > 0 and opid != my_pid and _is_pid_alive(opid):
                return True
        for q in st.get("queue") or []:
            if isinstance(q, dict):
                qpid = int(q.get("pid") or 0)
                if qpid > 0 and qpid != my_pid and _is_pid_alive(qpid):
                    return True
        return False

    def _is_owner_stale(self, owner: dict[str, Any] | None) -> bool:
        if not owner or not isinstance(owner, dict):
            return True
        opid = int(owner.get("pid") or 0)
        if opid == self.pid:
            return False
        if not _is_pid_alive(opid):
            return True
        hb = float(owner.get("heartbeat_ts") or owner.get("started_at") or 0.0)
        if hb > 0 and (time.time() - hb) > self.stale_timeout_s and not _is_pid_alive(opid):
            return True
        return False

    def _heartbeat_worker(self) -> None:
        while not self._stop_evt.wait(self.heartbeat_interval_s):
            st = _read_watchdog_state()
            owner = st.get("active_owner")
            if isinstance(owner, dict) and int(owner.get("pid") or 0) == self.pid:
                owner["heartbeat_ts"] = round(time.time(), 2)
                _write_watchdog_state(st)

    def acquire(self) -> "FlowStageWatchdog":
        # 1. Registra imediatamente nossa entrada na fila FIFO antes de inspecionar processos externos
        st = _read_watchdog_state()
        queue = [
            q for q in (st.get("queue") or [])
            if isinstance(q, dict) and _is_pid_alive(int(q.get("pid") or 0))
        ]
        if not any(int(q.get("pid") or 0) == self.pid for q in queue):
            queue.append({
                "pid": self.pid,
                "ppid": self.ppid,
                "slug": self.slug,
                "stage": self.stage,
                "enqueued_at": round(time.time(), 2),
            })
        st["queue"] = queue
        _write_watchdog_state(st)

        tracked_pids = {self.pid, self.ppid}
        for q in queue:
            if isinstance(q, dict):
                if q.get("pid"):
                    tracked_pids.add(int(q["pid"]))
                if q.get("ppid"):
                    tracked_pids.add(int(q["ppid"]))
        owner = st.get("active_owner")
        if isinstance(owner, dict):
            if owner.get("pid"):
                tracked_pids.add(int(owner["pid"]))
            if owner.get("ppid"):
                tracked_pids.add(int(owner["ppid"]))

        # Snapshot apenas processos pipeline_v2 legados pre-existentes (fora da fila Watchdog)
        preexisting = _detect_untracked_pipeline_processes(exclude_pids=tracked_pids)
        preexisting_pids = {p: cmd for p, cmd in preexisting}

        atexit.register(self.release)
        wait_logged = False
        while True:
            st = _read_watchdog_state()
            state_dirty = False

            # Qualquer PID/PPID que entrou na fila Watchdog nao e processo legado nao-rastreado
            for q in st.get("queue") or []:
                if isinstance(q, dict):
                    preexisting_pids.pop(int(q.get("pid") or 0), None)
                    preexisting_pids.pop(int(q.get("ppid") or 0), None)
            owner = st.get("active_owner")
            if isinstance(owner, dict):
                preexisting_pids.pop(int(owner.get("pid") or 0), None)
                preexisting_pids.pop(int(owner.get("ppid") or 0), None)

            alive_pre = {
                p: cmd
                for p, cmd in preexisting_pids.items()
                if _is_pid_alive(p) and not _is_legacy_process_done_with_flow(cmd)
            }
            preexisting_pids = alive_pre

            if owner and self._is_owner_stale(owner):
                dead_pid = owner.get("pid")
                dead_slug = owner.get("slug")
                print(
                    f"[FlowWatchdog] Processo anterior '{dead_slug}' (PID {dead_pid}) encerrou; limpando lock para avancar fila.",
                    flush=True,
                )
                owner = None
                st["active_owner"] = None
                state_dirty = True

            raw_queue = st.get("queue") or []
            queue = [
                q for q in raw_queue
                if isinstance(q, dict) and _is_pid_alive(int(q.get("pid") or 0))
            ]
            if len(queue) != len(raw_queue):
                state_dirty = True
            if not any(int(q.get("pid") or 0) == self.pid for q in queue):
                queue.append({
                    "pid": self.pid,
                    "ppid": self.ppid,
                    "slug": self.slug,
                    "stage": self.stage,
                    "enqueued_at": round(time.time(), 2),
                })
                state_dirty = True
            st["queue"] = queue

            first_in_queue = int(queue[0].get("pid") or 0) == self.pid if queue else True
            if owner is None and not alive_pre and first_in_queue:
                last_fin = st.get("last_finished")
                if wait_logged and isinstance(last_fin, dict):
                    print(
                        f"[FlowWatchdog] Recebido aviso de termino de '{last_fin.get('slug')}' (PID {last_fin.get('pid')}). "
                        f"Iniciando '{self.slug}' (PID {self.pid})!",
                        flush=True,
                    )
                now = round(time.time(), 2)
                st["active_owner"] = {
                    "pid": self.pid,
                    "ppid": self.ppid,
                    "slug": self.slug,
                    "stage": self.stage,
                    "started_at": now,
                    "heartbeat_ts": now,
                    "status": "running",
                }
                st["queue"] = [q for q in queue if int(q.get("pid") or 0) != self.pid]
                _write_watchdog_state(st)
                self._acquired = True
                self._stop_evt.clear()
                self._hb_thread = threading.Thread(target=self._heartbeat_worker, name=f"FlowWatchdog-{self.pid}", daemon=True)
                self._hb_thread.start()
                print(f"[FlowWatchdog] Lock Google Flow ativo para '{self.slug}' (PID {self.pid}).", flush=True)
                return self

            if not wait_logged:
                if owner:
                    print(
                        f"[FlowWatchdog] Google Flow em uso por '{owner.get('slug')}' (PID {owner.get('pid')}). "
                        f"'{self.slug}' (PID {self.pid}) aguardando aviso de termino na fila...",
                        flush=True,
                    )
                elif alive_pre:
                    pids_str = ", ".join(str(p) for p in alive_pre.keys())
                    print(
                        f"[FlowWatchdog] Processo(s) pipeline_v2 anterior(es) em execucao (PID {pids_str}). "
                        f"'{self.slug}' (PID {self.pid}) aguardando termino automatico para assumir o Google Flow...",
                        flush=True,
                    )
                wait_logged = True
            if state_dirty:
                _write_watchdog_state(st)
            time.sleep(4.0)

    def release(self) -> None:
        # Fecha as contas owned enquanto o Watchdog ainda bloqueia o proximo
        # processo; so depois envia finished_and_notified para a fila.
        try:
            released = release_all_owned_flow_accounts("watchdog_finished")
            if released:
                log_flow_event("stage_accounts_released", stage=self.stage, project=self.slug, accounts=",".join(released))
        except Exception:
            pass
        self._stop_evt.set()
        try:
            st = _read_watchdog_state()
            changed = False
            owner = st.get("active_owner")
            if isinstance(owner, dict) and int(owner.get("pid") or 0) == self.pid:
                st["active_owner"] = None
                st["last_finished"] = {
                    "pid": self.pid,
                    "slug": self.slug,
                    "stage": self.stage,
                    "finished_at": round(time.time(), 2),
                    "status": "finished_and_notified",
                }
                changed = True
            old_q = st.get("queue") or []
            new_q = [q for q in old_q if not (isinstance(q, dict) and int(q.get("pid") or 0) == self.pid)]
            if len(new_q) != len(old_q):
                st["queue"] = new_q
                changed = True
            if changed:
                _write_watchdog_state(st)
                if self._acquired:
                    print(
                        f"[FlowWatchdog] Sinalizado TERMINO de '{self.slug}' (PID {self.pid}) no Google Flow; "
                        "proximo processo da fila liberado para continuar!",
                        flush=True,
                    )
        except Exception:
            pass
        self._acquired = False

    def __enter__(self) -> "FlowStageWatchdog":
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

