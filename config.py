# -*- coding: utf-8 -*-
"""Configuracao central e autocontida do Videomaker v2 (Estudio Unico Frida & Luna)."""
from __future__ import annotations

import os
import shutil
import subprocess
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
    """Localiza ffmpeg e ffprobe priorizando binarios internos (autocontido) e depois PATH/utilitarios."""
    candidates = [
        (BASE_DIR / "bin" / "ffmpeg.exe", BASE_DIR / "bin" / "ffprobe.exe"),
        (VENDOR_DIR / "ffmpeg" / "bin" / "ffmpeg.exe", VENDOR_DIR / "ffmpeg" / "bin" / "ffprobe.exe"),
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

CPU_WORKERS = min(8, max(4, os.cpu_count() or 6))
NVENC_WORKERS = 2  # GTX 1060 suporta sessoes NVENC simultaneas com seguranca
_HAS_NVENC_CACHE: bool | None = None


def has_nvenc() -> bool:
    """Detecta suporte real a h264_nvenc na GPU NVIDIA (ex.: GTX 1060 6GB)."""
    global _HAS_NVENC_CACHE
    if _HAS_NVENC_CACHE is not None:
        return _HAS_NVENC_CACHE
    try:
        r = subprocess.run(
            [
                FFMPEG_EXE, "-y", "-v", "error",
                "-f", "lavfi", "-i", "color=c=black:s=128x128:d=0.1",
                "-c:v", "h264_nvenc", "-f", "null", "-",
            ],
            capture_output=True,
            timeout=6,
        )
        _HAS_NVENC_CACHE = (r.returncode == 0)
    except Exception:
        _HAS_NVENC_CACHE = False
    return _HAS_NVENC_CACHE


def get_h264_encoder_args(quality: str = "fast", allow_nvenc: bool = True) -> list[str]:
    """Retorna flags H.264 aceleradas por GPU (NVENC) ou fallback multi-core i7 (libx264)."""
    if allow_nvenc and has_nvenc():
        cq = "18" if quality == "master" else "19"
        preset = "p5" if quality == "master" else "p3"
        return ["-c:v", "h264_nvenc", "-preset", preset, "-rc", "vbr", "-cq", cq, "-pix_fmt", "yuv420p"]
    preset_cpu = "medium" if quality == "master" else "veryfast"
    crf_cpu = "18" if quality in ("master", "fast") else "17"
    return ["-c:v", "libx264", "-preset", preset_cpu, "-crf", crf_cpu, "-threads", "0", "-pix_fmt", "yuv420p"]

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
TARGET_VEO_VIDEOS = 10
MAX_VEO_GENERATIONS_PER_SCENE = 1
VOICE_LOCK_STRICT = True

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
        "FRIDA: young child-like female English bulldog puppy (around 10 months to 1 year old max, "
        "equivalent to a cute 6-to-10-year-old kid character in a 3D Disney Pixar movie, matching her avatar reference; "
        "youthful compact kid build, NOT an old or heavy mature adult dog and NOT a newborn infant), "
        "soft fawn golden-tan stylized 3D cartoon coat with cream chest and muzzle, gentle cute youthful face, "
        "short cute snout, small folded ears, big glossy expressive brown cartoon eyes with long curved eyelashes, "
        "graceful playful child expression, wearing a white pearl necklace with a small golden paw/flower pendant and tiny pearl ear stud"
    ),
    "luna": (
        "LUNA: young child-like female miniature smooth-haired dachshund puppy (around 10 months to 1 year old max, "
        "equivalent to a cute 6-to-10-year-old kid/tween character in a 3D Disney Pixar movie, matching her avatar reference; "
        "graceful youthful kid proportions, NOT an aged mature adult dog and NOT a newborn infant), "
        "dark chocolate-brown glossy stylized 3D cartoon coat with warm tan markings on muzzle, eyebrows, chest and paws, "
        "long velvety floppy ears, big sparkling expressive brown cartoon eyes with long eyelashes, small pearl ear stud, "
        "wearing a delicate double golden chain necklace with tiny heart pendants"
    ),
    "style": (
        "stylized 3D Disney Pixar animated feature film aesthetic matching the official character avatars, "
        "youthful child-like puppy characters (1 year old max, 5-to-10-year-old kid cartoon appeal), "
        "big expressive cartoon eyes, soft rounded graceful 3D cartoon geometry, vibrant fairytale lighting, "
        "non-photorealistic stylized 3D animation, never realistic live-action dogs, never old or mature adult dogs, "
        "dog-eye-level camera, no humans"
    ),
}

POSITIVE_IMAGE_RULE = "single full-frame 16:9 widescreen cinematic scene, unified single composition"
NEGATIVE_IMAGE_RULE = (
    "split screen, comic panels, grid, multi-panel, collage, storyboard, "
    "frames, text, letters, numbers, watermark, subtitles, speech bubbles, "
    "old dogs, mature adult dogs, heavy aged wrinkles, photorealistic live-action dogs, realistic coarse fur, scary or aggressive dogs"
)

CREDENTIALS_DIR = BASE_DIR / ".credentials"
CHIRP3_CREDENTIALS_DEFAULT = CREDENTIALS_DIR / "google_cloud_tts.json"
CHIRP3_OAUTH_CLIENT_DEFAULT = CREDENTIALS_DIR / "client_secret_tts.json"
CHIRP3_OAUTH_TOKEN_DEFAULT = CREDENTIALS_DIR / "cloud_tts_token.json"
CHIRP3_USAGE_STATE_FILE = CREDENTIALS_DIR / "chirp3_usage.json"
CHIRP3_MONTHLY_CHAR_LIMIT = 950_000  # Trava de seguranca abaixo da franquia gratuita de 1.000.000 chars/mes

# Casting emocional multi-voz (Gemini 3.8/2.5 Flash TTS + Google Cloud Chirp 3 HD travado)
GEMINI_TTS_MODELS = ("gemini-3.8-flash-tts", "gemini-2.5-flash-preview-tts")

SPEAKER_VOICE_PROFILES = {
    "narrador": {
        "gemini_voice": "Kore",
        "chirp3_voice": "pt-BR-Chirp3-HD-Kore",
        "gemini_alt_voices": (),
        "profile": "narrador",
        "emotion": "Narradora feminina jovem, amiga, muito alegre, sorridente e saltitante: narre com entusiasmo contagiante e sorriso na voz do início ao fim (nunca séria ou jornalística)",
        "edge_voice": "pt-BR-ThalitaNeural",
        "edge_rate": "+6%",
        "edge_pitch": "+4Hz",
        "subtitle_ass_color": "&H00FFFFFF",
    },
    "frida": {
        "gemini_voice": "Sulafat",
        "chirp3_voice": "pt-BR-Chirp3-HD-Sulafat",
        "gemini_alt_voices": (),
        "profile": "infantil",
        "emotion": "Voz feminina infantil muito jovem, super alegre, sorridente, risonha, saltitante e brincalhona de cachorrinha amiga",
        "edge_voice": "pt-BR-FranciscaNeural",
        "edge_rate": "-2%",
        "edge_pitch": "-5Hz",
        "subtitle_ass_color": "&H0051C4F5",
    },
    "luna": {
        "gemini_voice": "Leda",
        "chirp3_voice": "pt-BR-Chirp3-HD-Leda",
        "gemini_alt_voices": (),
        "profile": "infantil",
        "emotion": "Voz feminina infantil muito jovem, divertida, sorridente, saltitante, risonha e cheia de animação e curiosidade",
        "edge_voice": "pt-BR-ThalitaNeural",
        "edge_rate": "+12%",
        "edge_pitch": "+12Hz",
        "subtitle_ass_color": "&H00F5E04C",
    },
    "secundario": {
        "gemini_voice": "Puck",
        "chirp3_voice": "pt-BR-Chirp3-HD-Puck",
        "gemini_alt_voices": (),
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
