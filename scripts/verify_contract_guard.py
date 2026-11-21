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
    "core/script_engine.py",
    "core/youtube_publisher.py",
    "vendor/gerenciador_efeitos_sonoros.py",
)

FORBIDDEN_STAGED_PATTERNS = (
    re.compile(r"(?:^|/)\.env(?:\.|$)", re.I),
    re.compile(r"(?:^|/)\.credentials/", re.I),
    re.compile(r"(?:secret|youtube_token).*\.json$", re.I),
    re.compile(r"^flow_accounts(?:_state|_learned_sessions)?\.json$", re.I),
    re.compile(r"(?:^|/)\.chrome-", re.I),
    re.compile(r"^projects/", re.I),
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

    fa_txt = (ROOT / "core" / "flow_accounts.py").read_text(encoding="utf-8", errors="replace")
    if "def ensure_story_characters_created" not in fa_txt:
        errors.append("CONTRATO VIOLADO: ensure_story_characters_created removido de core/flow_accounts.py.")

    # 3b. Verifica REGRA DE OURO: PROIBIDO Edge TTS em producao
    vs_txt = (ROOT / "core" / "voice_studio.py").read_text(encoding="utf-8", errors="replace")
    if "REGRA DE OURO VIOLADA" not in vs_txt:
        errors.append("CONTRATO VIOLADO: core/voice_studio.py deve bloquear Edge TTS (Regra de Ouro das vozes emocionais).")
    pipe_txt = (ROOT / "pipeline_v2.py").read_text(encoding="utf-8", errors="replace")
    if 'choices=("gemini_emotion", "edge")' in pipe_txt:
        errors.append("CONTRATO VIOLADO: pipeline_v2.py nao pode oferecer 'edge' em --tts-provider.")

    # 3c. Verifica Shorts 70/30 + sincronia labial estrita + reprodutor continuo 30fps + cortes limpos
    ms_txt = (ROOT / "core" / "motion_shorts.py").read_text(encoding="utf-8", errors="replace")
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
    for sym in ("def audit_voice_consistency", "def generate_and_audit_scenes", "def audit_scene_visual_with_vision"):
        if sym not in sa_txt:
            errors.append(f"CONTRATO VIOLADO: {sym} ausente em core/scene_auditor.py.")
    fc_txt = (ROOT / "core" / "flow_continuity.py").read_text(encoding="utf-8", errors="replace")
    if "def _inject_at_character_mentions" not in fc_txt:
        errors.append("CONTRATO VIOLADO: _inject_at_character_mentions ausente em core/flow_continuity.py.")

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
