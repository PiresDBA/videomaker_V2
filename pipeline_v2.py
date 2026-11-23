# -*- coding: utf-8 -*-
"""Motor Unico e Autocontido do Videomaker v2 (Novo Episodio, Legados 30+, Dual-Avatar & Auto-Auditoria)."""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from config import (
    CHIRP3_MONTHLY_CHAR_LIMIT,
    CPU_WORKERS,
    MAX_IMAGE_SECONDS,
    PROJECTS_DIR,
    SCRIPT_MAX_WORDS,
    SCRIPT_MIN_WORDS,
    SHORT_TARGET_SECONDS,
    TARGET_VEO_VIDEOS,
)
import core.pacing_planner as _pacing_mod
import core.self_audit as _audit_mod
from core.avatar_studio import build_luna_avatar_pack
from core.flow_accounts import FlowStageWatchdog, cdp_is_alive, load_accounts_config
from core.flow_continuity import FLOW_YOUTHFUL_PUPPY_STYLE_PREFIX
from core.legacy_auditor import batch_scan_legacy_root, import_and_upgrade_legacy
from core.media_studio import (
    generate_images_for_plan,
    generate_prompts_for_script,
    generate_thumbnail_variants,
    generate_veo_videos_for_episode,
    select_veo_scenes,
)
from core.motion_shorts import export_3_shorts_pack
from core.pacing_planner import build_pacing_plan
from core.scene_auditor import generate_and_audit_scenes
from core.script_engine import generate_script, normalize_script_records, validate_script_schema
from core.self_audit import run_final_audit
from core.video_assembler import assemble_video, export_short_9_16
from core.voice_studio import (
    _load_chirp3_usage,
    _synthesize_chirp3_hd,
    authenticate_chirp3_oauth,
    synthesize_all_scenes,
)
from core.youtube_publisher import publish_episode_youtube_pt, publish_shorts_pack_youtube_pt


def slugify(text: str, max_len: int = 44) -> str:
    norm = unicodedata.normalize("NFKD", (text or "projeto").lower().strip())
    ascii_txt = "".join(c for c in norm if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_txt).strip("-")
    return slug[:max_len].strip("-") or "projeto"


def should_generate_new_veo(
    skip_veo: bool,
    target_veo: int,
    existing_base_sids: list[str] | set[str],
    force: bool = False,
) -> bool:
    """Trava anti-regeneracao (melhorias): se ja ha videos no disco, NAO gera novos.

    So gera novos se nao existir nenhum video E nao for pedido --skip-veo.
    `--force` e a unica escapatoria para regenerar de proposito (Regra 25).
    """
    if skip_veo or target_veo <= 0:
        return False
    if existing_base_sids and not force:
        return False
    return True


def run_pipeline(args: argparse.Namespace) -> int:
    if args.batch_scan:
        rows = batch_scan_legacy_root(Path(args.batch_scan))
        out_rep = PROJECTS_DIR.parent / "legacy_batch_audit.json"
        out_rep.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Batch scan concluido: {len(rows)} projetos -> {out_rep}")
        for r in rows:
            print(f"  - {r['project']:48s} | palavras={r['words']:4d} | imgs_ok={r['images_usable']:2d} | colagem={r['images_collage']:2d} | acoes={len(r['recommended_actions'])}")
        return 0

    if args.build_avatar:
        created = build_luna_avatar_pack()
        print("Avatar Luna gerado/atualizado:", {k: str(v) for k, v in created.items()})
        if args.stage == "avatar-only":
            return 0

    if getattr(args, "auth_chirp3", False):
        import tempfile

        tok_path, proj_id = authenticate_chirp3_oauth()
        print(f"Chirp 3 HD OAuth2 OK: token={tok_path} | quota_project={proj_id or '-'}", flush=True)
        with tempfile.TemporaryDirectory() as td:
            for spk in ("narrador", "frida", "luna"):
                out_mp3 = Path(td) / f"smoke_{spk}.mp3"
                used_v, _ = _synthesize_chirp3_hd("Oi! Tudo pronto!", spk, out_mp3)
                print(f"  [Chirp3-Smoke] {spk:8s} -> {used_v} ({out_mp3.stat().st_size} bytes)", flush=True)
        usage = _load_chirp3_usage()
        print(f"Uso mensal Chirp 3 HD: {usage.get('chars_used', 0)}/{CHIRP3_MONTHLY_CHAR_LIMIT} caracteres", flush=True)
        return 0

    if getattr(args, "flow_accounts_status", False):
        import asyncio
        from core.flow_accounts import inspect_all_accounts_status

        rows = asyncio.run(inspect_all_accounts_status())
        print("\n=== CONTAS GOOGLE FLOW (POOL FAILOVER) ===")
        for r in rows:
            print(
                f"  - {r['id']} (:{r['port']}) | cdp={'ON' if r['cdp_alive'] else 'OFF'} "
                f"| login={'OK' if r['logged_in'] else 'NAO'} | {r['email'] or '-'} "
                f"| restam ~{r['credits_remaining_est']}/50 cred | chars={r['characters']}"
            )
        return 0

    if getattr(args, "setup_flow_account", ""):
        import asyncio
        from core.flow_accounts import (
            check_needs_google_login,
            detect_logged_email,
            ensure_account_cdp,
            ensure_flow_project,
            mark_account_usage,
        )
        from playwright.async_api import async_playwright

        cfg = load_accounts_config()
        target = next((a for a in cfg["accounts"] if a["id"] == args.setup_flow_account), None)
        if target is None:
            raise ValueError(f"Conta desconhecida: {args.setup_flow_account}")
        cdp = ensure_account_cdp(target)
        print(f"Janela Chrome aberta para {target['id']} em {cdp} (perfil {target['profile_dir']}).")
        print("Faca login na conta Google no navegador se solicitado; verificando status...")

        async def _probe():
            async with async_playwright() as pw:
                b = await pw.chromium.connect_over_cdp(cdp, timeout=10000)
                ctx = b.contexts[0]
                pg = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or await ctx.new_page()
                await pg.goto("https://flow.google.com/", wait_until="domcontentloaded", timeout=30000)
                await pg.wait_for_timeout(2500)
                need = await check_needs_google_login(pg)
                em = await detect_logged_email(pg)
                if not need:
                    await ensure_flow_project(pg, target, cfg)
                    mark_account_usage(target["id"], credits_delta=0, email=em)
                await b.close()
                return need, em, target.get("project_url", "")

        need, em, purl = asyncio.run(_probe())
        print(f"Conta {target['id']}: login={'PENDENTE (faça login na janela aberta)' if need else 'OK'} | email={em} | projeto={purl}")
        return 0

    if getattr(args, "learn_flow_accounts", False):
        import asyncio
        from core.flow_accounts import interactive_learn_accounts_wizard

        ids = [x.strip() for x in args.flow_account_ids.split(",") if x.strip()] if getattr(args, "flow_account_ids", "") else None
        saved = asyncio.run(interactive_learn_accounts_wizard(ids))
        print(f"\nModo aprendizado concluido: {len(saved)} sessoes aprendidas e guardadas em flow_learned_sessions.json.")
        return 0

    if getattr(args, "save_learned_session", ""):
        import asyncio
        from core.flow_accounts import capture_learned_session

        rec = asyncio.run(capture_learned_session(args.save_learned_session, auto_seed_refs=True))
        print("Sessao aprendida e salva:", json.dumps(rec, ensure_ascii=False, indent=2))
        return 0

    if getattr(args, "max_clip_seconds", None):
        _pacing_mod.MAX_IMAGE_SECONDS = float(args.max_clip_seconds)
        _audit_mod.MAX_IMAGE_SECONDS = float(args.max_clip_seconds)

    if args.legacy_dir:
        leg = Path(args.legacy_dir)
        slug = args.slug or slugify(leg.name)
    else:
        slug = args.slug or slugify(args.prompt or Path(args.script_file).stem)

    proj_dir = PROJECTS_DIR / slug
    artifacts_dir = proj_dir / "artifacts"
    images_dir = proj_dir / "assets" / "images"
    videos_dir = proj_dir / "assets" / "videos"
    audio_dir = proj_dir / "assets" / "audio"
    work_dir = proj_dir / "work"
    output_dir = proj_dir / "output"
    thumbs_dir = output_dir / "thumbs"
    for d in (artifacts_dir, images_dir, videos_dir, audio_dir, work_dir, output_dir, thumbs_dir):
        d.mkdir(parents=True, exist_ok=True)

    script_path = artifacts_dir / "script_v2.json"
    prompts_path = artifacts_dir / "image_prompts_v2.json"
    timings_path = artifacts_dir / "tts_timings_v2.json"
    pacing_path = artifacts_dir / "pacing_plan_v2.json"
    meta_path = artifacts_dir / "youtube_metadata_v2.json"

    # 1. ROTEIRO / IMPORTACAO DE LEGADO
    if args.legacy_dir and (not script_path.exists() or args.force):
        imp = import_and_upgrade_legacy(
            Path(args.legacy_dir),
            proj_dir,
            reuse_clean_images=True,
            vision_filter=True,
            force=args.force,
        )
        print(f"Legado importado: {imp['images_reused']} imagens limpas reaproveitadas | acoes={imp['audit']['recommended_actions']}")
        script_data = normalize_script_records(json.loads(script_path.read_text(encoding="utf-8")))
    elif args.script_file:
        raw = json.loads(Path(args.script_file).read_text(encoding="utf-8"))
        script_data = normalize_script_records(raw)
        errs = validate_script_schema(script_data, min_words=args.min_words, max_words=args.max_words)
        if errs:
            raise ValueError("Roteiro invalido:\n - " + "\n - ".join(errs))
        script_path.write_text(json.dumps(script_data, ensure_ascii=False, indent=2), encoding="utf-8")
    elif script_path.exists() and not args.force:
        script_data = normalize_script_records(json.loads(script_path.read_text(encoding="utf-8")))
    else:
        if not args.prompt:
            raise ValueError("Informe --prompt, --script-file ou --legacy-dir.")
        humor_prompt = ""
        if not getattr(args, "skip_viral_research", False):
            try:
                from core.viral_research import build_prompt_section, research_viral_humor
                viral = research_viral_humor(args.prompt, artifacts_dir / "viral_research.json")
                humor_prompt = build_prompt_section(viral)
                sinais = [s.get("signal", "") for s in (viral.get("humor") or {}).get("signals", [])[:4]]
                print(
                    f"[VIRAL] {viral.get('viral_count', 0)} video(s) acima de 1M | "
                    f"estrutura: {', '.join(sinais) if sinais else 'sugestao fallback'}",
                    flush=True,
                )
            except Exception as exc:
                print(f"[VIRAL] pesquisa indisponivel ({str(exc)[:120]}); seguindo com formula padrao.", flush=True)
        script_data = generate_script(
            args.prompt, script_path,
            min_words=args.min_words, max_words=args.max_words,
            humor_prompt=humor_prompt,
        )

    if getattr(args, "target_minutes", None):
        script_data["target_minutes"] = float(args.target_minutes)
    if getattr(args, "thumb_hook", ""):
        script_data["thumb_hook"] = " ".join(args.thumb_hook.split()).upper()
    if getattr(args, "character_age_mode", "child") == "baby":
        for sc in script_data.get("scenes", []):
            if "newborn baby" not in (sc.get("visual_action") or "").lower():
                sc["visual_action"] = f"Tiny 8-week-old newborn baby puppies: {sc.get('visual_action', '')}"
    if getattr(args, "avatar_mode", "auto") != "auto":
        mode_val = args.avatar_mode
        for sc in script_data.get("scenes", []):
            sc["avatar_mode"] = mode_val
            sc["avatar_pip"] = mode_val != "none"

    meta_path.write_text(json.dumps({
        "title": script_data["title"],
        "thumb_hook": script_data["thumb_hook"],
        "description": script_data["description"],
        "tags": script_data["tags"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. PROMPTS DE IMAGEM
    generate_prompts_for_script(script_data, prompts_path)
    if args.stage == "script":
        print(f"OK script + prompts + metadados -> {script_path}")
        return 0

    # 3. TTS EMOCIONAL EMBUTIDO + PORTAO DE PROSODIA + WHISPER QA
    timings = synthesize_all_scenes(
        script_data,
        audio_dir,
        provider=args.tts_provider,
        enable_whisper_qa=not args.skip_whisper_qa,
        enable_prosody_gate=not args.skip_prosody_gate,
        allow_flat_fallback=args.allow_flat_fallback,
        force=args.force,
    )
    timings_path.write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.stage == "tts":
        return 0

    # 4. RITMO (DIVISAO <= 5s + KEN BURNS + DUAL AVATAR)
    # Regra 20: cenas que ja tem video Veo nao recebem rajada (evita movimento duplicado).
    existing_video_sids: set[str] = set()
    if videos_dir.exists():
        for vp in videos_dir.glob("*.mp4"):
            m_veo = re.match(r"^(sc_\d+)", vp.stem)
            if m_veo and vp.stat().st_size > 50_000:
                existing_video_sids.add(m_veo.group(1))
    visual_clips, final_prompts = build_pacing_plan(script_data, timings, video_scene_ids=existing_video_sids)
    pacing_path.write_text(json.dumps(visual_clips, ensure_ascii=False, indent=2), encoding="utf-8")
    prompts_path.write_text(json.dumps(final_prompts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Pacing: {len(visual_clips)} sub-clips visuais (<= 5s cada)", flush=True)
    if args.stage == "pacing":
        return 0

    # 5. IMAGENS 16:9 + AUDITORIA CENA-A-CENA (Narracao x Imagem x Personagem x Objeto) + VEO 3.1 LITE (10x 8s)
    target_veo = int(getattr(args, "veo_videos", TARGET_VEO_VIDEOS) or 0)
    flow_accounts = load_accounts_config().get("accounts", [])
    flow_cdp_alive = any(cdp_is_alive(int(a["cdp_port"])) for a in flow_accounts)
    # Detecta SEMPRE os videos Veo ja existentes para APROVEITA-LOS (Regra: nao gerar de novo).
    # `--skip-veo` so impede gerar NOVos; nunca descarta os que ja estao no disco.
    existing_veo = sorted(
        [p for p in videos_dir.glob("*.mp4") if p.stat().st_size > 50_000],
        key=lambda p: p.name,
    ) if videos_dir.exists() else []
    valid_scene_ids = {s["scene_id"] for s in script_data.get("scenes", []) if s.get("scene_id")}
    existing_base_sids: list[str] = []
    for ep in existing_veo:
        base_sid = re.sub(r"_(?:v|p)\d+$", "", ep.stem)
        if base_sid in valid_scene_ids and base_sid not in existing_base_sids:
            existing_base_sids.append(base_sid)
    if existing_base_sids:
        print(f"[VEO] Reaproveitando {len(existing_base_sids)} video(s) Veo ja existente(s): {', '.join(existing_base_sids)}", flush=True)

    veo_scene_ids: set[str] = set()
    if existing_base_sids:
        veo_scene_ids.update(existing_base_sids)

    # TRAVA ANTI-REGENERACAO: se existem videos no disco, APROVEITA e NAO gera novos.
    # So gera novos quando nao ha nenhum video E o usuario nao pediu --skip-veo.
    # (Usuario: "o video ja foi gerado, so estamos mudando vozes e imagens; pare de gerar video".)
    generate_new_veo = should_generate_new_veo(
        skip_veo=bool(getattr(args, "skip_veo", False)),
        target_veo=target_veo,
        existing_base_sids=existing_base_sids,
        force=bool(getattr(args, "force", False)),
    )
    if existing_base_sids:
        print("[VEO] TRAVA: videos existentes detectados -> NENHUM novo video sera gerado neste episodio.", flush=True)

    if generate_new_veo:
        if flow_cdp_alive:
            archived_only_sids: set[str] = set()
            if not args.force and (videos_dir / "_archive").exists():
                for ap in (videos_dir / "_archive").glob("*.mp4"):
                    if ap.stat().st_size >= 50_000:
                        m_arch = re.match(r"^(sc_\d+)_", ap.name)
                        if m_arch and m_arch.group(1) not in existing_base_sids:
                            archived_only_sids.add(m_arch.group(1))
            # Aproveita TODAS as cenas distintas que ja tem Veo no disco (>= target_veo quando houver >10)
            for bsid in existing_base_sids:
                veo_scene_ids.add(bsid)
            for s in select_veo_scenes(script_data, visual_clips, target_count=max(target_veo, len(script_data.get("scenes", [])))):
                if len(veo_scene_ids) >= target_veo:
                    break
                if s["scene_id"] in archived_only_sids:
                    continue
                veo_scene_ids.add(s["scene_id"])
        elif len(existing_base_sids) >= target_veo:
            veo_scene_ids.update(existing_base_sids)
        elif not args.skip_images and len(existing_base_sids) < target_veo:
            raise RuntimeError(
                f"Nenhuma conta Google Flow CDP ativa para gerar os {target_veo} videos Veo 3.1 Lite obrigatorios "
                f"(use --skip-veo apenas se quiser modo somente imagem)."
            )

    if not args.skip_images:
        recovery_rep_path = artifacts_dir / "flow_recovery_report.json"
        if flow_cdp_alive and (args.force or not recovery_rep_path.exists()):
            try:
                import asyncio as _asyncio
                from scripts.recover_flow_media import recover_and_audit

                print(
                    "[FlowRecover] Varrendo TODAS as 5 contas Flow (todos os projetos, sem limite) "
                    "para reaproveitar videos e imagens antes de gerar novos...",
                    flush=True,
                )
                with FlowStageWatchdog(slug=slug, stage="flow_recover"):
                    _asyncio.run(
                        recover_and_audit(
                            proj_dir=proj_dir,
                            legacy_dir=(Path(args.legacy_dir) if args.legacy_dir else None),
                            apply_reuse=True,
                            launch_closed=True,
                            videos_only=False,
                            max_videos=0,
                        )
                    )
            except Exception as rec_exc:
                print(f"  [FlowRecover] Aviso na pre-varredura das contas Flow: {rec_exc}", flush=True)

        if not getattr(args, "skip_scene_audit", False) and FlowStageWatchdog.is_busy_by_other():
            print(
                f"[FlowMultiAccount] Conta de video em uso por outro processo; adiantando geracao e auditoria de IMAGENS "
                f"(0 creditos, ilimitadas) para '{slug}' nas outras contas Flow livres (acc_4/acc_3/acc_2)...",
                flush=True,
            )
            pre_visual_clips = [
                c for c in visual_clips
                if (c.get("scene_id") not in veo_scene_ids) or str(c.get("clip_id") or "").endswith("_p1")
            ]
            generate_and_audit_scenes(
                proj_dir=proj_dir,
                script_data=script_data,
                visual_clips=pre_visual_clips,
                prompts_manifest=final_prompts,
                images_dir=images_dir,
                videos_dir=None,
                auto_fix=True,
                max_retries=3,
                force_audit_cached=True,
                force=args.force,
                veo_scene_ids=set(),
                generate_veo_inline=False,
                strict_vision=True,
                audit_profile=getattr(args, "audit_profile", "light"),
            )
        with FlowStageWatchdog(slug=slug, stage="flow_media"):
            if not getattr(args, "skip_scene_audit", False):
                sc_audit = generate_and_audit_scenes(
                    proj_dir=proj_dir,
                    script_data=script_data,
                    visual_clips=visual_clips,
                    prompts_manifest=final_prompts,
                    images_dir=images_dir,
                    videos_dir=(videos_dir if veo_scene_ids else None),
                    auto_fix=True,
                    max_retries=3,
                    force_audit_cached=True,
                    force=args.force,
                    veo_scene_ids=veo_scene_ids,
                    # Reaproveita existentes, mas NUNCA gera novos se ja ha videos no disco.
                    generate_veo_inline=generate_new_veo,
                    veo_max_retries=2,
                    max_new_veo_per_scene=1,
                    strict_vision=True,
                    audit_profile=getattr(args, "audit_profile", "light"),
                )
                print(
                    f"Auditoria Cena-a-Cena (Imagens + Veo): APPROVED={sc_audit['approved']} | "
                    f"Veo={sc_audit['veo_videos_count']}/{len(veo_scene_ids)} | "
                    f"Regeneradas={len(sc_audit['regenerated_clips'])} | Falhas={len(sc_audit['failed_clips'])}",
                    flush=True,
                )
                if not sc_audit["approved"]:
                    print("  [SCENE-AUDIT-FAIL] Falhas impeditivas:", sc_audit["failed_clips"], sc_audit.get("voice_errors", []), flush=True)
                    return 2
            else:
                generate_images_for_plan(final_prompts, images_dir, force=args.force, script_data=script_data)
                if generate_new_veo:
                    print(f"Gerando ate {target_veo} videos 8s (Veo 3.1 Lite) no pool Flow...", flush=True)
                    veo_map = generate_veo_videos_for_episode(
                        script_data=script_data,
                        visual_clips=visual_clips,
                        images_dir=images_dir,
                        videos_dir=videos_dir,
                        target_count=target_veo,
                        force=args.force,
                        proj_dir=proj_dir,
                    )
                    print(f"Veo 3.1 Lite concluidos: {len(veo_map)}/{target_veo}", flush=True)

    # Rajada (burst): deriva os quadros extras a partir da imagem aprovada da cena (0 crédito)
    try:
        from core.burst_montage import derive_burst_frames
        burst_groups: dict[tuple[str, str], list[dict]] = {}
        for c in visual_clips:
            if c.get("burst_from"):
                burst_groups.setdefault((str(c["scene_id"]), str(c["burst_from"])), []).append(c)
        for (sid, src_id), bclips in burst_groups.items():
            src_img = images_dir / f"{src_id}.jpg"
            if src_img.exists():
                derive_burst_frames(src_img, images_dir, n=len(bclips), base_name=f"{sid}_b")
                print(f"[BURST] {sid}: {len(bclips)} quadros derivados de {src_id}.jpg", flush=True)
    except Exception as exc:
        print(f"[BURST] aviso na derivação: {str(exc)[:160]}", flush=True)

    if args.stage == "images":
        return 0

    out_16_9 = output_dir / f"{slug}_16x9.mp4"
    out_srt = output_dir / f"{slug}.srt"
    out_9_16 = None if args.skip_short else (output_dir / f"{slug}_short_9x16.mp4")

    if args.stage not in ("audit", "publish", "shorts"):
        bgm = Path(args.bgm) if args.bgm else None
        use_av = (not args.no_avatar) and (getattr(args, "avatar_mode", "auto") != "none")
        assemble_video(
            visual_clips,
            images_dir,
            work_dir,
            out_16_9,
            out_srt,
            bgm_wav=bgm,
            with_avatar=use_av,
            burn_captions=args.burn_captions,
            sfx_volume=float(getattr(args, "sfx_volume", 0.35)),
            bgm_volume=float(getattr(args, "bgm_volume", 0.22)),
            target_lufs=float(getattr(args, "target_lufs", -14.0)),
            overlay_style=getattr(args, "overlay_style", "auto"),
            cpu_workers=int(getattr(args, "cpu_workers", CPU_WORKERS) or CPU_WORKERS),
            disable_nvenc=bool(getattr(args, "disable_nvenc", False)),
        )
        print(f"Video 16:9 pronto: {out_16_9}", flush=True)

    if args.stage not in ("audit", "publish"):
        if out_9_16 is not None:
            if args.short_engine in ("auto", "split_70_30", "split_60_40"):
                shorts_list = export_3_shorts_pack(
                    out_16_9,
                    visual_clips,
                    output_dir,
                    slug,
                    hook_badge=script_data["thumb_hook"],
                    target_seconds=getattr(args, "short_seconds", None),
                )
                print(f"3 Shorts Split 70/30 prontos ({len(shorts_list)}):", [s.name for s in shorts_list], flush=True)
            else:
                export_short_9_16(
                    out_16_9,
                    visual_clips,
                    out_9_16,
                    hook_badge=script_data["thumb_hook"],
                    engine=args.short_engine,
                    target_seconds=getattr(args, "short_seconds", None),
                )
                print(f"Short 9:16 ({args.short_engine}) pronto: {out_9_16}", flush=True)

        if args.stage != "shorts" and not args.skip_thumbs:
            first_img = images_dir / f"{visual_clips[0]['clip_id']}.jpg"
            if first_img.exists():
                thumbs = generate_thumbnail_variants(first_img, thumbs_dir, hook_words=script_data["thumb_hook"])
                print("Thumbnails A/B prontas:", [t.name for t in thumbs], flush=True)

    # 7. AUTO-AUDITORIA FINAL OBRIGATORIA
    audit = run_final_audit(
        proj_dir=proj_dir,
        script_data=script_data,
        tts_timings=timings,
        visual_clips=visual_clips,
        images_dir=images_dir,
        out_16_9=out_16_9,
        out_short=out_9_16,
        thumbs_dir=thumbs_dir,
        vision_check=args.vision_audit,
        min_veo_videos=(target_veo if (not args.skip_images and not getattr(args, "skip_veo", False) and target_veo > 0 and args.stage not in ("shorts", "publish")) else 0),
    )
    print(f"Auto-Auditoria Final: APPROVED={audit['approved']} | Issues={audit['issues_count']}", flush=True)
    if not audit["approved"]:
        for iss in audit["issues"]:
            print("  [AUDIT-FAIL]", iss, flush=True)
        return 2

    if getattr(args, "publish_pt", False) or args.stage == "publish":
        hero = images_dir / f"{visual_clips[0]['clip_id']}.jpg"
        rec = publish_episode_youtube_pt(
            proj_dir=proj_dir,
            script_data=script_data,
            video_mp4=out_16_9,
            srt_path=out_srt if out_srt.exists() else None,
            hero_image=hero if hero.exists() else None,
            privacy=getattr(args, "publish_privacy", "public"),
            title_override=getattr(args, "publish_title", ""),
            description_override=getattr(args, "publish_description", ""),
            badge_text=getattr(args, "thumb_badge", "VOCÊ NÃO VAI ACREDITAR!"),
        )
        print(f"YouTube PT publicado: {rec['url']} | Title: {rec['title']}", flush=True)

    if getattr(args, "publish_shorts_pt", False):
        short_files = [
            output_dir / f"{slug}_short_01_hook.mp4",
            output_dir / f"{slug}_short_02_storybook.mp4",
            output_dir / f"{slug}_short_03_final.mp4",
        ]
        short_files = [p for p in short_files if p.is_file()]
        if not short_files and out_9_16 is not None and out_9_16.is_file():
            short_files = [out_9_16]
        s_recs = publish_shorts_pack_youtube_pt(
            proj_dir=proj_dir,
            script_data=script_data,
            shorts_paths=short_files,
            privacy=getattr(args, "publish_privacy", "public"),
        )
        for sr in s_recs:
            print(f"YouTube PT Short publicado: {sr['url']} | Title: {sr['title']}", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Videomaker v2 — Motor Unico Frida & Luna")
    ap.add_argument("--prompt", default="", help="Tema do novo episodio")
    ap.add_argument("--slug", default="", help="Slug do projeto")
    ap.add_argument("--script-file", default="", help="Caminho para script_v2.json pronto")
    ap.add_argument("--legacy-dir", default="", help="Pasta de um video legado para auditar e refazer no motor v2")
    ap.add_argument("--batch-scan", default="", help="Escaneia e audita todas as pastas de video dentro de um diretorio")
    ap.add_argument("--stage", choices=("all", "avatar-only", "script", "tts", "pacing", "images", "shorts", "audit", "publish"), default="all")
    ap.add_argument("--build-avatar", choices=("luna",), default="", help="Gera o pacote de avatar Luna dentro do programa")
    ap.add_argument("--tts-provider", choices=("voice_studio", "gemini_emotion", "chirp3_hd", "auto"), default="voice_studio", help="Voice Studio local (padrao: Luninha/Frida/Simone-feliz, com emoção) → fallback Chirp 3 HD; Edge TTS proibido (Regra de Ouro)")
    ap.add_argument("--auth-chirp3", action="store_true", help="Autentica OAuth 2.0 para Google Cloud Chirp 3 HD e testa as vozes Kore/Sulafat/Leda")
    ap.add_argument("--short-engine", choices=("auto", "split_70_30", "split_60_40", "motion_hud", "remotion"), default="auto")
    ap.add_argument("--min-words", type=int, default=SCRIPT_MIN_WORDS, help="Minimo de palavras no roteiro")
    ap.add_argument("--max-words", type=int, default=SCRIPT_MAX_WORDS, help="Maximo de palavras no roteiro")
    ap.add_argument("--target-minutes", type=float, default=None, help="Duracao alvo em minutos")
    ap.add_argument("--max-clip-seconds", type=float, default=None, help="Teto de segundos por imagem estatica")
    ap.add_argument("--overlay-style", choices=("auto", "zzz", "hearts", "steam", "fire", "bees", "birds", "fireflies", "sparkles", "leaves", "none"), default="auto")
    ap.add_argument("--character-age-mode", choices=("child", "baby"), default="child", help="Padrao crianca/pre-adolescente ou flashback bebe")
    ap.add_argument("--sfx-volume", type=float, default=0.35, help="Teto de volume de SFX (padrao 0.35)")
    ap.add_argument("--bgm-volume", type=float, default=0.22, help="Volume base da musica de fundo antes do ducking")
    ap.add_argument("--target-lufs", type=float, default=-14.0, help="Loudness integrado alvo (LUFS)")
    ap.add_argument("--avatar-mode", choices=("auto", "duo", "frida", "luna", "none"), default="auto", help="Controle do Dual-Avatar PiP")
    ap.add_argument("--short-seconds", type=float, default=None, help="Duracao alvo do Short 9:16 em segundos")
    ap.add_argument("--thumb-hook", default="", help="Sobrescreve frase viral da thumbnail")
    ap.add_argument("--thumb-badge", default="VOCÊ NÃO VAI ACREDITAR!", help="Texto do selo superior na thumbnail viral PT")
    ap.add_argument("--cpu-workers", type=int, default=CPU_WORKERS, help="Numero de workers paralelos em CPU")
    ap.add_argument("--disable-nvenc", action="store_true", help="Forca encode em CPU (libx264) ignorando NVENC")
    ap.add_argument("--allow-flat-fallback", action="store_true")
    ap.add_argument("--skip-prosody-gate", action="store_true")
    ap.add_argument("--skip-whisper-qa", action="store_true")
    ap.add_argument("--skip-images", action="store_true")
    ap.add_argument("--skip-veo", action="store_true", help="Pula geracao dos 10 videos 8s Veo 3.1 Lite")
    ap.add_argument("--veo-videos", type=int, default=TARGET_VEO_VIDEOS, help="Quantidade alvo de videos 8s Veo 3.1 Lite (padrao 10)")
    ap.add_argument("--skip-scene-audit", action="store_true", help="Desativa auditoria cena-a-cena antes de avancar")
    ap.add_argument("--audit-profile", choices=("light", "strict"), default="light", help="light (padrao) libera midia utilizavel e so bloqueia defeitos toscos; strict restaura o fail-closed total")
    ap.add_argument("--skip-viral-research", action="store_true", help="Pula a pesquisa automatica de virais do YouTube antes de escrever o roteiro")
    ap.add_argument("--skip-short", action="store_true")
    ap.add_argument("--skip-thumbs", action="store_true")
    ap.add_argument("--vision-audit", action="store_true", help="Compara imagens geradas x cenario via Gemini Vision")
    ap.add_argument("--burn-captions", action="store_true")
    ap.add_argument("--no-avatar", action="store_true")
    ap.add_argument("--bgm", default="", help="Trilha instrumental opcional (.wav)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--publish-pt", action="store_true", help="Publica episodio no YouTube PT-BR (todo publico, sem restricao infantil)")
    ap.add_argument("--publish-shorts-pt", action="store_true", help="Publica os 3 Shorts 9:16 no YouTube PT-BR (todo publico, linkando ao episodio)")
    ap.add_argument("--publish-privacy", choices=("public", "unlisted", "private"), default="public")
    ap.add_argument("--publish-title", default="", help="Titulo viral customizado para publicacao YouTube PT")
    ap.add_argument("--publish-description", default="", help="Descricao customizada para publicacao YouTube PT")
    ap.add_argument("--flow-accounts-status", action="store_true", help="Lista status/creditos/personagens das 5 contas Google Flow")
    ap.add_argument("--setup-flow-account", default="", help="Abre Chrome CDP dedicado para logar uma conta Flow (ex: acc_2..acc_5)")
    ap.add_argument("--learn-flow-accounts", action="store_true", help="Modo interativo de aprendizado passo a passo das contas Flow (sessao por sessao)")
    ap.add_argument("--flow-account-ids", default="", help="Lista separada por virgula para aprendizado (ex: acc_2,acc_3)")
    ap.add_argument("--save-learned-session", default="", help="Captura e guarda imediatamente a sessao/cliques/projeto da conta informada")
    args = ap.parse_args()
    return run_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
