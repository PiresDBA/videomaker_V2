# -*- coding: utf-8 -*-
"""Planejador de ritmo visual (3.5-5.0s por cena), Ken Burns e Dual-Avatar Frida x Luna."""
from __future__ import annotations

import math
from typing import Any

from config import KEN_BURNS_PRESETS, MAX_IMAGE_SECONDS, TARGET_BEAT_SECONDS
from core.media_studio import build_image_prompt

_SPLIT_VARIANTS = ("main", "reaction", "angle_b", "detail")


def _parse_pip_window(win: str | None, audio_dur: float, scene_dur: float) -> tuple[float, float]:
    """Converte 'X.Xs->end' ou 'X.Xs->Y.Ys' em offsets (segundos) relativos ao inicio da cena."""
    if not win:
        return 0.0, scene_dur
    try:
        a, b = [p.strip().lower().rstrip("s") for p in str(win).split("->")]
        st = max(0.0, float(a))
        en = scene_dur if b in ("end", "fim") else min(scene_dur, float(b))
        if en - st < 0.8:
            return 0.0, scene_dur
        return round(st, 3), round(en, 3)
    except Exception:
        return 0.0, scene_dur


def build_pacing_plan(
    script_data: dict[str, Any],
    tts_timings: list[dict[str, Any]],
    gap_seconds: float = 0.25,
    montage_plan: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    """Garante <= 5.0s por imagem, alterna Ken Burns e define o avatar ativo (frida/luna/duo).

    Com `montage_plan` (plano de direcao cena a cena): aplica `comic_beat_pause_s` apos cada fala,
    PiP pontual (personagem/canto/janela), overlay narrativo por cena e `force_still_parts`.
    """
    timing_by_id = {t["scene_id"]: t for t in tts_timings}
    plan_by_id: dict[str, dict[str, Any]] = {}
    if montage_plan:
        plan_by_id = {str(s["scene_id"]): s for s in montage_plan.get("scenes", [])}
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
        base_gap = gap_seconds if sc_idx < len(scenes) - 1 else 0.35
        base_dur = round(audio_dur + base_gap, 3)
        sp = plan_by_id.get(sid)
        pause = float(sp.get("comic_beat_pause_s", base_gap)) if sp else base_gap
        scene_dur = round(audio_dur + pause, 3)

        # Numero de partes fixado pela duracao base (preserva imagens existentes), ampliado so se violar o teto
        n_parts = 1 if base_dur <= MAX_IMAGE_SECONDS else max(2, math.ceil(base_dur / TARGET_BEAT_SECONDS))
        while scene_dur / n_parts > MAX_IMAGE_SECONDS:
            n_parts += 1
        part_dur = round(scene_dur / n_parts, 3)

        speaker = str(sc.get("speaker") or "narrador").lower()
        avatar_mode = str(sc.get("avatar_mode") or ("frida" if sc.get("avatar_pip") else "none")).lower()

        pip_plan: dict[str, Any] | None = None
        overlay_style = None
        force_still: set[int] = set()
        if sp:
            avatar_mode = str(sp.get("pip_character") or "none").lower() if sp.get("pip_enabled") else "none"
            if sp.get("pip_enabled"):
                w_st, w_en = _parse_pip_window(sp.get("pip_window"), audio_dur, scene_dur)
                pip_plan = {
                    "character": avatar_mode,
                    "corner": str(sp.get("pip_corner") or "TR").upper(),
                    "start_offset": w_st,
                    "end_offset": w_en,
                }
            overlay_style = sp.get("overlay_style")
            force_still = {int(x) for x in (sp.get("force_still_parts") or [])}

        for p_idx in range(n_parts):
            variant = _SPLIT_VARIANTS[p_idx % len(_SPLIT_VARIANTS)]
            img_key = f"{sid}_p{p_idx + 1}"
            prompts_manifest[img_key] = build_image_prompt(sc, variant=variant)

            kb_preset = KEN_BURNS_PRESETS[kb_idx % len(KEN_BURNS_PRESETS)]
            kb_idx += 1

            dur_this = round(scene_dur - part_dur * (n_parts - 1), 3) if p_idx == n_parts - 1 else part_dur
            sub_start = round(cursor + p_idx * part_dur, 3)

            clip = {
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
                "scene_total_dur": scene_dur,
                "comic_beat_pause_s": round(pause, 3),
                "wav_path": t_info["wav_path"],
            }
            if pip_plan:
                clip["pip_plan"] = pip_plan
            if overlay_style:
                clip["overlay_style"] = overlay_style
            if (p_idx + 1) in force_still:
                clip["force_still"] = True
            visual_clips.append(clip)

        cursor = round(cursor + scene_dur, 3)

    return visual_clips, prompts_manifest
