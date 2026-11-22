# -*- coding: utf-8 -*-
"""Junta os 25 WAVs de narração emocional no vídeo 16:9 SEM áudio, sequencialmente
(sem sobreposicao), com pausas curtas distribuidas entre cenas e loudnorm -14 LUFS."""
import json, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import FFMPEG_EXE

root = Path(".")
proj = root / "projects" / "o-campeonato-de-caes-mais-maluco-do-mundo"
timings = json.loads((proj / "artifacts" / "tts_timings_v2.json").read_text(encoding="utf-8"))

def probe_dur(p):
    r = subprocess.run([str(root / "bin" / "ffprobe.exe"), "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip().split(",")[0])

video = root / "work" / "main16x9_sem_audio.mp4"
dur_v = probe_dur(video)

wavs = []
for t in timings:
    p = Path(t["wav_path"])
    if p.exists():
        wavs.append((p, float(t["duration"])))
if not wavs:
    sys.exit("nenhum wav encontrado")

total_audio = sum(d for _, d in wavs)
gap = max(0.0, (dur_v - total_audio) / (len(wavs) - 1)) if len(wavs) > 1 else 0.0
print(f"video={dur_v:.3f}s | audio={total_audio:.3f}s | cenas={len(wavs)} | pausa entre cenas={gap:.3f}s")

inputs, filters = [], []
cursor = 0.0
for i, (w, d) in enumerate(wavs):
    inputs += ["-i", str(w)]
    off_ms = int(round(cursor * 1000))
    filters.append(f"[{i}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{i}]")
    filters.append(f"[a{i}]adelay=delays={off_ms}|{off_ms}[b{i}]")
    cursor += d + gap
n = len(wavs)
filters.append("".join(f"[b{i}]" for i in range(n)) + f"amix=inputs={n}:duration=longest:normalize=0[mix]")
filters.append(f"[mix]apad=whole_dur={dur_v:.3f},atrim=0:{dur_v:.3f},loudnorm=I=-14:TP=-1.5:LRA=11[out]")

audio_mix = root / "work" / "main16x9_narration_new.wav"
subprocess.run([FFMPEG_EXE, "-y", "-v", "error"] + inputs +
               ["-filter_complex", ";".join(filters), "-map", "[out]", "-c:a", "pcm_s16le", str(audio_mix)], check=True)

final = proj / "output" / "o-campeonato-de-caes-mais-maluco-do-mundo_16x9.mp4"
tmp = root / "work" / "main16x9_final_tmp.mp4"
subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-i", str(video), "-i", str(audio_mix),
                "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-t", f"{dur_v:.3f}", str(tmp)], check=True)
shutil.copy2(tmp, final)
print(f"OK: {final} | dur={probe_dur(final):.3f}s")
