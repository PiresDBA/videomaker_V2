# -*- coding: utf-8 -*-
"""Corrige os Shorts com problema: 02_storybook e 03_final (mudos -91dB) e
9x16 (som antigo). Junta o som novo (chirp3_hd) EM SEQUENCIA, sem amix em timestamps
velhos, com pausa distribuida e loudnorm -14 LUFS. NAO mexe no 01_hook (OK)."""
import json, shutil, subprocess, sys
from collections import OrderedDict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import FFMPEG_EXE
from core.motion_shorts import select_3_short_windows

root = Path(".")
proj = root / "projects" / "o-campeonato-de-caes-mais-maluco-do-mundo"
clips = json.loads((proj / "artifacts" / "pacing_plan_v2.json").read_text(encoding="utf-8"))
timings = json.loads((proj / "artifacts" / "tts_timings_v2.json").read_text(encoding="utf-8"))
wavs = {t["scene_id"]: Path(t["wav_path"]) for t in timings if Path(t["wav_path"]).exists()}
durs = {t["scene_id"]: float(t["duration"]) for t in timings}

def scene_start(sid):
    return min(float(c["start"]) for c in clips if c["scene_id"] == sid)

def probe_dur(p):
    r = subprocess.run([str(root / "bin" / "ffprobe.exe"), "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip().split(",")[0])

def build_audio_for(short_path, st, en, out_wav):
    scs = OrderedDict()
    for sid in sorted(wavs, key=lambda s: scene_start(s)):
        s = scene_start(sid)
        if s >= st - 0.05 and s < en:
            scs[sid] = s
    dur = probe_dur(short_path)
    total = sum(durs[sid] for sid in scs)
    gap = max(0.0, (dur - total) / (len(scs) - 1)) if len(scs) > 1 else 0.0
    print(f"  cenas={len(scs)} | audio={total:.2f}s | video={dur:.3f}s | pausa={gap:.3f}s")
    inputs, filters, cursor = [], [], 0.0
    for i, sid in enumerate(scs):
        inputs += ["-i", str(wavs[sid])]
        filters.append(f"[{i}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{i}]")
        off = int(round(cursor * 1000))
        filters.append(f"[a{i}]adelay=delays={off}|{off}[b{i}]")
        cursor += durs[sid] + gap
    n = len(scs)
    filters.append("".join(f"[b{i}]" for i in range(n)) + f"amix=inputs={n}:duration=longest:normalize=0[mix]")
    filters.append(f"[mix]apad=whole_dur={dur:.3f},atrim=0:{dur:.3f},loudnorm=I=-14:TP=-1.5:LRA=11[out]")
    subprocess.run([FFMPEG_EXE, "-y", "-v", "error"] + inputs +
                   ["-filter_complex", ";".join(filters), "-map", "[out]", "-c:a", "pcm_s16le", str(out_wav)], check=True)

def remux(short_path, out_wav, tag):
    backup = root / "work" / f"{tag}_antes.mp4"
    shutil.copy2(short_path, backup)
    tmp = root / "work" / f"{tag}_remux.mp4"
    subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-i", str(short_path), "-i", str(out_wav),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-t", f"{probe_dur(short_path):.3f}", str(tmp)], check=True)
    shutil.copy2(tmp, short_path)

wins = select_3_short_windows(clips)
# 02_storybook = win[1], 03_final = win[2], 9x16 = copia do 01_hook = win[0]
targets = [
    ("02_storybook", wins[1]["start"], wins[1]["end"]),
    ("03_final", wins[2]["start"], wins[2]["end"]),
    ("9x16", wins[0]["start"], wins[0]["end"]),
]
for name, st, en in targets:
    short = proj / "output" / f"o-campeonato-de-caes-mais-maluco-do-mundo_short_{name}.mp4"
    print(f"[{name}] janela [{st:.2f},{en:.2f}] -> {short.name}")
    out_wav = root / "work" / f"{name}_nova_voz.wav"
    build_audio_for(short, st, en, out_wav)
    remux(short, out_wav, name)
    print(f"[{name}] OK")
print("DONE")
