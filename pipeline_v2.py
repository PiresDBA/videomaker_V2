# -*- coding: utf-8 -*-
"""Motor Unico e Autocontido do Videomaker v2 (Novo Episodio, Legados 30+, Dual-Avatar & Auto-Auditoria)."""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

from config import CPU_WORKERS, MAX_IMAGE_SECONDS, PROJECTS_DIR, SCRIPT_MAX_WORDS, SCRIPT_MIN_WORDS, SHORT_TARGET_SECONDS
import core.pacing_planner as _pacing_mod
import core.self_audit as _audit_mod
from core.avatar_studio import build_luna_avatar_pack
from core.flow_continuity import FLOW_YOUTHFUL_PUPPY_STYLE_PREFIX
from core.legacy_auditor import batch_scan_legacy_root, import_and_upgrade_legacy
from core.media_studio import (
    generate_images_for_plan,
    generate_prompts_for_script,
    generate_thumbnail_variants,
)
from core.motion_shorts import export_3_shorts_pack
from core.pacing_planner import build_pacing_plan
from core.script_engine import generate_script, normalize_script_records, validate_script_schema
from core.self_audit import run_final_audit
from core.video_assembler import assemble_video, export_short_9_16
from core.voice_studio import synthesize_all_scenes
from core.youtube_publisher import publish_episode_youtube_pt, publish_shorts_pack_youtube_pt


def slugify(text: str, max_len: int = 44) -> str:
    norm = unicodedata.normalize("NFKD", (text or "projeto").lower().strip())
    ascii_txt = "".join(c for c in norm if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_txt).strip("-")
    return slug[:max_len].strip("-") or "projeto"


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
            load_accounts_config,
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
    audio_dir = proj_dir / "assets" / "audio"
    work_dir = proj_dir / "work"
    output_dir = proj_dir / "output"
    thumbs_dir = output_dir / "thumbs"
    for d in (artifacts_dir, images_dir, audio_dir, work_dir, output_dir, thumbs_dir):
        d.mkdir(parents=True, exist_ok=True)

    script_path = artifacts_dir / "script_v2.json"
    prompts_path = artifacts_dir / "image_prompts_v2.json"
    timings_path = artifacts_dir / "tts_timings_v2.json"
    pacing_path = artifacts_dir / "pacing_plan_v2.json"
    meta_path = artifacts_dir / "youtube_metadata_v2.json"

    # 1. ROTEIRO / IMPORTACAO DE LEGADO
    if args.legacy_dir and (not script_path.exists() or args.force):
        imp = import_and_upgrade_legacy(Path(args.legacy_dir), proj_dir, reuse_clean_images=True, vision_filter=args.vision_audit)
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
        script_data = generate_script(args.prompt, script_path, min_words=args.min_words, max_words=args.max_words)

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

    # 4. RITMO (DIVISAO <= 5s + KEN BURNS + DUAL AVATAR + PLANO DE DIRECAO OPCIONAL)
    montage_plan = None
    mp_arg = getattr(args, "montage_plan", "")
    mp_path = Path(mp_arg) if mp_arg else (artifacts_dir / "plano_montagem_direcao_v2.json")
    if mp_path.is_file():
        montage_plan = json.loads(mp_path.read_text(encoding="utf-8"))
        print(f"Plano de direcao carregado: {mp_path.name} ({len(montage_plan.get('scenes', []))} cenas)", flush=True)
    visual_clips, final_prompts = build_pacing_plan(script_data, timings, montage_plan=montage_plan)
    pacing_path.write_text(json.dumps(visual_clips, ensure_ascii=False, indent=2), encoding="utf-8")
    prompts_path.write_text(json.dumps(final_prompts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Pacing: {len(visual_clips)} sub-clips visuais (<= 5s cada)", flush=True)
    if args.stage == "pacing":
        return 0

    # 5. IMAGENS 16:9 SEM COLAGEM (recria apenas o que faltar ou reprovar)
    if not args.skip_images:
        generate_images_for_plan(final_prompts, images_dir, force=args.force)
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
    ap.add_argument("--montage-plan", default="", help="JSON opcional de direcao cena a cena (pausas comicas + PiP pontual)")
    ap.add_argument("--legacy-dir", default="", help="Pasta de um video legado para auditar e refazer no motor v2")
    ap.add_argument("--batch-scan", default="", help="Escaneia e audita todas as pastas de video dentro de um diretorio")
    ap.add_argument("--stage", choices=("all", "avatar-only", "script", "tts", "pacing", "images", "shorts", "audit", "publish"), default="all")
    ap.add_argument("--build-avatar", choices=("luna",), default="", help="Gera o pacote de avatar Luna dentro do programa")
    ap.add_argument("--tts-provider", choices=("gemini_emotion",), default="gemini_emotion", help="Vozes emocionais Gemini TTS (Regra de Ouro: Edge TTS proibido)")
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
