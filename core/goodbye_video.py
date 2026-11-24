# -*- coding: utf-8 -*-
"""Despedida canônica (Regra 25): um único vídeo reuseável em todos os episódios.

O arquivo `assets/reference/goodbye/despedida_subscribe.mp4` é a cena final.
Áudio nunca entra: a narração já diz "se inscreve no canal", e a voz do clipe
brigava com ela. Se o arquivo canônico ainda não existe, usa-se a composição
antiga (confete + clipe legado) apenas como ponte — mas o clipe legado com
patinha fantasma está na blacklist e será reprovado pela porta de entrega.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from config import FFMPEG_EXE, GOODBYE_VIDEO_PATH, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH

LEGACY_CONFETE = (GOODBYE_VIDEO_PATH.parent.parent / "primeiro-dia-de-praia" / "flow_all"
                  / "acc_3" / "videos" / "acc_3_225a8b1e_vid_11_ae84f4b6a0.mp4")
LEGACY_SUBSCRIBE = LEGACY_CONFETE.with_name("acc_3_225a8b1e_vid_10_f3c7928cd5.mp4")


def _probe(p: Path) -> float:
    ffprobe = Path(FFMPEG_EXE).with_name("ffprobe.exe")
    r = subprocess.run([str(ffprobe), "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _trim_silent(src: Path, start: float, duration: float, out: Path) -> Path:
    vf = (f"fps={VIDEO_FPS},scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
          f"force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
          "setsar=1,format=yuv420p")
    subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-ss", f"{start:.3f}", "-i", str(src),
                    "-t", f"{duration:.3f}", "-an", "-vf", vf, "-c:v", "libx264",
                    "-preset", "fast", "-crf", "18", str(out)], check=True)
    return out


def _concat_xfade(parts: list[Path], out: Path, fade: float = 0.4) -> None:
    cmd = [FFMPEG_EXE, "-y", "-v", "error"]
    for p in parts:
        cmd += ["-i", str(p)]
    filters = [f"[{i}:v]fps={VIDEO_FPS},settb=AVTB,format=yuv420p,setpts=PTS-STARTPTS[s{i}]"
               for i in range(len(parts))]
    durs = [_probe(p) for p in parts]
    prev, cum = "[s0]", durs[0]
    for i in range(1, len(parts)):
        lbl = "[vout]" if i == len(parts) - 1 else f"[x{i}]"
        off = max(0.0, cum - fade)
        filters.append(f"{prev}[s{i}]xfade=transition=fade:duration={fade}:offset={off:.3f}{lbl}")
        prev = lbl
        cum = off + durs[i]
    subprocess.run(cmd + ["-filter_complex", ";".join(filters), "-map", "[vout]", "-an",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                          "-pix_fmt", "yuv420p", str(out)], check=True)


def prepare_goodbye(proj_dir: Path, target_seconds: float = 7.5) -> dict[str, Any]:
    """Materializa `assets/videos/sc_30.mp4`. Nunca copia áudio do clipe de despedida."""
    out_dir = proj_dir / "assets" / "videos"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "sc_30.mp4"
    work = proj_dir / "work"
    work.mkdir(parents=True, exist_ok=True)

    if GOODBYE_VIDEO_PATH.exists() and GOODBYE_VIDEO_PATH.stat().st_size > 1000:
        d = _probe(GOODBYE_VIDEO_PATH)
        start = min(0.5, max(0.0, d - target_seconds))
        _trim_silent(GOODBYE_VIDEO_PATH, start, min(target_seconds, d - start), out)
        return {"source": "canonical", "path": str(GOODBYE_VIDEO_PATH),
                "duration": round(_probe(out), 3), "audio": "muted"}

    # Ponte legada — será reprovada se o clipe antigo estiver na blacklist.
    if not LEGACY_CONFETE.exists() or not LEGACY_SUBSCRIBE.exists():
        raise FileNotFoundError(
            f"Despedida canônica ausente: {GOODBYE_VIDEO_PATH}. "
            "Coloque o MP4 novo em assets/reference/goodbye/despedida_subscribe.mp4"
        )
    tmp1 = work / "_gb1.mp4"
    tmp2 = work / "_gb2.mp4"
    _trim_silent(LEGACY_CONFETE, 0.6, 1.6, tmp1)
    _trim_silent(LEGACY_SUBSCRIBE, 1.4, 5.0, tmp2)
    _concat_xfade([tmp1, tmp2], out, fade=0.4)
    tmp1.unlink(missing_ok=True)
    tmp2.unlink(missing_ok=True)
    return {"source": "legacy", "path": str(LEGACY_SUBSCRIBE),
            "duration": round(_probe(out), 3), "audio": "muted"}
