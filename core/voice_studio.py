# -*- coding: utf-8 -*-
"""Estudio de Voz Embutido (VoiceCraft multi-chave + Portao de Prosodia + Whisper QA)."""
from __future__ import annotations

import asyncio
import base64
import datetime as dt
import difflib
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path
from typing import Any

import numpy as np

from config import (
    CHIRP3_CREDENTIALS_DEFAULT,
    CHIRP3_MONTHLY_CHAR_LIMIT,
    CHIRP3_SPEAKING_RATE,
    CHIRP3_OAUTH_CLIENT_DEFAULT,
    CHIRP3_OAUTH_TOKEN_DEFAULT,
    CHIRP3_USAGE_STATE_FILE,
    CPU_WORKERS,
    CREDENTIALS_DIR,
    ENV_FILE,
    FFMPEG_EXE,
    FFPROBE_EXE,
    GEMINI_TTS_MODELS,
    PROSODY_LIMITS,
    SPEAKER_VOICE_PROFILES,
    VENDOR_DIR,
    VOICE_STUDIO_VOICES,
)

sys.path.insert(0, str(VENDOR_DIR))
from env_keys import load_env_key  # noqa: E402

# Dicionario de normalizacao fonetica pre-TTS (aplicado APENAS ao audio; legendas ficam intactas)
PHONETIC_PT_RULES: tuple[tuple[str, str], ...] = (
    (r"\bcães\s+falantes\b", "cãis falantes"),
    (r"\bcães\b", "cãis"),
    (r"\bcOEs\b", "cãis"),
    (r"\bce[uU]\b", "céu"),
    (r"\b[jJ]a\b", "já"),
    (r"\beh\b", "é"),
    (r"\bnao\b", "não"),
    (r"\bvoce\b", "você"),
    (r"\bvoces\b", "vocês"),
    (r"\bpenas\b", "pênas"),
    (r"\bcoro\b", "côro"),
    (r"\bpatinha\b", "patínha"),
    (r"\bpassarinhos\b", "passarínhos"),
    (r"\bpiadas\b", "piádas"),
    (r"\bgatinha\b", "cachorrinha"),
    (r"\bgatinho\b", "cachorro"),
    (r"\bc[oó]cegas\b", "có-ce-gas"),
    (r"\bc[oó]cega\b", "cósega"),
)

_WHISPER_MODEL = None
_KEY_ROTATION = itertools.count()
_CHIRP3_CREDS_CACHE: dict[str, Any] = {}


def normalize_phonetics_pt(text: str) -> str:
    """Aplica correcoes foneticas em portugues para evitar distorcoes do TTS e remove '@' de marcacoes visuais."""
    out = re.sub(r"@+", "", text or "")
    out = " ".join(out.split())
    out = re.sub(r"(?i)\b(?:hahaha+|ha\s+ha\s+ha+|kkkk+|rsrs+)\b[!.]*", " ", out)
    for pat, repl in PHONETIC_PT_RULES:
        out = re.sub(pat, repl, out, flags=re.I)
    out = re.sub(r"\s+([,.!?;:])", r"\1", out)
    return " ".join(out.split())


def _norm_for_compare(text: str) -> list[str]:
    """Normaliza tokens sem acento para comparacao justa entre roteiro e Whisper."""
    normed = unicodedata.normalize("NFKD", (text or "").lower())
    ascii_only = "".join(c for c in normed if not unicodedata.combining(c))
    ascii_only = re.sub(r"\bcais\b", "caes", ascii_only)
    return re.findall(r"[a-z0-9]+", ascii_only)


def _get_whisper(model_name: str = "small"):
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        from faster_whisper import WhisperModel
        try:
            _WHISPER_MODEL = WhisperModel(model_name, device="cuda", compute_type="float16")
        except Exception:
            _WHISPER_MODEL = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=CPU_WORKERS)
    return _WHISPER_MODEL


def probe_duration(path: Path) -> float:
    """Mede duracao real do audio via FFprobe/FFmpeg."""
    if FFPROBE_EXE != FFMPEG_EXE and Path(FFPROBE_EXE).exists():
        r = subprocess.run(
            [FFPROBE_EXE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True,
        )
        try:
            return round(float(r.stdout.strip()), 3)
        except Exception:
            pass
    r = subprocess.run([FFMPEG_EXE, "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
    if m:
        return round(int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)), 3)
    return 0.0


def _pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = 24000, channels: int = 1) -> bytes:
    import io
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def _load_google_tts_keys() -> list[str]:
    names = ["GOOGLE_TTS_API_KEY"] + [f"GOOGLE_TTS_API_KEY_{i}" for i in range(1, 21)] + ["GEMINI_API_KEY"]
    keys = []
    for n in names:
        val = (load_env_key(n, ENV_FILE) or os.environ.get(n) or "").strip()
        if val and val not in keys:
            keys.append(val)
    return keys


def _load_mono_16k(audio_path: Path) -> np.ndarray:
    raw = subprocess.run(
        [FFMPEG_EXE, "-v", "error", "-i", str(audio_path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32) if raw else np.zeros(0, dtype=np.float32)


def analyze_prosody(audio_path: Path, text: str | None = None) -> dict[str, Any]:
    """Portao acustico de emocao (VoiceCraft/prosodia.py): mede F0, ritmo, ataque e dinamica."""
    sr = 16000
    frame = int(0.040 * sr)
    hop = int(0.010 * sr)
    x = _load_mono_16k(audio_path)
    dur = len(x) / sr
    if len(x) < frame * 2:
        return {"ok": False, "motivos": ["audio curto demais"], "amplitude_st": 0.0, "dinamica": 0.0, "taxa_car_s": 0.0}

    f0_vals = []
    rms_list = []
    lo, hi = int(sr / 450), int(sr / 70)
    for i in range(0, len(x) - frame, hop):
        seg = x[i:i + frame]
        rms_val = float(np.sqrt(np.mean(seg ** 2)))
        rms_list.append(rms_val)
        if np.abs(seg).max() < 0.02:
            continue
        s0 = seg - seg.mean()
        ac = np.correlate(s0, s0, "full")[frame - 1:]
        if hi < len(ac) and ac[0] > 0:
            k = int(np.argmax(ac[lo:hi])) + lo
            if ac[k] > 0.28 * ac[0]:
                f0_vals.append(sr / k)

    rms = np.asarray(rms_list, dtype=np.float32)
    f0 = np.asarray(f0_vals, dtype=np.float32)
    voiced = rms > 0.012
    pausa = float(1.0 - voiced.mean()) if len(voiced) else 1.0
    ataque = float(np.argmax(voiced) * hop / sr) if voiced.any() else dur

    if len(f0) > 8:
        st = 12.0 * np.log2(f0 / np.median(f0))
        amplitude = float(np.percentile(st, 95) - np.percentile(st, 5))
    else:
        amplitude = 0.0

    som = rms[voiced]
    dinamica = float(som.std() / som.mean()) if len(som) and som.mean() > 0 else 0.0
    idx = np.flatnonzero(voiced)
    dur_fala = float((idx[-1] - idx[0] + 1) * hop / sr) if len(idx) else dur
    taxa = (len(re.sub(r"\s+", "", text)) / dur_fala) if (text and dur_fala > 0) else None

    lim = PROSODY_LIMITS
    motivos = []
    if taxa is not None:
        if taxa < lim["taxa_min"]:
            motivos.append(f"leitura lenta ({taxa:.1f} car/s < {lim['taxa_min']})")
        elif taxa > lim["taxa_max"]:
            motivos.append(f"atropelado ({taxa:.1f} car/s > {lim['taxa_max']})")
    if amplitude < lim["amplitude_min"]:
        motivos.append(f"monotono ({amplitude:.1f}st < {lim['amplitude_min']}st)")
    if pausa < lim["pausa_min"] or pausa > lim["pausa_max"]:
        motivos.append(f"pausa fora da faixa ({pausa:.2f})")
    if dinamica < lim["dinamica_min"]:
        motivos.append(f"dinamica plana ({dinamica:.2f} < {lim['dinamica_min']})")
    if ataque > lim["ataque_max"]:
        motivos.append(f"ataque lento ({ataque:.2f}s > {lim['ataque_max']}s)")

    return {
        "ok": len(motivos) == 0,
        "dur_s": round(dur, 2),
        "dur_fala_s": round(dur_fala, 2),
        "taxa_car_s": round(taxa, 2) if taxa else None,
        "amplitude_st": round(amplitude, 2),
        "pausa": round(pausa, 3),
        "dinamica": round(dinamica, 3),
        "ataque_s": round(ataque, 3),
        "motivos": motivos,
    }


def validate_audio_with_whisper(
    audio_path: Path,
    expected_text: str,
    min_similarity: float = 0.78,
    model_name: str = "small",
) -> dict[str, Any]:
    """Transcreve o audio gerado e detecta distorcoes foneticas ou instrucao vazada."""
    audio_np = _load_mono_16k(audio_path)
    if len(audio_np) < 1600:
        return {"ok": False, "similarity": 0.0, "heard_text": "", "reason": "audio vazio ou truncado"}

    model = _get_whisper(model_name)
    segs, _ = model.transcribe(audio_np, language="pt", vad_filter=True, word_timestamps=False)
    heard_text = " ".join(s.text.strip() for s in segs).strip()

    exp_tokens = _norm_for_compare(expected_text)
    heard_tokens = _norm_for_compare(heard_text)
    if not exp_tokens or not heard_tokens:
        return {"ok": False, "similarity": 0.0, "heard_text": heard_text, "reason": "transcricao vazia"}

    ratio = difflib.SequenceMatcher(a=exp_tokens, b=heard_tokens, autojunk=False).ratio()
    dup_ratio = len(heard_tokens) / max(1, len(exp_tokens))
    ok = ratio >= min_similarity and dup_ratio <= 1.45
    reason = "ok"
    if ratio < min_similarity:
        reason = f"baixa similaridade ({ratio:.2f} < {min_similarity}); ouviu='{heard_text}'"
    elif dup_ratio > 1.45:
        reason = f"possivel duplicacao/vazamento de instrucao (tokens x{dup_ratio:.2f})"
    return {"ok": ok, "similarity": round(ratio, 3), "heard_text": heard_text, "reason": reason}


def _decode_gemini_audio_to_file(data: dict[str, Any], out_audio: Path) -> None:
    cands = data.get("candidates") or []
    parts = cands[0].get("content", {}).get("parts", []) if cands else []
    inline = next((p.get("inlineData") for p in parts if isinstance(p, dict) and p.get("inlineData")), None)
    if not inline or not inline.get("data"):
        raise RuntimeError("Gemini TTS retornou resposta sem audio")
    raw_bytes = base64.b64decode(inline["data"])
    mime = str(inline.get("mimeType") or "audio/L16;rate=24000").lower()
    if "wav" in mime:
        wav_bytes = raw_bytes
    else:
        m = re.search(r"rate=(\d+)", mime)
        sr = int(m.group(1)) if m else 24000
        wav_bytes = _pcm_to_wav_bytes(raw_bytes, sample_rate=sr)
    raw_wav = out_audio.with_suffix(".raw.wav")
    raw_wav.write_bytes(wav_bytes)
    out_audio.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-i", str(raw_wav), str(out_audio)], check=True)
    raw_wav.unlink(missing_ok=True)


def _synthesize_gemini_direct(
    text: str,
    speaker: str,
    emotion_direction: str | None,
    out_audio: Path,
    voice_override: str | None = None,
    energy_boost: bool = False,
) -> tuple[str, str]:
    """Sintetiza via Gemini 3.8 / 2.5 Flash TTS com rotacao de chaves e emocao."""
    keys = _load_google_tts_keys()
    if not keys:
        raise RuntimeError("Nenhuma chave Google TTS configurada em .env")

    if len(keys) > 1:
        rest = keys[1:]
        offset = next(_KEY_ROTATION) % len(rest)
        ordered_keys = [keys[0]] + rest[offset:] + rest[:offset]
    else:
        ordered_keys = keys
    profile = SPEAKER_VOICE_PROFILES.get(speaker, SPEAKER_VOICE_PROFILES["narrador"])
    voice = voice_override or profile["gemini_voice"]
    env_model = (load_env_key("GEMINI_TTS_MODEL", ENV_FILE) or "").strip()
    models = ([env_model] if env_model else []) + [m for m in GEMINI_TTS_MODELS if m != env_model]

    base_dir = emotion_direction.strip() if emotion_direction else profile["emotion"]
    if energy_boost:
        base_dir = f"Com ainda mais vivacidade, variação melódica e ritmo ágil, {base_dir}"

    last_err: Exception | None = None
    for model in models:
        # gemini-3.x-tts entrega alta emocao nativa direto no texto e le prefixos antes de ':' em voz alta
        prompt_text = text if "gemini-3" in model else f"{base_dir}: {text}"
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}
                },
            },
        }).encode("utf-8")
        for key in ordered_keys:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(key)}"
            )
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                _decode_gemini_audio_to_file(data, out_audio)
                return f"{model}:{voice}", "native_3_8" if "gemini-3" in model else "prompt"
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")[:240]
                last_err = RuntimeError(f"HTTP {exc.code} ({model}): {detail}")
                if exc.code == 404:
                    break
            except Exception as exc:
                last_err = exc

    raise RuntimeError(f"Gemini TTS falhou em todas as {len(keys)} chaves: {last_err}")


def synthesize_dialogue_multispeaker(
    turns: list[tuple[str, str]],
    out_audio: Path,
    voice_map: dict[str, str] | None = None,
    emotion_direction: str = "Diálogo animado e expressivo em português do Brasil",
) -> tuple[str, str]:
    """Sintetiza dialogo Frida x Luna na mesma chamada (MultiSpeakerVoiceConfig)."""
    keys = _load_google_tts_keys()
    if not keys:
        raise RuntimeError("Nenhuma chave Google TTS configurada em .env")

    vmap = voice_map or {"Frida": "Sulafat", "Luna": "Leda"}
    spk_cfgs = [
        {"speaker": spk, "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": vname}}}
        for spk, vname in vmap.items()
    ]
    parts_meta = [
        {"text": normalize_phonetics_pt(txt), "speechMetadata": {"speaker": spk}}
        for spk, txt in turns
    ]
    plain_dialogue = "\n".join(f"{spk}: {normalize_phonetics_pt(txt)}" for spk, txt in turns)

    last_err: Exception | None = None
    for model in GEMINI_TTS_MODELS:
        use_meta = "3." in model
        contents = [{"parts": parts_meta}] if use_meta else [{"parts": [{"text": f"{emotion_direction}:\n{plain_dialogue}"}]}]
        payload = json.dumps({
            "contents": contents,
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": spk_cfgs}},
            },
        }).encode("utf-8")
        offset = next(_KEY_ROTATION) % len(keys)
        for key in keys[offset:] + keys[:offset]:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(key)}"
            )
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                _decode_gemini_audio_to_file(data, out_audio)
                return f"{model}:multispeaker", "multi_speaker"
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")[:240]
                last_err = RuntimeError(f"HTTP {exc.code} ({model}): {detail}")
                if exc.code == 404:
                    break
            except Exception as exc:
                last_err = exc
    raise RuntimeError(f"Gemini MultiSpeaker TTS falhou: {last_err}")


async def _synthesize_edge_async(text: str, voice: str, rate: str, pitch: str, out_mp3: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(out_mp3))


def _synthesize_edge(text: str, speaker: str, out_mp3: Path, slow_retry: bool = False) -> tuple[str, str]:
    profile = SPEAKER_VOICE_PROFILES.get(speaker, SPEAKER_VOICE_PROFILES["narrador"])
    rate = "-2%" if slow_retry else profile["edge_rate"]
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_synthesize_edge_async(text, profile["edge_voice"], rate, profile["edge_pitch"], out_mp3))
    return f"edge:{profile['edge_voice']}({rate},{profile['edge_pitch']})", "pitch"


def resolve_chirp3_credentials_path() -> Path | None:
    """Localiza JSON de Conta de Servico Google Cloud para Text-to-Speech (Chirp 3 HD)."""
    for env_name in ("GOOGLE_CLOUD_TTS_CREDENTIALS", "GOOGLE_APPLICATION_CREDENTIALS"):
        raw = (load_env_key(env_name, ENV_FILE) or os.environ.get(env_name) or "").strip()
        if raw:
            p = Path(raw)
            if not p.is_absolute():
                p = ENV_FILE.parent / p
            if p.is_file():
                return p
    if CHIRP3_CREDENTIALS_DEFAULT.is_file():
        return CHIRP3_CREDENTIALS_DEFAULT
    if CREDENTIALS_DIR.is_dir():
        for cand in sorted(CREDENTIALS_DIR.glob("*.json")):
            if cand.name.startswith(("client_secret", "youtube_token")):
                continue
            try:
                data = json.loads(cand.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(data, dict) and data.get("type") == "service_account":
                    return cand
            except Exception:
                continue
    return None


def _load_chirp3_usage(state_file: Path = CHIRP3_USAGE_STATE_FILE) -> dict[str, Any]:
    month_key = dt.date.today().strftime("%Y-%m")
    if state_file.is_file():
        try:
            st = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(st, dict) and st.get("month") == month_key:
                return st
        except Exception:
            pass
    return {"month": month_key, "chars_used": 0}


def _consume_chirp3_chars(
    n_chars: int,
    state_file: Path = CHIRP3_USAGE_STATE_FILE,
    limit: int = CHIRP3_MONTHLY_CHAR_LIMIT,
) -> int:
    st = _load_chirp3_usage(state_file)
    used = int(st.get("chars_used", 0))
    projected = used + max(0, int(n_chars))
    if projected > int(limit):
        raise RuntimeError(
            f"TRAVA DE CUSTO CHIRP 3 HD: uso mensal ({projected}) excederia o limite gratuito seguro "
            f"({limit}/1.000.000 chars)."
        )
    st["chars_used"] = projected
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    return projected


def _extract_oauth_project_id(secret_path: Path) -> str:
    try:
        data = json.loads(secret_path.read_text(encoding="utf-8", errors="ignore"))
        inner = data.get("installed") or data.get("web") or {}
        return str(inner.get("project_id") or "").strip()
    except Exception:
        return ""


def resolve_chirp3_oauth_paths() -> tuple[Path | None, Path, str]:
    """Localiza client_secret OAuth 2.0 (App para computador), arquivo de token e project_id de cota."""
    quota_proj = (load_env_key("GOOGLE_CLOUD_TTS_PROJECT", ENV_FILE) or os.environ.get("GOOGLE_CLOUD_TTS_PROJECT") or "").strip()
    client_path: Path | None = None

    raw = (load_env_key("GOOGLE_CLOUD_TTS_OAUTH_CLIENT", ENV_FILE) or os.environ.get("GOOGLE_CLOUD_TTS_OAUTH_CLIENT") or "").strip()
    if raw:
        p = Path(raw)
        if not p.is_absolute():
            p = ENV_FILE.parent / p
        if p.is_file():
            client_path = p

    if client_path is None and CHIRP3_OAUTH_CLIENT_DEFAULT.is_file():
        client_path = CHIRP3_OAUTH_CLIENT_DEFAULT

    if client_path is None and CREDENTIALS_DIR.is_dir():
        for cand in sorted(CREDENTIALS_DIR.glob("client_secret*.json")):
            pid = _extract_oauth_project_id(cand)
            low_name = cand.name.lower()
            if (quota_proj and pid == quota_proj) or ("ingles" in pid.lower()) or ("tts" in low_name) or ("ingles" in low_name):
                client_path = cand
                break

    if not quota_proj and client_path is not None:
        quota_proj = _extract_oauth_project_id(client_path)

    return client_path, CHIRP3_OAUTH_TOKEN_DEFAULT, quota_proj


def has_chirp3_auth_configured(token_path: Path = CHIRP3_OAUTH_TOKEN_DEFAULT) -> bool:
    """Retorna True se houver Conta de Servico JSON ou token OAuth 2.0 salvo para Chirp 3 HD."""
    return (resolve_chirp3_credentials_path() is not None) or token_path.is_file()


def authenticate_chirp3_oauth(
    client_secret_path: Path | None = None,
    token_path: Path = CHIRP3_OAUTH_TOKEN_DEFAULT,
) -> tuple[Path, str]:
    """Autentica via OAuth 2.0 Desktop (sem precisar de Conta de Servico) e salva cloud_tts_token.json."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    resolved_client, default_tok, quota_proj = resolve_chirp3_oauth_paths()
    cpath = client_secret_path or resolved_client
    tpath = token_path or default_tok

    if cpath is None or not cpath.is_file():
        raise FileNotFoundError(
            f"Arquivo OAuth 2.0 nao encontrado. Salve o JSON do cliente OAuth em {CHIRP3_OAUTH_CLIENT_DEFAULT}."
        )
    if not quota_proj:
        quota_proj = _extract_oauth_project_id(cpath)

    creds: Credentials | None = None
    if tpath.is_file():
        try:
            creds = Credentials.from_authorized_user_file(str(tpath), scopes=scopes)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(cpath), scopes=scopes)
            creds = flow.run_local_server(port=0)
        tpath.parent.mkdir(parents=True, exist_ok=True)
        tpath.write_text(creds.to_json(), encoding="utf-8")

    return tpath, quota_proj


def _get_chirp3_access_token(cred_path: Path) -> str:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    key = str(cred_path.resolve())
    creds = _CHIRP3_CREDS_CACHE.get(key)
    if creds is None:
        creds = service_account.Credentials.from_service_account_file(
            key,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        _CHIRP3_CREDS_CACHE[key] = creds
    if not creds.valid or not creds.token:
        creds.refresh(Request())
    return str(creds.token)


def _get_chirp3_auth_headers(token_path: Path = CHIRP3_OAUTH_TOKEN_DEFAULT) -> dict[str, str]:
    """Retorna cabecalhos Authorization (+ x-goog-user-project no OAuth2 usuario) para Cloud TTS."""
    cred_path = resolve_chirp3_credentials_path()
    if cred_path is not None:
        token = _get_chirp3_access_token(cred_path)
        return {"Authorization": f"Bearer {token}"}

    if token_path.is_file():
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        creds = Credentials.from_authorized_user_file(str(token_path), scopes=scopes)
        if not creds.valid or not creds.token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json(), encoding="utf-8")
        _, _, quota_proj = resolve_chirp3_oauth_paths()
        proj_id = quota_proj or str(getattr(creds, "quota_project_id", "") or "").strip()
        hdrs = {"Authorization": f"Bearer {creds.token}"}
        if proj_id:
            hdrs["x-goog-user-project"] = proj_id
        return hdrs

    raise RuntimeError(
        "Credencial Google Cloud TTS nao encontrada. Salve o JSON do cliente OAuth 2.0 em "
        f"{CHIRP3_OAUTH_CLIENT_DEFAULT} e rode '--auth-chirp3', ou salve uma Conta de Servico em "
        f"{CHIRP3_CREDENTIALS_DEFAULT}."
    )


def _synthesize_chirp3_hd(
    text: str,
    speaker: str,
    out_audio: Path,
    speaking_rate: float = 1.0,
    state_file: Path = CHIRP3_USAGE_STATE_FILE,
    token_path: Path = CHIRP3_OAUTH_TOKEN_DEFAULT,
) -> tuple[str, str]:
    """Sintetiza via Google Cloud Text-to-Speech Chirp 3 HD (franquia 1M chars/mes) com OAuth2."""
    profile = SPEAKER_VOICE_PROFILES.get(speaker, SPEAKER_VOICE_PROFILES["narrador"])
    chirp_voice = str(profile.get("chirp3_voice") or "")
    if not chirp_voice.startswith("pt-BR-Chirp3-HD-"):
        raise RuntimeError(f"Voz Chirp 3 HD invalida para '{speaker}': {chirp_voice}")

    headers = _get_chirp3_auth_headers(token_path=token_path)
    headers["Content-Type"] = "application/json; charset=utf-8"
    _consume_chirp3_chars(len(text), state_file=state_file, limit=CHIRP3_MONTHLY_CHAR_LIMIT)

    payload = json.dumps({
        "input": {"text": text},
        "voice": {"languageCode": "pt-BR", "name": chirp_voice},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": float(speaking_rate)},
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://texttospeech.googleapis.com/v1/text:synthesize",
        data=payload,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    audio_b64 = data.get("audioContent") or ""
    if not audio_b64:
        raise RuntimeError(f"Resposta Chirp 3 HD sem audioContent para {chirp_voice}")
    out_audio.parent.mkdir(parents=True, exist_ok=True)
    out_audio.write_bytes(base64.b64decode(audio_b64))
    return f"chirp3_hd:{chirp_voice}", "chirp3_hd"


def _to_wav_norm(src_audio: Path, wav_path: Path) -> float:
    """Converte para WAV 44.1kHz stereo normalizado em -16 LUFS."""
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [FFMPEG_EXE, "-y", "-v", "error", "-i", str(src_audio),
         "-ar", "44100", "-ac", "2", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-c:a", "pcm_s16le", str(wav_path)],
        check=True,
    )
    return probe_duration(wav_path)


def _voice_studio_cli() -> str:
    """Localiza o CLI do Voice Studio no PATH ou na instalacao padrao do usuario."""
    exe = shutil.which("voicestudio")
    if exe:
        return exe
    local = Path.home() / "AppData" / "Local" / "Programs" / "VoiceStudio" / "resources" / "cli" / "voicestudio.exe"
    if local.exists():
        return str(local)
    raise RuntimeError("VoiceStudio CLI nao encontrado (PATH ou instalacao local).")


def _synthesize_voice_studio(
    text: str,
    speaker: str,
    out_raw: Path,
    emotion_hint: str = "",
    attempt: int = 1,
) -> tuple[str, str]:
    """Sintetiza com uma voz salva no Voice Studio (luninha/frida/simone-feliz)."""
    voice = VOICE_STUDIO_VOICES.get(speaker, VOICE_STUDIO_VOICES["narrador"])
    cmd = [
        _voice_studio_cli(), "speak",
        "--voice", voice,
        "--language", "Portuguese (Brazil)",
        "-o", str(out_raw),
        "--overwrite",
    ]
    # O backend do Voice Studio nao aceita --instruct em texto livre (HTTP 400).
    # As vozes salvas (Simone-feliz/Frida/Luninha) ja carregam a emoção desejada.
    cmd.append(text)
    r = subprocess.run(
        cmd, capture_output=True, timeout=600,
        encoding="utf-8", errors="replace",
    )
    if r.returncode != 0 or not out_raw.exists() or out_raw.stat().st_size < 2000:
        raise RuntimeError(f"VoiceStudio falhou para '{voice}': {(r.stderr or r.stdout or '').strip()[:180]}")
    return f"voice_studio:{voice}", "voice_studio"


def synthesize_all_scenes(
    script_data: dict[str, Any],
    audio_dir: Path,
    provider: str = "voice_studio",
    enable_whisper_qa: bool = True,
    enable_prosody_gate: bool = True,
    allow_flat_fallback: bool = False,
    max_attempts: int = 3,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Sintetiza todas as cenas com casting emocional Gemini TTS (Kore/Sulafat/Leda), Prosodia e Whisper QA.

    REGRA DE OURO: Edge TTS e estritamente proibido em producao (sem emocao).
    """
    prov = str(provider or "voice_studio").strip().lower()
    if prov not in ("voice_studio", "gemini", "gemini_emotion", "chirp3_hd", "auto"):
        raise ValueError(
            f"REGRA DE OURO VIOLADA: provedor '{provider}' nao permitido. "
            "Use 'voice_studio' (vozes luninha/frida/simone-feliz, first option), 'chirp3_hd' (fallback) ou 'gemini_emotion'. Edge TTS e proibido."
        )

    raw_dir = audio_dir / "raw"
    wav_dir = audio_dir / "wav"
    raw_dir.mkdir(parents=True, exist_ok=True)
    wav_dir.mkdir(parents=True, exist_ok=True)

    prev_timings_path = audio_dir.parent.parent / "artifacts" / "tts_timings_v2.json"
    prev_voice_map: dict[str, str] = {}
    if prev_timings_path.exists():
        try:
            for item in json.loads(prev_timings_path.read_text(encoding="utf-8")):
                if isinstance(item, dict) and item.get("scene_id") and item.get("voice"):
                    prev_voice_map[str(item["scene_id"])] = str(item["voice"])
        except Exception:
            pass

    timings: list[dict[str, Any]] = []
    for sc in script_data.get("scenes", []):
        sid = sc["scene_id"]
        speaker = sc.get("speaker", "narrador").lower()
        orig_text = sc["text"]
        tts_text = normalize_phonetics_pt(orig_text)
        emo_dir = sc.get("emotion_direction")

        mp3_path = raw_dir / f"{sid}.mp3"
        wav_path = wav_dir / f"{sid}.wav"

        profile = SPEAKER_VOICE_PROFILES.get(speaker, SPEAKER_VOICE_PROFILES["narrador"])
        locked_voice = profile["gemini_voice"]
        prev_v = prev_voice_map.get(sid, "")
        voice_matches_lock = (
            (not prev_v)
            or prev_v.endswith(f":{locked_voice}")
            or prev_v.endswith(f"-{locked_voice}")
            or prev_v == locked_voice
        )
        if prov == "chirp3_hd" and prev_v and not prev_v.startswith("chirp3_hd:"):
            voice_matches_lock = False
        if prov == "voice_studio" and prev_v and not prev_v.startswith("voice_studio:"):
            voice_matches_lock = False

        if not force and voice_matches_lock and wav_path.exists() and wav_path.stat().st_size > 4000:
            dur = probe_duration(wav_path)
            if dur > 0.2:
                timings.append({
                    "scene_id": sid, "speaker": speaker,
                    "voice": prev_v or f"locked:{locked_voice}",
                    "wav_path": str(wav_path),
                    "duration": dur, "emotion_mode": "cached", "qa": {"ok": True, "cached": True},
                })
                continue

        qa_report: dict[str, Any] = {"ok": False}
        prosody_report: dict[str, Any] = {"ok": True, "motivos": []}
        used_voice = ""
        emo_mode = "none"
        best_score = -1.0
        best_wav_bytes: bytes | None = None
        best_meta: tuple[str, str, dict[str, Any], dict[str, Any]] | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                # REGRA DE OURO: trava absoluta de voz por personagem (proibido alternar para outra voz)
                v_choice = locked_voice
                converted = False
                if prov == "voice_studio":
                    vs_raw = raw_dir / f"{sid}_vs.wav"
                    try:
                        used_voice, emo_mode = _synthesize_voice_studio(
                            tts_text, speaker, vs_raw, emo_dir, attempt
                        )
                        dur = _to_wav_norm(vs_raw, wav_path)
                        converted = True
                    except Exception as vs_exc:
                        print(f"  [VOICE-STUDIO] {sid} fallback Chirp 3 HD: {str(vs_exc)[:120]}", flush=True)
                        base_rate = float(CHIRP3_SPEAKING_RATE.get(speaker, 1.10))
                        rate = min(1.12, base_rate + (0.02 if attempt >= 2 else 0.0))
                        used_voice, emo_mode = _synthesize_chirp3_hd(
                            tts_text, speaker, mp3_path, speaking_rate=rate
                        )
                elif prov == "chirp3_hd":
                    base_rate = float(CHIRP3_SPEAKING_RATE.get(speaker, 1.10))
                    rate = min(1.12, base_rate + (0.02 if attempt >= 2 else 0.0))
                    used_voice, emo_mode = _synthesize_chirp3_hd(
                        tts_text, speaker, mp3_path, speaking_rate=rate
                    )
                else:
                    try:
                        used_voice, emo_mode = _synthesize_gemini_direct(
                            tts_text, speaker, emo_dir, mp3_path,
                            voice_override=v_choice, energy_boost=(attempt >= 2),
                        )
                    except Exception:
                        if prov == "auto" and has_chirp3_auth_configured():
                            base_rate = float(CHIRP3_SPEAKING_RATE.get(speaker, 1.10))
                            rate = min(1.12, base_rate + (0.02 if attempt >= 2 else 0.0))
                            used_voice, emo_mode = _synthesize_chirp3_hd(
                                tts_text, speaker, mp3_path, speaking_rate=rate
                            )
                        else:
                            raise

                if not converted:
                    dur = _to_wav_norm(mp3_path, wav_path)
                if dur <= 0.25:
                    raise RuntimeError(f"duracao invalida ({dur}s)")

                if enable_prosody_gate:
                    prosody_report = analyze_prosody(wav_path, text=orig_text)
                else:
                    prosody_report = {"ok": True, "motivos": []}

                if enable_whisper_qa:
                    qa_report = validate_audio_with_whisper(
                        wav_path, orig_text,
                        min_similarity=0.50 if prov == "voice_studio" else 0.78,
                    )
                else:
                    qa_report = {"ok": True, "similarity": 1.0, "reason": "qa_desativado"}

                score = (
                    (10.0 if qa_report.get("ok") else 0.0)
                    + (5.0 if prosody_report.get("ok") else 0.0)
                    + float(qa_report.get("similarity") or 0.0)
                )
                if score > best_score and wav_path.exists() and wav_path.stat().st_size > 2000:
                    best_score = score
                    best_wav_bytes = wav_path.read_bytes()
                    best_meta = (used_voice, emo_mode, dict(prosody_report), dict(qa_report))

                if enable_prosody_gate and not prosody_report["ok"] and attempt < max_attempts:
                    print(f"  [PROSODIA] {sid} tentativa {attempt}/{max_attempts}: {prosody_report['motivos']}; regenerando com mais emocao...", flush=True)
                    continue

                if enable_whisper_qa and not qa_report["ok"]:
                    if attempt < max_attempts:
                        print(f"  [TTS-QA] {sid} tentativa {attempt}/{max_attempts}: {qa_report['reason']}; regenerando...", flush=True)
                        continue
                    print(f"  [TTS-QA] {sid} ultima tentativa ainda abaixo do ideal: {qa_report['reason']}", flush=True)

                break
            except Exception as exc:
                qa_report = {"ok": False, "reason": str(exc)[:160]}
                print(f"  [TTS] {sid} tentativa {attempt}/{max_attempts} erro: {qa_report['reason']}", flush=True)
                time.sleep(0.8)

        if best_wav_bytes is not None and best_meta is not None:
            cur_score = (
                (10.0 if qa_report.get("ok") else 0.0)
                + (5.0 if prosody_report.get("ok") else 0.0)
                + float(qa_report.get("similarity") or 0.0)
            )
            if cur_score < best_score or not wav_path.exists():
                wav_path.write_bytes(best_wav_bytes)
                used_voice, emo_mode, prosody_report, qa_report = best_meta

        if not wav_path.exists() or wav_path.stat().st_size < 2000:
            raise RuntimeError(f"TTS falhou definitivamente na cena '{sid}': {qa_report.get('reason')}")
        if enable_whisper_qa and not qa_report.get("ok", True):
            raise RuntimeError(f"Whisper QA reprovou definitivamente a cena '{sid}': {qa_report.get('reason')}")
        dur = probe_duration(wav_path)
        timings.append({
            "scene_id": sid,
            "speaker": speaker,
            "voice": used_voice,
            "emotion_mode": emo_mode,
            "wav_path": str(wav_path),
            "duration": dur,
            "prosody": prosody_report,
            "qa": qa_report,
        })
        st_amp = prosody_report.get("amplitude_st", "-")
        print(f"  [TTS] {sid:6s} | {speaker:10s} | {dur:5.2f}s | {used_voice} ({emo_mode}, F0={st_amp}st) | QA={qa_report.get('similarity', '-')}", flush=True)

    return timings
