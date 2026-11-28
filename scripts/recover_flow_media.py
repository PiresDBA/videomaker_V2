# -*- coding: utf-8 -*-
"""Recupera videos e imagens ja gerados nas contas Google Flow e audita contra o script_v2.json."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import re
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.flow_accounts import (  # noqa: E402
    FlowAccountLock,
    cdp_is_alive,
    check_needs_google_login,
    detect_logged_email,
    ensure_account_cdp,
    ensure_flow_project,
    load_accounts_config,
    release_account_chrome,
)
from core.logging_manager import log_flow_event  # noqa: E402
from core.media_studio import detect_split_collage, fit_aspect_jpeg  # noqa: E402
from core.scene_auditor import _encode_vision_jpeg_b64, _extract_video_keyframes  # noqa: E402
from core.script_engine import _get_google_keys, normalize_script_records  # noqa: E402


async def _harvest_account_tiles(
    acc: dict[str, Any],
    cfg: dict[str, Any],
    out_acc_dir: Path,
    max_videos: int = 0,
    max_images: int = 0,
    include_images: bool = True,
) -> list[dict[str, Any]]:
    from playwright.async_api import async_playwright

    port = int(acc["cdp_port"])
    if not cdp_is_alive(port):
        return []

    vids_dir = out_acc_dir / "videos"
    imgs_dir = out_acc_dir / "images"
    vids_dir.mkdir(parents=True, exist_ok=True)
    imgs_dir.mkdir(parents=True, exist_ok=True)
    harvested: list[dict[str, Any]] = []

    async with async_playwright() as pw:
        b = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=10000)
        try:
            ctx = b.contexts[0]
            page = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or await ctx.new_page()
            await page.set_viewport_size({"width": 1600, "height": 920})
            await page.goto("https://flow.google.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2500)
            if await check_needs_google_login(page):
                print(f"[RecoverFlow] {acc['id']} deslogada; pulando.", flush=True)
                return []
            email = await detect_logged_email(page)

            # Descobre TODOS os projetos da conta na pagina inicial do Flow
            project_urls: list[str] = []
            seen_projs: set[str] = set()
            try:
                for _ in range(4):
                    await page.mouse.wheel(0, 1200)
                    await page.wait_for_timeout(500)
                links = await page.evaluate(
                    "() => Array.from(document.querySelectorAll('a[href*=\"/project/\"]')).map(a => a.getAttribute('href') || '')"
                )
                for href in links or []:
                    if not href:
                        continue
                    full_u = href if href.startswith("http") else f"https://flow.google.com{href}"
                    m_proj = re.search(r"(https://flow\.google\.com(?:/u/\d+)?/project/[0-9a-fA-F-]+)", full_u)
                    norm_u = m_proj.group(1) if m_proj else full_u.split("?")[0].rstrip("/")
                    if "/project/" in norm_u and norm_u not in seen_projs:
                        seen_projs.add(norm_u)
                        project_urls.append(norm_u)
            except Exception:
                pass
            cfg_proj = (acc.get("project_url") or "").strip().split("?")[0].rstrip("/")
            if cfg_proj and cfg_proj not in seen_projs:
                seen_projs.add(cfg_proj)
                project_urls.append(cfg_proj)
            if not project_urls:
                fallback_u = await ensure_flow_project(page, acc, cfg)
                if fallback_u:
                    project_urls.append(fallback_u)
            print(f"[RecoverFlow] {acc['id']} ({email}): {len(project_urls)} projeto(s) encontrado(s).", flush=True)

            async def _click_grid_filter(label: str) -> bool:
                labels = (label, "Videos") if label == "Vídeos" else (label,)
                for lbl in labels:
                    for sel in (
                        f'button[role="tab"]:has-text("{lbl}")',
                        f'[role="tab"]:has-text("{lbl}")',
                        f'button:has-text("{lbl}")',
                        f'mat-chip-option:has-text("{lbl}")',
                    ):
                        loc = page.locator(sel)
                        cnt = await loc.count()
                        for i in range(min(cnt, 8)):
                            el = loc.nth(i)
                            try:
                                box = await el.bounding_box()
                                if box and box["y"] < 420 and await el.is_visible():
                                    await el.click(timeout=3000)
                                    await page.wait_for_timeout(1200)
                                    return True
                            except Exception:
                                pass
                return False

            async def _collect_tiles(max_scrolls: int = 40) -> list[dict[str, Any]]:
                prev_cnt = -1
                stable = 0
                for _ in range(max_scrolls):
                    await page.mouse.wheel(0, 1600)
                    await page.wait_for_timeout(600)
                    cur_cnt = await page.locator("flow-grid-tile-container").count()
                    if cur_cnt == prev_cnt:
                        stable += 1
                        if stable >= 2:
                            break
                    else:
                        stable = 0
                        prev_cnt = cur_cnt
                await page.evaluate("() => window.scrollTo(0, 0)")
                await page.wait_for_timeout(800)
                return await page.evaluate(
                    """() => Array.from(document.querySelectorAll('flow-grid-tile-container')).map((t, idx) => ({
                        idx,
                        aria: t.getAttribute('aria-label') || '',
                        txt: (t.innerText || '').trim(),
                        has_more: !!t.querySelector('button[aria-label="Mais opções"]'),
                        imgs: Array.from(t.querySelectorAll('img')).map(i => ({
                            src: i.src || '', w: i.naturalWidth || 0, h: i.naturalHeight || 0
                        })),
                        vids: Array.from(t.querySelectorAll('video')).map(v => v.currentSrc || v.src || '').filter(Boolean),
                    }))"""
                )

            vid_count = 0
            img_count = 0
            for proj_idx, proj_url in enumerate(project_urls, 1):
                if max_videos > 0 and vid_count >= max_videos and (not include_images or (max_images > 0 and img_count >= max_images)):
                    break
                proj_short = proj_url.rstrip("/").split("/")[-1][:8]
                try:
                    await page.goto(proj_url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)
                except Exception:
                    continue
                dash = page.locator('mat-nav-list button:has-text("dashboard")').first
                if await dash.count():
                    try:
                        await dash.click(timeout=3000)
                        await page.wait_for_timeout(700)
                    except Exception:
                        pass
                try:
                    await page.wait_for_selector("flow-grid-tile-container", timeout=8000)
                except Exception:
                    pass

                # Fase A: Filtro Vídeos (prioridade maxima para recuperar todos os Veo)
                vid_filtered = await _click_grid_filter("Vídeos")
                video_tiles = await _collect_tiles(max_scrolls=40)
                print(
                    f"[RecoverFlow] {acc['id']} proj {proj_idx}/{len(project_urls)} ({proj_short}) "
                    f"[filtro Vídeos={vid_filtered}]: {len(video_tiles)} tiles.",
                    flush=True,
                )

                for t in video_tiles:
                    if max_videos > 0 and vid_count >= max_videos:
                        break
                    txt = t.get("txt") or ""
                    aria = t.get("aria") or ""
                    is_video = vid_filtered or ("play_circle" in txt) or bool(t.get("vids"))
                    if not is_video or re.search(r"\b\d+%", txt):
                        continue
                    key_seed = aria or "|".join(im["src"] for im in t.get("imgs", [])) or f"{acc['id']}_{proj_short}_v_{t['idx']}"
                    short_hash = hashlib.sha1(key_seed.encode("utf-8", errors="ignore")).hexdigest()[:10]
                    out_mp4 = vids_dir / f"{acc['id']}_{proj_short}_vid_{t['idx']:02d}_{short_hash}.mp4"
                    if not (out_mp4.exists() and out_mp4.stat().st_size > 80_000):
                        tile_loc = page.locator("flow-grid-tile-container").nth(int(t["idx"]))
                        downloaded = False
                        try:
                            await tile_loc.scroll_into_view_if_needed()
                            await tile_loc.hover()
                            await page.wait_for_timeout(650)
                            mb = tile_loc.locator('button[aria-label="Mais opções"]').first
                            if await mb.count():
                                await mb.click(timeout=4000, force=True)
                                await page.wait_for_timeout(650)
                                dl_item = page.locator(
                                    '.cdk-overlay-pane :is(button,[role="menuitem"]):has-text("Fazer o download")'
                                ).first
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
                                    downloaded = out_mp4.exists() and out_mp4.stat().st_size > 80_000
                        except Exception:
                            await page.keyboard.press("Escape")

                        if not downloaded:
                            vid_urls = list(t.get("vids") or [])
                            if not vid_urls:
                                proj_grid_url = page.url or ""
                                try:
                                    await tile_loc.scroll_into_view_if_needed()
                                    await tile_loc.click(timeout=4000, force=True)
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
                                            downloaded = out_mp4.exists() and out_mp4.stat().st_size > 80_000
                                        except Exception:
                                            pass
                                    if not downloaded:
                                        vid_urls = await page.evaluate(
                                            "() => Array.from(document.querySelectorAll('video')).map(v => v.currentSrc || v.src || '').filter(u => u && u.startsWith('http'))"
                                        )
                                except Exception:
                                    pass
                                finally:
                                    await page.keyboard.press("Escape")
                                    if "/edit/" in (page.url or "") and proj_grid_url:
                                        try:
                                            await page.goto(proj_grid_url, wait_until="domcontentloaded", timeout=20000)
                                        except Exception:
                                            await page.go_back()
                                        try:
                                            await page.wait_for_selector("flow-grid-tile-container", timeout=8000)
                                        except Exception:
                                            pass
                                    await page.wait_for_timeout(600)
                            if not downloaded and vid_urls:
                                try:
                                    resp = await page.context.request.get(vid_urls[-1], timeout=90000)
                                    if resp.ok:
                                        out_mp4.write_bytes(await resp.body())
                                except Exception:
                                    pass
                    if out_mp4.exists() and out_mp4.stat().st_size > 80_000:
                        vid_count += 1
                        harvested.append({
                            "kind": "video",
                            "account_id": acc["id"],
                            "email": email,
                            "tile_idx": t["idx"],
                            "aria": aria[:240],
                            "path": str(out_mp4),
                            "bytes": out_mp4.stat().st_size,
                        })
                    else:
                        out_mp4.unlink(missing_ok=True)

                # Fase B: Filtro Imagens (ou volta para Todas) para recuperar imagens limpas
                if include_images:
                    await _click_grid_filter("Imagens")
                    img_tiles = await _collect_tiles(max_scrolls=40)
                    for t in img_tiles:
                        if max_images > 0 and img_count >= max_images:
                            break
                        txt = t.get("txt") or ""
                        aria = t.get("aria") or ""
                        if ("play_circle" in txt) or bool(t.get("vids")):
                            continue
                        big_imgs = [im for im in t.get("imgs", []) if im["src"].startswith("http") and im["w"] >= 800]
                        if not big_imgs:
                            continue
                        key_seed = aria or big_imgs[0]["src"]
                        short_hash = hashlib.sha1(key_seed.encode("utf-8", errors="ignore")).hexdigest()[:10]
                        out_jpg = imgs_dir / f"{acc['id']}_{proj_short}_img_{t['idx']:02d}_{short_hash}.jpg"
                        if not (out_jpg.exists() and out_jpg.stat().st_size > 15_000):
                            try:
                                resp = await page.context.request.get(big_imgs[0]["src"], timeout=45000)
                                if resp.ok:
                                    data = await resp.body()
                                    im = Image.open(io.BytesIO(data)).convert("RGB")
                                    if im.width >= im.height:
                                        fit_aspect_jpeg(_save_tmp_bytes(out_jpg, data), out_jpg)
                            except Exception:
                                out_jpg.unlink(missing_ok=True)
                        if out_jpg.exists() and out_jpg.stat().st_size > 15_000 and detect_split_collage(out_jpg) == 1:
                            img_count += 1
                            harvested.append({
                                "kind": "image",
                                "account_id": acc["id"],
                                "email": email,
                                "tile_idx": t["idx"],
                                "aria": aria[:240],
                                "path": str(out_jpg),
                                "bytes": out_jpg.stat().st_size,
                            })
        finally:
            await b.close()
    return harvested


def _save_tmp_bytes(dst: Path, raw: bytes) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(raw)
    return dst


def _match_and_audit_media_against_script(
    item: dict[str, Any],
    script_data: dict[str, Any],
    anchor_prop_image: Path | None = None,
) -> dict[str, Any]:
    """Audita um video/imagem recuperado e identifica a qual cena do script_v2 ele pertence."""
    p = Path(item["path"])
    if item["kind"] == "video":
        with tempfile.TemporaryDirectory() as td:
            frames = _extract_video_keyframes(p, Path(td), p.stem, count=3)
            if not frames:
                return {"approved": False, "reason": "sem keyframes validos"}
            return _vision_match_scene(frames, script_data, anchor_prop_image, item.get("aria", ""))
    else:
        if detect_split_collage(p) > 1:
            return {"approved": False, "reason": "colagem detectada"}
        return _vision_match_scene([p], script_data, anchor_prop_image, item.get("aria", ""))


def _vision_match_scene(
    frames: list[Path],
    script_data: dict[str, Any],
    anchor_prop_image: Path | None,
    tile_hint: str = "",
) -> dict[str, Any]:
    keys = _get_google_keys()
    if not keys:
        return {"approved": False, "reason": "sem chave Google para Vision"}

    scenes_summary = "\n".join(
        f"- {sc['scene_id']}: speaker={sc.get('speaker')} | chars={sc.get('characters')} | "
        f"text=\"{sc.get('text')}\" | action=\"{sc.get('visual_action')}\""
        for sc in script_data.get("scenes", [])
    )
    props_desc = "; ".join(
        f"{pr.get('name')}: {pr.get('description')}"
        for pr in (script_data.get("story_props") or [])
        if isinstance(pr, dict)
    )
    prompt = (
        "You are an animation continuity auditor matching recovered Flow media against an episode script.\n"
        f"Tile Hint / Prompt Fragment: {tile_hint}\n"
        "STRICT RULES:\n"
        "- Frida MUST be a soft fawn golden-tan young English bulldog puppy with white pearl necklace & small gold paw pendant (NEVER Golden Retriever, NEVER black-and-white spotted).\n"
        "- Luna MUST be a dark chocolate-brown young miniature dachshund puppy with tan markings and double gold heart chain (NEVER Cocker Spaniel, NEVER random breed).\n"
        "- Background competitor dogs ARE allowed ONLY if the matched race/competition scene mentions multiple dogs/competitors (e.g. 'vários cães', 'corrida'), while Frida & Luna remain recognizable in the foreground. NEVER allow literal red furry monster creatures.\n"
        + (
            f"- VIDEO KEYFRAMES AUDIT: The {len(frames)} attached images are sequential snapshots from ONE continuous video — NEVER treat them as a collage.\n"
            if len(frames) > 1
            else ""
        )
        + (f"- Story Objects (apply ONLY to scenes where that object appears/is mentioned; do NOT reject other scenes for not showing it): {props_desc}\n" if props_desc else "")
        + ("The LAST image attached is the reference anchor portrait for the story's key object/prop (relevant only to scenes featuring that prop).\n" if anchor_prop_image and anchor_prop_image.exists() else "")
        + "- YOUTUBE ENDING / CTA EXCEPTION: For the FINAL closing/CTA scene (e.g. the last scene mentioning 'inscreva-se', 'curta', 'compartilhe', 'subscribe', 'próximo vídeo'), intentional 'SUBSCRIBE' / 'INSCREVA-SE' text, YouTube logo, and like/play/bell icons ARE INTENTIONAL AND ALLOWED (set approved=true if characters & ending mood fit).\n"
        + f"\nCandidate Scenes:\n{scenes_summary}\n\n"
        "Identify if this media cleanly matches ONE of the candidate scenes AND passes all breed/object/quality rules (no collage, no unwanted watermark/text except the allowed ending CTA/subscribe overlays on the final scene).\n"
        "Respond ONLY in JSON (confidence MUST be a float strictly on a 0.0 to 1.0 scale, e.g. 0.95 — NOT 0 to 10 or 0 to 100): "
        '{"approved": bool, "best_scene_id": "sc_XX or empty", "confidence": 0.95, "reason": "short summary in PT"}'
    )
    parts: list[dict[str, Any]] = [{"text": prompt}]
    for fp in frames[:3]:
        parts.append({"inlineData": {"mimeType": "image/jpeg", "data": _encode_vision_jpeg_b64(fp)}})
    if anchor_prop_image and anchor_prop_image.exists() and anchor_prop_image not in frames:
        parts.append({"inlineData": {"mimeType": "image/jpeg", "data": _encode_vision_jpeg_b64(anchor_prop_image)}})

    payload = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }).encode("utf-8")

    import time as _time
    for round_idx in range(2):
        for model in ("gemini-3.1-flash-lite-preview", "gemini-3-flash-preview"):
            for key in keys:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(key)}"
                )
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                try:
                    with urllib.request.urlopen(req, timeout=28) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    res = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
                    if isinstance(res, list):
                        res = next((x for x in res if isinstance(x, dict)), {})
                    if not isinstance(res, dict):
                        continue
                    conf = float(res.get("confidence") or 0.0)
                    if conf > 1.0:
                        conf = round(conf / (10.0 if conf <= 10.0 else 100.0), 3)
                    res["confidence"] = conf
                    return res
                except Exception:
                    _time.sleep(0.4)
                    continue
        if round_idx == 0:
            _time.sleep(2.5)
    return {"approved": False, "best_scene_id": "", "confidence": 0.0, "reason": "Vision QA indisponivel"}


async def recover_and_audit(
    proj_dir: Path,
    legacy_dir: Path | None = None,
    apply_reuse: bool = True,
    local_only: bool = False,
    launch_closed: bool = True,
    min_confidence: float = 0.75,
    accounts_filter: set[str] | None = None,
    videos_only: bool = False,
    max_videos: int = 0,
    skip_cached_work: bool = False,
) -> dict[str, Any]:
    script_data = normalize_script_records(
        json.loads((proj_dir / "artifacts" / "script_v2.json").read_text(encoding="utf-8"))
    )
    work_rec = proj_dir / "work" / "flow_recovered"
    work_rec.mkdir(parents=True, exist_ok=True)
    cfg = load_accounts_config()

    harvested: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    if not local_only:
        for acc in cfg.get("accounts", []):
            if accounts_filter and acc["id"] not in accounts_filter:
                continue
            port = int(acc["cdp_port"])
            opened_here = False
            try:
                with FlowAccountLock(port, slug=proj_dir.name, kind="recover", wait=False):
                    if not cdp_is_alive(port):
                        if not launch_closed:
                            log_flow_event("offline_skipped", acc["id"], stage="recover", project=proj_dir.name)
                            continue
                        ensure_account_cdp(acc, wait_s=18, purpose="recover", project_name=proj_dir.name)
                        opened_here = True
                    items = await _harvest_account_tiles(
                        acc,
                        cfg,
                        work_rec / acc["id"],
                        max_videos=max_videos,
                        include_images=not videos_only,
                    )
                    for it in items:
                        rp = str(Path(it["path"]).resolve())
                        if rp not in seen_paths:
                            seen_paths.add(rp)
                            harvested.append(it)
            except Exception as exc:
                err_low = str(exc).lower()
                event = "busy" if any(token in err_low for token in ("em uso", "aguardando liberacao", "ocupada", "busy")) else "attempt_failed"
                log_flow_event(event, acc["id"], stage="recover", project=proj_dir.name, error=str(exc)[:500])
                print(f"[RecoverFlow] Falha/ocupacao em {acc['id']}: {exc}", flush=True)
            finally:
                # A recuperacao varre todas as contas, mas uma por vez: fecha a que
                # abriu antes de iniciar a seguinte. Chrome preexistente e preservado.
                if opened_here:
                    release_account_chrome(acc, reason="recover_account_finished")

    # Inclui tambem videos/imagens ja baixados previamente em work/flow_recovered/<acc_id>
    if not skip_cached_work:
        for acc_dir in sorted(work_rec.iterdir()):
            if not acc_dir.is_dir():
                continue
            if accounts_filter and acc_dir.name not in accounts_filter:
                continue
            for mp4 in sorted((acc_dir / "videos").glob("*.mp4")):
                rp = str(mp4.resolve())
                if rp not in seen_paths and mp4.stat().st_size > 80_000:
                    seen_paths.add(rp)
                    harvested.append({
                        "kind": "video",
                        "account_id": acc_dir.name,
                        "email": "",
                        "tile_idx": -1,
                        "aria": mp4.stem,
                        "path": str(mp4),
                        "bytes": mp4.stat().st_size,
                    })
            if not videos_only:
                for jpg in sorted((acc_dir / "images").glob("*.jpg")):
                    rp = str(jpg.resolve())
                    if rp not in seen_paths and jpg.stat().st_size > 15_000:
                        seen_paths.add(rp)
                        harvested.append({
                            "kind": "image",
                            "account_id": acc_dir.name,
                            "email": "",
                            "tile_idx": -1,
                            "aria": jpg.stem,
                            "path": str(jpg),
                            "bytes": jpg.stat().st_size,
                        })

        if not videos_only and legacy_dir and legacy_dir.exists():
            for mp4 in sorted((legacy_dir / "assets" / "images" / "gemini" / "scenes").glob("*.mp4")):
                rp = str(mp4.resolve())
                if rp not in seen_paths and mp4.stat().st_size > 80_000:
                    seen_paths.add(rp)
                    harvested.append({
                        "kind": "video",
                        "account_id": "legacy",
                        "email": "",
                        "tile_idx": -1,
                        "aria": mp4.stem,
                        "path": str(mp4),
                        "bytes": mp4.stat().st_size,
                    })

    harvested.sort(key=lambda x: 0 if x["kind"] == "video" else 1)

    chars_dir = proj_dir / "assets" / "characters"
    anchor: Path | None = None
    for pr in (script_data.get("story_props") or []):
        if isinstance(pr, dict) and pr.get("name"):
            safe_slug = re.sub(r"[^a-z0-9]+", "_", str(pr["name"]).strip().lower()).strip("_") or "objeto"
            cand = chars_dir / f"{safe_slug}_portrait.jpg"
            if cand.exists() and cand.stat().st_size > 10_000:
                anchor = cand
                break
    videos_dir = proj_dir / "assets" / "videos"
    images_dir = proj_dir / "assets" / "images"
    videos_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    reused_videos: dict[str, str] = {}
    reused_images: dict[str, str] = {}
    best_videos: dict[str, tuple[float, dict[str, Any]]] = {}
    best_images: dict[str, tuple[float, dict[str, Any]]] = {}
    audited_rows: list[dict[str, Any]] = []

    for it in harvested:
        res = _match_and_audit_media_against_script(it, script_data, anchor)
        sid = str(res.get("best_scene_id") or "").strip()
        conf = float(res.get("confidence") or 0.0)
        ok = bool(res.get("approved")) and bool(sid) and (conf >= min_confidence)
        row = {**it, "audit": res}
        audited_rows.append(row)
        print(
            f"  [RECOVER-{it['kind'].upper()}] {Path(it['path']).name} ({it['account_id']}) -> "
            f"scene={sid or '-'} | conf={conf:.2f} | approved={ok} | {res.get('reason', '')}",
            flush=True,
        )
        if ok:
            target_map = best_videos if it["kind"] == "video" else best_images
            prev = target_map.get(sid)
            if prev is None or conf > prev[0]:
                target_map[sid] = (conf, it)

    if apply_reuse:
        for sid, (_conf, it) in sorted(best_videos.items()):
            dst = videos_dir / f"{sid}.mp4"
            if not (dst.exists() and dst.stat().st_size > 80_000):
                shutil.copy2(it["path"], dst)
            reused_videos[sid] = str(dst)
        for sid, (_conf, it) in sorted(best_images.items()):
            dst = images_dir / f"{sid}_p1.jpg"
            if not dst.exists():
                shutil.copy2(it["path"], dst)
            reused_images[sid] = str(dst)

    rep = {
        "total_harvested": len(harvested),
        "videos_harvested": sum(1 for x in harvested if x["kind"] == "video"),
        "images_harvested": sum(1 for x in harvested if x["kind"] == "image"),
        "reused_videos_count": len(reused_videos),
        "reused_videos": reused_videos,
        "reused_images_count": len(reused_images),
        "reused_images": reused_images,
        "items": audited_rows,
    }
    rep_path = proj_dir / "artifacts" / "flow_recovery_report.json"
    rep_path.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    return rep


def main() -> int:
    ap = argparse.ArgumentParser(description="Recupera e audita videos/imagens ja gerados no Google Flow.")
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--legacy-dir", default="")
    ap.add_argument("--no-apply", action="store_true", help="Apenas baixa e audita, sem copiar para assets/")
    ap.add_argument("--local-only", action="store_true", help="Audita apenas arquivos ja baixados em work/flow_recovered")
    ap.add_argument("--launch-closed", action="store_true", help="Abre contas com Chrome CDP fechado antes de coletar")
    ap.add_argument("--min-confidence", type=float, default=0.75, help="Confianca minima (0.0-1.0) para reaproveitar")
    ap.add_argument("--accounts", default="", help="Lista separada por virgula de contas Flow (ex: acc_5)")
    ap.add_argument("--videos-only", action="store_true", help="Coleta/audita apenas videos (pula aba Imagens)")
    ap.add_argument("--max-videos", type=int, default=0, help="Limite de tiles de video coletados por conta (0 = ilimitado)")
    ap.add_argument("--skip-cached-work", action="store_true", help="Audita somente itens coletados nesta execucao")
    args = ap.parse_args()

    acc_set = {a.strip() for a in str(args.accounts or "").split(",") if a.strip()} or None
    rep = asyncio.run(
        recover_and_audit(
            proj_dir=Path(args.project_dir),
            legacy_dir=(Path(args.legacy_dir) if args.legacy_dir else None),
            apply_reuse=not args.no_apply,
            local_only=args.local_only,
            launch_closed=args.launch_closed,
            min_confidence=args.min_confidence,
            accounts_filter=acc_set,
            videos_only=args.videos_only,
            max_videos=args.max_videos,
            skip_cached_work=args.skip_cached_work,
        )
    )
    print(
        f"\nResumo Recuperacao Flow: {rep['videos_harvested']} videos + {rep['images_harvested']} imagens coletadas | "
        f"Reaproveitados aprovados: {rep['reused_videos_count']} videos, {rep['reused_images_count']} imagens.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
