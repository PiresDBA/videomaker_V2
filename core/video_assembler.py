# -*- coding: utf-8 -*-
"""Montagem final FFmpeg: Ken Burns, Dual-Avatar Frida & Luna, Legenda Pop ASS, -14 LUFS e Short 9:16."""
from __future__ import annotations

import concurrent.futures
import math
import re
import subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from config import (
    AVATAR_PROFILES,
    CPU_WORKERS,
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
    get_h264_encoder_args,
)
from core.audio_fx import build_sfx_stem, master_with_soundcraft, resolve_act_bgm
from core.avatar_studio import (
    _index_character_bank,
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


def _run_h264_ffmpeg(
    cmd_head: list[str],
    tail_args: list[str],
    quality: str = "fast",
    cwd: str | None = None,
    allow_nvenc: bool = True,
) -> None:
    """Executa encode H.264 preferindo GPU (h264_nvenc) e caindo automaticamente para libx264 multi-thread."""
    enc_args = get_h264_encoder_args(quality=quality, allow_nvenc=allow_nvenc)
    try:
        subprocess.run(cmd_head + enc_args + tail_args, cwd=cwd, check=True)
    except subprocess.CalledProcessError:
        if "h264_nvenc" not in enc_args:
            raise
        cpu_args = get_h264_encoder_args(quality=quality, allow_nvenc=False)
        subprocess.run(cmd_head + cpu_args + tail_args, cwd=cwd, check=True)


def render_ken_burns_clip(
    image_path: Path,
    preset: str,
    duration: float,
    out_mp4: Path,
    allow_nvenc: bool = True,
) -> Path:
    """Renderiza sub-clip estatico com Ken Burns suave em 1920x1080@30fps."""
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    _run_h264_ffmpeg(
        [FFMPEG_EXE, "-y", "-v", "error", "-loop", "1", "-framerate", str(VIDEO_FPS),
         "-i", str(image_path), "-vf", _zoompan_filter(preset, duration), "-t", f"{duration:.3f}"],
        [str(out_mp4)],
        quality="fast",
        allow_nvenc=allow_nvenc,
    )
    return out_mp4


_OVERLAY_RULES: tuple[tuple[str, str], ...] = (
    (r"dorm|cochil|sleep|acordou|pregui[cç]", "zzz"),
    (r"lareira|fogueira|fogo|fireplace|chama", "fire"),
    (r"biscoit|ossinh|lanche|comid|pote|biscuit|food", "steam"),
    (r"abra[cç]|carinh|amig|obrigad|desculp|amor|cora[cç]|gentil|doce|hug|sweet", "hearts"),
    (r"margarid|flor|jardim|abelh|borbolet|daisies|flower", "bees"),
    (r"pombo|passarinh|pigeon|bird|voou|bico", "birds"),
    (r"vagalum|firefl|noite|twilight", "fireflies"),
    (r"poeira\s+dourada|m[aá]gic|espirr|brilh|sparkl", "sparkles"),
)


def infer_scene_overlay_style(clip: dict[str, Any]) -> str:
    """Escolhe dinamicamente a animacao contextual sobre imagens estaticas."""
    hay = f"{clip.get('text', '')} {clip.get('visual_action', '')} {clip.get('location', '')}".lower()
    for rx, style in _OVERLAY_RULES:
        if re.search(rx, hay, re.I):
            return style
    return "leaves"


def _draw_heart_poly(x: int, y: int, r: int) -> np.ndarray:
    ts = np.linspace(0, 2 * math.pi, 20)
    xs = 16 * np.sin(ts) ** 3
    ys = 13 * np.cos(ts) - 5 * np.cos(2 * ts) - 2 * np.cos(3 * ts) - np.cos(4 * ts)
    s = r / 17.0
    return np.array([[x + int(a * s), y - int(b * s)] for a, b in zip(xs, ys)], np.int32)


def apply_contextual_particle_overlay(
    clip_mp4: Path,
    style: str,
    seed: int = 42,
    allow_nvenc: bool = True,
) -> Path:
    """Desenha overlay contextual animado suave (Zzz, coracoes, fumacinha, abelhas, etc.) em sub-clip estatico."""
    if style == "none":
        return clip_mp4
    cap = cv2.VideoCapture(str(clip_mp4))
    fps = cap.get(cv2.CAP_PROP_FPS) or float(VIDEO_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or VIDEO_WIDTH
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or VIDEO_HEIGHT

    counts = {
        "zzz": 14, "hearts": 18, "steam": 15, "fire": 22,
        "bees": 16, "birds": 12, "fireflies": 24, "sparkles": 26, "leaves": 20,
    }
    sizes = {
        "zzz": (20, 38), "hearts": (11, 22), "steam": (20, 48), "fire": (5, 13),
        "bees": (9, 16), "birds": (12, 22), "fireflies": (4, 8), "sparkles": (6, 14), "leaves": (9, 18),
    }
    speeds = {
        "zzz": (26, 46), "hearts": (22, 42), "steam": (20, 38), "fire": (38, 72),
        "bees": (42, 85), "birds": (55, 110), "fireflies": (12, 28), "sparkles": (10, 24), "leaves": (30, 60),
    }
    n_p = counts.get(style, 18)
    slo, shi = sizes.get(style, (8, 16))
    vlo, vhi = speeds.get(style, (18, 40))

    rng = np.random.default_rng(seed)
    parts = [
        (
            float(rng.uniform(40, w - 40)),
            float(rng.uniform(40, h - 40)),
            float(rng.uniform(slo, shi)),
            float(rng.uniform(vlo, vhi)),
            float(rng.uniform(0, 2 * math.pi)),
            float(rng.uniform(-0.4, 0.4)),
        )
        for _ in range(n_p)
    ]

    tmp_avi = clip_mp4.with_suffix(".ov_tmp.avi")
    tmp_out = clip_mp4.with_suffix(".ov_enc.mp4")
    vw = cv2.VideoWriter(str(tmp_avi), cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            t = idx / fps
            overlay = np.zeros_like(frame)
            alpha_u8 = np.zeros((h, w), np.uint8)

            for x0, y0, sz, sp, ph, dr in parts:
                delta = sp * t
                if style in ("zzz", "hearts", "steam", "fire", "fireflies", "sparkles"):
                    xx = int((x0 + dr * delta * 0.4 + 18 * math.sin(t * 1.1 + ph)) % (w + 60) - 30)
                    yy = int((y0 - delta) % (h + 60) - 30)
                elif style in ("bees", "birds"):
                    xx = int((x0 + delta) % (w + 60) - 30)
                    yy = int((y0 + 26 * math.sin(t * 2.2 + ph)) % (h + 60) - 30)
                else:  # leaves
                    xx = int((x0 + dr * delta * 0.6 + 24 * math.sin(t * 1.2 + ph)) % (w + 60) - 30)
                    yy = int((y0 + delta) % (h + 60) - 30)

                if xx < 12 or xx > w - 12 or yy < 12 or yy > h - 12:
                    continue

                pulse = 0.58 + 0.42 * math.sin(t * 2.1 + ph)
                a = int(np.clip(165 * pulse, 55, 200))
                r = int(sz)

                if style == "zzz":
                    sc = max(0.55, r / 28.0)
                    ch = "Z" if r > 28 else "z"
                    cv2.putText(overlay, ch, (xx + 2, yy + 2), cv2.FONT_HERSHEY_SIMPLEX, sc, (40, 20, 80), 4, cv2.LINE_AA)
                    cv2.putText(overlay, ch, (xx, yy), cv2.FONT_HERSHEY_SIMPLEX, sc, (255, 235, 190), 2, cv2.LINE_AA)
                    cv2.putText(alpha_u8, ch, (xx, yy), cv2.FONT_HERSHEY_SIMPLEX, sc, int(min(220, a + 30)), 4, cv2.LINE_AA)
                elif style == "hearts":
                    pts = _draw_heart_poly(xx, yy, r)
                    cv2.fillPoly(overlay, [pts], (145, 95, 255), cv2.LINE_AA)
                    cv2.fillPoly(alpha_u8, [pts], a, cv2.LINE_AA)
                elif style == "steam":
                    for k in range(3):
                        rr = max(4, int(r * (1.0 - k * 0.24)))
                        ox = xx + int(8 * math.sin(t * 1.5 + ph + k))
                        oy = max(4, yy - k * (r // 2))
                        cv2.circle(overlay, (ox, oy), rr, (245, 245, 250), -1, cv2.LINE_AA)
                        cv2.circle(alpha_u8, (ox, oy), rr, max(24, int(a * 0.48) // (k + 1)), -1, cv2.LINE_AA)
                elif style == "fire":
                    col_f = (60, 145, 255) if (int(ph * 10) % 2 == 0) else (80, 215, 255)
                    cv2.circle(overlay, (xx, yy), r, col_f, -1, cv2.LINE_AA)
                    cv2.circle(alpha_u8, (xx, yy), r, int(min(210, a + 20)), -1, cv2.LINE_AA)
                elif style == "bees":
                    cv2.ellipse(overlay, (xx, yy), (max(3, r // 2), max(2, r // 3)), 0, 0, 360, (45, 205, 255), -1, cv2.LINE_AA)
                    cv2.line(overlay, (xx, yy - r // 3), (xx, yy + r // 3), (30, 30, 40), 2, cv2.LINE_AA)
                    for s in (-1, 1):
                        cv2.ellipse(overlay, (xx + s * (r // 4), yy - r // 3), (max(2, r // 3), max(2, r // 4)), 20, 0, 360, (250, 250, 255), -1, cv2.LINE_AA)
                    cv2.circle(alpha_u8, (xx, yy), r, a, -1, cv2.LINE_AA)
                elif style == "birds":
                    flap = int(6 * math.sin(t * 7.0 + ph))
                    pts = np.array([[xx - r, yy - flap], [xx, yy + 3], [xx + r, yy - flap]], np.int32)
                    cv2.polylines(overlay, [pts], False, (250, 245, 235), 2, cv2.LINE_AA)
                    cv2.polylines(alpha_u8, [pts], False, min(200, a + 25), 3, cv2.LINE_AA)
                elif style == "fireflies":
                    cv2.circle(overlay, (xx, yy), max(2, r // 2), (130, 255, 255), -1, cv2.LINE_AA)
                    cv2.circle(alpha_u8, (xx, yy), r + 2, int(210 * pulse), -1, cv2.LINE_AA)
                elif style == "sparkles":
                    cv2.line(overlay, (xx - r, yy), (xx + r, yy), (165, 240, 255), 2, cv2.LINE_AA)
                    cv2.line(overlay, (xx, yy - r), (xx, yy + r), (165, 240, 255), 2, cv2.LINE_AA)
                    cv2.line(alpha_u8, (xx - r, yy), (xx + r, yy), a, 2, cv2.LINE_AA)
                    cv2.line(alpha_u8, (xx, yy - r), (xx, yy + r), a, 2, cv2.LINE_AA)
                else:  # leaves
                    ang = int((t * 50 + ph * 60) % 360)
                    pts = np.array(cv2.ellipse2Poly((xx, yy), (r, max(3, r // 2)), ang, 0, 360, 12), np.int32)
                    cv2.fillPoly(overlay, [pts], (95, 195, 110), cv2.LINE_AA)
                    cv2.fillPoly(alpha_u8, [pts], a, cv2.LINE_AA)

            nz = alpha_u8 > 0
            if np.any(nz):
                af = (alpha_u8[nz].astype(np.float32) / 255.0)[:, None]
                frame[nz] = np.clip(
                    frame[nz].astype(np.float32) * (1.0 - af) + overlay[nz].astype(np.float32) * af,
                    0, 255,
                ).astype(np.uint8)
            vw.write(frame)
            idx += 1
    finally:
        cap.release()
        vw.release()

    try:
        if tmp_avi.exists() and tmp_avi.stat().st_size > 2000:
            _run_h264_ffmpeg([FFMPEG_EXE, "-y", "-v", "error", "-i", str(tmp_avi), "-an"], [str(tmp_out)], quality="fast")
            if tmp_out.exists() and tmp_out.stat().st_size > 2000:
                tmp_out.replace(clip_mp4)
    finally:
        tmp_avi.unlink(missing_ok=True)
        tmp_out.unlink(missing_ok=True)
    return clip_mp4


def render_motion_video_subclip(
    video_path: Path,
    src_start_s: float,
    duration: float,
    out_mp4: Path,
    pts_factor: float = 1.0,
    allow_nvenc: bool = True,
) -> Path:
    """Extrai trecho continuo de video Veo em 1920x1080@30fps sem audio para intercalacao."""
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    src_dur = max(0.5, probe_duration(video_path))
    safe_pts = max(0.75, min(1.35, float(pts_factor)))
    ss = max(0.0, min(src_start_s, max(0.0, src_dur - 0.4)))
    vf = (
        f"setpts={safe_pts:.5f}*(PTS-STARTPTS),"
        f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        f"fps={VIDEO_FPS},setsar=1,format=yuv420p"
    )
    need_loop = (src_dur - ss) * safe_pts < (duration - 0.05)
    cmd = [FFMPEG_EXE, "-y", "-v", "error"]
    if need_loop:
        cmd += ["-stream_loop", "1"]
    cmd += ["-ss", f"{ss:.3f}", "-i", str(video_path), "-vf", vf, "-t", f"{duration:.3f}", "-an"]
    _run_h264_ffmpeg(cmd, [str(out_mp4)], quality="fast", allow_nvenc=allow_nvenc)
    return out_mp4


def _resolve_scene_videos(scene_id: str, images_dir: Path) -> list[Path]:
    """Localiza todos os videos Veo validos (>50KB) associados a cena em ordem deterministica."""
    videos_dir = images_dir.parent / "videos"
    found: list[Path] = []
    seen: set[str] = set()

    def _add(p: Path) -> None:
        try:
            rp = str(p.resolve())
        except Exception:
            rp = str(p)
        if rp not in seen and p.exists() and p.is_file() and p.stat().st_size > 50_000:
            seen.add(rp)
            found.append(p)

    for base in (videos_dir, images_dir):
        _add(base / f"{scene_id}.mp4")
        if base.exists():
            for pat in (f"{scene_id}_v*.mp4", f"{scene_id}_p*.mp4"):
                for cand in sorted(base.glob(pat)):
                    _add(cand)
    return found


def render_multi_video_montage_subclip(
    video_paths: list[Path],
    scene_start_s: float,
    clip_start_s: float,
    clip_dur: float,
    scene_total_dur: float,
    out_mp4: Path,
    allow_nvenc: bool = True,
) -> Path:
    """Edita multiplos videos da mesma cena em sequencia uniforme dentro dos sub-clips."""
    if len(video_paths) <= 1:
        return render_motion_video_subclip(
            video_paths[0],
            max(0.0, float(clip_start_s) - float(scene_start_s)),
            clip_dur,
            out_mp4,
            allow_nvenc=allow_nvenc,
        )
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    n_vids = len(video_paths)
    tot = max(0.5, float(scene_total_dur))
    slot = tot / n_vids
    rel_start = max(0.0, float(clip_start_s) - float(scene_start_s))
    rel_end = rel_start + max(0.1, float(clip_dur))

    overlaps: list[tuple[int, float, float]] = []
    for idx in range(n_vids):
        ov_s = max(rel_start, idx * slot)
        ov_e = min(rel_end, (idx + 1) * slot)
        if ov_e > ov_s + 1e-4:
            if overlaps and (ov_e - ov_s) < 0.12:
                pi, ps, _ = overlaps[-1]
                overlaps[-1] = (pi, ps, ov_e)
            else:
                overlaps.append((idx, ov_s, ov_e))
    if len(overlaps) >= 2 and (overlaps[0][2] - overlaps[0][1]) < 0.12:
        _, first_s, _ = overlaps.pop(0)
        ni, _, ne = overlaps[0]
        overlaps[0] = (ni, first_s, ne)

    pieces: list[Path] = []
    for idx, ov_s, ov_e in overlaps:
        ov_dur = ov_e - ov_s
        vp = video_paths[idx]
        v_dur = max(0.5, probe_duration(vp))
        src_ss = min(max(0.0, (ov_s - idx * slot) + 0.35), max(0.0, v_dur - ov_dur - 0.1))
        part_mp4 = out_mp4.parent / f"{out_mp4.stem}_part{idx}_{len(pieces)}.mp4"
        render_motion_video_subclip(vp, src_ss, ov_dur, part_mp4, pts_factor=1.0, allow_nvenc=allow_nvenc)
        pieces.append(part_mp4)

    if not pieces:
        return render_motion_video_subclip(video_paths[0], 0.0, clip_dur, out_mp4, allow_nvenc=allow_nvenc)
    if len(pieces) == 1:
        pieces[0].replace(out_mp4)
        return out_mp4

    concat_list = out_mp4.parent / f"{out_mp4.stem}_concat.txt"
    try:
        concat_list.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in pieces) + "\n",
            encoding="utf-8",
        )
        _run_h264_ffmpeg(
            [FFMPEG_EXE, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-an"],
            [str(out_mp4)],
            quality="fast",
            allow_nvenc=allow_nvenc,
        )
    finally:
        concat_list.unlink(missing_ok=True)
        for p in pieces:
            p.unlink(missing_ok=True)
    return out_mp4


def _resolve_clip_video(clip: dict[str, Any], images_dir: Path) -> Path | None:
    """Localiza clipe de video Veo associado ao sub-clip ou a cena."""
    explicit = clip.get("video_path")
    if explicit and Path(explicit).exists():
        return Path(explicit)
    videos_dir = images_dir.parent / "videos"
    for cand in (
        images_dir / f"{clip['clip_id']}.mp4",
        videos_dir / f"{clip['clip_id']}.mp4",
        videos_dir / f"{clip['scene_id']}.mp4",
        images_dir / f"{clip['scene_id']}.mp4",
    ):
        if cand.exists() and cand.stat().st_size > 2048:
            return cand
    return None


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
    bgm_volume: float = 0.22,
    target_lufs: float = -14.0,
) -> Path:
    """Mixa narracao (-16 LUFS) + SFX + BGM com ducking automatico para LUFS alvo."""
    out_m4a.parent.mkdir(parents=True, exist_ok=True)
    bv = max(0.0, min(0.50, float(bgm_volume)))
    lufs = max(-24.0, min(-9.0, float(target_lufs)))
    if bgm_wav and bgm_wav.exists():
        fc = (
            "[0:a]aformat=sample_rates=44100:channel_layouts=stereo,asplit=2[nar][nar_sc];"
            f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{total_dur:.3f},asetpts=PTS-STARTPTS,"
            f"aformat=sample_rates=44100:channel_layouts=stereo,volume={bv:.2f}[bgm];"
            "[bgm][nar_sc]sidechaincompress=threshold=0.03:ratio=6:attack=25:release=600[bgm_duck];"
            "[2:a]aformat=sample_rates=44100:channel_layouts=stereo[sfx];"
            "[nar][bgm_duck][sfx]amix=inputs=3:duration=first:normalize=0,"
            f"loudnorm=I={lufs:.1f}:TP=-1.5:LRA=11[out]"
        )
        cmd = [FFMPEG_EXE, "-y", "-v", "error", "-i", str(narration_wav), "-i", str(bgm_wav), "-i", str(sfx_wav)]
    else:
        fc = (
            "[0:a]aformat=sample_rates=44100:channel_layouts=stereo[nar];"
            "[1:a]aformat=sample_rates=44100:channel_layouts=stereo[sfx];"
            "[nar][sfx]amix=inputs=2:duration=first:normalize=0,"
            f"loudnorm=I={lufs:.1f}:TP=-1.5:LRA=11[out]"
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
    """Prepara overlays de Dual-Avatar em paralelo usando os cantos mais vazios da cena."""
    jobs: list[dict[str, Any]] = []
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
            chosen = next((cn for cn in corners if cn not in used_corners), corners[0])
            used_corners.append(chosen)
            x_expr, y_expr = _CORNER_POS[chosen]
            jobs.append({
                "sid": sid, "char": char, "wav": wav, "dur": dur, "mov": mov,
                "card_sz": card_sz, "active": active, "st": st, "en": en,
                "x_expr": x_expr, "y_expr": y_expr,
            })

    if not jobs:
        return []

    chars_needed = sorted({j["char"] for j in jobs})
    if chars_needed:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(2, len(chars_needed))) as pre_ex:
            list(pre_ex.map(_index_character_bank, chars_needed))

    def _render_job(j: dict[str, Any]) -> tuple[float, float, str, str, Path] | None:
        res = render_avatar_pip_clip(
            j["sid"], j["char"], j["wav"], j["dur"], j["mov"],
            card_size=j["card_sz"], is_active_speaker=j["active"],
        )
        if res and res.exists():
            return (j["st"], j["en"], j["x_expr"], j["y_expr"], res)
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, CPU_WORKERS)) as ex:
        results = list(ex.map(_render_job, jobs))
    return [r for r in results if r is not None]


def export_short_9_16(
    master_16_9: Path,
    visual_clips: list[dict[str, Any]],
    out_short: Path,
    hook_badge: str = "FRIDA & LUNA",
    engine: str = "auto",
    target_seconds: float | None = None,
) -> Path:
    """Delega para core.motion_shorts (Remotion / FFmpeg Motion HUD)."""
    return export_motion_short_9_16(
        master_16_9, visual_clips, out_short, hook_badge=hook_badge, engine=engine, target_seconds=target_seconds
    )


def assemble_video(
    visual_clips: list[dict[str, Any]],
    images_dir: Path,
    work_dir: Path,
    out_mp4: Path,
    out_srt: Path,
    bgm_wav: Path | None = None,
    with_avatar: bool = True,
    burn_captions: bool = False,
    sfx_volume: float = 0.35,
    bgm_volume: float = 0.22,
    target_lufs: float = -14.0,
    overlay_style: str = "auto",
    cpu_workers: int | None = None,
    disable_nvenc: bool = False,
) -> tuple[Path, Path]:
    """Monta 16:9 final com Ken Burns, overlays contextuais, Dual-Avatar PiP, SFX, BGM por ato e LUFS alvo."""
    clips_dir = work_dir / "clips"
    avatar_dir = work_dir / "avatar_pip"
    clips_dir.mkdir(parents=True, exist_ok=True)
    avatar_dir.mkdir(parents=True, exist_ok=True)
    workers = max(1, int(cpu_workers or CPU_WORKERS))
    allow_gpu = not bool(disable_nvenc)

    scene_totals: dict[str, float] = {}
    scene_starts: dict[str, float] = {}
    for c in visual_clips:
        sid = c["scene_id"]
        scene_totals[sid] = scene_totals.get(sid, 0.0) + float(c["duration"])
        scene_starts.setdefault(sid, float(c.get("start", 0.0)))

    def _render_subclip(clip: dict[str, Any]) -> Path:
        sid = clip["scene_id"]
        dur = float(clip["duration"])
        img_path = images_dir / f"{clip['clip_id']}.jpg"
        scene_vids = _resolve_scene_videos(sid, images_dir)
        seg_mp4 = clips_dir / f"{clip['clip_id']}.mp4"
        if len(scene_vids) >= 2:
            vid_path = scene_vids[0]
            v_dur = max(0.5, probe_duration(vid_path))
            tot_scene = max(dur, scene_totals.get(sid, dur))
            if not img_path.exists():
                img_path.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    [FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{min(dur * 0.25, max(0.0, v_dur - 0.1)):.2f}",
                     "-i", str(vid_path), "-vframes", "1", "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
                     str(img_path)],
                    check=True,
                )
            render_multi_video_montage_subclip(
                scene_vids,
                scene_starts[sid],
                float(clip.get("start", scene_starts[sid])),
                dur,
                tot_scene,
                seg_mp4,
                allow_nvenc=allow_gpu,
            )
        else:
            vid_path = scene_vids[0] if scene_vids else _resolve_clip_video(clip, images_dir)
            if vid_path is not None:
                v_dur = max(0.5, probe_duration(vid_path))
                tot_scene = max(dur, scene_totals.get(sid, dur))
                pts = (tot_scene / (v_dur - 0.05)) if tot_scene > (v_dur - 0.05) else 1.0
                rel_out = max(0.0, float(clip.get("start", scene_starts[sid])) - scene_starts[sid])
                src_ss = rel_out / max(0.5, pts)
                if not img_path.exists():
                    img_path.parent.mkdir(parents=True, exist_ok=True)
                    subprocess.run(
                        [FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{min(src_ss + dur * 0.25, max(0.0, v_dur - 0.1)):.2f}",
                         "-i", str(vid_path), "-vframes", "1", "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
                         str(img_path)],
                        check=True,
                    )
                render_motion_video_subclip(vid_path, src_ss, dur, seg_mp4, pts_factor=pts, allow_nvenc=allow_gpu)
            else:
                if not img_path.exists():
                    raise FileNotFoundError(f"Imagem ausente: {img_path}")
                render_ken_burns_clip(img_path, clip["ken_burns"], dur, seg_mp4, allow_nvenc=allow_gpu)
                ov_style = infer_scene_overlay_style(clip) if overlay_style == "auto" else overlay_style
                apply_contextual_particle_overlay(
                    seg_mp4,
                    ov_style,
                    seed=abs(hash(clip["clip_id"])) % (2 ** 31),
                    allow_nvenc=allow_gpu,
                )
        return seg_mp4

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as clip_ex:
        rendered_segments = list(clip_ex.map(_render_subclip, visual_clips))

    concat_txt = work_dir / "concat_video.txt"
    concat_txt.write_text("\n".join("file '%s'" % p.as_posix() for p in rendered_segments) + "\n", encoding="utf-8")
    base_video = work_dir / "base_video_16x9.mp4"
    _run_h264_ffmpeg(
        [FFMPEG_EXE, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat_txt)],
        [str(base_video)],
        quality="master",
        allow_nvenc=allow_gpu,
    )

    total_dur = probe_duration(base_video)
    nar_wav = work_dir / "narration_master.wav"
    nar_sc_wav = work_dir / "narration_soundcraft.wav"
    sfx_wav = work_dir / "sfx_master.wav"
    mix_m4a = work_dir / "final_mix.m4a"
    build_narration_track(visual_clips, total_dur, nar_wav)
    nar_mastered = master_with_soundcraft(nar_wav, nar_sc_wav)
    build_sfx_stem(visual_clips, total_dur, sfx_wav, sfx_volume=sfx_volume, narration_wav=nar_mastered)
    chosen_bgm = resolve_act_bgm(visual_clips, total_dur, work_dir, bgm_wav)
    mix_audio_master(
        nar_mastered, sfx_wav, total_dur, mix_m4a,
        bgm_wav=chosen_bgm, bgm_volume=bgm_volume, target_lufs=target_lufs,
    )

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
    _run_h264_ffmpeg(
        cmd + ["-filter_complex", ";".join(filters), "-map", prev, "-map", f"{audio_idx}:a"],
        ["-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out_mp4)],
        quality="master",
        cwd=str(work_dir),
    )
    return out_mp4, out_srt
