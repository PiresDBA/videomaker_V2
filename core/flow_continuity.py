# -*- coding: utf-8 -*-
"""Automacao de continuidade visual no Google Flow (Nano Banana 2.1 + Veo 3.1 Lite) via Chrome CDP."""
from __future__ import annotations

import asyncio
import io
import json
import re
import time
from pathlib import Path
from typing import Any

from PIL import Image

DEFAULT_FLOW_PROJECT_URL = "https://flow.google.com/project/2700c141-d4ed-4bd2-9f7a-2f82cffa8083"
DEFAULT_CDP_URL = "http://127.0.0.1:18800"

FLOW_YOUTHFUL_PUPPY_STYLE_PREFIX = (
    "Stylized 3D Disney-Pixar animated cartoon matching the character avatars: "
    "two young child-like puppies (1 year old max, playful 6-to-10-year-old kid/tween cartoon proportions, "
    "graceful rounded faces, big glossy expressive cartoon eyes with eyelashes; "
    "NEVER old or mature adult dogs, NEVER photorealistic real-world dogs): "
)
FLOW_BABY_PUPPY_STYLE_PREFIX = FLOW_YOUTHFUL_PUPPY_STYLE_PREFIX


def enforce_youthful_puppy_prompt(prompt: str) -> str:
    """Garante no prompt do Flow o padrão criança/pré-adolescente (até 1 ano, fiel ao avatar 3D Disney/Pixar), exceto em flashbacks explícitos de bebê."""
    txt = (prompt or "").strip()
    low = txt.lower()
    if any(tok in low for tok in ("quando eram bebês", "newborn baby", "flashback bebê", "as newborn babies")):
        return txt
    if "1 year old max" in low and "kid/tween" in low:
        return txt
    return f"{FLOW_YOUTHFUL_PUPPY_STYLE_PREFIX}{txt}"


enforce_baby_puppy_prompt = enforce_youthful_puppy_prompt


async def _find_bottom_pill(page):
    vp = page.viewport_size or {"width": 1600, "height": 920}
    min_y = max(280, int(vp.get("height", 920) * 0.55))
    min_x = max(200, int(vp.get("width", 1600) * 0.25))
    btns = page.locator("button")
    n = await btns.count()
    for i in range(n):
        b = btns.nth(i)
        try:
            box = await b.bounding_box()
            if not box or box["y"] < min_y or box["x"] < min_x:
                continue
            txt = (await b.inner_text() or "").strip()
            if any(tok in txt for tok in ("Nano", "Veo", "720p", "x1", "x2", "x3", "x4")):
                return b
        except Exception:
            pass
    return None


async def ensure_direct_mode(page) -> Any:
    """Garante tab 'Tudo' (dashboard) e sai do modo Agente ('spark') para o painel direto."""
    async def _try_enter_direct():
        close_btn = page.locator('button:has-text("right_panel_close")').first
        if await close_btn.count() and await close_btn.is_visible():
            await close_btn.click()
            await page.wait_for_timeout(700)

        dash = page.locator('mat-nav-list button:has-text("dashboard")').first
        if await dash.count():
            await dash.click()
            await page.wait_for_timeout(700)

        pill = await _find_bottom_pill(page)
        if pill is None:
            spark = page.locator('button[aria-label*="agente" i], button:has-text("spark")').last
            if await spark.count():
                await spark.click()
                await page.wait_for_timeout(1200)
            pill = await _find_bottom_pill(page)
        return pill

    pill = await _try_enter_direct()
    if pill is None:
        m = re.match(r"(https://flow\.google\.com(?:/u/\d+)?/project/[^/?#]+)", page.url or "")
        try:
            await page.set_viewport_size({"width": 1600, "height": 920})
            if m:
                await page.goto(m.group(1), wait_until="domcontentloaded", timeout=30000)
            else:
                await page.reload(wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2500)
            await page.keyboard.press("Escape")
        except Exception:
            pass
        for _ in range(5):
            pill = await _try_enter_direct()
            if pill is not None:
                break
            await page.wait_for_timeout(1000)
    if pill is None:
        raise RuntimeError("Botao de configuracao direta (Nano/Veo) nao encontrado no Flow.")
    return pill


async def configure_flow_mode(
    page,
    kind: str = "Imagem",
    aspect: str = "16:9",
    model_hint: str = "Nano Banana 2.1",
    count: str = "x1",
    video_submode: str = "Elementos",
) -> str:
    """Configura Imagem (Nano Banana 2.1, x1, 0 creditos) ou Video (Veo 3.1 Lite, x1, 10 creditos)."""
    # Fecha qualquer overlay pendente (ex.: menu dropdown aberto de chamada anterior)
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(200)
    pill = await ensure_direct_mode(page)
    await pill.click()
    await page.wait_for_timeout(700)

    pane = page.locator(".cdk-overlay-pane").first
    targets = [kind, aspect, count]
    if kind == "Vídeo" and video_submode:
        targets.insert(1, video_submode)

    for lbl in targets:
        btn = pane.locator(f'button:has-text("{lbl}"), mat-button-toggle:has-text("{lbl}")').first
        if await btn.count():
            await btn.click()
            await page.wait_for_timeout(320)

    pane_txt = await pane.inner_text()
    if model_hint not in pane_txt:
        dd = pane.locator('button:has-text("arrow_drop_down")').first
        if await dd.count():
            await dd.click()
            await page.wait_for_timeout(500)
            m = page.locator(
                f'.cdk-overlay-pane button:has-text("{model_hint}"), '
                f'.cdk-overlay-pane [role="menuitem"]:has-text("{model_hint}"), '
                f'.cdk-overlay-pane [role="option"]:has-text("{model_hint}")'
            ).last
            if await m.count():
                await m.click()
                await page.wait_for_timeout(450)

    # Rele o painel principal (.first, nao o dropdown fechado)
    summary = (await page.locator(".cdk-overlay-pane").first.inner_text()).replace("\n", " | ")
    if count not in summary:
        await page.keyboard.press("Escape")
        raise RuntimeError(f"Quantidade '{count}' nao confirmada no painel Flow: {summary}")
    if kind == "Imagem" and "0 créditos" not in summary:
        await page.keyboard.press("Escape")
        raise RuntimeError(f"Imagem no Flow deveria usar 0 creditos; obtido: {summary}")
    if kind == "Vídeo" and ("Veo 3.1 - Lite" not in summary or "10 créditos" not in summary):
        await page.keyboard.press("Escape")
        raise RuntimeError(f"Video deve usar Veo 3.1 - Lite x1 (10 creditos); obtido: {summary}")

    await page.keyboard.press("Escape")
    await page.wait_for_timeout(400)
    return summary


async def clear_attached_chips(page) -> None:
    """Remove anexos pendentes da caixa de comando antes de anexar novas referencias."""
    for _ in range(8):
        rm = page.locator(
            'button[aria-label*="Remover" i], button[aria-label*="Remove" i], button[aria-label*="Excluir" i]'
        )
        found = False
        cnt = await rm.count()
        for i in range(cnt):
            b = rm.nth(i)
            try:
                box = await b.bounding_box()
                if box and box["y"] > 540:
                    await b.click(timeout=2000)
                    await page.wait_for_timeout(200)
                    found = True
                    break
            except Exception:
                pass
        if not found:
            break


async def attach_reference_from_plus(page, tab_name: str, match_label: str, exact: bool = False) -> bool:
    """Anexa Personagem, Imagem ou Video no prompt via '+' -> Incluir no comando."""
    add_btn = page.locator('button[aria-label="Adicionar elementos à caixa de comando"]').first
    await add_btn.click()
    await page.wait_for_timeout(850)

    pane = page.locator(".cdk-overlay-pane").last
    tab = pane.locator(f'button:has-text("{tab_name}"), [role="tab"]:has-text("{tab_name}")').first
    if await tab.count():
        await tab.click()
        await page.wait_for_timeout(700)

    async def _find_option():
        opts = page.locator('.cdk-overlay-pane [role="option"]')
        cnt = await opts.count()
        for i in range(cnt):
            it = opts.nth(i)
            try:
                t = (await it.inner_text() or "").strip()
                aria = (await it.get_attribute("aria-label") or "").strip()
                first_line = t.split("\n", 1)[0].strip() if t else ""
                if exact:
                    hit = (first_line == match_label) or (aria == match_label)
                else:
                    needle = match_label.lower().rstrip("….")
                    hit = (
                        first_line == match_label
                        or needle in first_line.lower()
                        or needle in t.lower()
                        or needle in aria.lower()
                    )
                if hit:
                    return it
            except Exception:
                pass
        return None

    target_opt = await _find_option()
    if target_opt is None and tab_name in ("Imagens", "Vídeos"):
        srch = page.locator('.cdk-overlay-pane input[placeholder*="Pesquisar" i], .cdk-overlay-pane input[aria-label*="Pesquisar" i]').first
        if await srch.count() and await srch.is_visible():
            await srch.fill(match_label[:32].rstrip("…."))
            await page.wait_for_timeout(700)
            target_opt = await _find_option()

    if target_opt is None and tab_name == "Imagens":
        srch = page.locator('.cdk-overlay-pane input[placeholder*="Pesquisar" i], .cdk-overlay-pane input[aria-label*="Pesquisar" i]').first
        if await srch.count() and await srch.is_visible():
            await srch.fill("")
            await page.wait_for_timeout(400)
        for alt_tab in ("Envios", "Todas as mídias", "Imagens"):
            t_btn = pane.locator(f'button:has-text("{alt_tab}"), [role="tab"]:has-text("{alt_tab}")').first
            if await t_btn.count():
                await t_btn.click()
                await page.wait_for_timeout(700)
                target_opt = await _find_option()
                if target_opt is not None:
                    break
        if target_opt is None and match_label.lower().endswith((".jpg", ".jpeg", ".png")):
            for fb_tab in ("Envios", "Imagens"):
                t_btn = pane.locator(f'button:has-text("{fb_tab}"), [role="tab"]:has-text("{fb_tab}")').first
                if await t_btn.count():
                    await t_btn.click()
                    await page.wait_for_timeout(700)
                first_opt = page.locator('.cdk-overlay-pane [role="option"]').first
                if await first_opt.count():
                    target_opt = first_opt
                    print(f"  [Flow] Fallback: selecionando 1a midia de '{fb_tab}' para '{match_label}'", flush=True)
                    break

    if target_opt is None:
        print(f"  [Flow] AVISO: '{match_label}' nao encontrado na aba '{tab_name}'", flush=True)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
        return False

    await target_opt.click()
    await page.wait_for_timeout(550)

    inc = page.locator('.cdk-overlay-pane button:has-text("Incluir no comando")').last
    if await inc.count() and await inc.is_visible():
        await inc.click()
        await page.wait_for_timeout(650)
        return True

    await page.keyboard.press("Escape")
    await page.wait_for_timeout(300)
    return False


async def _snapshot_top_tiles(page, limit: int = 6) -> list[dict[str, Any]]:
    return await page.evaluate(
        """(lim) => Array.from(document.querySelectorAll('flow-grid-tile-container')).slice(0, lim).map((t, idx) => ({
            idx,
            aria: t.getAttribute('aria-label') || '',
            txt: (t.innerText || '').trim(),
            has_more: !!t.querySelector('button[aria-label="Mais opções"]'),
            imgs: Array.from(t.querySelectorAll('img')).map(i => ({src: i.src || '', w: i.naturalWidth || 0, h: i.naturalHeight || 0})),
            vids: Array.from(t.querySelectorAll('video')).map(v => v.currentSrc || v.src || '').filter(Boolean),
        }))""",
        limit,
    )


def _inject_at_character_mentions(prompt: str, attached_chars: list[str]) -> str:
    """Garante mencoes @Personagem (ex.: @Frida @Luna @Pipoca) no prompt para trava no Flow."""
    clean_names = []
    for ch in attached_chars:
        name = ch.split(":", 1)[-1].strip()
        if name and f"@{name.lower()}" not in prompt.lower():
            clean_names.append(f"@{name}")
    if not clean_names:
        return prompt
    return f"{' '.join(clean_names)}: {prompt}"


async def _retry_failed_flow_tile(page, retries_done: int, max_retries: int = 3) -> bool:
    """Detecta tile cinza/falhado no Flow e clica no botao circular de refresh/retry (canto inferior direito)."""
    if retries_done >= max_retries:
        return False
    tile0 = page.locator("flow-grid-tile-container").first
    if not await tile0.count():
        return False
    try:
        info = await tile0.evaluate(
            """(el) => {
                const txt = (el.innerText || '').toLowerCase();
                const hasImg = Array.from(el.querySelectorAll('img')).some(i => (i.naturalWidth || 0) >= 800);
                const hasVidReady = txt.includes('play_circle') && !!el.querySelector('button[aria-label="Mais opções"]');
                const inProgress = /\\b\\d+%/.test(txt);
                const btns = Array.from(el.querySelectorAll('button')).map(b => ({
                    aria: (b.getAttribute('aria-label') || '').toLowerCase(),
                    txt: (b.innerText || '').trim().toLowerCase(),
                    cls: (b.className || '').toLowerCase(),
                }));
                const hasRetryBtn = btns.some(b =>
                    b.aria.includes('tentar') || b.aria.includes('refaz') || b.aria.includes('retry') ||
                    b.aria.includes('refresh') || b.aria.includes('novamente') ||
                    b.txt === 'refresh' || b.txt === 'replay' || b.txt.includes('tentar') || b.txt.includes('refaz')
                );
                const hasErrTxt = txt.includes('algo deu errado') || txt.includes('falha') || txt.includes('não foi possível') || txt.includes('erro');
                return { hasImg, hasVidReady, inProgress, hasRetryBtn, hasErrTxt };
            }"""
        )
    except Exception:
        return False
    if info.get("inProgress") or info.get("hasImg") or info.get("hasVidReady"):
        return False
    if not (info.get("hasRetryBtn") or info.get("hasErrTxt")):
        return False

    # Tenta clicar no botao circular de refresh/retry dentro do tile (parte direita embaixo)
    for sel in (
        'button[aria-label*="Tentar" i]',
        'button[aria-label*="Refaz" i]',
        'button[aria-label*="Retry" i]',
        'button[aria-label*="Refresh" i]',
        'button:has-text("refresh")',
        'button:has-text("replay")',
        'button:has-text("Tentar novamente")',
    ):
        btn = tile0.locator(sel).first
        if await btn.count():
            try:
                await tile0.hover()
                await page.wait_for_timeout(300)
                await btn.click(timeout=3000, force=True)
                print(
                    f"  [Flow] Tile falhou (cinza/erro); clicando no refresh circular ({retries_done + 1}/{max_retries})...",
                    flush=True,
                )
                await page.wait_for_timeout(1500)
                return True
            except Exception:
                pass
    # Fallback: ultimo botao dentro do tile quando erro detectado
    if info.get("hasErrTxt"):
        last_btn = tile0.locator("button").last
        if await last_btn.count():
            try:
                await last_btn.click(timeout=3000, force=True)
                print(
                    f"  [Flow] Tile com erro; acionando botao inferior direito ({retries_done + 1}/{max_retries})...",
                    flush=True,
                )
                await page.wait_for_timeout(1500)
                return True
            except Exception:
                pass
    return False


async def generate_flow_image(
    page,
    prompt: str,
    out_jpg: Path,
    characters: tuple[str, ...] = ("Frida", "Luna"),
    ref_images: tuple[str, ...] = (),
    ref_videos: tuple[str, ...] = (),
    wait_s: int = 120,
) -> dict[str, Any]:
    """Gera 1 imagem 16:9 via Nano Banana 2.1 (0 creditos) e salva RGB JPEG 1920x1080."""
    summary = await configure_flow_mode(page, kind="Imagem", aspect="16:9", model_hint="Nano Banana 2.1", count="x1")
    await clear_attached_chips(page)

    attached: list[str] = []
    for ch in characters:
        if await attach_reference_from_plus(page, "Personagens", ch, exact=True):
            attached.append(f"char:{ch}")
    for im_ref in ref_images:
        if im_ref and await attach_reference_from_plus(page, "Imagens", im_ref, exact=False):
            attached.append(f"img:{im_ref[:30]}")
    for vid_ref in ref_videos:
        if vid_ref and await attach_reference_from_plus(page, "Vídeos", vid_ref, exact=False):
            attached.append(f"vid:{vid_ref[:30]}")

    before = await _snapshot_top_tiles(page)
    before_srcs = {im["src"] for t in before for im in t["imgs"] if im["src"]}

    prompt = enforce_baby_puppy_prompt(prompt)
    prompt = _inject_at_character_mentions(prompt, [a for a in attached if a.startswith("char:")])
    ed = page.locator('[contenteditable="true"]').last
    await ed.click()
    await ed.fill(prompt)
    await page.wait_for_timeout(450)

    await page.locator('button[aria-label="Iniciar geração"]').first.click()
    t0 = time.time()
    winner = None
    tile_retries = 0
    while time.time() - t0 < wait_s:
        await page.wait_for_timeout(3000)
        cur = await _snapshot_top_tiles(page, limit=4)
        if not cur:
            continue
        top = cur[0]
        if re.search(r"\b\d+%", top["txt"]) or "play_circle" in top["txt"]:
            continue
        for im in top["imgs"]:
            if im["src"].startswith("http") and im["src"] not in before_srcs and im["w"] >= 800:
                winner = (im["src"], top["aria"], im["w"], im["h"])
                break
        if winner:
            break
        if (time.time() - t0) >= 9.0 and await _retry_failed_flow_tile(page, tile_retries, max_retries=3):
            tile_retries += 1
            t0 = time.time()

    if not winner:
        raise TimeoutError(f"Timeout ({wait_s}s) aguardando imagem Flow para {out_jpg.name}")

    resp = await page.context.request.get(winner[0], timeout=60000)
    if not resp.ok:
        raise RuntimeError(f"Falha ao baixar imagem Flow HTTP {resp.status}")
    data = await resp.body()
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(io.BytesIO(data)).convert("RGB").resize((1920, 1080), Image.Resampling.LANCZOS)
    im.save(out_jpg, "JPEG", quality=93)

    return {
        "ok": True,
        "kind": "image",
        "path": str(out_jpg),
        "bytes": out_jpg.stat().st_size,
        "tile_aria": winner[1],
        "src_size": f"{winner[2]}x{winner[3]}",
        "attached": attached,
        "mode": summary,
        "elapsed_s": round(time.time() - t0, 1),
    }


async def _wait_for_inflight_flow_generation(page, max_wait_s: int = 180) -> bool:
    """Aguarda qualquer geracao em andamento no grid do Flow concluir antes de enviar novo prompt."""
    t0 = time.time()
    logged = False
    while time.time() - t0 < max_wait_s:
        cur = await _snapshot_top_tiles(page, limit=3)
        busy = any(re.search(r"\b\d+%", t.get("txt") or "") for t in cur)
        if not busy:
            return True
        if not logged:
            print(
                "  [Flow] Geracao em andamento detectada no grid; aguardando concluir antes de enviar novo prompt...",
                flush=True,
            )
            logged = True
        await page.wait_for_timeout(4000)
    raise TimeoutError(f"Geracao anterior no grid do Flow nao finalizou em {max_wait_s}s; envio bloqueado para evitar duplicata.")


async def generate_flow_video(
    page,
    prompt: str,
    out_mp4: Path,
    characters: tuple[str, ...] = ("Frida", "Luna"),
    ref_images: tuple[str, ...] = (),
    ref_videos: tuple[str, ...] = (),
    video_submode: str = "Elementos",
    wait_s: int = 360,
) -> dict[str, Any]:
    """Gera 1 video 8s 16:9 via Veo 3.1 - Lite (x1, 10 creditos) com continuidade de personagens/cenas."""
    summary = await configure_flow_mode(
        page, kind="Vídeo", aspect="16:9", model_hint="Veo 3.1 - Lite", count="x1", video_submode=video_submode
    )
    await clear_attached_chips(page)

    attached: list[str] = []
    for ch in characters:
        if await attach_reference_from_plus(page, "Personagens", ch, exact=True):
            attached.append(f"char:{ch}")
    for im_ref in ref_images:
        if im_ref and await attach_reference_from_plus(page, "Imagens", im_ref, exact=False):
            attached.append(f"img:{im_ref[:30]}")
    for vid_ref in ref_videos:
        if vid_ref and await attach_reference_from_plus(page, "Vídeos", vid_ref, exact=False):
            attached.append(f"vid:{vid_ref[:30]}")

    await _wait_for_inflight_flow_generation(page, max_wait_s=min(wait_s, 180))
    before = await _snapshot_top_tiles(page, limit=4)
    before_srcs = {im["src"] for t in before for im in t["imgs"] if im["src"]}
    before_arias = [t["aria"] for t in before]

    prompt = enforce_baby_puppy_prompt(prompt)
    prompt = _inject_at_character_mentions(prompt, [a for a in attached if a.startswith("char:")])
    ed = page.locator('[contenteditable="true"]').last
    await ed.click()
    await ed.fill(prompt)
    await page.wait_for_timeout(500)

    net_video_urls: list[str] = []

    def on_resp(r):
        try:
            ct = (r.headers or {}).get("content-type", "").split(";")[0].lower()
            if ct.startswith("video/") and r.status in (200, 206):
                net_video_urls.append(r.url)
        except Exception:
            pass

    page.on("response", on_resp)
    try:
        await page.locator('button[aria-label="Iniciar geração"]').first.click()
        t0 = time.time()
        ready_tile = None
        saw_progress = False
        tile_retries = 0
        while time.time() - t0 < wait_s:
            await page.wait_for_timeout(4000)
            body_low = (await page.evaluate("() => (document.body && document.body.innerText || '').slice(0, 2200)")).lower()
            if any(m in body_low for m in ("créditos insuficientes", "creditos insuficientes", "sem créditos", "out of credits", "limite diário", "insufficient credits")):
                raise RuntimeError("Creditos insuficientes no Google Flow")
            cur = await _snapshot_top_tiles(page, limit=3)
            if not cur:
                continue
            top = cur[0]
            if re.search(r"\b\d+%", top["txt"]):
                saw_progress = True
                continue
            new_img = any(im["src"] and im["src"] not in before_srcs for im in top["imgs"])
            aria_changed = bool(top["aria"]) and (not before_arias or top["aria"] != before_arias[0])
            tile_ready = bool(top.get("has_more")) or ("more_vert" in top["txt"]) or bool(top["vids"])
            if "play_circle" in top["txt"] and tile_ready and (aria_changed or (saw_progress and (new_img or top["vids"]))):
                ready_tile = top
                break
            if (time.time() - t0) >= 12.0 and await _retry_failed_flow_tile(page, tile_retries, max_retries=3):
                tile_retries += 1
                saw_progress = False
                t0 = time.time()

        if not ready_tile:
            raise TimeoutError(f"Timeout ({wait_s}s) aguardando video Veo 3.1 Lite para {out_mp4.name}")

        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        # Aguarda hidratacao breve apos play_circle surgir e tenta menu rapido (timeout curto)
        await page.wait_for_timeout(1200)
        tile0 = page.locator("flow-grid-tile-container").first
        downloaded = False
        try:
            await tile0.scroll_into_view_if_needed()
            await tile0.hover()
            await page.wait_for_timeout(650)
            mb = tile0.locator('button[aria-label="Mais opções"]').first
            if await mb.count():
                await mb.click(timeout=4000, force=True)
                await page.wait_for_timeout(650)
                dl_item = page.locator('.cdk-overlay-pane :is(button,[role="menuitem"]):has-text("Fazer o download")').first
                if await dl_item.count():
                    await dl_item.hover()
                    await page.wait_for_timeout(650)
                    sub_dl = page.locator(
                        '.cdk-overlay-pane :is(button,[role="menuitem"]):has-text("720p"), '
                        '.cdk-overlay-pane :is(button,[role="menuitem"]):has-text("Original")'
                    ).last
                    async with page.expect_download(timeout=45000) as dinfo:
                        if await sub_dl.count():
                            await sub_dl.click(timeout=4000)
                        else:
                            await dl_item.click(timeout=4000)
                    dl_obj = await dinfo.value
                    await dl_obj.save_as(str(out_mp4))
                    downloaded = out_mp4.exists() and out_mp4.stat().st_size >= 50_000
        except Exception as dl_err:
            print(f"  [Flow] Download via menu falhou rapido ({str(dl_err).splitlines()[0]}); usando fallback direto.", flush=True)
        finally:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)

        if not downloaded:
            # Fallback robusto: abre o tile se hover nao hidratar <video src>, tenta botao de download do player ou URLs reais >= 50KB
            await tile0.hover()
            await page.wait_for_timeout(900)
            cur = await _snapshot_top_tiles(page, limit=1)
            modal_urls: list[str] = []
            if not (cur and cur[0].get("vids")):
                proj_page_url = page.url or ""
                try:
                    await tile0.scroll_into_view_if_needed()
                    await tile0.click(timeout=4000, force=True)
                    await page.wait_for_timeout(1800)
                    dl_btn = page.locator(
                        'button[aria-label="Baixar mídia"], button[aria-label*="download" i], button[aria-label*="Baixar" i], button:has-text("Fazer o download")'
                    ).first
                    if await dl_btn.count() and await dl_btn.is_visible():
                        try:
                            async with page.expect_download(timeout=25000) as dinfo:
                                await dl_btn.click(timeout=4000)
                                await page.wait_for_timeout(600)
                                sub_pop = page.locator(
                                    '.cdk-overlay-pane :is(button,[role="menuitem"]):has-text("720p"), '
                                    '.cdk-overlay-pane :is(button,[role="menuitem"]):has-text("Original")'
                                ).last
                                if await sub_pop.count():
                                    await sub_pop.click(timeout=4000)
                            dl_obj = await dinfo.value
                            await dl_obj.save_as(str(out_mp4))
                            downloaded = out_mp4.exists() and out_mp4.stat().st_size >= 50_000
                        except Exception:
                            pass
                    if not downloaded:
                        modal_urls = await page.evaluate(
                            "() => Array.from(document.querySelectorAll('video')).map(v => v.currentSrc || v.src || '').filter(u => u && u.startsWith('http'))"
                        )
                except Exception:
                    pass
                finally:
                    await page.keyboard.press("Escape")
                    if "/edit/" in (page.url or "") and proj_page_url:
                        try:
                            await page.goto(proj_page_url, wait_until="domcontentloaded", timeout=20000)
                        except Exception:
                            await page.go_back()
                    await page.wait_for_timeout(500)

            if not downloaded:
                cand_urls: list[str] = []
                for u in [*(cur[0]["vids"] if cur and cur[0].get("vids") else []), *modal_urls, *reversed(net_video_urls)]:
                    if u and u not in cand_urls:
                        cand_urls.append(u)
                if not cand_urls:
                    raise RuntimeError(f"Nao foi possivel baixar MP4 gerado do Flow para {out_mp4.name}")
                last_http_info = ""
                for u in cand_urls:
                    try:
                        resp = await page.context.request.get(u, timeout=120000)
                        if not resp.ok:
                            last_http_info = f"HTTP {resp.status}"
                            continue
                        body = await resp.body()
                        if len(body) < 50_000:
                            last_http_info = f"payload curto ({len(body)}B)"
                            continue
                        out_mp4.write_bytes(body)
                        downloaded = True
                        break
                    except Exception as fetch_exc:
                        last_http_info = str(fetch_exc)[:120]
                if not downloaded:
                    raise RuntimeError(f"Falha ao baixar MP4 valido (>=50KB) do Flow para {out_mp4.name}: {last_http_info}")

        if not out_mp4.exists() or out_mp4.stat().st_size < 50_000:
            out_mp4.unlink(missing_ok=True)
            raise RuntimeError(f"Arquivo MP4 baixado do Flow veio vazio/corrompido para {out_mp4.name}")

        return {
            "ok": True,
            "kind": "video",
            "path": str(out_mp4),
            "bytes": out_mp4.stat().st_size,
            "tile_aria": ready_tile["aria"],
            "attached": attached,
            "mode": summary,
            "elapsed_s": round(time.time() - t0, 1),
        }
    finally:
        page.remove_listener("response", on_resp)
