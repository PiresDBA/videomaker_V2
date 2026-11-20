# -*- coding: utf-8 -*-
"""Sonoplastia (Earshot + Freesound), trilha por Ato e ducking controlado."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

import numpy as np

from config import FFMPEG_EXE, MUSIC_DIR, VENDOR_DIR

sys.path.insert(0, str(VENDOR_DIR))
from gerenciador_efeitos_sonoros import obter_efeito_sonoro  # noqa: E402

EARSHOT_DEFAULTS = {
    "whoosh": ("whoosh_fast/crisp", None),
    "whip": ("whoosh_fast/whip", None),
    "swipe": ("swipe/paper", None),
    "swish": ("swish/soft", None),
    "pop": ("ui_pop/soft", None),
    "boop": ("ui_pop/boop", None),
    "bloop": ("drip/bloop", None),
    "celesta": ("mallet/celesta", None),
    "glock": ("mallet/glock", None),
    "spark": ("logo_sting/spark", None),
    "bloom": ("logo_sting/soft_bloom", None),
    "hit": ("cut_hit/punch", None),
    "riser": ("riser/swell", None),
    "knock": ("knock/plastic", None),
    "shutter": ("shutter/quick", None),
}

# Regras semanticas de foley automatico para animacoes infantis (funciona nos 30+ videos!)
SEMANTIC_FOLEY_RULES: tuple[tuple[str, str, str, float], ...] = (
    (r"espirr|sneeze|nuvem|poeira\s+m[aá]gica|brilhou|sparkles|estrel", "logo_sting/spark", "earshot", 0.28),
    (r"gato|pingo|cat|miado|garras", "cat meow", "freesound", 0.28),
    (r"pombo|pigeon|voou|flight|asa", "pigeon wings", "freesound", 0.26),
    (r"passarinh|bird|pia|canta", "bird chirp", "freesound", 0.24),
    (r"patinho|rubber\s+duck", "rubber duck squeak", "freesound", 0.30),
    (r"z[ií]per|zipper|mochila|backpack", "zipper", "freesound", 0.28),
    (r"biscoit|ossinh|crocant|biscuit", "crunchy bite", "freesound", 0.28),
    (r"carros?\s+vermelh|cars?\s+pass|rua|street", "car pass by", "freesound", 0.22),
    (r"latid|latiu|bark|cachorr", "small dog bark", "freesound", 0.28),
    (r"disparou|correu|pulo|saltou|trott|jump", "whoosh_fast/whip", "earshot", 0.24),
    (r"sol|p[oô]r\s+do\s+sol|sunset|aprendeu|abrac|carinho", "logo_sting/soft_bloom", "earshot", 0.22),
    (r"piada|bobo|surpres|choque|boca\s+aberta", "drip/bloop", "earshot", 0.20),
)


def resolve_sfx_file(sfx_hint: str | None) -> tuple[Path | None, str]:
    """Resolve hint de SFX via Earshot (ritmo/UI/transicoes) ou Freesound (som realista)."""
    if not sfx_hint:
        return None, ""
    hint = sfx_hint.strip()
    if not hint or hint.lower() in ("null", "none", "nenhum"):
        return None, ""

    if "/" in hint:
        try:
            return obter_efeito_sonoro(hint, origem="earshot"), "earshot"
        except Exception:
            return obter_efeito_sonoro("whoosh_fast/crisp", origem="earshot"), "earshot"

    low = hint.lower()
    for key, (eid, _dur) in EARSHOT_DEFAULTS.items():
        if key in low:
            return obter_efeito_sonoro(eid, origem="earshot"), "earshot"

    try:
        return obter_efeito_sonoro(hint, origem="freesound", max_duracao=3.5), "freesound"
    except Exception:
        return obter_efeito_sonoro("ui_pop/soft", origem="earshot"), "earshot_fallback"


def detect_pauses_in_wav(wav_path: Path, min_pause_s: float = 0.16, rms_thr: float = 0.012) -> list[dict[str, float]]:
    """Detecta pausas naturais na faixa de narracao para posicionar sonoplastia sem atropelar a fala."""
    if not wav_path.exists():
        return []
    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if nch > 1:
        samples = samples.reshape(-1, nch).mean(axis=1)
    hop = max(1, int(sr * 0.02))
    sil_start: float | None = None
    pauses: list[dict[str, float]] = []
    for i in range(0, len(samples), hop):
        seg = samples[i:i + hop]
        rms = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
        t = i / sr
        if rms < rms_thr:
            if sil_start is None:
                sil_start = t
        else:
            if sil_start is not None and (t - sil_start) >= min_pause_s:
                pauses.append({"start": round(sil_start, 3), "end": round(t, 3), "dur": round(t - sil_start, 3)})
            sil_start = None
    return pauses


def _snap_to_nearest_pause(target_s: float, pauses: list[dict[str, float]], max_shift_s: float = 0.25) -> float:
    best_t = target_s
    best_d = max_shift_s
    for p in pauses:
        mid = 0.5 * (p["start"] + p["end"])
        d = abs(mid - target_s)
        if d <= best_d:
            best_d = d
            best_t = mid
    return round(max(0.0, best_t), 3)


def _infer_semantic_foleys(clip: dict[str, Any]) -> list[tuple[str, float]]:
    """Extrai ate 2 camadas leves de sonoplastia infantil a partir do texto e acao da cena."""
    hay = f"{clip.get('text', '')} {clip.get('visual_action', '')}".lower()
    hits: list[tuple[str, float]] = []
    seen_hints: set[str] = set()
    if clip.get("sfx"):
        h = str(clip["sfx"]).strip()
        seen_hints.add(h.lower())
        hits.append((h, 0.30))

    for rx, query, _orig, vol in SEMANTIC_FOLEY_RULES:
        if len(hits) >= 2:
            break
        if query.lower() not in seen_hints and re.search(rx, hay, re.I):
            seen_hints.add(query.lower())
            hits.append((query, vol))

    # Se nenhuma regra bateu mas ha troca de personagem/dialogo, coloca micro-pop leve e natural
    if not hits:
        spk = str(clip.get("speaker") or "narrador").lower()
        if spk == "frida":
            hits.append(("mallet/celesta", 0.17))
        elif spk == "luna":
            hits.append(("ui_pop/boop", 0.17))
        else:
            hits.append(("ui_pop/soft", 0.15))
    return hits


def build_sfx_stem(
    visual_clips: list[dict[str, Any]],
    total_duration: float,
    out_wav: Path,
    sfx_volume: float = 0.35,
    narration_wav: Path | None = None,
) -> Path:
    """Constroi sonoplastia infantil rica em camadas (foley semantico + micro-pops + cortes com som)."""
    pauses = detect_pauses_in_wav(narration_wav) if narration_wav else []
    events: list[tuple[float, Path, float]] = []
    seen_scenes: set[str] = set()
    last_act: int | None = None
    last_spk: str | None = None

    for clip in visual_clips:
        sid = clip["scene_id"]
        is_first_sub = sid not in seen_scenes
        seen_scenes.add(sid)

        if not is_first_sub:
            # Sub-corte visual (> 5s dividido): swish bem suave na troca de angulo (0.14)
            path_sw, _ = resolve_sfx_file("swish/soft")
            if path_sw:
                events.append((max(0.0, float(clip["start"]) - 0.05), path_sw, 0.14))
            continue

        act = clip.get("act", 1)
        if last_act is not None and act != last_act:
            path_trans, _ = resolve_sfx_file("whoosh_fast/crisp")
            if path_trans:
                ts_t = _snap_to_nearest_pause(max(0.0, float(clip["start"]) - 0.10), pauses)
                events.append((ts_t, path_trans, 0.28))
        last_act = act

        # Micro-pop quando alterna Frida <-> Luna para marcar o bate-bola com leveza
        spk = str(clip.get("speaker") or "narrador").lower()
        if last_spk and spk != last_spk and spk in ("frida", "luna"):
            pop_id = "ui_pop/boop" if spk == "luna" else "ui_pop/soft"
            path_spk, _ = resolve_sfx_file(pop_id)
            if path_spk:
                events.append((max(0.0, float(clip["start"])), path_spk, 0.18))
        last_spk = spk

        for idx_hit, (hint, base_vol) in enumerate(_infer_semantic_foleys(clip)):
            path_sfx, _ = resolve_sfx_file(hint)
            if path_sfx:
                raw_ts = float(clip["start"]) + (0.06 if idx_hit == 0 else min(1.8, float(clip["duration"]) * 0.48))
                ts_s = _snap_to_nearest_pause(raw_ts, pauses, max_shift_s=0.30)
                events.append((ts_s, path_sfx, min(sfx_volume, base_vol)))

    # Camada suave de ambiencia (passarinhos/brisa CC0) se a maioria for parque/natureza
    all_loc = " ".join(str(c.get("location") or "") for c in visual_clips).lower()
    amb_path: Path | None = None
    if any(k in all_loc for k in ("park", "praca", "lawn", "garden", "forest", "trees")):
        try:
            amb_path = obter_efeito_sonoro("park birds nature", origem="freesound", max_duracao=15.0)
        except Exception:
            amb_path = None

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    if not events and not amb_path:
        subprocess.run(
            [FFMPEG_EXE, "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
             "-t", f"{total_duration:.3f}", "-c:a", "pcm_s16le", str(out_wav)],
            check=True,
        )
        return out_wav

    cmd = [FFMPEG_EXE, "-y", "-v", "error", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={total_duration:.3f}"]
    filters = []
    labels = ["[0:a]"]
    in_idx = 1

    if amb_path and amb_path.exists():
        cmd += ["-stream_loop", "-1", "-t", f"{total_duration:.3f}", "-i", str(amb_path)]
        filters.append(f"[{in_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,highpass=f=220,volume=0.07[amb]")
        labels.append("[amb]")
        in_idx += 1

    for ts, p, vol in events:
        cmd += ["-i", str(p)]
        delay_ms = max(0, int(round(ts * 1000)))
        safe_v = min(0.35, max(0.05, float(vol)))
        filters.append(
            f"[{in_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            f"volume={safe_v:.2f},adelay={delay_ms}|{delay_ms}[s{in_idx}]"
        )
        labels.append(f"[s{in_idx}]")
        in_idx += 1

    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:normalize=0[out]")
    cmd += ["-filter_complex", ";".join(filters), "-map", "[out]", "-c:a", "pcm_s16le", str(out_wav)]
    subprocess.run(cmd, check=True)
    return out_wav


def resolve_act_bgm(visual_clips: list[dict[str, Any]], total_dur: float, work_dir: Path, fallback_bgm: Path | None) -> Path | None:
    """Monta trilha por Ato ou busca trilha infantil alegre CC0 automatica no Freesound."""
    act_files = {act: MUSIC_DIR / f"act{act}.wav" for act in (1, 2, 3)}
    if not all(p.exists() for p in act_files.values()):
        if fallback_bgm and fallback_bgm.exists():
            return fallback_bgm
        # Busca uma musica alegre leve CC0 no Freesound para nunca deixar o video seco
        for query in ("happy ukulele", "playful acoustic", "kids comedy"):
            try:
                return obter_efeito_sonoro(query, origem="freesound", max_duracao=60.0)
            except Exception:
                continue
        return None

    act_spans: dict[int, tuple[float, float]] = {}
    for c in visual_clips:
        a = int(c.get("act", 1))
        st, en = float(c["start"]), float(c["end"])
        if a not in act_spans:
            act_spans[a] = (st, en)
        else:
            act_spans[a] = (min(act_spans[a][0], st), max(act_spans[a][1], en))

    out_bgm = work_dir / "bgm_by_act.wav"
    cmd = [FFMPEG_EXE, "-y", "-v", "error"]
    parts = []
    for i, act in enumerate(sorted(act_spans)):
        st, en = act_spans[act]
        dur = max(1.0, (total_dur - st) if act == max(act_spans) else (en - st))
        cmd += ["-stream_loop", "-1", "-t", f"{dur:.3f}", "-i", str(act_files[act])]
        parts.append(f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo[m{i}]")
    concat_in = "".join(f"[m{i}]" for i in range(len(parts)))
    fc = ";".join(parts) + f";{concat_in}concat=n={len(parts)}:v=0:a=1[outm]"
    subprocess.run(cmd + ["-filter_complex", fc, "-map", "[outm]", "-c:a", "pcm_s16le", str(out_bgm)], check=True)
    return out_bgm


SOUNDCRAFT_CLI = Path(r"D:\Utilitarios\SoundCraft\soundcraft-cli.exe")


def master_with_soundcraft(audio_path: Path, out_wav: Path) -> Path:
    """Aplica de_esser + eq_7band + maximizer via SoundCraft CLI; fallback seguro se falhar."""
    if not SOUNDCRAFT_CLI.exists():
        return audio_path
    try:
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(SOUNDCRAFT_CLI), "run",
            "--cmd", "session.new",
            "--cmd", f'file.import_audio={{"path":"{audio_path.as_posix()}"}}',
            "--cmd", 'mix.insert={"track":2,"slot":"a","plugin":"de_esser"}',
            "--cmd", 'mix.insert={"track":2,"slot":"b","plugin":"eq_7band"}',
            "--cmd", 'mix.insert={"track":2,"slot":"c","plugin":"maximizer"}',
            "--bounce", str(out_wav),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and out_wav.exists() and out_wav.stat().st_size > 4000:
            return out_wav
    except Exception:
        pass
    return audio_path


def run_earshot_critique(media_path: Path, video_path: Path | None = None, fast: bool = True) -> dict[str, Any]:
    """Audita o audio/video final usando `earshot critique --json` (loudness, cortes com som, buracos)."""
    if not media_path.exists():
        return {"ran": False, "reason": "arquivo ausente"}
    env = os.environ.copy()
    ff_dir = str(Path(FFMPEG_EXE).parent)
    if ff_dir not in env.get("PATH", ""):
        env["PATH"] = ff_dir + os.pathsep + env.get("PATH", "")

    cmd = ["earshot", "critique", str(media_path), "--json"]
    if video_path and video_path.exists():
        cmd.extend(["--video", str(video_path)])
    if fast:
        cmd.append("--fast")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=240)
        if r.returncode == 0 and r.stdout.strip():
            data = json.loads(r.stdout)
            data["ran"] = True
            return data
        return {"ran": False, "reason": (r.stderr or r.stdout or "erro earshot")[:220]}
    except Exception as exc:
        return {"ran": False, "reason": str(exc)[:180]}


