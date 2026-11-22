# -*- coding: utf-8 -*-
"""Junta o som novo (assets/audio/wav/sc_XX.wav, sintetizado com vozes emocionais)
nas 3 Shorts existentes de output/, sem re-renderizar o vídeo."""
import json, shutil, subprocess, sys
from collections import OrderedDict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import FFMPEG_EXE
from core.motion_shorts import select_3_short_windows

root = Path(".")
proj = root / "projects" / "o-campeonato-de-caes-mais-maluco-do-mundo"
clips = json.loads((proj / "artifacts" / "pacing_plan_v2.json").read_text(encoding="utf-8"))
wavs = {p.stem: p for p in (proj / "assets" / "audio" / "wav").glob("*.wav")}

def scene_start(sid):
    return min(float(c["start"]) for c in clips if c["scene_id"] == sid)

def probe_dur(p):
    r = subprocess.run([str(root / "bin" / "ffprobe.exe"), "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip().split(",")[0])

names = ["01_hook", "02_storybook", "03_final"]
for idx, win in enumerate(select_3_short_windows(clips)):
    st, en = float(win["start"]), float(win["end"])
    scs = OrderedDict()
    for sid in {c["scene_id"] for c in clips}:
        s = scene_start(sid)
        if s >= st - 0.05 and s < en and sid in wavs:
            scs[sid] = s
    short = proj / "output" / f"o-campeonato-de-caes-mais-maluco-do-mundo_short_{names[idx]}.mp4"
    if not short.exists():
        print(f"[{win['name']}] short nao existe: {short}")
        continue
    dur = probe_dur(short)
    items = [(off, wavs[sid]) for sid, off in sorted(scs.items(), key=lambda kv: kv[1])]
    if not items:
        print(f"[{win['name']}] nenhuma cena com wav na janela [{st:.2f},{en:.2f}]")
        continue
    inputs, filters = [], []
    for i, (off, wav) in enumerate(items):
        inputs += ["-i", str(wav)]
        filters.append(f"[{i}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{i}]")
        d = int(round(off * 1000))
        filters.append(f"[a{i}]adelay=delays={d}|{d}[b{i}]")
    n = len(items)
    filters.append("".join(f"[b{i}]" for i in range(n)) + f"amix=inputs={n}:duration=longest:normalize=0[aout]")
    filters.append(f"[aout]apad=whole_dur={dur:.3f},atrim=0:{dur:.3f}[out]")
    out_wav = root / "work" / f"short{idx+1}_new.wav"
    subprocess.run([FFMPEG_EXE, "-y", "-v", "error"] + inputs +
                   ["-filter_complex", ";".join(filters), "-map", "[out]", "-c:a", "pcm_s16le", str(out_wav)],
                   check=True)
    backup = root / "work" / f"short{idx+1}_old.mp4"
    shutil.copy2(short, backup)
    remux = root / "work" / f"short{idx+1}_remuxed.mp4"
    subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-i", str(short), "-i", str(out_wav),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(remux)],
                   check=True)
    shutil.copy2(remux, short)
    print(f"[{win['name']}] som novo juntado: {len(items)} cenas | janela [{st:.2f},{en:.2f}] | {short}")
print("DONE")
