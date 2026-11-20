# -*- coding: utf-8 -*-
"""Configuracao central e autocontida do Videomaker v2 (Estudio Unico Frida & Luna)."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
CORE_DIR = BASE_DIR / "core"
VENDOR_DIR = BASE_DIR / "vendor"
ASSETS_DIR = BASE_DIR / "assets"
PROJECTS_DIR = BASE_DIR / "projects"
ENV_FILE = BASE_DIR / ".env"

AVATARS_DIR = ASSETS_DIR / "avatars"
REFERENCE_DIR = ASSETS_DIR / "reference"
MUSIC_DIR = ASSETS_DIR / "music"
SFX_CACHE_DIR = ASSETS_DIR / "sfx_cache"

FRIDA_LUNA_REF_SHEET = REFERENCE_DIR / "frida_luna_reference.jpg"


def resolve_ffmpeg() -> tuple[str, str]:
    """Localiza ffmpeg e ffprobe disponiveis no ambiente."""
    candidates = [
        (Path(r"D:\Utilitarios\ffmpeg\bin\ffmpeg.exe"), Path(r"D:\Utilitarios\ffmpeg\bin\ffprobe.exe")),
        (Path(r"C:\videomaker\ffmpeg\bin\ffmpeg.exe"), Path(r"C:\videomaker\ffmpeg\bin\ffprobe.exe")),
    ]
    for ff, fp in candidates:
        if ff.exists() and fp.exists():
            return str(ff), str(fp)
    which_ff = shutil.which("ffmpeg")
    which_fp = shutil.which("ffprobe")
    if which_ff:
        return which_ff, (which_fp or which_ff.replace("ffmpeg", "ffprobe"))
    try:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        return ff, ff
    except Exception:
        return "ffmpeg", "ffprobe"


FFMPEG_EXE, FFPROBE_EXE = resolve_ffmpeg()

# Avatares 100% embutidos dentro de assets/avatars/<personagem>/
AVATAR_PROFILES = {
    "frida": {
        "label": "Frida",
        "dir": AVATARS_DIR / "frida",
        "border_gold_bgr": (74, 178, 240),   # Dourado quente
        "border_accent_bgr": (234, 246, 255),
        "subtitle_ass_color": "&H0051C4F5",   # Dourado (BGR ASS)
        "corner": "right",
    },
    "luna": {
        "label": "Luna",
        "dir": AVATARS_DIR / "luna",
        "border_gold_bgr": (225, 195, 45),   # Turquesa vibrante
        "border_accent_bgr": (255, 248, 232),
        "subtitle_ass_color": "&H00F5E04C",   # Ciano/Turquesa (BGR ASS)
        "corner": "left",
    },
}


def get_avatar_clips(character: str) -> dict[str, Any]:
    """Retorna caminhos reais de reposo.mp4 e hablando_*.mp4 dentro de assets/avatars/."""
    prof = AVATAR_PROFILES.get(character.lower())
    if not prof:
        return {"reposo": None, "hablando": []}
    d = prof["dir"]
    rep = d / "reposo.mp4"
    habs = sorted(d.glob("hablando*.mp4"))
    return {
        "reposo": rep if rep.exists() and rep.stat().st_size > 10000 else None,
        "hablando": [p for p in habs if p.exists() and p.stat().st_size > 10000],
    }


# Limites rigidos de roteiro, ritmo e YouTube Shorts
SCRIPT_MIN_WORDS = 450
SCRIPT_MAX_WORDS = 550
SCRIPT_TARGET_MINUTES = (3, 4)
CTA_TAIL_SECONDS = 10.0

MAX_IMAGE_SECONDS = 5.0
MIN_IMAGE_SECONDS = 3.5
TARGET_BEAT_SECONDS = 4.2

SHORT_MIN_SECONDS = 30.0
SHORT_MAX_SECONDS = 40.0
SHORT_TARGET_SECONDS = 35.0
SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920
SHORT_SAFE_BOTTOM_PX = 260

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30
THUMB_WIDTH = 1280
THUMB_HEIGHT = 720

# Biblia Visual fixa (injetada de forma limpa em todo prompt de imagem)
VISUAL_BIBLE = {
    "frida": (
        "FRIDA: female English bulldog, large compact and stocky build, "
        "fawn golden-tan coat with cream chest and muzzle, soft facial wrinkles, "
        "short flat snout, small folded ears, big expressive brown eyes with eyelashes, "
        "wearing a white pearl necklace with a small crystal flower pendant"
    ),
    "luna": (
        "LUNA: female miniature smooth-haired dachshund (sausage dog), "
        "dark chocolate-brown glossy coat with warm tan markings on muzzle, eyebrows, "
        "chest and paws, very long elongated body, short stubby legs, long floppy ears, "
        "big expressive brown eyes with eyelashes, small pearl ear stud, "
        "wearing a delicate double golden chain necklace with heart pendants"
    ),
    "style": (
        "high-end 3D family animated movie style, soft global illumination, "
        "detailed fur shading, rich expressive cartoon faces, dog-eye-level camera, no humans"
    ),
}

POSITIVE_IMAGE_RULE = "single full-frame 16:9 widescreen cinematic scene, unified single composition"
NEGATIVE_IMAGE_RULE = (
    "split screen, comic panels, grid, multi-panel, collage, storyboard, "
    "frames, text, letters, numbers, watermark, subtitles, speech bubbles"
)

# Casting emocional multi-voz (Gemini 3.8/2.5 Flash TTS + fallback Edge apenas em ultimo recurso)
GEMINI_TTS_MODELS = ("gemini-3.8-flash-tts", "gemini-2.5-flash-preview-tts")

SPEAKER_VOICE_PROFILES = {
    "narrador": {
        "gemini_voice": "Kore",
        "gemini_alt_voices": ("Puck", "Aoede"),
        "profile": "narrador",
        "emotion": "Narre com energia contagiante, curiosidade e ritmo vivo de storytelling infantil",
        "edge_voice": "pt-BR-ThalitaNeural",
        "edge_rate": "+6%",
        "edge_pitch": "+4Hz",
        "subtitle_ass_color": "&H00FFFFFF",
    },
    "frida": {
        "gemini_voice": "Sulafat",
        "gemini_alt_voices": ("Aoede", "Leda"),
        "profile": "infantil",
        "emotion": "Voz feminina doce, calorosa, levemente grave e expressiva de buldogue simpatica",
        "edge_voice": "pt-BR-FranciscaNeural",
        "edge_rate": "-2%",
        "edge_pitch": "-5Hz",
        "subtitle_ass_color": "&H0051C4F5",
    },
    "luna": {
        "gemini_voice": "Leda",
        "gemini_alt_voices": ("Zephyr", "Puck"),
        "profile": "infantil",
        "emotion": "Voz feminina infantil brilhante, rapida, curiosa e dramatica de cachorrinha agitada",
        "edge_voice": "pt-BR-ThalitaNeural",
        "edge_rate": "+12%",
        "edge_pitch": "+12Hz",
        "subtitle_ass_color": "&H00F5E04C",
    },
    "secundario": {
        "gemini_voice": "Puck",
        "gemini_alt_voices": ("Fenrir", "Orus"),
        "profile": "narrador",
        "emotion": "Voz divertida, expressiva e teatral de personagem coadjuvante de desenho animado",
        "edge_voice": "pt-BR-AntonioNeural",
        "edge_rate": "+4%",
        "edge_pitch": "+6Hz",
        "subtitle_ass_color": "&H00A8FF99",
    },
}

# Limiares acusticos de emocao calibrados (VoiceCraft / prosodia.py)
PROSODY_LIMITS = {
    "taxa_min": 10.6,
    "taxa_max": 19.5,
    "amplitude_min": 8.0,
    "pausa_min": 0.04,
    "pausa_max": 0.45,
    "dinamica_min": 0.25,
    "ataque_max": 0.50,
}

KEN_BURNS_PRESETS = ("zoom_in", "zoom_out", "pan_left", "pan_right")
