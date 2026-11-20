# -*- coding: utf-8 -*-
"""Motion Graphics para Shorts 9:16 (Remotion Engine + FFmpeg Motion HUD integrado)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from config import FFMPEG_EXE, SHORT_HEIGHT, SHORT_MAX_SECONDS, SHORT_MIN_SECONDS, SHORT_SAFE_BOTTOM_PX, SHORT_TARGET_SECONDS, SHORT_WIDTH, SPEAKER_VOICE_PROFILES

REMOTION_DIR = Path(r"D:\Utilitarios\OpenMontage\remotion-composer")


def select_best_short_window(visual_clips: list[dict[str, Any]]) -> tuple[float, float]:
    """Seleciona janela de 30-40s com maior densidade de cortes, SFX e gancho."""
    if not visual_clips:
        return 0.0, SHORT_TARGET_SECONDS
    total = float(visual_clips[-1]["end"])
    if total <= SHORT_MAX_SECONDS:
        return 0.0, total

    best_score = -1.0
    best_win = (0.0, min(total, SHORT_TARGET_SECONDS))
    starts = sorted({round(float(c["start"]), 3) for c in visual_clips if float(c["start"]) <= max(0.0, total - SHORT_MIN_SECONDS)})
    for st in starts:
        en = min(total, st + SHORT_TARGET_SECONDS)
        if en - st < SHORT_MIN_SECONDS:
            continue
        in_win = [c for c in visual_clips if float(c["end"]) > st and float(c["start"]) < en]
        score = len(in_win) * 1.5 + sum(1 for c in in_win if c.get("sfx")) * 2.0 + (3.0 if st < 2.0 else 0.0)
        if score > best_score:
            best_score = score
            best_win = (st, en)
    return best_win


def _fmt_ass_time(seconds: float) -> str:
    sec = max(0.0, float(seconds))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = min(99, int(round((sec - int(sec)) * 100)))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_word_captions(visual_clips: list[dict[str, Any]], offset_s: float = 0.0, end_s: float = 9999.0) -> list[dict[str, Any]]:
    """Constroi lista de palavras cronometradas para Remotion CaptionOverlay ou ASS."""
    words_out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for c in visual_clips:
        sid = c["scene_id"]
        if sid in seen:
            continue
        seen.add(sid)
        st = float(c["scene_audio_start"])
        dur = float(c["scene_audio_dur"])
        if st + dur <= offset_s or st >= end_s:
            continue
        tokens = " ".join((c.get("text") or "").split()).split()
        if not tokens:
            continue
        w_dur = dur / len(tokens)
        for i, tok in enumerate(tokens):
            ws = max(0.0, (st + i * w_dur) - offset_s)
            we = max(ws + 0.06, (st + (i + 1) * w_dur) - offset_s)
            words_out.append({
                "text": tok,
                "startMs": int(round(ws * 1000)),
                "endMs": int(round(we * 1000)),
                "speaker": str(c.get("speaker") or "narrador").lower(),
            })
    return words_out


def write_short_pop_ass(
    visual_clips: list[dict[str, Any]],
    out_ass: Path,
    hook_badge: str,
    offset_s: float,
    dur: float,
) -> Path:
    """Gera legendas pop coloridas + banner superior animado ASS para o Short 9:16."""
    header = "\n".join([
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {SHORT_WIDTH}",
        f"PlayResY: {SHORT_HEIGHT}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Pop,Arial Rounded MT Bold,64,&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,2,2,56,56,{SHORT_SAFE_BOTTOM_PX},1",
        "Style: HookTop,Impact,68,&H0032E0FF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,1,0,1,5,3,8,40,40,120,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ])
    lines = [header]
    if hook_badge.strip():
        lines.append(
            f"Dialogue: 1,0:00:00.00,{_fmt_ass_time(min(dur, 4.5))},HookTop,,0,0,0,,"
            r"{\fscx85\fscy85\t(0,180,\fscx106\fscy106)\t(180,320,\fscx100\fscy100)}"
            + hook_badge.upper()
        )

    seen: set[str] = set()
    for c in visual_clips:
        sid = c["scene_id"]
        if sid in seen:
            continue
        seen.add(sid)
        st = float(c["scene_audio_start"]) - offset_s
        sdur = float(c["scene_audio_dur"])
        if st + sdur <= 0 or st >= dur:
            continue
        words = " ".join((c.get("text") or "").split()).split()
        if not words:
            continue
        spk = str(c.get("speaker") or "narrador").lower()
        color = SPEAKER_VOICE_PROFILES.get(spk, SPEAKER_VOICE_PROFILES["narrador"])["subtitle_ass_color"]
        chunks = [" ".join(words[i:i + 3]) for i in range(0, len(words), 3)]
        cdur = sdur / len(chunks)
        for k, ch in enumerate(chunks):
            cs = max(0.0, st + k * cdur)
            ce = min(dur, max(cs + 0.08, st + (k + 1) * cdur))
            tag = r"{\c" + color + r"\fscx90\fscy90\t(0,80,\fscx105\fscy105)}"
            lines.append(f"Dialogue: 0,{_fmt_ass_time(cs)},{_fmt_ass_time(ce)},Pop,,0,0,0,,{tag}{ch}")

    out_ass.parent.mkdir(parents=True, exist_ok=True)
    out_ass.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_ass


def _render_with_remotion(
    raw_9_16_mp4: Path,
    visual_clips: list[dict[str, Any]],
    hook_badge: str,
    st: float,
    dur: float,
    out_short: Path,
) -> bool:
    """Usa D:\\Utilitarios\\OpenMontage\\remotion-composer (TalkingHead 9:16) quando disponivel."""
    if not (REMOTION_DIR / "package.json").exists() or not (REMOTION_DIR / "node_modules").exists():
        return False
    npx = shutil.which("npx")
    if not npx:
        return False

    pub_name = f"vm2_{out_short.stem}.mp4"
    pub_video = REMOTION_DIR / "public" / pub_name
    pub_video.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw_9_16_mp4, pub_video)

    word_caps = [
        {"text": w["text"], "startMs": w["startMs"], "endMs": w["endMs"]}
        for w in build_word_captions(visual_clips, offset_s=st, end_s=st + dur)
    ]
    props = {
        "videoSrc": pub_name,
        "captions": {"words": word_caps, "wordsPerPage": 3, "fontSize": 60, "highlightColor": "#FACC15"},
        "overlays": [
            {
                "id": "hook_top",
                "type": "HeroTitle",
                "in_seconds": 0.0,
                "out_seconds": min(3.8, dur),
                "position": "upper_third",
                "title": hook_badge or "FRIDA & LUNA",
                "subtitle": "Cenas Inéditas",
                "accentColor": "#FACC15",
            }
        ],
    }
    props_file = out_short.with_suffix(".remotion.json")
    props_file.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        r = subprocess.run(
            [npx, "remotion", "render", "src/index.tsx", "TalkingHead", str(out_short), f"--props={props_file}"],
            cwd=str(REMOTION_DIR),
            capture_output=True, text=True, timeout=180,
        )
        return r.returncode == 0 and out_short.exists() and out_short.stat().st_size > 40000
    except Exception:
        return False
    finally:
        pub_video.unlink(missing_ok=True)
        props_file.unlink(missing_ok=True)


def export_motion_short_9_16(
    master_16_9: Path,
    visual_clips: list[dict[str, Any]],
    out_short: Path,
    hook_badge: str = "FRIDA & LUNA",
    engine: str = "auto",
) -> Path:
    """Exporta Short 9:16 com Motion Graphics (barra de progresso + Hook + Pop Captions ou Remotion)."""
    st, en = select_best_short_window(visual_clips)
    dur = max(1.0, round(en - st, 3))
    out_short.parent.mkdir(parents=True, exist_ok=True)

    # 1) Pre-corte 9:16 base limpo com pan dinamico
    base_9_16 = out_short.with_suffix(".base916.mp4")
    crop_w = f"ih*{SHORT_WIDTH}/{SHORT_HEIGHT}"
    x_pan = f"(iw-{crop_w})*(0.5+0.22*sin(2*PI*t/8))"
    subprocess.run(
        [FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{st:.3f}", "-t", f"{dur:.3f}", "-i", str(master_16_9),
         "-vf", f"crop={crop_w}:ih:{x_pan}:0,scale={SHORT_WIDTH}:{SHORT_HEIGHT}:flags=lanczos,setsar=1",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
         "-c:a", "aac", "-b:a", "192k", str(base_9_16)],
        check=True,
    )

    try:
        if engine == "remotion":
            if _render_with_remotion(base_9_16, visual_clips, hook_badge, st, dur, out_short):
                return out_short

        # Motion Graphics HUD embutido (barra de progresso animada no topo + Hook animado + Legendas Pop)
        ass_short = out_short.with_suffix(".ass")
        win_clips = [c for c in visual_clips if float(c["end"]) > st and float(c["start"]) < en]
        write_short_pop_ass(win_clips, ass_short, hook_badge=hook_badge, offset_s=st, dur=dur)

        # Barra de progresso dinamica animada no topo da tela
        vf = (
            f"drawbox=x=0:y=0:w={SHORT_WIDTH}:h=14:color=black@0.45:t=fill,"
            f"drawbox=x=0:y=0:w='iw*t/{dur:.3f}':h=14:color=#FACC15@0.95:t=fill,"
            f"ass={ass_short.name}"
        )
        subprocess.run(
            [FFMPEG_EXE, "-y", "-v", "error", "-i", str(base_9_16),
             "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-c:a", "copy", "-movflags", "+faststart", str(out_short)],
            cwd=str(ass_short.parent),
            check=True,
        )
        return out_short
    finally:
        base_9_16.unlink(missing_ok=True)
