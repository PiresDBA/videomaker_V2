# -*- coding: utf-8 -*-
"""Motion Graphics e Split-Screen 70/30 Infantil/Familia para Shorts 9:16."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

from config import (
    FFMPEG_EXE,
    SHORT_HEIGHT,
    SHORT_MAX_SECONDS,
    SHORT_MIN_SECONDS,
    SHORT_SAFE_BOTTOM_PX,
    SHORT_TARGET_SECONDS,
    SHORT_WIDTH,
    SPEAKER_VOICE_PROFILES,
    VENDOR_DIR,
)

_LOCAL_REMOTION = VENDOR_DIR / "remotion-composer"
REMOTION_DIR = _LOCAL_REMOTION if _LOCAL_REMOTION.exists() else Path(r"D:\Utilitarios\OpenMontage\remotion-composer")

# Proporcao oficial do Short Split-Screen: 70% topo (filme) / 30% base (avatares alegres)
SHORT_SPLIT_TOP_RATIO = 0.70
SHORT_SPLIT_TOP_H = int(round(SHORT_HEIGHT * SHORT_SPLIT_TOP_RATIO))  # 1344
SHORT_SPLIT_BOT_H = SHORT_HEIGHT - SHORT_SPLIT_TOP_H  # 576

_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\ARLRDBD.TTF",   # Arial Rounded MT Bold (infantil/arredondada)
    r"C:\Windows\Fonts\comicbd.ttf",   # Comic Sans MS Bold
    r"C:\Windows\Fonts\BAUHS93.TTF",   # Bauhaus 93
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
)


def _load_playful_font(size: int):
    from PIL import ImageFont
    for fp in _FONT_CANDIDATES:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def resolve_split_avatar_states(speaker: str, speech_level: int) -> tuple[bool, bool]:
    """Regra estrita de sincronia labial nos Shorts:
    - Frida so mexe a boca quando `speaker == 'frida'` e `speech_level > 0`.
    - Luna so mexe a boca quando `speaker == 'luna'` e `speech_level > 0`.
    - Quando o narrador ou personagem secundario fala, AMBAS ficam estritamente de boca fechada.
    """
    spk = str(speaker or "narrador").strip().lower()
    lv = int(speech_level or 0)
    return (spk == "frida" and lv > 0), (spk == "luna" and lv > 0)


def select_best_short_window(
    visual_clips: list[dict[str, Any]],
    target_seconds: float | None = None,
) -> tuple[float, float]:
    """Seleciona janela de 30-40s com maior densidade de cortes, SFX e gancho."""
    tgt = float(target_seconds) if target_seconds is not None else SHORT_TARGET_SECONDS
    if not visual_clips:
        return 0.0, tgt
    total = float(visual_clips[-1]["end"])
    if total <= max(SHORT_MAX_SECONDS, tgt):
        return 0.0, min(total, tgt) if target_seconds is not None else total

    best_score = -1.0
    best_win = (0.0, min(total, tgt))
    starts = sorted({round(float(c["start"]), 3) for c in visual_clips if float(c["start"]) <= max(0.0, total - min(SHORT_MIN_SECONDS, tgt))})
    for st in starts:
        en = min(total, st + tgt)
        if en - st < min(SHORT_MIN_SECONDS, tgt):
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
    split_mode: bool = False,
    variant: str = "hook",
) -> Path:
    """Gera legendas pop infantis arredondadas + gancho animado ASS para o Short 9:16."""
    # No Split 70/30, as legendas ficam na parte inferior do filme de cima (y ~ 1215..1310),
    # acima da faixa de avatares (y = 1344..1920) e 100% livres da UI do YouTube.
    margin_v = SHORT_SPLIT_BOT_H + 34 if split_mode else SHORT_SAFE_BOTTOM_PX
    hook_primary = "&H0012E8FF" if variant == "hook" else ("&H0038DCFF" if variant == "storybook" else "&H0078FF96")
    hook_outline = "&H00581A36" if variant == "hook" else ("&H00182C5C" if variant == "storybook" else "&H00581A42")

    # Paleta alegre e contrastada por personagem (formato ASS &HBBGGRR)
    playful_colors = {
        "narrador": ("&H00FFFFFF", "&H004E1D34"),
        "frida": ("&H001CE2FF", "&H00182B5E"),
        "luna": ("&H00FFF066", "&H00541944"),
        "secundario": ("&H008CFF9E", "&H001D3D18"),
    }

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
        f"Style: Pop,Arial Rounded MT Bold,64,&H00FFFFFF,&H0000FFFF,&H004E1D34,&H80000000,-1,0,0,0,100,100,1,0,1,6,3,2,54,54,{margin_v},1",
        f"Style: HookTop,Arial Rounded MT Bold,70,{hook_primary},&H00FFFFFF,{hook_outline},&H96000000,-1,0,0,0,100,100,1,0,1,7,4,8,44,44,108,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ])
    lines = [header]
    if hook_badge.strip():
        lines.append(
            f"Dialogue: 1,0:00:00.00,{_fmt_ass_time(min(dur, 4.5))},HookTop,,0,0,0,,"
            r"{\fscx80\fscy80\t(0,180,\fscx109\fscy109)\t(180,320,\fscx100\fscy100)}"
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
        p_col, o_col = playful_colors.get(
            spk,
            (SPEAKER_VOICE_PROFILES.get(spk, SPEAKER_VOICE_PROFILES["narrador"])["subtitle_ass_color"], "&H004E1D34"),
        )
        chunks = [" ".join(words[i:i + 3]) for i in range(0, len(words), 3)]
        cdur = sdur / len(chunks)
        for k, ch in enumerate(chunks):
            cs = max(0.0, st + k * cdur)
            ce = min(dur, max(cs + 0.08, st + (k + 1) * cdur))
            tag = r"{\c" + p_col + r"\3c" + o_col + r"\fscx88\fscy88\t(0,90,\fscx106\fscy106)\t(90,170,\fscx100\fscy100)}"
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
    """Usa remotion-composer (TalkingHead 9:16) quando disponivel."""
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
    target_seconds: float | None = None,
) -> Path:
    """Exporta Short 9:16 com Motion Graphics (barra de progresso + Hook + Pop Captions ou Remotion)."""
    st, en = select_best_short_window(visual_clips, target_seconds=target_seconds)
    dur = max(1.0, round(en - st, 3))
    out_short.parent.mkdir(parents=True, exist_ok=True)

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

        ass_short = out_short.with_suffix(".ass")
        win_clips = [c for c in visual_clips if float(c["end"]) > st and float(c["start"]) < en]
        write_short_pop_ass(win_clips, ass_short, hook_badge=hook_badge, offset_s=st, dur=dur, split_mode=False)

        vf = (
            f"drawbox=x=0:y=0:w={SHORT_WIDTH}:h=16:color=black@0.40:t=fill,"
            f"drawbox=x=0:y=0:w='iw*t/{dur:.3f}':h=16:color=#FFD60A@0.98:t=fill,"
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


def _snap_window_to_scenes(
    scene_bounds: list[tuple[float, float]],
    target_start: float,
    tgt_dur: float,
    total: float,
    max_end: float | None = None,
) -> tuple[float, float]:
    """Alinha inicio e fim do Short exatamente nas fronteiras das falas para NUNCA cortar palavras."""
    end_limit = min(total, max_end) if max_end is not None else total
    if not scene_bounds:
        st = max(0.0, min(end_limit - tgt_dur, target_start))
        return round(st, 3), round(min(end_limit, st + tgt_dur), 3)

    min_span = min(SHORT_MIN_SECONDS, tgt_dur)
    max_span = max(SHORT_MAX_SECONDS, tgt_dur + 4.0)

    valid_starts = [s for s, _ in scene_bounds if s <= max(0.0, end_limit - min_span)]
    best_st = min(valid_starts, key=lambda s: abs(s - target_start)) if valid_starts else 0.0

    # Escolhe obrigatoriamente o final exato de uma cena dentro do limite permitido
    cands = [ce for _, ce in scene_bounds if ce <= end_limit + 0.05 and min_span <= (ce - best_st) <= max_span]
    if not cands:
        cands = [ce for _, ce in scene_bounds if ce <= end_limit + 0.05 and (ce - best_st) >= 12.0]
    if cands:
        best_en = min(cands, key=lambda ce: abs((ce - best_st) - tgt_dur))
    else:
        best_en = min(end_limit, best_st + tgt_dur)
    return round(best_st, 3), round(min(end_limit, best_en), 3)


def select_3_short_windows(
    visual_clips: list[dict[str, Any]],
    target_seconds: float | None = None,
) -> list[dict[str, Any]]:
    """Seleciona 3 janelas limpas (Gancho Ato 1, Storybook Ato 2, Climax Ato 3 sem pegar a despedida final)."""
    tgt = float(target_seconds) if target_seconds is not None else SHORT_TARGET_SECONDS
    if not visual_clips:
        return [{"name": "01_hook", "variant": "hook", "badge": "ELAS FALARAM?!", "start": 0.0, "end": tgt}]
    total = float(visual_clips[-1]["end"])
    if total <= tgt + 2.0:
        return [{"name": "01_hook", "variant": "hook", "badge": "ELAS FALARAM?!", "start": 0.0, "end": total}]

    scene_bounds: list[tuple[float, float]] = []
    seen: set[str] = set()
    for c in visual_clips:
        sid = c["scene_id"]
        if sid in seen:
            continue
        seen.add(sid)
        cs = float(c["scene_audio_start"])
        ce = cs + float(c["scene_audio_dur"]) + 0.22
        scene_bounds.append((cs, min(total, ce)))

    # Evita pegar o encerramento/CTA final do episodio longo no Short 03 quando ha duracao suficiente
    outro_guard = (scene_bounds[-2][0] - 0.1) if len(scene_bounds) >= 6 and total > 90.0 else total

    s1_st, s1_en = _snap_window_to_scenes(scene_bounds, 0.0, tgt, total)
    s2_st, s2_en = _snap_window_to_scenes(scene_bounds, max(s1_en * 0.85, total * 0.38), tgt, total)
    s3_st, s3_en = _snap_window_to_scenes(
        scene_bounds,
        max(s2_en * 0.85, outro_guard - tgt),
        tgt,
        total,
        max_end=outro_guard,
    )

    return [
        {"name": "01_hook", "variant": "hook", "badge": "ELAS FALARAM?!", "start": s1_st, "end": s1_en},
        {"name": "02_storybook", "variant": "storybook", "badge": "CAPÍTULO SECRETO!", "start": s2_st, "end": s2_en},
        {"name": "03_final", "variant": "final", "badge": "VIRADA SURPREENDENTE!", "start": s3_st, "end": s3_en},
    ]


def _draw_star_pil(draw, cx: float, cy: float, r_outer: float, r_inner: float, fill, outline=None, width: int = 2) -> None:
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        r = r_outer if k % 2 == 0 else r_inner
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    draw.polygon(pts, fill=fill)
    if outline:
        draw.line(pts + [pts[0]], fill=outline, width=width, joint="curve")


def _draw_paw_pil(draw, cx: float, cy: float, scale: float, fill) -> None:
    r_pad = 12 * scale
    draw.ellipse((cx - r_pad * 1.15, cy - r_pad * 0.7, cx + r_pad * 1.15, cy + r_pad * 1.1), fill=fill)
    for dx, dy in ((-14, -14), (-5, -20), (5, -20), (14, -14)):
        rt = 5.2 * scale
        draw.ellipse((cx + dx * scale - rt, cy + dy * scale - rt, cx + dx * scale + rt, cy + dy * scale + rt), fill=fill)


def _draw_cartoon_text(draw, xy: tuple[float, float], text: str, font, fill, outline, stroke_w: int = 4, shadow_offset: int = 3) -> None:
    x, y = xy
    if shadow_offset > 0:
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(32, 18, 42, 160), stroke_width=stroke_w, stroke_fill=(32, 18, 42, 160))
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_w, stroke_fill=outline)


def _build_top_frame_overlay(variant: str, out_png: Path) -> Path:
    """Cria moldura infantil/alegre transparente em PNG para o bloco superior de 70% (1080x1344)."""
    from PIL import Image, ImageDraw

    w, h = SHORT_WIDTH, SHORT_SPLIT_TOP_H
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if variant == "storybook":
        outer_col = (255, 245, 214, 245)
        inner_col = (245, 158, 11, 235)
        star_col = (253, 224, 71, 245)
    elif variant == "final":
        outer_col = (125, 211, 252, 240)
        inner_col = (251, 113, 133, 235)
        star_col = (253, 224, 71, 245)
    else:
        outer_col = (254, 240, 138, 240)
        inner_col = (255, 118, 87, 235)
        star_col = (255, 255, 255, 245)

    # Moldura arredondada suave nas bordas do filme (sem cobrir o centro)
    draw.rounded_rectangle((10, 22, w - 10, h - 10), radius=34, outline=outer_col, width=12)
    draw.rounded_rectangle((22, 34, w - 22, h - 22), radius=26, outline=inner_col, width=5)

    # Estrelinhas e patinhas nos cantos superiores
    _draw_star_pil(draw, 54, 66, 20, 9, star_col, outline=(120, 53, 15, 220), width=2)
    _draw_star_pil(draw, w - 54, 66, 20, 9, star_col, outline=(120, 53, 15, 220), width=2)
    _draw_star_pil(draw, 92, 54, 11, 5, (255, 255, 255, 235))
    _draw_star_pil(draw, w - 92, 54, 11, 5, (255, 255, 255, 235))
    if variant == "storybook":
        _draw_paw_pil(draw, 62, h - 54, 0.95, (255, 245, 214, 215))
        _draw_paw_pil(draw, w - 62, h - 54, 0.95, (255, 245, 214, 215))

    img.save(out_png)
    return out_png


def _build_bottom_playful_backdrop(w: int, h: int, variant: str):
    """Constroi o cenario infantil alegre dos 30% inferiores (1080x576) usando PIL com acentos perfeitos."""
    import numpy as np
    from PIL import Image, ImageDraw

    if variant == "storybook":
        c_top = (255, 216, 168)   # pessego quente livro de historias
        c_bot = (254, 247, 198)   # creme manteiga alegre
        ribbon_bg = (249, 115, 22)
        ribbon_border = (255, 255, 255)
        dot_cols = ((255, 255, 255, 110), (251, 146, 60, 75), (250, 204, 21, 95))
        trim_cols = ((251, 146, 60), (250, 204, 21), (244, 114, 182), (56, 189, 248))
    elif variant == "final":
        c_top = (221, 214, 254)   # lavanda doce festa
        c_bot = (186, 230, 253)   # azul ceu turquesa
        ribbon_bg = (236, 72, 153)
        ribbon_border = (255, 255, 255)
        dot_cols = ((255, 255, 255, 120), (192, 132, 252, 85), (56, 189, 248, 85))
        trim_cols = ((236, 72, 153), (250, 204, 21), (56, 189, 248), (74, 222, 128))
    else:
        c_top = (147, 220, 255)   # azul ceu ensolarado
        c_bot = (254, 243, 168)   # amarelo sol pastel
        ribbon_bg = (255, 77, 109)
        ribbon_border = (255, 255, 255)
        dot_cols = ((255, 255, 255, 125), (253, 224, 71, 95), (56, 189, 248, 70))
        trim_cols = ((255, 77, 109), (250, 204, 21), (56, 189, 248), (168, 85, 247))

    # Gradiente pastel luminoso e feliz
    grad = np.zeros((h, w, 3), dtype=np.uint8)
    for yy in range(h):
        r = yy / max(1, h - 1)
        grad[yy, :] = [int(c_top[k] * (1.0 - r) + c_bot[k] * r) for k in range(3)]

    img = Image.fromarray(grad, mode="RGB").convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Bolinhas suaves / nuvens de fundo
    bubbles = [
        (70, 145, 58), (195, 510, 44), (540, 170, 62), (540, 395, 52),
        (985, 155, 56), (1020, 470, 48), (445, 520, 36), (635, 525, 36),
    ]
    for idx, (bx, by, br) in enumerate(bubbles):
        col = dot_cols[idx % len(dot_cols)]
        draw.ellipse((bx - br, by - br, bx + br, by + br), fill=col)

    # Patinhas decorativas sutis nas laterais e centro
    _draw_paw_pil(draw, 540, 285, 1.35, (255, 255, 255, 110))
    _draw_paw_pil(draw, 44, 340, 1.0, (255, 255, 255, 115))
    _draw_paw_pil(draw, w - 44, 340, 1.0, (255, 255, 255, 115))

    # Faixa colorida festiva dividindo os 70% de cima e os 30% de baixo
    seg_w = w // 12
    for s_idx in range(13):
        x0 = s_idx * seg_w
        draw.rectangle((x0, 0, x0 + seg_w, 10), fill=trim_cols[s_idx % len(trim_cols)] + (255,))
    draw.rectangle((0, 10, w, 14), fill=(255, 255, 255, 235))

    # Pilula CTA infantil alegre com acentos perfeitos
    pill_box = (84, 18, w - 84, 76)
    draw.rounded_rectangle((pill_box[0] + 4, pill_box[1] + 5, pill_box[2] + 4, pill_box[3] + 5), radius=28, fill=(45, 20, 60, 85))
    draw.rounded_rectangle(pill_box, radius=28, fill=ribbon_bg + (255,), outline=ribbon_border + (255,), width=4)

    font_cta = _load_playful_font(33)
    cta_txt = "VÍDEO COMPLETO NO CANAL!"
    bbox = draw.textbbox((0, 0), cta_txt, font=font_cta, stroke_width=3)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (w - tw) / 2.0
    ty = pill_box[1] + (pill_box[3] - pill_box[1] - th) / 2.0 - bbox[1]
    _draw_cartoon_text(draw, (tx, ty), cta_txt, font_cta, fill=(255, 255, 255, 255), outline=(92, 18, 45, 255), stroke_w=3, shadow_offset=2)

    # Estrelinhas nas pontas da pilula CTA
    _draw_star_pil(draw, pill_box[0] + 44, (pill_box[1] + pill_box[3]) / 2, 17, 8, (254, 240, 138, 255), outline=(146, 64, 14, 255), width=2)
    _draw_star_pil(draw, pill_box[2] - 44, (pill_box[1] + pill_box[3]) / 2, 17, 8, (254, 240, 138, 255), outline=(146, 64, 14, 255), width=2)

    # Converte para BGR (OpenCV)
    rgb = np.array(img.convert("RGB"), dtype=np.uint8)
    return rgb[:, :, ::-1].copy()


def _make_sticker_badge_bgra(label: str, bg_rgb: tuple[int, int, int], outline_rgb: tuple[int, int, int], w: int = 230, h: int = 58):
    """Cria sticker arredondado infantil com nome (FRIDA / LUNA / FALANDO!) em BGRA."""
    import numpy as np
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((5, 6, w - 3, h - 2), radius=h // 2, fill=(35, 18, 52, 95))
    draw.rounded_rectangle((3, 2, w - 5, h - 6), radius=h // 2, fill=bg_rgb + (255,), outline=(255, 255, 255, 255), width=4)

    font = _load_playful_font(30 if len(label) <= 7 else 24)
    bbox = draw.textbbox((0, 0), label, font=font, stroke_width=3)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (w - tw) / 2.0 - 1
    ty = (h - 6 - th) / 2.0 - bbox[1] + 1
    _draw_cartoon_text(draw, (tx, ty), label, font, fill=(255, 255, 255, 255), outline=outline_rgb + (255,), stroke_w=3, shadow_offset=2)

    rgba = np.array(img, dtype=np.uint8)
    bgra = rgba[:, :, [2, 1, 0, 3]].copy()
    return bgra


def _alpha_paste_bgra(canvas, bgra, cx: int, cy: int) -> None:
    import numpy as np
    sh, sw = bgra.shape[:2]
    ch, cw = canvas.shape[:2]
    x0 = max(0, min(cw - sw, int(cx - sw // 2)))
    y0 = max(0, min(ch - sh, int(cy - sh // 2)))
    roi = canvas[y0:y0 + sh, x0:x0 + sw]
    a = (bgra[:, :, 3:4].astype(np.float32)) / 255.0
    canvas[y0:y0 + sh, x0:x0 + sw] = np.clip(
        roi.astype(np.float32) * (1.0 - a) + bgra[:, :, :3].astype(np.float32) * a, 0, 255
    ).astype(np.uint8)


def _build_per_frame_speaker_and_levels(
    visual_clips: list[dict[str, Any]],
    st: float,
    dur: float,
    wav_fallback: Path,
    fps: int,
    n_frames: int,
) -> tuple[list[str], list[int]]:
    """Mapeia cada frame para (speaker, level) usando o WAV isolado da fala de Frida/Luna quando disponivel."""
    from core.avatar_studio import _compute_speech_levels

    fallback_levels = _compute_speech_levels(wav_fallback, fps, n_frames, threshold=0.015, silence_ms=420) if wav_fallback.exists() else [0] * n_frames

    speakers = ["narrador"] * n_frames
    levels = [0] * n_frames

    seen_sids: set[str] = set()
    for c in visual_clips:
        sid = c["scene_id"]
        if sid in seen_sids:
            continue
        seen_sids.add(sid)
        cs = float(c["scene_audio_start"]) - st
        sdur = float(c["scene_audio_dur"])
        ce = cs + sdur
        if ce <= 0.0 or cs >= dur:
            continue

        spk = str(c.get("speaker") or "narrador").strip().lower()
        i0 = max(0, int(round(cs * fps)))
        i1 = min(n_frames, int(round(ce * fps)))

        if spk not in ("frida", "luna"):
            for i in range(i0, i1):
                speakers[i] = spk
                levels[i] = 0
            continue

        # Usa o WAV limpo e isolado da fala do personagem (sem musica/SFX misturados!)
        scene_wav_str = str(c.get("wav_path") or "")
        scene_wav = Path(scene_wav_str) if scene_wav_str else None
        scene_levels: list[int] | None = None
        if scene_wav and scene_wav.is_file():
            sc_total_frames = max(1, int(round(sdur * fps)))
            try:
                scene_levels = _compute_speech_levels(scene_wav, fps, sc_total_frames, threshold=0.015, silence_ms=420)
            except Exception:
                scene_levels = None

        for i in range(i0, i1):
            speakers[i] = spk
            if scene_levels is not None:
                local_t = (i / float(fps)) - cs
                sc_idx = max(0, min(len(scene_levels) - 1, int(round(local_t * fps))))
                levels[i] = scene_levels[sc_idx]
            else:
                levels[i] = fallback_levels[i]

    return speakers, levels


class _SmoothAvatarPlayer:
    """Reprodutor sequencial 30fps continuo (igual ao video principal) sem trepidacao nem teleporte de frames."""

    def __init__(self, bank: dict[str, Any], seed: int = 1, crossfade_len: int = 9) -> None:
        import random
        self.rng = random.Random(seed)
        self.rep_frames = bank["reposo"]
        self.hab_bank = bank["hablando"]
        self.crossfade_len = max(1, int(crossfade_len))

        self.idx_rep = 0
        self.cur_vid_idx = self.rng.randrange(len(self.hab_bank))
        self.cur_vid = self.hab_bank[self.cur_vid_idx]
        self.idx_hab = self.rng.choice(self.cur_vid.get("peak_starts") or [4])
        self.was_talking = False

        self.blend_rem = 0
        self.xf_from = self.rep_frames[0]
        self.last_out = self.rep_frames[0]

    def _start_crossfade(self) -> None:
        self.xf_from = self.last_out.copy()
        self.blend_rem = self.crossfade_len

    def _pick_next_hab_clip(self, prefer_peak: bool = False) -> None:
        if len(self.hab_bank) > 1:
            cands = [k for k in range(len(self.hab_bank)) if k != self.cur_vid_idx]
            self.cur_vid_idx = self.rng.choice(cands)
        self.cur_vid = self.hab_bank[self.cur_vid_idx]
        peaks = self.cur_vid.get("peak_starts") or []
        if prefer_peak and peaks:
            self.idx_hab = self.rng.choice(peaks)
        else:
            max_start = max(4, len(self.cur_vid["frames"]) - 24)
            self.idx_hab = self.rng.randint(4, max_start)
        self._start_crossfade()

    def next_frame(self, talking: bool, speech_level: int):
        import cv2

        if not talking:
            if self.was_talking:
                self._start_crossfade()
                self.was_talking = False
            else:
                self.idx_rep += 1
                if self.idx_rep >= max(1, len(self.rep_frames) - 6):
                    self._start_crossfade()
                    self.idx_rep = 0
            raw_sq = self.rep_frames[self.idx_rep % len(self.rep_frames)]
        else:
            if not self.was_talking:
                self._pick_next_hab_clip(prefer_peak=(speech_level >= 2))
                self.was_talking = True
            else:
                self.idx_hab += 1
                if self.idx_hab >= max(1, len(self.cur_vid["frames"]) - 6):
                    self._pick_next_hab_clip(prefer_peak=(speech_level >= 2))
            raw_sq = self.cur_vid["frames"][self.idx_hab % len(self.cur_vid["frames"])]

        if self.blend_rem > 0:
            a = (self.crossfade_len - self.blend_rem + 1) / float(self.crossfade_len + 1)
            out = cv2.addWeighted(self.xf_from, 1.0 - a, raw_sq, a, 0)
            self.blend_rem -= 1
        else:
            out = raw_sq
        self.last_out = out
        return out


def _render_split_bottom_stage(
    visual_clips: list[dict[str, Any]],
    st: float,
    dur: float,
    wav_path: Path,
    out_mp4: Path,
    variant: str = "hook",
) -> Path | None:
    """Renderiza os 30% inferiores (1080x576) com visual infantil alegre, 30fps fluido e sincronia labial estrita."""
    import cv2
    import numpy as np
    from config import AVATAR_PROFILES, VIDEO_FPS
    from core.avatar_studio import _index_character_bank, _make_card_mask

    frida_bank = _index_character_bank("frida")
    luna_bank = _index_character_bank("luna")
    if not frida_bank or not luna_bank:
        return None

    w, h = SHORT_WIDTH, SHORT_SPLIT_BOT_H  # 1080 x 576
    fps = VIDEO_FPS
    n_frames = max(1, int(round(dur * fps)))
    frame_speakers, frame_levels = _build_per_frame_speaker_and_levels(
        visual_clips, st, dur, wav_path, fps, n_frames
    )

    # ZONA SEGURA (DESIGN.md): y global 1620..1920 = y local 276..576 do palco fica LIVRE
    # (UI do YouTube Shorts/Reels/TikTok tampa essa faixa). Todo conteudo importante fica em y local <= 270.
    SAFE_BOTTOM_LOCAL = SHORT_SPLIT_BOT_H - 300  # 576 - 300 = 276 (limite superior da zona livre)

    # Card reduzido para caber inteiro acima da zona segura (cy=145, card=250 -> y 20..270)
    card_sz = 250
    card_mask = _make_card_mask(card_sz)
    in_sz = card_sz - 2 * card_mask["margin"]
    alpha_f = (card_mask["alpha"].astype(np.float32) / 255.0)[:, :, None]

    bg_base = _build_bottom_playful_backdrop(w, h, variant)
    badge_frida = _make_sticker_badge_bgra("FRIDA", (245, 158, 11), (120, 53, 15), w=180, h=44)
    badge_luna = _make_sticker_badge_bgra("LUNA", (6, 182, 212), (22, 78, 99), w=180, h=44)
    badge_talk_f = _make_sticker_badge_bgra("FALANDO!", (255, 77, 109), (125, 18, 48), w=170, h=40)
    badge_talk_l = _make_sticker_badge_bgra("FALANDO!", (139, 92, 246), (62, 24, 128), w=170, h=40)

    # Estrelinhas tambem limitadas a y <= 250 (nunca na zona segura)
    sparkle_pts = [
        (58, 110, 0.0), (540, 100, 1.3), (1022, 112, 2.5),
        (540, 238, 0.8), (64, 246, 2.1), (1016, 244, 3.1),
    ]

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    tmp_raw = out_mp4.with_suffix(".bot_raw.mp4")
    vw = cv2.VideoWriter(str(tmp_raw), fourcc, float(fps), (w, h))

    seed_base = abs(hash(f"{variant}_{int(round(st * 10))}")) % (2 ** 31)
    frida_player = _SmoothAvatarPlayer(frida_bank, seed=seed_base + 11, crossfade_len=10)
    luna_player = _SmoothAvatarPlayer(luna_bank, seed=seed_base + 29, crossfade_len=18)

    prof_f = AVATAR_PROFILES["frida"]
    prof_l = AVATAR_PROFILES["luna"]

    def _paste_card(
        canvas: np.ndarray,
        raw_sq: np.ndarray,
        cx: int,
        cy: int,
        highlighted: bool,
        prof: dict[str, Any],
        glow_bgr: tuple[int, int, int],
    ) -> None:
        sq = cv2.resize(raw_sq, (in_sz, in_sz), interpolation=cv2.INTER_AREA)
        card = np.zeros((card_sz, card_sz, 3), np.uint8)
        m = card_mask["margin"]
        card[m:card_sz - m, m:card_sz - m] = sq
        card[card_mask["outer_border"] > 0] = glow_bgr if highlighted else (255, 255, 255)
        card[card_mask["inner_border"] > 0] = prof["border_gold_bgr"] if highlighted else prof["border_accent_bgr"]
        card[card_mask["outline"] > 0] = (90, 48, 86)

        x0 = max(0, min(w - card_sz, cx - card_sz // 2))
        y0 = max(0, min(h - card_sz, cy - card_sz // 2))

        if highlighted:
            cv2.circle(canvas, (cx, cy), card_sz // 2 + 10, glow_bgr, 10, cv2.LINE_AA)

        roi = canvas[y0:y0 + card_sz, x0:x0 + card_sz]
        canvas[y0:y0 + card_sz, x0:x0 + card_sz] = np.clip(
            roi.astype(np.float32) * (1.0 - alpha_f) + card.astype(np.float32) * alpha_f, 0, 255
        ).astype(np.uint8)

    try:
        for i in range(n_frames):
            t = i / float(fps)
            spk = frame_speakers[i]
            lv = frame_levels[i]
            f_talking, l_talking = resolve_split_avatar_states(spk, lv)

            # Destaque visual firme durante todo o turno da personagem (sem piscar em virgulas)
            f_turn = (spk == "frida")
            l_turn = (spk == "luna")

            fr_img = frida_player.next_frame(f_talking, lv)
            lu_img = luna_player.next_frame(l_talking, lv)

            frame = bg_base.copy()

            # Estrelinhas piscando suavemente no fundo pastel
            for sx, sy, ph in sparkle_pts:
                pulse = 0.5 + 0.5 * math.sin(t * 3.0 + ph)
                rad = int(5 + 6 * pulse)
                cv2.line(frame, (sx - rad, sy), (sx + rad, sy), (255, 255, 255), 3, cv2.LINE_AA)
                cv2.line(frame, (sx, sy - rad), (sx, sy + rad), (255, 255, 255), 3, cv2.LINE_AA)
                cv2.circle(frame, (sx, sy), max(2, rad // 3), (120, 235, 255), -1, cv2.LINE_AA)

            # Posicao 100% estavel (zero trepidacao!) — tudo acima de SAFE_BOTTOM_LOCAL (y local <= 270)
            _paste_card(frame, fr_img, 285, 145, f_turn, prof_f, (20, 215, 255))
            _paste_card(frame, lu_img, 795, 145, l_turn, prof_l, (240, 225, 45))

            # Badges de identificacao colados logo abaixo do card, ainda dentro da zona segura
            _alpha_paste_bgra(frame, badge_frida, 285, 250)
            _alpha_paste_bgra(frame, badge_luna, 795, 250)

            # Badge FALANDO! no topo do palco (y local ~30)
            if f_turn:
                _alpha_paste_bgra(frame, badge_talk_f, 285, 34)
            elif l_turn:
                _alpha_paste_bgra(frame, badge_talk_l, 795, 34)

            vw.write(frame)
    finally:
        vw.release()

    subprocess.run(
        [FFMPEG_EXE, "-y", "-v", "error", "-i", str(tmp_raw),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out_mp4)],
        check=True,
    )
    tmp_raw.unlink(missing_ok=True)
    return out_mp4


def export_split_short_70_30(
    master_16_9: Path,
    visual_clips: list[dict[str, Any]],
    out_short: Path,
    st: float,
    en: float,
    hook_badge: str = "ELAS FALARAM?!",
    variant: str = "hook",
) -> Path:
    """Gera Short 9:16 Split-Screen 70% topo (filme) / 30% base (Frida & Luna alegres com sincronia estrita)."""
    dur = max(1.0, round(en - st, 3))
    top_h = SHORT_SPLIT_TOP_H  # 1344 (70%)
    out_short.parent.mkdir(parents=True, exist_ok=True)

    tmp_audio = out_short.with_suffix(".s_aud.wav")
    tmp_top = out_short.with_suffix(".s_top.mp4")
    tmp_bot = out_short.with_suffix(".s_bot.mp4")
    tmp_frame = out_short.with_suffix(".s_frame.png")
    ass_short = out_short.with_suffix(".ass")

    try:
        subprocess.run(
            [FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{st:.3f}", "-t", f"{dur:.3f}",
             "-i", str(master_16_9), "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(tmp_audio)],
            check=True,
        )
        from config import VIDEO_FPS
        _build_top_frame_overlay(variant, tmp_frame)

        crop_w = f"ih*{SHORT_WIDTH}/{top_h}"
        x_pan = f"(iw-{crop_w})*(0.5+0.18*sin(2*PI*t/8))"
        top_fc = (
            f"[0:v]fps={VIDEO_FPS},setpts=PTS-STARTPTS,crop={crop_w}:ih:{x_pan}:0,scale={SHORT_WIDTH}:{top_h}:flags=lanczos,setsar=1[base];"
            f"[1:v]fps={VIDEO_FPS},setpts=PTS-STARTPTS[frm];"
            f"[base][frm]overlay=0:0:shortest=1[topout]"
        )
        subprocess.run(
            [FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{st:.3f}", "-t", f"{dur:.3f}", "-i", str(master_16_9),
             "-framerate", str(VIDEO_FPS), "-loop", "1", "-i", str(tmp_frame),
             "-filter_complex", top_fc, "-map", "[topout]", "-t", f"{dur:.3f}",
             "-r", str(VIDEO_FPS), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", str(tmp_top)],
            check=True,
        )

        bot_ok = _render_split_bottom_stage(visual_clips, st, dur, tmp_audio, tmp_bot, variant=variant)
        if bot_ok is None:
            return export_motion_short_9_16(master_16_9, visual_clips, out_short, hook_badge=hook_badge, engine="motion_hud")

        win_clips = [c for c in visual_clips if float(c["end"]) > st and float(c["start"]) < en]
        write_short_pop_ass(win_clips, ass_short, hook_badge=hook_badge, offset_s=st, dur=dur, split_mode=True, variant=variant)

        fc = (
            f"[0:v]fps={VIDEO_FPS},setpts=PTS-STARTPTS[tv];"
            f"[1:v]fps={VIDEO_FPS},setpts=PTS-STARTPTS[bv];"
            f"[tv][bv]vstack=inputs=2,"
            f"drawbox=x=0:y=0:w={SHORT_WIDTH}:h=16:color=#FFFBEB@0.45:t=fill,"
            f"drawbox=x=0:y=0:w='iw*t/{dur:.3f}':h=16:color=#FFD60A@0.98:t=fill,"
            f"ass={ass_short.name}[vout]"
        )
        subprocess.run(
            [FFMPEG_EXE, "-y", "-v", "error", "-i", str(tmp_top), "-i", str(tmp_bot), "-i", str(tmp_audio),
             "-filter_complex", fc, "-map", "[vout]", "-map", "2:a",
             "-r", str(VIDEO_FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out_short)],
            cwd=str(ass_short.parent),
            check=True,
        )
        return out_short
    finally:
        tmp_audio.unlink(missing_ok=True)
        tmp_top.unlink(missing_ok=True)
        tmp_bot.unlink(missing_ok=True)
        tmp_frame.unlink(missing_ok=True)


def export_split_short_60_40(
    master_16_9: Path,
    visual_clips: list[dict[str, Any]],
    out_short: Path,
    st: float,
    en: float,
    hook_badge: str = "ELAS FALARAM?!",
    variant: str = "hook",
) -> Path:
    """Alias de compatibilidade que redireciona para o layout oficial Split 70/30 infantil."""
    return export_split_short_70_30(master_16_9, visual_clips, out_short, st=st, en=en, hook_badge=hook_badge, variant=variant)


def export_3_shorts_pack(
    master_16_9: Path,
    visual_clips: list[dict[str, Any]],
    output_dir: Path,
    slug: str,
    hook_badge: str = "ELAS FALARAM?!",
    target_seconds: float | None = None,
) -> list[Path]:
    """Gera 3 Shorts 9:16 Split-Screen 70/30 distintos por episodio + copia compatibilidade."""
    windows = select_3_short_windows(visual_clips, target_seconds=target_seconds)
    out_paths: list[Path] = []
    for idx, win in enumerate(windows):
        out_p = output_dir / f"{slug}_short_{win['name']}.mp4"
        badge = hook_badge if idx == 0 and hook_badge else win["badge"]
        export_split_short_70_30(
            master_16_9,
            visual_clips,
            out_p,
            st=win["start"],
            en=win["end"],
            hook_badge=badge,
            variant=win["variant"],
        )
        out_paths.append(out_p)
    compat = output_dir / f"{slug}_short_9x16.mp4"
    if out_paths and out_paths[0].exists():
        shutil.copy2(out_paths[0], compat)
    return out_paths
