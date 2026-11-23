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

from config import BASE_DIR, FFMPEG_EXE, MUSIC_DIR, SFX_CACHE_DIR, VENDOR_DIR

sys.path.insert(0, str(VENDOR_DIR))
from gerenciador_efeitos_sonoros import obter_efeito_sonoro  # noqa: E402

EARSHOT_DEFAULTS = {
    "whoosh": ("swish/soft", None),
    "whip": ("swish/soft", None),
    "swipe": ("swipe/paper", None),
    "swish": ("swish/soft", None),
    "pop": ("ui_pop/boop", None),
    "boop": ("ui_pop/boop", None),
    "bloop": ("drip/bloop", None),
    "celesta": ("mallet/celesta", None),
    "glock": ("mallet/glock", None),
    "spark": ("mallet/celesta", None),
    "bloom": ("mallet/glock", None),
    "hit": ("drip/bloop", None),
    "riser": ("mallet/celesta", None),
    "knock": ("ui_pop/boop", None),
    "shutter": ("ui_pop/soft", None),
}

# Regra 16: ate 3 foleys cartoon por cena, colados no instante da piada.
MAX_COMEDY_FOLEYS = 3

# Dicas explicitas de som dentro do campo "comedy_beat" do roteiro.
_COMEDY_BEAT_SOUNDS: tuple[tuple[str, str], ...] = (
    ("boing", "cartoon boing"),
    ("giggle", "cartoon giggle"),
    ("risadinha", "cartoon giggle"),
    ("fanfare", "cartoon fanfare"),
    ("whistle", "slide whistle"),
    ("apito", "slide whistle"),
    ("squeak", "rubber duck squeak"),
    ("crunch", "cartoon crunch bite"),
    ("splash", "cartoon splash"),
    ("sneeze", "cartoon sneeze"),
    ("celesta", "mallet/celesta"),
    ("glock", "mallet/glock"),
    ("pop", "ui_pop/boop"),
)

# Regras semanticas de foley estilo desenho animado classico (Pica-Pau / Tom & Jerry / Snoopy)
SEMANTIC_FOLEY_RULES: tuple[tuple[str, str, str, float], ...] = (
    (r"gato|pingo|cat|miado|garras|cochilo|dorminhoco", "cartoon cat meow", "freesound", 0.32),
    (r"patinho|rubber\s+duck", "rubber duck squeak", "freesound", 0.34),
    (r"pombo|pigeon|voou|flight|asa", "cartoon bird whistle", "freesound", 0.30),
    (r"passarinh|bird|bico|canta", "cartoon bird chirp", "freesound", 0.30),
    (r"z[ií]per|zipper|mochila|backpack|trava", "slide whistle up", "freesound", 0.31),
    (r"biscoit|ossinh|crocant|biscuit|lanche|bacon|petisc", "cartoon crunch bite", "freesound", 0.32),
    (r"cheir|farej|focinho|nariz", "cartoon sniff", "freesound", 0.30),
    (r"carros?\s+vermelh|cars?\s+pass|rua|street|bombeir", "cartoon horn honk", "freesound", 0.28),
    (r"latid|latiu|bark", "small dog bark", "freesound", 0.32),
    (r"espirr|sneeze", "cartoon sneeze", "freesound", 0.33),
    (r"nuvem|poeira\s+m[aá]gica|brilhou|sparkles|estrel", "mallet/celesta", "earshot", 0.30),
    (r"trof[eé]u|medalha|campe[aã]o|vit[oó]ria|p[oó]dio|vencer", "cartoon fanfare", "freesound", 0.31),
    (r"tomb|cambalhot|piruet|girou|rolou|esborrach|caiu", "cartoon spin", "freesound", 0.32),
    (r"almofad|caminha|colch[aã]o|fof[ao]|mergulh|afund", "cartoon bounce", "freesound", 0.31),
    (r"disparou|correu|velocid|frenetic|disputa|largada", "cartoon run", "freesound", 0.30),
    (r"pulo|saltou|trott|jump|obst[aá]cul", "cartoon boing", "freesound", 0.31),
    (r"bolha|sab[aã]o|estour|onda\s+de\s+choque", "cartoon bubble pop", "freesound", 0.32),
    (r"t[uú]nel|escorreg|desvi|trope[cç]", "slide whistle", "freesound", 0.30),
    (r"meia|orelha|enrosc|bagun[cç]", "cartoon spring", "freesound", 0.30),
    (r"apito|largada|ju[ií]z|jurad", "cartoon whistle", "freesound", 0.30),
    (r"ops|eita|susto|arregalad|surpres|choque|boca\s+aberta", "xylophone cartoon", "freesound", 0.29),
    (r"desist|chatead|trist|perdeu|ops", "sad trombone", "freesound", 0.28),
    (r"cornet|buzin|palha[cç]|maluc", "comedy horn", "freesound", 0.29),
    (r"sol|p[oô]r\s+do\s+sol|sunset|aprendeu|abra[cç]|carinho|amig|beij", "mallet/glock", "earshot", 0.26),
    (r"piada|bobo|rir|rindo|risad|engra[cç]|divert", "cartoon giggle", "freesound", 0.28),
    (r"aben[cç]|acenar|tchau|beijos|like|inscrev", "cartoon kiss", "freesound", 0.27),
    # Praia / primeiro dia de praia — gags fisicos e sonoros bem casados com a acao
    (r"areia|sand|praia|beach|concha|shell|casco", "cartoon sand shuffle", "freesound", 0.30),
    (r"onda|mar[aá]?|wave|surf|mergulh|splash|resping", "cartoon splash", "freesound", 0.32),
    (r"protetor|solar|sunscreen|lo[cç][aã]o|creme|bronze", "slide whistle", "freesound", 0.28),
    (r"escorreg|desliz|tobog[aã]|ladeira|morro", "slide whistle", "freesound", 0.30),
    (r"biqu[íi]ni|shorts|roupa|trocar|vesti", "cartoon giggle", "freesound", 0.27),
    (r"p[aá]ssaro|gaivota|seagull|gaviota", "cartoon bird whistle", "freesound", 0.29),
    (r"frio|gelad|calafrio|estremec", "cartoon teeth chatter", "freesound", 0.28),
    (r"quente|calor|sol escaldante|suor", "cartoon fanfare", "freesound", 0.27),
    (r"olhar pra c[aâ]mera|pausa de riso|respiro|risadinha|sorri", "cartoon giggle", "freesound", 0.27),
)


def _normalize_sfx_to_wav(src_path: Path, max_dur_s: float = 3.5, target_peak_db: float = -6.0) -> Path:
    """Normaliza cada efeito sonoro para pico consistente (-6 dBFS) evitando SFX baixos na mixagem."""
    norm_dir = SFX_CACHE_DIR / "norm_wav"
    norm_dir.mkdir(parents=True, exist_ok=True)
    dst = norm_dir / f"{src_path.stem}_n6.wav"
    if dst.exists() and dst.stat().st_size > 1000:
        return dst
    tmp = norm_dir / f"{src_path.stem}_tmp.wav"
    subprocess.run(
        [FFMPEG_EXE, "-y", "-v", "error", "-i", str(src_path), "-t", f"{max_dur_s:.2f}",
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(tmp)],
        check=True,
    )
    with wave.open(str(tmp), "rb") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
    arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    peak = float(np.max(np.abs(arr))) if arr.size else 0.0
    target_lin = 32767.0 * (10.0 ** (target_peak_db / 20.0))
    if peak > 20.0:
        gain = min(14.0, target_lin / peak)
        arr = arr * gain
    # Fade suave nas pontas (12ms) evitando estalos
    if nch >= 1 and len(arr) >= nch * int(sr * 0.025):
        st_arr = arr.reshape(-1, nch)
        fn = max(1, int(sr * 0.012))
        ramp = np.linspace(0.0, 1.0, fn, dtype=np.float32)[:, None]
        st_arr[:fn] *= ramp
        st_arr[-fn:] *= ramp[::-1]
        arr = st_arr.reshape(-1)
    pcm = np.clip(arr, -32767, 32767).astype(np.int16)
    with wave.open(str(dst), "wb") as wf:
        wf.setnchannels(nch)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    tmp.unlink(missing_ok=True)
    return dst


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
    """Extrai ate 3 foleys cartoon: som do roteiro + timing da piada + acao da cena."""
    hay = " ".join(str(clip.get(k) or "") for k in ("text", "visual_action", "comedy_beat")).lower()
    hits: list[tuple[str, float]] = []
    seen_hints: set[str] = set()

    # 1) Som principal escrito no roteiro (aceita um ou mais termos separados por virgula/;)
    for h in re.split(r"[,;|]+", str(clip.get("sfx") or "")):
        h = h.strip().strip('"').strip("'")
        if h and h.lower() not in seen_hints and h.lower() not in ("null", "none", "nenhum"):
            seen_hints.add(h.lower())
            hits.append((h, 0.30))
        if len(hits) >= MAX_COMEDY_FOLEYS:
            break

    # 2) Sons explicitos no timing da piada ("acao -> cartoon boing -> pausa")
    cb = str(clip.get("comedy_beat") or "").lower()
    for kw, hint in _COMEDY_BEAT_SOUNDS:
        if len(hits) >= MAX_COMEDY_FOLEYS:
            break
        if re.search(r"\b" + re.escape(kw) + r"\b", cb) and hint.lower() not in seen_hints:
            seen_hints.add(hint.lower())
            hits.append((hint, 0.29))

    # 3) Foleys semanticos pelo texto/acao da cena
    for rx, query, _orig, vol in SEMANTIC_FOLEY_RULES:
        if len(hits) >= MAX_COMEDY_FOLEYS:
            break
        if query.lower() not in seen_hints and re.search(rx, hay, re.I):
            seen_hints.add(query.lower())
            hits.append((query, vol))

    # Micro-pop de presenca quando nada bateu (mantem a cena viva sem atropelar)
    if not hits:
        spk = str(clip.get("speaker") or "narrador").lower()
        if spk == "frida":
            hits.append(("mallet/celesta", 0.17))
        elif spk == "luna":
            hits.append(("ui_pop/boop", 0.17))
        else:
            hits.append(("ui_pop/soft", 0.15))
    return hits[:MAX_COMEDY_FOLEYS]


def _find_pause_slot_for_window(
    win_start: float,
    win_end: float,
    pauses: list[dict[str, float]],
    min_slot_s: float = 0.24,
    prefer_end: bool = True,
) -> tuple[float, float] | None:
    """Encontra uma janela real de pausa dentro de [win_start, win_end] para tocar SFX sem atropelar a fala."""
    cands = [
        p for p in pauses
        if p["end"] > win_start + 0.05 and p["start"] < win_end + 0.35
    ]
    if not cands:
        return None
    best: tuple[float, float, float] | None = None
    for p in cands:
        s = max(win_start, p["start"] + 0.03)
        e = min(win_end + 0.30, p["end"] - 0.03)
        avail = e - s
        if avail < min_slot_s:
            continue
        # Prefere pausas maiores e, quando prefer_end=True, pausas logo apos a frase (ex: fim da cena)
        score = avail + (0.45 if (prefer_end and s >= win_start + (win_end - win_start) * 0.55) else 0.0)
        if best is None or score > best[0]:
            best = (score, s, avail)
    if best is None:
        return None
    return round(best[1], 3), round(min(1.6, best[2]), 3)


def build_sfx_stem(
    visual_clips: list[dict[str, Any]],
    total_duration: float,
    out_wav: Path,
    sfx_volume: float = 0.35,
    narration_wav: Path | None = None,
) -> Path:
    """Constroi sonoplastia infantil posicionada ESTRITAMENTE nas pausas reais da narracao (nunca atropela a fala)."""
    pauses = detect_pauses_in_wav(narration_wav, min_pause_s=0.22, rms_thr=0.015) if narration_wav else []
    # Cada evento: (timestamp_s, wav_path, volume, max_dur_s)
    events: list[tuple[float, Path, float, float]] = []

    # Agrupa sub-clips por cena para colocar no maximo 1 SFX limpo na pausa real daquela cena
    scenes_meta: list[dict[str, Any]] = []
    by_sid: dict[str, dict[str, Any]] = {}
    for clip in visual_clips:
        sid = clip["scene_id"]
        if sid not in by_sid:
            by_sid[sid] = {
                "scene_id": sid,
                "start": float(clip["start"]),
                "end": float(clip["end"]),
                "audio_end": float(clip.get("scene_audio_start", clip["start"])) + float(clip.get("scene_audio_dur", clip["duration"])),
                "act": clip.get("act", 1),
                "speaker": clip.get("speaker", "narrador"),
                "text": clip.get("text", ""),
                "visual_action": clip.get("visual_action", ""),
                "sfx": clip.get("sfx"),
                "comedy_beat": clip.get("comedy_beat", ""),
            }
            scenes_meta.append(by_sid[sid])
        else:
            by_sid[sid]["end"] = max(by_sid[sid]["end"], float(clip["end"]))

    last_act: int | None = None
    last_event_ts = -1.0
    for idx_sc, sc in enumerate(scenes_meta):
        sc_start = sc["start"]
        sc_end = sc["end"]
        next_start = scenes_meta[idx_sc + 1]["start"] if idx_sc + 1 < len(scenes_meta) else total_duration

        # Garante que a janela entre o fim do audio da cena e o inicio da proxima cena conste como pausa valida
        local_pauses = list(pauses)
        gap_s = sc["audio_end"]
        gap_e = next_start
        if gap_e - gap_s >= 0.24:
            local_pauses.append({"start": gap_s, "end": gap_e, "dur": gap_e - gap_s})

        # Transicao de ato: assobio antes da virada (fora do limite de 3 foleys da cena)
        act = sc.get("act", 1)
        act_transition_used = False
        if last_act is not None and act != last_act:
            path_trans, _ = resolve_sfx_file("slide whistle")
            if path_trans:
                slot_act = _find_pause_slot_for_window(max(0.0, sc_start - 0.8), sc_start + 0.15, local_pauses, min_slot_s=0.22, prefer_end=False)
                if slot_act:
                    events.append((slot_act[0], path_trans, min(sfx_volume, 0.26), slot_act[1]))
                    last_event_ts = slot_act[0]
                    act_transition_used = True
        last_act = act

        # Regra 16: ate 3 foleys por cena, cada um na pausa real mais proxima do instante da piada.
        budget = MAX_COMEDY_FOLEYS - (1 if act_transition_used else 0)
        hits = _infer_semantic_foleys(sc)[:budget]
        if not hits:
            continue

        windows = (
            (max(0.0, sc_start - 0.7), sc_start + 0.18, False),          # reacao/antecipacao
            (sc_start, max(sc_end, sc_start + 0.25), False),            # instante da acao
            (max(sc_end, sc["audio_end"]), next_start + 0.25, True),    # respiro apos a piada
        )
        for j, (hint, base_vol) in enumerate(hits):
            path_sfx, _ = resolve_sfx_file(hint)
            if not path_sfx:
                continue
            w_start, w_end, prefer_end = windows[min(j, len(windows) - 1)]
            slot = _find_pause_slot_for_window(w_start, w_end, local_pauses, min_slot_s=0.22, prefer_end=prefer_end)
            if slot is None:
                if not local_pauses:
                    # Fallback sintetico quando nao ha WAV de narracao (testes unitarios)
                    slot = (round(max(0.0, sc_end - 0.35 + j * 0.20), 3), 0.7)
                elif j == 0:
                    # Ultimo recurso: pausa logo apos a fala (protegida por sidechaincompress na mixagem)
                    slot = (round(max(0.0, sc["audio_end"]), 3), 0.6)
                else:
                    continue
            ts = round(slot[0] + j * 0.07, 3)
            if ts - last_event_ts < 0.15:
                continue
            last_event_ts = ts
            events.append((ts, path_sfx, min(sfx_volume, base_vol), slot[1]))

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

    norm_cache: dict[Path, Path] = {}
    cmd = [FFMPEG_EXE, "-y", "-v", "error", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={total_duration:.3f}"]
    filters = []
    labels = ["[0:a]"]
    in_idx = 1

    if amb_path and amb_path.exists():
        cmd += ["-stream_loop", "-1", "-t", f"{total_duration:.3f}", "-i", str(amb_path)]
        filters.append(f"[{in_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,highpass=f=220,volume=0.05[amb]")
        labels.append("[amb]")
        in_idx += 1

    for ts, p, vol, max_dur in events:
        if p not in norm_cache:
            try:
                norm_cache[p] = _normalize_sfx_to_wav(p)
            except Exception:
                norm_cache[p] = p
        p_use = norm_cache[p]
        cmd += ["-i", str(p_use)]
        delay_ms = max(0, int(round(ts * 1000)))
        safe_v = min(0.35, max(0.06, float(vol)))
        trim_d = max(0.22, min(1.8, float(max_dur)))
        fade_st = max(0.05, trim_d - 0.16)
        filters.append(
            f"[{in_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            f"atrim=0:{trim_d:.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=out:st={fade_st:.3f}:d=0.16,"
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


_LOCAL_SOUNDCRAFT = VENDOR_DIR / "soundcraft" / "soundcraft-cli.exe"
SOUNDCRAFT_CLI = _LOCAL_SOUNDCRAFT if _LOCAL_SOUNDCRAFT.exists() else Path(r"D:\Utilitarios\SoundCraft\soundcraft-cli.exe")


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

    local_ear = BASE_DIR / "bin" / "earshot.exe"
    exe = str(local_ear) if local_ear.is_file() else "earshot"
    cmd = [exe, "critique", str(media_path), "--json"]
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


