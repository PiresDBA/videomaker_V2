# -*- coding: utf-8 -*-
"""Planejador de ritmo visual (3.5-5.0s por cena), Ken Burns e Dual-Avatar Frida x Luna."""
from __future__ import annotations

import math
from typing import Any

from config import KEN_BURNS_PRESETS, MAX_IMAGE_SECONDS, TARGET_BEAT_SECONDS
from core.media_studio import build_image_prompt

_SPLIT_VARIANTS = ("main", "reaction", "angle_b", "detail")


def build_pacing_plan(
    script_data: dict[str, Any],
    tts_timings: list[dict[str, Any]],
    gap_seconds: float = 0.25,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    """Garante <= 5.0s por imagem, alterna Ken Burns e define o avatar ativo (frida/luna/duo)."""
    timing_by_id = {t["scene_id"]: t for t in tts_timings}
    visual_clips: list[dict[str, Any]] = []
    prompts_manifest: dict[str, dict[str, str]] = {}

    cursor = 0.0
    kb_idx = 0
    scenes = script_data.get("scenes", [])

    for sc_idx, sc in enumerate(scenes):
        sid = sc["scene_id"]
        t_info = timing_by_id.get(sid)
        if not t_info or float(t_info.get("duration", 0.0)) <= 0:
            continue

        audio_dur = float(t_info["duration"])
        scene_dur = round(audio_dur + (gap_seconds if sc_idx < len(scenes) - 1 else 0.35), 3)
        n_parts = 1 if scene_dur <= MAX_IMAGE_SECONDS else max(2, math.ceil(scene_dur / TARGET_BEAT_SECONDS))
        part_dur = round(scene_dur / n_parts, 3)

        speaker = str(sc.get("speaker") or "narrador").lower()
        avatar_mode = str(sc.get("avatar_mode") or ("frida" if sc.get("avatar_pip") else "none")).lower()

        for p_idx in range(n_parts):
            variant = _SPLIT_VARIANTS[p_idx % len(_SPLIT_VARIANTS)]
            img_key = f"{sid}_p{p_idx + 1}"
            prompts_manifest[img_key] = build_image_prompt(sc, variant=variant)

            kb_preset = KEN_BURNS_PRESETS[kb_idx % len(KEN_BURNS_PRESETS)]
            kb_idx += 1

            dur_this = round(scene_dur - part_dur * (n_parts - 1), 3) if p_idx == n_parts - 1 else part_dur
            sub_start = round(cursor + p_idx * part_dur, 3)

            visual_clips.append({
                "clip_id": img_key,
                "scene_id": sid,
                "act": sc.get("act", 1),
                "speaker": speaker,
                "location": sc.get("location", ""),
                "text": sc.get("text", ""),
                "sfx": sc.get("sfx") if p_idx == 0 else None,
                "avatar_mode": avatar_mode,
                "avatar_pip": avatar_mode != "none",
                "start": sub_start,
                "duration": dur_this,
                "end": round(sub_start + dur_this, 3),
                "ken_burns": kb_preset,
                "variant": variant,
                "scene_audio_start": round(cursor, 3),
                "scene_audio_dur": audio_dur,
                "wav_path": t_info["wav_path"],
            })

        cursor = round(cursor + scene_dur, 3)

    return visual_clips, prompts_manifest
