# -*- coding: utf-8 -*-
"""Planejador de ritmo visual (3.5-5.0s por cena), Ken Burns e Dual-Avatar Frida x Luna."""
from __future__ import annotations

import math
from typing import Any

from config import (
    BURST_KEYWORDS, BURST_MAX_SCENES, BURST_MONTAGE,
    IMAGE_MONTAGE_BEAT_SECONDS, IMAGE_MONTAGE_MAX_PARTS, KEN_BURNS_PRESETS,
    MAX_IMAGE_SECONDS, RICH_IMAGE_MONTAGE, SLOWMO_XFADE_SECONDS, TARGET_BEAT_SECONDS,
)
from core.media_studio import build_image_prompt

_SPLIT_VARIANTS = ("main", "reaction", "angle_b", "detail", "close")


def build_pacing_plan(
    script_data: dict[str, Any],
    tts_timings: list[dict[str, Any]],
    gap_seconds: float = 0.25,
    video_scene_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    """Garante <= 5.0s por imagem, alterna Ken Burns e define o avatar ativo (frida/luna/duo).

    `video_scene_ids`: cenas que ja tem video Veo (movimento real) — a rajada as ignora
    para nao duplicar movimento (Regra 20: equilibrio entre Veo, rajada e estatico).
    """
    timing_by_id = {t["scene_id"]: t for t in tts_timings}
    visual_clips: list[dict[str, Any]] = []
    prompts_manifest: dict[str, dict[str, str]] = {}

    cursor = 0.0
    kb_idx = 0
    scenes = script_data.get("scenes", [])
    sec_chars = script_data.get("secondary_characters") or []
    story_props = script_data.get("story_props") or []

    burst_scenes_used = 0
    for sc_idx, sc in enumerate(scenes):
        sid = sc["scene_id"]
        t_info = timing_by_id.get(sid)
        if not t_info or float(t_info.get("duration", 0.0)) <= 0:
            continue

        audio_dur = float(t_info["duration"])
        scene_dur = round(audio_dur + (gap_seconds if sc_idx < len(scenes) - 1 else 0.35), 3)
        n_parts = 1 if scene_dur <= MAX_IMAGE_SECONDS else max(2, math.ceil(scene_dur / TARGET_BEAT_SECONDS))
        if RICH_IMAGE_MONTAGE:
            # Regra 20: mais sub-clips curtos -> troca suave (xfade) com aparencia de movimento.
            rich_parts = min(IMAGE_MONTAGE_MAX_PARTS, max(2, math.ceil(scene_dur / IMAGE_MONTAGE_BEAT_SECONDS)))
            n_parts = max(n_parts, rich_parts)
        # Regra 28: cada quadro do slow-motion precisa ficar >= 1,0s na tela.
        # Frases curtas (1 parte) sao melhores do que dois quadros de 0,5s.
        n_parts = max(1, min(n_parts, int(scene_dur / 1.0))) if scene_dur >= 1.0 else 1
        # Sequencia de imagens (stop-motion): o roteiro traz N quadros progressivos
        # (ex.: gaivota subindo -> descendo -> no biscoito). Forcamos n_parts = N e
        # dissolve curto entre eles para simular movimento.
        seq_imgs = sc.get("image_sequence") if isinstance(sc.get("image_sequence"), list) else []
        is_sequence = len(seq_imgs) >= 2 and sid not in (video_scene_ids or set())
        if is_sequence:
            n_parts = len(seq_imgs)
        part_dur = round(scene_dur / n_parts, 3)

        speaker = str(sc.get("speaker") or "narrador").lower()
        avatar_mode = str(sc.get("avatar_mode") or ("frida" if sc.get("avatar_pip") else "none")).lower()

        # SLOW-MOTION (correcao do "tremendo dos lados"): cena sem video Veo vira
        # UM movimento continuo — as partes usam a MESMA imagem base com Ken Burns
        # diferentes e dissolve longo entre elas. Nunca mais flipbook de 0,14s.
        hay = f"{sc.get('text', '')} {sc.get('visual_action', '')} {sc.get('comedy_beat', '')}".lower()
        scene_is_burst = (
            BURST_MONTAGE
            and burst_scenes_used < BURST_MAX_SCENES
            and sid not in (video_scene_ids or set())
            and any(k in hay for k in BURST_KEYWORDS)
        )
        if scene_is_burst:
            burst_scenes_used += 1
        has_video_scene = sid in (video_scene_ids or set())

        for p_idx in range(n_parts):
            variant = _SPLIT_VARIANTS[p_idx % len(_SPLIT_VARIANTS)]
            img_key = f"{sid}_p{p_idx + 1}"
            prompts_manifest[img_key] = build_image_prompt(
                sc,
                variant=variant,
                secondary_characters=sec_chars,
                story_props=story_props,
            )

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
                "visual_action": sc.get("visual_action", ""),
                "characters": list(sc.get("characters") or ["Frida", "Luna"]),
                "sfx": sc.get("sfx") if p_idx == 0 else None,
                "comedy_beat": sc.get("comedy_beat", "") if p_idx == 0 else "",
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
                # Cena parada: dissolve LONGO entre as partes (mesma imagem base),
                # lendo como camera lenta. Cena com video Veo mantem o corte curto.
                # Sequencia de imagens: dissolve curto (stop-motion).
                "xfade_duration": (0.0 if has_video_scene
                                   else (0.25 if is_sequence
                                         else round(min(float(SLOWMO_XFADE_SECONDS), max(0.4, part_dur * 0.5)), 3))),
            })
            if scene_is_burst:
                clip = visual_clips[-1]
                clip["burst"] = True
                clip["burst_from"] = f"{sid}_p1"
                clip["burst_index"] = p_idx
                clip["motion"] = "slowmo"
                if p_idx > 0:
                    # som/comedia so no primeiro quadro da cena
                    clip["sfx"] = None
                    clip["comedy_beat"] = ""

        cursor = round(cursor + scene_dur, 3)

    return visual_clips, prompts_manifest
