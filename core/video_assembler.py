# -*- coding: utf-8 -*-
"""Montagem final FFmpeg: Ken Burns, Dual-Avatar Frida & Luna, Legenda Pop ASS, -14 LUFS e Short 9:16."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from config import (
    AVATAR_PROFILES,
    FFMPEG_EXE,
    SHORT_HEIGHT,
    SHORT_MAX_SECONDS,
    SHORT_MIN_SECONDS,
    SHORT_SAFE_BOTTOM_PX,
    SHORT_TARGET_SECONDS,
    SHORT_WIDTH,
    SPEAKER_VOICE_PROFILES,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
)
from core.audio_fx import build_sfx_stem, master_with_soundcraft, resolve_act_bgm
from core.avatar_studio import (
    detect_emptiest_corners,
    render_avatar_pip_clip,
    render_magic_sparkles_overlay,
)
from core.motion_shorts import export_motion_short_9_16
from core.voice_studio import probe_duration


def _fmt_srt_time(seconds: float) -> str:
    sec = max(0.0, float(seconds))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms >= 1000:
        s += 1
        ms -= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _fmt_ass_time(seconds: float) -> str:
    sec = max(0.0, float(seconds))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = min(99, int(round((sec - int(sec)) * 100)))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def write_synced_srt(visual_clips: list[dict[str, Any]], out_srt: Path, offset_s: float = 0.0) -> Path:
    """Gera .srt usando timestamps reais medidos (texto original acentuado)."""
    blocks = []
    seen: set[str] = set()
    idx = 1
    for clip in visual_clips:
        sid = clip["scene_id"]
        if sid in seen:
            continue
        seen.add(sid)
        start = float(clip["scene_audio_start"]) - offset_s
        end = start + float(clip["scene_audio_dur"])
        if end <= 0:
            continue
        start = max(0.0, start)
        txt = " ".join((clip.get("text") or "").split())
        if not txt:
            continue
        blocks.append(f"{idx}\n{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}\n{txt}\n")
        idx += 1
    out_srt.parent.mkdir(parents=True, exist_ok=True)
    out_srt.write_text("\n".join(blocks).strip() + "\n", encoding="utf-8")
    return out_srt


def write_pop_ass(
    visual_clips: list[dict[str, Any]],
    out_ass: Path,
    play_res_x: int = VIDEO_WIDTH,
    play_res_y: int = VIDEO_HEIGHT,
    margin_v: int = 86,
    font_size: int = 62,
    offset_s: float = 0.0,
    words_per_chunk: int = 4,
) -> Path:
    """Gera legenda pop dinamica ASS (blocos de 2-4 palavras) com cor por personagem."""
    header = "\n".join([
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {play_res_x}",
        f"PlayResY: {play_res_y}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Pop,Arial Rounded MT Bold,{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,2,2,48,48,{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ])
    lines = [header]
    seen: set[str] = set()
    for c in visual_clips:
        sid = c["scene_id"]
        if sid in seen:
            continue
        seen.add(sid)
        st = float(c["scene_audio_start"]) - offset_s
        dur = float(c["scene_audio_dur"])
        if st + dur <= 0:
            continue
        words = " ".join((c.get("text") or "").split()).split()
        if not words:
            continue
        spk = str(c.get("speaker") or "narrador").lower()
        color = SPEAKER_VOICE_PROFILES.get(spk, SPEAKER_VOICE_PROFILES["narrador"])["subtitle_ass_color"]
        chunks = [" ".join(words[i:i + words_per_chunk]) for i in range(0, len(words), words_per_chunk)]
        c_dur = dur / max(1, len(chunks))
        for k, ch in enumerate(chunks):
            cs = max(0.0, st + k * c_dur)
            ce = max(cs + 0.08, st + (k + 1) * c_dur)
            tag = r"{\c" + color + r"\fscx92\fscy92\t(0,90,\fscx103\fscy103)}"
            lines.append(f"Dialogue: 0,{_fmt_ass_time(cs)},{_fmt_ass_time(ce)},Pop,,0,0,0,,{tag}{ch}")

    out_ass.parent.mkdir(parents=True, exist_ok=True)
    out_ass.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_ass


def _zoompan_filter(preset: str, duration: float, fps: int = VIDEO_FPS) -> str:
    frames = max(2, int(round(duration * fps)))
    n_denom = max(1, frames - 1)
    if preset == "zoom_in":
        z_expr, x_expr, y_expr = f"1.0+0.12*(on/{n_denom})", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif preset == "zoom_out":
        z_expr, x_expr, y_expr = f"1.12-0.12*(on/{n_denom})", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif preset == "pan_left":
        z_expr, x_expr, y_expr = "1.10", f"(iw-iw/zoom)*(1.0-(on/{n_denom}))", "ih/2-(ih/zoom/2)"
    else:
        z_expr, x_expr, y_expr = "1.10", f"(iw-iw/zoom)*(on/{n_denom})", "ih/2-(ih/zoom/2)"

    return (
        f"scale={VIDEO_WIDTH*2}:{VIDEO_HEIGHT*2}:force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH*2}:{VIDEO_HEIGHT*2},"
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={fps},"
        f"setsar=1,format=yuv420p"
    )


def render_ken_burns_clip(image_path: Path, preset: str, duration: float, out_mp4: Path) -> Path:
    """Renderiza sub-clip estatico com Ken Burns suave em 1920x1080@30fps."""
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [FFMPEG_EXE, "-y", "-v", "error", "-loop", "1", "-framerate", str(VIDEO_FPS),
         "-i", str(image_path), "-vf", _zoompan_filter(preset, duration), "-t", f"{duration:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out_mp4)],
        check=True,
    )
    return out_mp4


def build_narration_track(visual_clips: list[dict[str, Any]], total_dur: float, out_wav: Path) -> Path:
    events: list[tuple[float, Path]] = []
    seen: set[str] = set()
    for c in visual_clips:
        sid = c["scene_id"]
        if sid in seen:
            continue
        seen.add(sid)
        events.append((float(c["scene_audio_start"]), Path(c["wav_path"])))

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG_EXE, "-y", "-v", "error", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={total_dur:.3f}"]
    filters = []
    labels = ["[0:a]"]
    for idx, (st, wpath) in enumerate(events, 1):
        cmd += ["-i", str(wpath)]
        ms = max(0, int(round(st * 1000)))
        filters.append(f"[{idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,adelay={ms}|{ms}[n{idx}]")
        labels.append(f"[n{idx}]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:normalize=0[outn]")
    cmd += ["-filter_complex", ";".join(filters), "-map", "[outn]", "-c:a", "pcm_s16le", str(out_wav)]
    subprocess.run(cmd, check=True)
    return out_wav


def mix_audio_master(
    narration_wav: Path,
    sfx_wav: Path,
    total_dur: float,
    out_m4a: Path,
    bgm_wav: Path | None = None,
) -> Path:
    """Mixa narracao (-16 LUFS) + SFX + BGM com ducking automatico para -14 LUFS."""
    out_m4a.parent.mkdir(parents=True, exist_ok=True)
    if bgm_wav and bgm_wav.exists():
        fc = (
            "[0:a]aformat=sample_rates=44100:channel_layouts=stereo,asplit=2[nar][nar_sc];"
            f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{total_dur:.3f},asetpts=PTS-STARTPTS,"
            "aformat=sample_rates=44100:channel_layouts=stereo,volume=0.22[bgm];"
            "[bgm][nar_sc]sidechaincompress=threshold=0.03:ratio=6:attack=25:release=600[bgm_duck];"
            "[2:a]aformat=sample_rates=44100:channel_layouts=stereo[sfx];"
            "[nar][bgm_duck][sfx]amix=inputs=3:duration=first:normalize=0,"
            "loudnorm=I=-14:TP=-1.5:LRA=11[out]"
        )
        cmd = [FFMPEG_EXE, "-y", "-v", "error", "-i", str(narration_wav), "-i", str(bgm_wav), "-i", str(sfx_wav)]
    else:
        fc = (
            "[0:a]aformat=sample_rates=44100:channel_layouts=stereo[nar];"
            "[1:a]aformat=sample_rates=44100:channel_layouts=stereo[sfx];"
            "[nar][sfx]amix=inputs=2:duration=first:normalize=0,"
            "loudnorm=I=-14:TP=-1.5:LRA=11[out]"
        )
        cmd = [FFMPEG_EXE, "-y", "-v", "error", "-i", str(narration_wav), "-i", str(sfx_wav)]

    cmd += ["-filter_complex", fc, "-map", "[out]", "-t", f"{total_dur:.3f}", "-c:a", "aac", "-b:a", "192k", str(out_m4a)]
    subprocess.run(cmd, check=True)
    return out_m4a


_CORNER_POS = {
    "TL": ("44", "42"),
    "TR": ("W-w-44", "42"),
    "BL": ("44", "H-h-42"),
    "BR": ("W-w-44", "H-h-42"),
}


def _plan_avatar_overlays(
    visual_clips: list[dict[str, Any]],
    images_dir: Path,
    avatar_dir: Path,
) -> list[tuple[float, float, str, str, Path]]:
    """Prepara overlays de Dual-Avatar usando os cantos mais vazios da cena (evita cobrir rostos)."""
    overlays: list[tuple[float, float, str, str, Path]] = []
    seen: set[str] = set()
    for c in visual_clips:
        sid = c["scene_id"]
        if sid in seen:
            continue
        seen.add(sid)
        mode = str(c.get("avatar_mode") or "none").lower()
        if mode == "none":
            continue

        spk = str(c.get("speaker") or "narrador").lower()
        st = float(c["scene_audio_start"])
        dur = float(c["scene_audio_dur"])
        en = st + dur
        wav = Path(c["wav_path"])

        corners = detect_emptiest_corners(images_dir / f"{c['clip_id']}.jpg")
        if mode == "duo":
            targets = [("frida", spk == "frida"), ("luna", spk == "luna")]
            if spk not in ("frida", "luna"):
                targets = [("frida", False), ("luna", False)]
        elif mode in ("frida", "luna"):
            targets = [(mode, True)]
        else:
            continue

        used_corners: list[str] = []
        for char, active in targets:
            mov = avatar_dir / f"{sid}_{char}.mov"
            card_sz = 285 if active else 235
            res = render_avatar_pip_clip(sid, char, wav, dur, mov, card_size=card_sz, is_active_speaker=active)
            if res and res.exists():
                # No modo duo, coloca Frida e Luna em cantos distintos priorizando os mais vazios
                chosen = next((cn for cn in corners if cn not in used_corners), corners[0])
                used_corners.append(chosen)
                x_expr, y_expr = _CORNER_POS[chosen]
                overlays.append((st, en, x_expr, y_expr, res))
    return overlays


def export_short_9_16(
    master_16_9: Path,
    visual_clips: list[dict[str, Any]],
    out_short: Path,
    hook_badge: str = "FRIDA & LUNA",
    engine: str = "auto",
) -> Path:
    """Delega para core.motion_shorts (Remotion / FFmpeg Motion HUD)."""
    return export_motion_short_9_16(master_16_9, visual_clips, out_short, hook_badge=hook_badge, engine=engine)


def assemble_video(
    visual_clips: list[dict[str, Any]],
    images_dir: Path,
    work_dir: Path,
    out_mp4: Path,
    out_srt: Path,
    bgm_wav: Path | None = None,
    with_avatar: bool = True,
    burn_captions: bool = False,
) -> tuple[Path, Path]:
    """Monta 16:9 final com Ken Burns, Dual-Avatar PiP, SFX, BGM por ato e -14 LUFS."""
    clips_dir = work_dir / "clips"
    avatar_dir = work_dir / "avatar_pip"
    clips_dir.mkdir(parents=True, exist_ok=True)
    avatar_dir.mkdir(parents=True, exist_ok=True)

    rendered_segments: list[Path] = []
    for clip in visual_clips:
        img_path = images_dir / f"{clip['clip_id']}.jpg"
        if not img_path.exists():
            raise FileNotFoundError(f"Imagem ausente: {img_path}")
        seg_mp4 = clips_dir / f"{clip['clip_id']}.mp4"
        render_ken_burns_clip(img_path, clip["ken_burns"], float(clip["duration"]), seg_mp4)
        rendered_segments.append(seg_mp4)

    concat_txt = work_dir / "concat_video.txt"
    concat_txt.write_text("\n".join("file '%s'" % p.as_posix() for p in rendered_segments) + "\n", encoding="utf-8")
    base_video = work_dir / "base_video_16x9.mp4"
    subprocess.run(
        [FFMPEG_EXE, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", str(base_video)],
        check=True,
    )

    total_dur = probe_duration(base_video)
    nar_wav = work_dir / "narration_master.wav"
    nar_sc_wav = work_dir / "narration_soundcraft.wav"
    sfx_wav = work_dir / "sfx_master.wav"
    mix_m4a = work_dir / "final_mix.m4a"
    build_narration_track(visual_clips, total_dur, nar_wav)
    nar_mastered = master_with_soundcraft(nar_wav, nar_sc_wav)
    build_sfx_stem(visual_clips, total_dur, sfx_wav, narration_wav=nar_mastered)
    chosen_bgm = resolve_act_bgm(visual_clips, total_dur, work_dir, bgm_wav)
    mix_audio_master(nar_mastered, sfx_wav, total_dur, mix_m4a, bgm_wav=chosen_bgm)

    write_synced_srt(visual_clips, out_srt)
    ass_16_9 = work_dir / "captions_pop.ass"
    if burn_captions:
        write_pop_ass(visual_clips, ass_16_9)

    overlays = _plan_avatar_overlays(visual_clips, images_dir, avatar_dir) if with_avatar else []
    sparkles_mov = avatar_dir / "hook_sparkles.mov"
    hook_spark_dur = min(7.5, total_dur)
    if with_avatar and hook_spark_dur >= 2.0:
        render_magic_sparkles_overlay(hook_spark_dur, sparkles_mov)
    else:
        sparkles_mov = None

    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    if not overlays and not burn_captions and not (sparkles_mov and sparkles_mov.exists()):
        subprocess.run(
            [FFMPEG_EXE, "-y", "-v", "error", "-i", str(base_video), "-i", str(mix_m4a),
             "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out_mp4)],
            check=True,
        )
        return out_mp4, out_srt

    cmd = [FFMPEG_EXE, "-y", "-v", "error", "-i", str(base_video)]
    filters = []
    prev = "[0:v]"
    in_idx = 1

    if sparkles_mov and sparkles_mov.exists():
        cmd += ["-i", str(sparkles_mov)]
        nxt = "[vsp]"
        filters.append(f"{prev}[{in_idx}:v]overlay=0:0:enable='between(t,0,{hook_spark_dur:.3f})':eof_action=pass{nxt}")
        prev = nxt
        in_idx += 1

    for idx, (st, en, x_expr, y_expr, mov_path) in enumerate(overlays):
        cmd += ["-itsoffset", f"{st:.3f}", "-i", str(mov_path)]
        nxt = f"[v{idx}]"
        filters.append(
            f"{prev}[{in_idx}:v]overlay=x={x_expr}:y={y_expr}:enable='between(t,{st:.3f},{en:.3f})':eof_action=pass{nxt}"
        )
        prev = nxt
        in_idx += 1

    if burn_captions:
        nxt = "[vcap]"
        filters.append(f"{prev}ass={ass_16_9.name}{nxt}")
        prev = nxt

    cmd += ["-i", str(mix_m4a)]
    audio_idx = in_idx
    subprocess.run(
        cmd + ["-filter_complex", ";".join(filters), "-map", prev, "-map", f"{audio_idx}:a",
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
               "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out_mp4)],
        cwd=str(work_dir),
        check=True,
    )
    return out_mp4, out_srt
