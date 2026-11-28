# -*- coding: utf-8 -*-
"""Guardiao do Contrato Motor v2: valida invariantes criticos e impede vazamento de segredos/midias no Git."""
from __future__ import annotations

import py_compile
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = (
    "config.py",
    "pipeline_v2.py",
    "CONTRATO_MOTOR_V2.md",
    "AGENTS.md",
    "core/video_assembler.py",
    "core/scene_auditor.py",
    "core/audio_fx.py",
    "core/flow_continuity.py",
    "core/flow_accounts.py",
    "core/logging_manager.py",
    "core/script_engine.py",
    "core/viral_research.py",
    "core/youtube_publisher.py",
    "tests/suite/manifest.json",
    "tests/suite/runner.py",
    "tests/suite/README.md",
    "vendor/gerenciador_efeitos_sonoros.py",
)

FORBIDDEN_STAGED_PATTERNS = (
    re.compile(r"(?:^|/)\.env(?:\.|$)", re.I),
    re.compile(r"(?:^|/)\.credentials/", re.I),
    re.compile(r"(?:secret|youtube_token).*\.json$", re.I),
    re.compile(r"^flow_(?:accounts(?:_state|_learned_sessions)?|projects)\.json$", re.I),
    re.compile(r"(?:^|/)\.chrome-", re.I),
    re.compile(r"^projects/", re.I),
    re.compile(r"^logs/", re.I),
    re.compile(r"^bin/", re.I),
    re.compile(r"^vendor/(?:soundcraft|earshot-sfx)/", re.I),
    re.compile(r"\.(?:mp4|mov|mkv|avi|wav|mp3|m4a|exe|dll)$", re.I),
)

SECRET_TOKEN_RE = re.compile(
    r"(?:AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z]{20,}|ghp_[0-9A-Za-z]{20,}|-----BEGIN " + r"PRIVATE KEY-----)"
)


def check_contract() -> list[str]:
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            errors.append(f"Arquivo obrigatorio ausente: {rel}")

    if errors:
        return errors

    # 1. Verifica invariants de configuracao & canone visual
    cfg_txt = (ROOT / "config.py").read_text(encoding="utf-8", errors="replace")
    m_max = re.search(r"MAX_IMAGE_SECONDS\s*=\s*([0-9.]+)", cfg_txt)
    if not m_max or float(m_max.group(1)) > 5.0:
        errors.append("CONTRATO VIOLADO: MAX_IMAGE_SECONDS em config.py deve ser <= 5.0.")
    if "1 year old max" not in cfg_txt:
        errors.append("CONTRATO VIOLADO: config.py VISUAL_BIBLE deve manter o canone '1 year old max' (crianca/pre-adolescente 3D).")
    if "VOICE_LOCK_STRICT = True" not in cfg_txt:
        errors.append("CONTRATO VIOLADO: config.py deve manter VOICE_LOCK_STRICT = True (trava absoluta Kore/Sulafat/Leda).")
    m_veo = re.search(r"TARGET_VEO_VIDEOS\s*=\s*([0-9]+)", cfg_txt)
    if not m_veo or int(m_veo.group(1)) < 10:
        errors.append("CONTRATO VIOLADO: config.py deve manter TARGET_VEO_VIDEOS >= 10 (videos 8s Veo 3.1 Lite).")
    m_veo_scene = re.search(r"MAX_VEO_GENERATIONS_PER_SCENE\s*=\s*([0-9]+)", cfg_txt)
    if not m_veo_scene or int(m_veo_scene.group(1)) != 1:
        errors.append("CONTRATO VIOLADO: config.py deve manter MAX_VEO_GENERATIONS_PER_SCENE = 1 (maximo 1 geracao Veo paga por cena).")

    # 2. Verifica YouTube PT nao marcado para criancas
    yt_txt = (ROOT / "core" / "youtube_publisher.py").read_text(encoding="utf-8", errors="replace")
    if '"selfDeclaredMadeForKids": False' not in yt_txt or '"selfDeclaredMadeForKids": True' in yt_txt:
        errors.append("CONTRATO VIOLADO: core/youtube_publisher.py deve manter 'selfDeclaredMadeForKids': False.")

    # 3. Verifica overlays contextuais estaticos e sonoplastia normalizada
    va_txt = (ROOT / "core" / "video_assembler.py").read_text(encoding="utf-8", errors="replace")
    for sym in ("def infer_scene_overlay_style", "def apply_contextual_particle_overlay"):
        if sym not in va_txt:
            errors.append(f"CONTRATO VIOLADO: {sym} removido de core/video_assembler.py.")

    afx_txt = (ROOT / "core" / "audio_fx.py").read_text(encoding="utf-8", errors="replace")
    if "def _normalize_sfx_to_wav" not in afx_txt:
        errors.append("CONTRATO VIOLADO: _normalize_sfx_to_wav removido de core/audio_fx.py.")
    if "cartoon boing" not in afx_txt or "slide whistle" not in afx_txt:
        errors.append("CONTRATO VIOLADO: core/audio_fx.py deve manter sonoplastia estilo Cartoon (cartoon boing, slide whistle, etc.).")
    if '"gemini_voice": "Puck"' not in cfg_txt or '"chirp3_voice": "pt-BR-Chirp3-HD-Puck"' not in cfg_txt:
        errors.append("CONTRATO VIOLADO: config.py deve manter Narradora alegre/brincalhona 'Puck' no SPEAKER_VOICE_PROFILES (escolhida pelo usuario em 2026-11-22).")

    fa_txt = (ROOT / "core" / "flow_accounts.py").read_text(encoding="utf-8", errors="replace")
    if "def ensure_story_characters_created" not in fa_txt or "story_props" not in fa_txt:
        errors.append("CONTRATO VIOLADO: ensure_story_characters_created em core/flow_accounts.py deve registrar secondary_characters e story_props.")
    if "class FlowStageWatchdog" not in fa_txt or "finished_and_notified" not in fa_txt:
        errors.append("CONTRATO VIOLADO: FlowStageWatchdog (fila FIFO + heartbeat + aviso de termino) ausente em core/flow_accounts.py.")
    # Regra 34: Flow sequencial/on-demand e liberacao segura por ownership/perfil/porta.
    for fa_sym in ("def ensure_account_cdp", "def release_account_chrome", "def release_all_owned_flow_accounts", "_runtime_matches_account"):
        if fa_sym not in fa_txt:
            errors.append(f"HOOK VIOLADO: abertura/liberacao sequencial Flow sem a trava '{fa_sym}' (Regra 34).")
    if 'ensure_account_cdp(acc, purpose="video"' not in fa_txt:
        errors.append("HOOK VIOLADO: failover de video deve abrir a conta sob demanda, uma por vez (Regra 34).")
    lm_txt = (ROOT / "core" / "logging_manager.py").read_text(encoding="utf-8", errors="replace")
    for lm_sym in ("KEEP_UNCOMPACTED_PROJECTS = 3", "def rotate_project_logs", "def mark_project_completed", "ARCHIVE_UNPACKED_DIR"):
        if lm_sym not in lm_txt:
            errors.append(f"HOOK VIOLADO: rotacao de logs sem a trava '{lm_sym}' (Regra 34).")

    # 3b. Verifica REGRA DE OURO: PROIBIDO Edge TTS em producao + trava gratuita Chirp 3 HD
    vs_txt = (ROOT / "core" / "voice_studio.py").read_text(encoding="utf-8", errors="replace")
    if "REGRA DE OURO VIOLADA" not in vs_txt:
        errors.append("CONTRATO VIOLADO: core/voice_studio.py deve bloquear Edge TTS (Regra de Ouro das vozes emocionais).")
    if "def _synthesize_chirp3_hd" not in vs_txt:
        errors.append("CONTRATO VIOLADO: _synthesize_chirp3_hd ausente em core/voice_studio.py.")
    m_chirp_lim = re.search(r"CHIRP3_MONTHLY_CHAR_LIMIT\s*=\s*([0-9_]+)", cfg_txt)
    if not m_chirp_lim or int(m_chirp_lim.group(1).replace("_", "")) > 1_000_000:
        errors.append("CONTRATO VIOLADO: config.py CHIRP3_MONTHLY_CHAR_LIMIT deve ser <= 1_000_000 (franquia gratuita).")
    pipe_txt = (ROOT / "pipeline_v2.py").read_text(encoding="utf-8", errors="replace")
    if "begin_run_logging" not in pipe_txt or "mark_project_completed" not in pipe_txt:
        errors.append("HOOK VIOLADO: pipeline_v2.py deve integrar logs centrais e conclusao/rotacao de projetos (Regra 34).")
    if 'choices=("gemini_emotion", "edge")' in pipe_txt:
        errors.append("CONTRATO VIOLADO: pipeline_v2.py nao pode oferecer 'edge' em --tts-provider.")

    # 3c. Verifica Shorts 70/30 + sincronia labial estrita + reprodutor continuo 30fps + cortes limpos
    ms_txt = (ROOT / "core" / "motion_shorts.py").read_text(encoding="utf-8", errors="replace")
    # HOOK zona segura: 300px do rodape livre de texto/dados (UI Shorts/Reels/TikTok)
    if "SHORT_SAFE_BOTTOM_PX = 300" not in cfg_txt:
        errors.append("HOOK VIOLADO: config.py SHORT_SAFE_BOTTOM_PX deve ser 300 (zona segura rodape Shorts).")
    if "SAFE_BOTTOM_LOCAL" not in ms_txt:
        errors.append("HOOK VIOLADO: motion_shorts.py deve respeitar SAFE_BOTTOM_LOCAL (conteudo ate y local 270).")
    if (
        "SHORT_SPLIT_TOP_RATIO = 0.70" not in ms_txt
        or "def resolve_split_avatar_states" not in ms_txt
        or "class _SmoothAvatarPlayer" not in ms_txt
        or "outro_guard" not in ms_txt
    ):
        errors.append(
            "CONTRATO VIOLADO: core/motion_shorts.py deve manter SHORT_SPLIT_TOP_RATIO = 0.70, "
            "resolve_split_avatar_states, _SmoothAvatarPlayer e outro_guard."
        )

    # 3d. Verifica auditoria cena-a-cena e trava de voz
    sa_txt = (ROOT / "core" / "scene_auditor.py").read_text(encoding="utf-8", errors="replace")
    for sym in ("def audit_voice_consistency", "def generate_and_audit_scenes", "def audit_scene_visual_with_vision", "strict_vision"):
        if sym not in sa_txt:
            errors.append(f"CONTRATO VIOLADO: {sym} ausente em core/scene_auditor.py.")
    ms_media_txt = (ROOT / "core" / "media_studio.py").read_text(encoding="utf-8", errors="replace")
    if "def generate_single_veo_video" not in ms_media_txt or "veo_generation_ledger" not in ms_media_txt:
        errors.append("CONTRATO VIOLADO: core/media_studio.py deve manter generate_single_veo_video e veo_generation_ledger.")
    if 'ensure_account_cdp(account, purpose="image"' not in ms_media_txt:
        errors.append("HOOK VIOLADO: geracao de imagem deve abrir candidatas Flow sob demanda, uma por vez (Regra 34).")
    au_txt = (ROOT / "core" / "self_audit.py").read_text(encoding="utf-8", errors="replace")
    if "min_veo_videos" not in au_txt:
        errors.append("CONTRATO VIOLADO: min_veo_videos ausente em core/self_audit.py.")
    fc_txt = (ROOT / "core" / "flow_continuity.py").read_text(encoding="utf-8", errors="replace")
    if "def _inject_at_character_mentions" not in fc_txt or "def _wait_for_inflight_flow_generation" not in fc_txt:
        errors.append("CONTRATO VIOLADO: core/flow_continuity.py deve manter _inject_at_character_mentions e _wait_for_inflight_flow_generation.")
    if "Fallback: selecionando 1a midia" in fc_txt:
        errors.append("CONTRATO VIOLADO: proibido fallback cego da 1a midia de 'Envios' em core/flow_continuity.py.")
    for fc_sym in ("max_elements = 3", "def _dismiss_open_overlays", 'button[role="radio"]', "cartoon prop object", "hasUnusualActivity", "reloaded = True", "on_missing_character"):
        if fc_sym not in fc_txt:
            errors.append(f"CONTRATO VIOLADO: trava anti-regressao '{fc_sym}' ausente em core/flow_continuity.py.")
    if "cur_pre = await _snapshot_top_tiles" in fc_txt:
        errors.append("CONTRATO VIOLADO: proibido re-checar cur_pre pos-upload em generate_flow_image (falso positivo de conta ocupada).")
    for sa_sym in ("def _scene_matching_secondary_chars", "_archive", "proporcao vertical invalida", "VIDEO LENIENCY RULE"):
        if sa_sym not in sa_txt:
            errors.append(f"CONTRATO VIOLADO: trava anti-regressao '{sa_sym}' ausente em core/scene_auditor.py.")
    if "v_mp4.unlink" in sa_txt:
        errors.append("CONTRATO VIOLADO: proibido apagar video Veo pago com v_mp4.unlink em core/scene_auditor.py (usar _archive).")
    if "def _resolve_scene_videos" not in va_txt or "def render_multi_video_montage_subclip" not in va_txt:
        errors.append("CONTRATO VIOLADO: _resolve_scene_videos / render_multi_video_montage_subclip ausente em core/video_assembler.py.")
    if "def _concat_segments_with_smooth_xfade" not in va_txt:
        errors.append("CONTRATO VIOLADO: _concat_segments_with_smooth_xfade ausente em core/video_assembler.py (transicao suave obrigatoria).")
    if "def _find_pause_slot_for_window" not in afx_txt:
        errors.append("CONTRATO VIOLADO: _find_pause_slot_for_window ausente em core/audio_fx.py (SFX apenas nas pausas da narracao).")
    # Perfil de auditoria light (custo de midia): so bloqueia defeitos toscos.
    sa_txt = (ROOT / "core" / "scene_auditor.py").read_text(encoding="utf-8", errors="replace")
    if 'AUDIT_PROFILES = ("light", "strict")' not in sa_txt or "def _is_hard_block" not in sa_txt:
        errors.append("HOOK VIOLADO: scene_auditor.py deve manter os perfis light/strict e _is_hard_block (Regra 19).")
    if '--audit-profile' not in pipe_txt:
        errors.append("HOOK VIOLADO: pipeline_v2.py deve manter --audit-profile (light por padrao, Regra 19).")
    # Regras 20/21: montagem rica de imagens, overlay de agua e voz Voice Studio first
    va2_txt = (ROOT / "core" / "video_assembler.py").read_text(encoding="utf-8", errors="replace")
    afx2_txt = (ROOT / "core" / "audio_fx.py").read_text(encoding="utf-8", errors="replace")
    if "RICH_IMAGE_MONTAGE = True" not in cfg_txt or 'style == "water"' not in va2_txt:
        errors.append("HOOK VIOLADO: montagem rica de imagens e overlay water ausentes (Regra 20).")
    if "ocean waves seaside" not in afx2_txt or "cartoon splash" not in afx2_txt:
        errors.append("HOOK VIOLADO: sonoplastia de mar/splash ausente (Regra 20).")
    # Regra 22: earshot e os ouvidos da aplicacao — unico arbitro de audio.
    contrato_txt = (ROOT / "CONTRATO_MOTOR_V2.md").read_text(encoding="utf-8", errors="replace")
    readme_txt = (ROOT / "README.md").read_text(encoding="utf-8", errors="replace")
    if "34. **REGRA DE OURO — Google Flow Sequencial/On-Demand + Logs Centrais sem Perda:**" not in contrato_txt:
        errors.append("HOOK VIOLADO: Regra 34 (Flow sequencial + logs centrais) ausente do contrato.")
    if "FLOW SEQUENCIAL + LOGS CENTRAIS (Regra 34)" not in (ROOT / "AGENTS.md").read_text(encoding="utf-8", errors="replace"):
        errors.append("HOOK VIOLADO: Regra 34 ausente do AGENTS.md.")
    if "EARSHOT É OS OUVIDOS DA APLICAÇÃO" not in contrato_txt or "ouvidos do aplicativo" not in readme_txt.lower():
        errors.append("HOOK VIOLADO: Regra 22 (earshot como ouvidos) ausente do contrato/manual.")
    if "def run_earshot_critique" not in afx2_txt:
        errors.append("HOOK VIOLADO: audio_fx.py deve manter run_earshot_critique (Regra 22).")
    # Regra 20/23: rajada de imagens e modo agente do Flow
    burst_txt = (ROOT / "core" / "burst_montage.py").read_text(encoding="utf-8", errors="replace")
    if "BURST_FRAMES = 10" not in cfg_txt or "def build_burst_prompt" not in burst_txt:
        errors.append("HOOK VIOLADO: burst de 10 imagens ausente (Regra 20).")
    if "BURST_MAX_SCENES = 5" not in cfg_txt:
        errors.append("HOOK VIOLADO: limite de cenas com burst ausente (Regra 20).")
    pace_txt = (ROOT / "core" / "pacing_planner.py").read_text(encoding="utf-8", errors="replace")
    if "video_scene_ids" not in pace_txt or "burst_scenes_used < BURST_MAX_SCENES" not in pace_txt:
        errors.append("HOOK VIOLADO: rajada nao respeita cenas com Veo / limite (Regra 20).")
    # Regra 25 (revisada 2026-11-24): anti-regeneracao de Veo + CTA em VIDEO com chroma key.
    # O overlay .mov antigo segue VETADO; entram like-sem-som.mp4 (meio) e like-com-som.mp4 (final).
    pipe_txt = (ROOT / "pipeline_v2.py").read_text(encoding="utf-8", errors="replace")
    if "def should_generate_new_veo" not in pipe_txt or "generate_new_veo = should_generate_new_veo" not in pipe_txt:
        errors.append("HOOK VIOLADO: trava anti-regeneracao de Veo ausente (Regra 25).")
    va2b_txt = (ROOT / "core" / "video_assembler.py").read_text(encoding="utf-8", errors="replace")
    if "cta_subscribe.mov" in va2b_txt or "render_cta_subscribe_overlay" in va2b_txt:
        errors.append(
            "HOOK VIOLADO: overlay CTA .mov antigo VETADO ainda em uso (Regra 25) — "
            "usar core/cta_video_overlay.py com os videos like-*.mp4."
        )
    cta_txt = (ROOT / "core" / "cta_video_overlay.py").read_text(encoding="utf-8", errors="replace")
    for sym in ("colorkey=0x00FF00", "CTA_SIMILARITY = 0.28", "CTA_BLEND = 0.12",
                "CTA_AUDIO_MUTED = True", "like-sem-som.mp4", "like-com-som.mp4", "def plan_ctas"):
        if sym not in cta_txt:
            errors.append(f"HOOK VIOLADO: CTA em video sem a trava '{sym}' (Regra 25).")
    if "despill=green" in cta_txt:
        errors.append("HOOK VIOLADO: despill agressivo no CTA estraga o sino amarelo (Regra 25).")
    if "plan_ctas" not in va2b_txt or "mix_cta_audio" not in va2b_txt:
        errors.append("HOOK VIOLADO: CTA em video nao integrado no assemble_video (Regra 25).")
    # Regras 27-29: anti-repeticao de imagem, slow-motion sem estrobo e narracao dominante
    ia_path = ROOT / "core" / "image_assignment.py"
    if not ia_path.exists() or "def assign_images" not in ia_path.read_text(encoding="utf-8", errors="replace"):
        errors.append("HOOK VIOLADO: core/image_assignment.py (cota/anti-repeticao) ausente (Regra 27).")
    if "SLOWMO_XFADE_SECONDS" not in cfg_txt or "scene_is_burst" not in pace_txt:
        errors.append("HOOK VIOLADO: slow-motion de imagem parada ausente (Regra 28).")
    da_txt = (ROOT / "core" / "delivery_audit.py").read_text(encoding="utf-8", errors="replace")
    for sym in ("MAX_SCENE_REUSE", "BURST_MIN_FRAME", "BURST_MIN_BASE_SIM", "load_blacklist"):
        if sym not in da_txt:
            errors.append(f"HOOK VIOLADO: porta de entrega sem a trava '{sym}' (Regras 27/28).")
    sa2_txt = (ROOT / "core" / "self_audit.py").read_text(encoding="utf-8", errors="replace")
    if "NARRATION_MIN_RATIO" not in sa2_txt:
        errors.append("HOOK VIOLADO: auditoria de narracao dominante ausente (Regra 29).")
    # Regra 26: pipeline redondo, voz local, duracao adaptativa
    if "def recommend_target_minutes" not in pipe_txt or "ADAPTIVE_DURATION" not in cfg_txt:
        errors.append("HOOK VIOLADO: duracao adaptativa por material ausente (Regra 26).")
    if '"--skip-tts"' not in pipe_txt or "Reaproveitando" not in pipe_txt:
        errors.append("HOOK VIOLADO: reaproveitamento de falas TTS ausente (Regra 26).")
    vs2_txt = (ROOT / "core" / "voice_studio.py").read_text(encoding="utf-8", errors="replace")
    if "voicestudio" not in vs2_txt.lower() or "edge" in cfg_txt.lower() and "edge_tts" in cfg_txt.lower():
        errors.append("HOOK VIOLADO: voz local Voice Studio nao preservada (Regra 26).")
    fc_txt = (ROOT / "core" / "flow_continuity.py").read_text(encoding="utf-8", errors="replace")
    if "def set_flow_agent_mode" not in fc_txt or "def generate_flow_image_batch" not in fc_txt:
        errors.append("HOOK VIOLADO: modo agente do Flow para lote de imagens ausente (Regra 23).")
    # Regra 24: separacao de contas/projetos Flow (uma conta imagens, contas videos, projeto por episodio)
    fa2_txt = (ROOT / "core" / "flow_accounts.py").read_text(encoding="utf-8", errors="replace")
    if "FLOW_IMAGE_ACCOUNT_ID" not in cfg_txt or "def get_image_flow_account" not in fa2_txt:
        errors.append("HOOK VIOLADO: conta unica de imagens ausente (Regra 24).")
    if "def get_video_flow_accounts" not in fa2_txt or "def ensure_named_flow_project" not in fa2_txt:
        errors.append("HOOK VIOLADO: contas de video separadas / projeto nomeado por episodio ausente (Regra 24).")
    if "def episode_project_name" not in fa2_txt or "FLOW_PROJECTS_REGISTRY" not in fa2_txt:
        errors.append("HOOK VIOLADO: registro de projetos nomeados do Flow ausente (Regra 24).")
    va2b_txt = (ROOT / "core" / "video_assembler.py").read_text(encoding="utf-8", errors="replace")
    if '"rain": (210, 360)' not in va2b_txt or 'elif style == "wind":' not in va2b_txt:
        errors.append("HOOK VIOLADO: overlays de chuva/vento incompletos (Regra 20).")
    if '"narrador": "Simone-feliz"' not in cfg_txt or '"luna": "Luninha"' not in cfg_txt:
        errors.append("HOOK VIOLADO: VOICE_STUDIO_VOICES deve manter Simone-feliz/Luninha/Frida (Regra 21).")
    if "is_video_scene" not in va_txt:
        errors.append("CONTRATO VIOLADO: core/video_assembler.py deve reduzir card_sz quando is_video_scene=True.")
    av_txt = (ROOT / "core" / "avatar_studio.py").read_text(encoding="utf-8", errors="replace")
    if "0.18, 0.82" in av_txt:
        errors.append("CONTRATO VIOLADO: core/avatar_studio.py nao pode cortar patinha da Luna com (0.18, 0.82); manter y_bot >= 0.95.")
    if 're.sub(r"@+", ""' not in vs_txt:
        errors.append("CONTRATO VIOLADO: normalize_phonetics_pt em core/voice_studio.py deve remover '@' antes do TTS.")

    # 3d. HOOKS DE TRAVAMENTO — travam as melhorias desta sessao (anti-regressao automatica)
    # HOOK 1: provedor padrao Chirp 3 HD (cota 1M chars/mes) — Gemini free tier tem so 10 req/dia.
    if 'default="voice_studio"' not in pipe_txt or 'choices=("voice_studio"' not in pipe_txt:
        errors.append("HOOK VIOLADO: pipeline_v2.py --tts-provider deve ter default='voice_studio' (Regra 21).")
    if 'provider: str = "voice_studio"' not in vs_txt:
        errors.append("HOOK VIOLADO: synthesize_all_scenes deve ter provider='voice_studio' como default (Regra 21).")
    if "def _synthesize_voice_studio" not in vs_txt or "voice_studio:" not in vs_txt:
        errors.append("HOOK VIOLADO: voice_studio.py deve manter _synthesize_voice_studio e fallback Chirp 3 HD (Regra 21).")
    # HOOK CRITICO: Gemini-TTS (gemini-2.5-flash-tts / modelName no Cloud TTS) E PROIBIDO — cobrado por token.
    if '"modelName": "gemini-' in vs_txt or 'gemini-2.5-flash-tts' in vs_txt and 'GEMINI_TTS_MODELS' not in vs_txt:
        errors.append("HOOK CRITICO VIOLADO: Gemini-TTS cobrado por token e proibido; usar apenas Chirp 3 HD (cota 1M).")
    # HOOK 2: vozes travadas Zephyr/Sulafat/Leda + secundario (Puck) — personagens secundarios podem usar OUTRAS vozes.
    for voice_sym in ('"gemini_voice": "Puck"', '"gemini_voice": "Sulafat"', '"gemini_voice": "Leda"',
                      '"chirp3_voice": "pt-BR-Chirp3-HD-Puck"', '"chirp3_voice": "pt-BR-Chirp3-HD-Sulafat"',
                      '"chirp3_voice": "pt-BR-Chirp3-HD-Leda"', '"secundario"', '"pt-BR-Chirp3-HD-Fenrir"'):
        if voice_sym not in cfg_txt:
            errors.append(f"HOOK VIOLADO: config.py deve manter '{voice_sym}' (vozes fixas + secundario).")
    # HOOK 3: pre-varredura de recuperacao total das 5 contas Flow antes de gerar (evita gerar o que ja existe).
    if 'recover_and_audit(' not in pipe_txt or 'max_videos=0' not in pipe_txt:
        errors.append("HOOK VIOLADO: pipeline_v2.py deve pre-varrer as 5 contas Flow (recover_and_audit, max_videos=0).")
    # HOOK 4: junta de audio limpa sem sobreposicao (ferramentas work/ + roteiro de 25 cenas em sequencia).
    # HOOK 5: deteccao de Short mudo (-91 dB) antes de publicar — SELF-AUDIT nao pode aprovar audio silencioso.
    for sa_sym in ("def build_narration_track", "def master_with_soundcraft"):
        if sa_sym not in va_txt and sa_sym not in afx_txt:
            errors.append(f"HOOK VIOLADO: '{sa_sym}' ausente (mixing de narracao/audio obrigatorio).")
    # HOOK 6: sonoplastia cartoon sinc (Pica-Pau/Pernalonga) + texto infantil divertido + BGM original.
    for cartoon_sym in ("cartoon boing", "cartoon giggle", "cartoon fanfare", "slide whistle"):
        if cartoon_sym not in afx_txt:
            errors.append(f"HOOK VIOLADO: audio_fx.py deve manter foley cartoon '{cartoon_sym}' (estilo Pica-Pau/Pernalonga).")
    if "def _infer_semantic_foleys" not in afx_txt:
        errors.append("HOOK VIOLADO: _infer_semantic_foleys ausente (foleys sematicos por cena).")
    if 'gerenciador_efeitos_sonoros' not in afx_txt or 'obter_efeito_sonoro' not in afx_txt:
        errors.append("HOOK VIOLADO: SFX deve passar por vendor/gerenciador_efeitos_sonoros.py (obter_efeito_sonoro).")
    # HOOK CRITICO DE TEXTO: risada e SENTIMENTO, nunca escrita (hahaha soa robotizado no TTS).
    if 'hahaha+|ha\\s+ha\\s+ha+' not in vs_txt:
        errors.append("HOOK VIOLADO: normalize_phonetics_pt deve remover 'hahaha' do texto antes do TTS (risada e sentimento, nunca escrita).")
    # HOOK CTA animado (Regra 25 revisada): 2 videos de referencia reutilizaveis em TODOS os episodios.
    cta_ref = ROOT / "assets/reference/overlays"
    for cta_name in ("like-sem-som.mp4", "like-com-som.mp4"):
        if not (cta_ref / cta_name).exists() and not (Path.home() / "Downloads" / cta_name).exists():
            errors.append(f"HOOK VIOLADO: CTA animado '{cta_name}' ausente em assets/reference/overlays/ (meio/final, joinha+sino).")
    cta_txt = (ROOT / "core/cta_video_overlay.py").read_text(encoding="utf-8", errors="replace") if (ROOT / "core/cta_video_overlay.py").exists() else ""
    if "colorkey=0x00FF00" not in cta_txt or "CTA_AUDIO_MUTED = True" not in cta_txt:
        errors.append("HOOK VIOLADO: cta_video_overlay deve manter chroma key 0x00FF00 sem despill e CTA_AUDIO_MUTED=True (voz tem prioridade).")
    # HOOK 7 (Regra 18): pesquisa automatica de virais por tema ESTRUTURA, nunca conteudo.
    vr_txt = (ROOT / "core" / "viral_research.py").read_text(encoding="utf-8", errors="replace")
    se_txt = (ROOT / "core" / "script_engine.py").read_text(encoding="utf-8", errors="replace")
    if "def research_viral_humor" not in vr_txt or "def build_prompt_section" not in vr_txt:
        errors.append("HOOK VIOLADO: core/viral_research.py deve manter research_viral_humor e build_prompt_section (Regra 18).")
    if "MIN_VIRAL_VIEWS = 1_000_000" not in vr_txt or "PROIBIDO copiar" not in vr_txt:
        errors.append("HOOK VIOLADO: pesquisa de virais deve usar limiar de 1M views e bloquear copia de conteudo (Regra 18).")
    if "--skip-viral-research" not in pipe_txt or "humor_prompt: str" not in se_txt:
        errors.append("HOOK VIOLADO: pipeline_v2.py precisa de --skip-viral-research e generate_script de humor_prompt (Regra 18).")

    # 4. Compilacao Python de todos os modulos principais
    for py_path in [ROOT / "config.py", ROOT / "pipeline_v2.py", *sorted((ROOT / "core").glob("*.py")), Path(__file__)]:
        try:
            py_compile.compile(str(py_path), doraise=True)
        except Exception as exc:
            errors.append(f"Erro de sintaxe em {py_path.relative_to(ROOT)}: {exc}")

    # 5. Verifica arquivos staged no Git (impede vazamento de segredos/midias/binarios)
    try:
        st_out = subprocess.check_output(
            ["git", "-C", str(ROOT), "diff", "--cached", "--name-only"],
            text=True, encoding="utf-8", errors="replace",
        ).splitlines()
    except Exception:
        st_out = []

    for fname in st_out:
        norm = fname.replace("\\", "/").strip()
        if not norm:
            continue
        if any(rx.search(norm) for rx in FORBIDDEN_STAGED_PATTERNS):
            errors.append(f"SEGURANCA GIT: arquivo proibido no staging: {norm}")

    if st_out:
        try:
            diff_txt = subprocess.check_output(
                ["git", "-C", str(ROOT), "diff", "--cached"],
                text=True, encoding="utf-8", errors="replace",
            )
            if SECRET_TOKEN_RE.search(diff_txt):
                errors.append("SEGURANCA GIT: padrao de API key / chave privada detectado no diff staged!")
        except Exception:
            pass

    return errors


def main() -> int:
    errs = check_contract()
    if errs:
        print("BLOQUEADO PELO GUARDIAO DO CONTRATO MOTOR V2:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("OK: Contrato Motor v2 verificado (invariantes, sintaxe e seguranca Git aprovados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
