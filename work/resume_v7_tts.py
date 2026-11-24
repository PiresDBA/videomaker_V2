# -*- coding: utf-8 -*-
"""Retoma o TTS do v7 sem refazer as cenas ja sintetizadas.

O processo anterior foi interrompido no sc_25. Este script:
  * le o log para descobrir quais cenas ja tiveram SUCESSO com voz local;
  * reaproveita esses wavs (sem nova chamada ao Voice Studio);
  * sintetiza apenas as cenas faltantes/que caíram no fallback Chirp;
  * insiste na voz local nessas cenas (a trava de voz reprova troca no video);
  * grava `artifacts/tts_timings_v2.json` com as 30 cenas em ordem.

Uso: python work/resume_v7_tts.py [slug]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import FFMPEG_EXE  # noqa: E402
from core.scene_auditor import audit_voice_consistency  # noqa: E402
from core.voice_studio import synthesize_all_scenes  # noqa: E402

LOG = ROOT / "work" / "build_v7_tts.log"
TTS_RE = re.compile(
    r"\[TTS\]\s+(sc_\d+)\s+\|\s*(\w+)\s+\|\s+([\d.]+)s\s+\|\s+(\S+)"
)


def probe_duration(path: Path) -> float:
    ffprobe = Path(FFMPEG_EXE).with_name("ffprobe.exe")
    r = subprocess.run([str(ffprobe), "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 3)
    except ValueError:
        return 0.0


def _read_log(path: Path) -> str:
    """O PowerShell `>` grava UTF-16 com BOM; Python normalmente grava UTF-8."""
    raw = path.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8", errors="replace")


def logged_successes() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    if not LOG.exists():
        return out
    for line in _read_log(LOG).splitlines():
        m = TTS_RE.search(line)
        if not m:
            continue
        sid, spk, dur, voice = m.groups()
        out[sid] = {"speaker": spk, "duration": dur, "voice": voice}
    return out


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "primeiro-dia-de-praia-v7"
    proj = ROOT / "projects" / slug
    audio = proj / "assets" / "audio"
    wav_dir = audio / "wav"
    wav_dir.mkdir(parents=True, exist_ok=True)
    script = json.loads((proj / "artifacts" / "script_v2.json").read_text(encoding="utf-8"))
    scenes = script["scenes"]
    log = logged_successes()
    print(f"[resume] cenas no log: {len(log)} / {len(scenes)}", flush=True)

    timings: dict[str, dict] = {}
    pending: list[dict] = []
    for sc in scenes:
        sid = sc["scene_id"]
        wav = wav_dir / f"{sid}.wav"
        entry = log.get(sid)
        voice = str(entry.get("voice") or "") if entry else ""
        ok = bool(entry and wav.exists() and wav.stat().st_size > 4000
                  and voice.startswith("voice_studio:"))
        if ok:
            dur = probe_duration(wav) or float(entry["duration"])
            timings[sid] = {
                "scene_id": sid,
                "speaker": str(entry["speaker"]),
                "voice": voice,
                "emotion_mode": "voice_studio",
                "wav_path": str(wav),
                "duration": dur,
                "qa": {"ok": True, "similarity": 1.0, "reason": "ok (reaproveitado)"},
            }
        else:
            pending.append(sc)
    print(f"[resume] reaproveitadas: {len(timings)} | pendentes: {[s['scene_id'] for s in pending]}",
          flush=True)

    if pending:
        for attempt in range(1, 4):
            mini = dict(script)
            mini["scenes"] = pending
            print(f"[resume] sintetizando {len(pending)} cena(s) — tentativa {attempt}/3", flush=True)
            got = synthesize_all_scenes(mini, audio, provider="voice_studio", force=True)
            still_pending = []
            for item in got:
                if not str(item.get("voice") or "").startswith("voice_studio:"):
                    still_pending.append(next(s for s in pending if s["scene_id"] == item["scene_id"]))
                    continue
                timings[item["scene_id"]] = item
            pending = still_pending
            if not pending:
                break
        if pending:
            print("[resume] AVISO: cenas sem voz local após 3 tentativas: "
                  + ", ".join(s["scene_id"] for s in pending), flush=True)
            # ainda assim registra o que existe para nao perder o trabalho
            got = synthesize_all_scenes({"scenes": pending}, audio, provider="voice_studio", force=True)
            for item in got:
                timings[item["scene_id"]] = item

    ordered = [timings[s["scene_id"]] for s in scenes if s["scene_id"] in timings]
    out = proj / "artifacts" / "tts_timings_v2.json"
    out.write_text(json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8")
    errs = audit_voice_consistency(ordered)
    total = sum(float(t.get("duration") or 0.0) for t in ordered)
    print(f"[resume] gravadas {len(ordered)} falas | {total:.1f}s de narração -> {out}", flush=True)
    for e in errs:
        print("  [VOZ-ERR]", e, flush=True)
    return 1 if errs or len(ordered) != len(scenes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
