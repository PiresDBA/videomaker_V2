# -*- coding: utf-8 -*-
"""CTA infantil em VIDEO (Regra 25, revisada em 2026-11-24).

Dois arquivos de referencia (baixados pelo usuario, em `Downloads`):

  * `like-sem-som.mp4` — entra no MEIO do video (sem audio);
  * `like-com-som.mp4` — entra nos ULTIMOS 10 segundos (com o som do sininho).

Ambos tem fundo verde solido: chroma key `colorkey=0x00FF00:0.28:0.12`.
Nao usar `despill` aqui — ele pintava o sino amarelo de laranja. O blend de
0,12 ja remove o contorno verde sem estragar as cores do desenho.

O overlay e redimensionado para 35% da largura do quadro, alinhado no terço
inferior com margem de seguranca de 5%, com fade de entrada/saida de 0,2s.
O audio do CTA final entra a -13 dB (faixa pedida: -12 a -15 dB) para nao
abafar a narracao.

Os arquivos de midia NAO sao versionados (`.gitignore`). Copie os dois `.mp4`
para `assets/reference/overlays/` na maquina nova; o modulo tambem procura em
`~/Downloads` por conveniencia.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from config import FFMPEG_EXE, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH

ROOT = Path(__file__).resolve().parent.parent
OVERLAY_DIR = ROOT / "assets" / "reference" / "overlays"

CTA_SIMILARITY = 0.28
CTA_BLEND = 0.12
CTA_FADE_S = 0.20
CTA_WIDTH_RATIO = 0.35       # 28%-35% da largura do quadro
CTA_MARGIN_RATIO = 0.05      # margem de seguranca
CTA_AUDIO_GAIN_DB = -13.0    # faixa usada quando o CTA NAO concorre com narração
# 2026-11-24: o like-com-som.mp4 fala "clica no sininho, se inscreva" ENQUANTO a
# narradora diz a mesma coisa — as duas vozes se sobrepunham. O usuario mandou
# deixar a animacao e SILENCIAR o audio do video final. Narração tem prioridade.
CTA_AUDIO_MUTED = True
CTA_MID_SECONDS = 600        # em videos longos, repetir a cada 10 minutos
CTA_FINAL_WINDOW_S = 9.5     # "ultimos 10 segundos"

# area util dos arquivos de referencia (1280x720), em fracoes do quadro
_CROP_X, _CROP_Y = 0.117, 0.055
_CROP_W, _CROP_H = 0.765, 0.917


def cta_reference(name: str) -> Path | None:
    """Localiza um arquivo de referencia (pasta do projeto primeiro, Downloads depois)."""
    for base in (OVERLAY_DIR, Path.home() / "Downloads"):
        p = base / name
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None


def _probe_wh(path: Path) -> tuple[int, int]:
    ffprobe = Path(FFMPEG_EXE).with_name("ffprobe.exe")
    r = subprocess.run([str(ffprobe), "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
                       capture_output=True, text=True)
    try:
        w, h = r.stdout.strip().split("x")[:2]
        return int(w), int(h)
    except (ValueError, TypeError):
        return 1280, 720


def _video_filter(src_w: int, src_h: int, duration: float) -> tuple[str, int, int, int, int]:
    cx = int(src_w * _CROP_X)
    cy = int(src_h * _CROP_Y)
    cw = int(src_w * _CROP_W)
    ch = int(src_h * _CROP_H)
    ow = int(VIDEO_WIDTH * CTA_WIDTH_RATIO)
    oh = int(round(ow * ch / cw))
    ox = (VIDEO_WIDTH - ow) // 2
    oy = VIDEO_HEIGHT - oh - int(VIDEO_HEIGHT * CTA_MARGIN_RATIO)
    vf = (
        f"fps={VIDEO_FPS},"
        f"colorkey=0x00FF00:{CTA_SIMILARITY}:{CTA_BLEND},"
        f"crop={cw}:{ch}:{cx}:{cy},"
        f"scale={ow}:{oh}:flags=lanczos,format=rgba,"
        f"fade=t=in:st=0:d={CTA_FADE_S:.2f}:alpha=1,"
        f"fade=t=out:st={max(0.0, duration - CTA_FADE_S):.2f}:d={CTA_FADE_S:.2f}:alpha=1"
    )
    return vf, ox, oy, ow, oh


def render_overlay_clip(src: Path, start_s: float, duration: float, out_mov: Path) -> dict[str, Any]:
    """Recorta o trecho, remove o verde e gera `.mov` com canal alpha (qtrle)."""
    out_mov.parent.mkdir(parents=True, exist_ok=True)
    sw, sh = _probe_wh(src)
    vf, ox, oy, ow, oh = _video_filter(sw, sh, duration)
    cmd = [FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{start_s:.3f}", "-i", str(src),
           "-t", f"{duration:.3f}", "-an", "-vf", vf, "-c:v", "qtrle",
           "-pix_fmt", "argb", str(out_mov)]
    subprocess.run(cmd, check=True)
    return {"path": out_mov, "start": start_s, "duration": duration,
            "x": ox, "y": oy, "width": ow, "height": oh}


def render_overlay_audio(src: Path, start_s: float, duration: float, out_wav: Path) -> Path:
    """Audio do CTA final (-13 dB), recortado exatamente como o video."""
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    af = (f"atrim=start={start_s:.3f}:duration={duration:.3f},asetpts=PTS-STARTPTS,"
          f"aformat=sample_rates=44100:channel_layouts=stereo,volume={CTA_AUDIO_GAIN_DB:.1f}dB")
    subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-i", str(src), "-vn",
                    "-af", af, "-c:a", "pcm_s16le", str(out_wav)], check=True)
    return out_wav


def _nearest_scene_start(visual_clips: list[dict[str, Any]], target: float) -> float:
    """Entra no inicio de uma cena (evita corte brusco no meio da fala)."""
    starts: dict[str, float] = {}
    for c in visual_clips:
        sid = c.get("scene_id", "")
        st = float(c.get("start") or 0.0)
        if sid not in starts or st < starts[sid]:
            starts[sid] = st
    if not starts:
        return max(0.0, target)
    return min(starts.values(), key=lambda s: abs(s - target))


def plan_ctas(proj_dir: Path, total_dur: float, visual_clips: list[dict[str, Any]],
              silent_ref: Path | None = None, sounded_ref: Path | None = None) -> dict[str, Any]:
    """Gera os overlays do meio/fim. Sem arquivos de referencia, nao faz nada."""
    silent = silent_ref or cta_reference("like-sem-som.mp4")
    sounded = sounded_ref or cta_reference("like-com-som.mp4")
    if silent is None or sounded is None or total_dur < 20:
        return {"events": [], "audio_wav": None, "enabled": False}

    work = proj_dir / "work" / "cta"
    work.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, Any]] = []

    # Meio do video: ~50%. Em episodios longos, repetir a cada 10 minutos tambem.
    if total_dur >= CTA_MID_SECONDS:
        targets = sorted(set([total_dur * 0.5]
                             + [float(t) for t in range(int(CTA_MID_SECONDS), int(total_dur),
                                                        int(CTA_MID_SECONDS))]))
    else:
        targets = [total_dur * 0.5]
    for i, target in enumerate(targets):
        st = _nearest_scene_start(visual_clips, target)
        dur = min(4.5, max(2.0, total_dur - st - 1.0))
        clip = render_overlay_clip(silent, 1.0, dur, work / f"cta_mid_{i:02d}.mov")
        clip["timeline_start"] = round(st, 3)
        clip["position"] = "middle"
        events.append(clip)

    # Final: ultimos 10 segundos, com o som do sininho.
    final_dur = min(CTA_FINAL_WINDOW_S, max(3.0, total_dur * 0.2))
    final_start = max(0.0, total_dur - final_dur)
    final = render_overlay_clip(sounded, 0.5, final_dur, work / "cta_final.mov")
    final["timeline_start"] = round(final_start, 3)
    final["position"] = "final"
    events.append(final)
    # Audio: o video final fica SEM VOZ (a narradora ja faz o CTA falado).
    audio = None
    if not CTA_AUDIO_MUTED:
        audio = render_overlay_audio(sounded, 0.5, final_dur, work / "cta_final_audio.wav")
    payload = {
        "version": 1,
        "events": [{k: e[k] for k in ("position", "timeline_start", "duration", "x", "y", "width", "height")}
                   for e in events],
        "similarity": CTA_SIMILARITY,
        "blend": CTA_BLEND,
        "fade_s": CTA_FADE_S,
        "audio_gain_db": CTA_AUDIO_GAIN_DB,
        "audio_muted": CTA_AUDIO_MUTED,
        "sources": {"middle": "like-sem-som.mp4", "final": "like-com-som.mp4"},
    }
    (work / "cta_plan.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"events": events, "audio_wav": audio, "enabled": True,
            "similarity": CTA_SIMILARITY, "blend": CTA_BLEND,
            "audio_gain_db": CTA_AUDIO_GAIN_DB, "audio_muted": CTA_AUDIO_MUTED}


def mix_cta_audio(mix_m4a: Path, cta_wav: Path, start_s: float, total_dur: float, out_m4a: Path) -> Path:
    """Mixa o som do CTA final ao mix master sem alterar o nivel da narracao."""
    ms = max(0, int(round(start_s * 1000)))
    fc = (f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,adelay={ms}|{ms}[cta];"
          "[0:a][cta]amix=inputs=2:duration=first:normalize=0,alimiter=level=false:limit=0.95[out]")
    subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-i", str(mix_m4a), "-i", str(cta_wav),
                    "-filter_complex", fc, "-map", "[out]", "-t", f"{total_dur:.3f}",
                    "-c:a", "aac", "-b:a", "192k", str(out_m4a)], check=True)
    return out_m4a
