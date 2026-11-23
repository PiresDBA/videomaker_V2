# -*- coding: utf-8 -*-
"""Junta a narração nova (assets/audio/wav/sc_XX.wav, vozes emocionais Zephyr/Leda/Sulafat)
no vídeo principal 16:9, sem alterar a lógica do pipeline (remux de áudio; vídeo preservado)."""
import json, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import FFMPEG_EXE

root = Path(".")
proj = root / "projects" / "o-campeonato-de-caes-mais-maluco-do-mundo"

clips = json.loads((proj / "artifacts" / "pacing_plan_v2.json").read_text(encoding="utf-8"))
wavs = {p.stem: p for p in (proj / "assets" / "audio" / "wav").glob("*.wav")}
tts = json.loads((proj / "artifacts" / "tts_timings_v2.json").read_text(encoding="utf-8"))
dur_by_scene = {t["scene_id"]: float(t["duration"]) for t in tts}

scenes = []
seen = set()
for c in clips:
    sid = c["scene_id"]
    if sid in seen or sid not in wavs or sid not in dur_by_scene:
        continue
    seen.add(sid)
    scenes.append((float(c["scene_audio_start"]), sid, wavs[sid]))
scenes.sort(key=lambda x: x[0])
if not scenes:
    sys.exit("nenhuma cena com wav nova")

def probe_dur(p):
    r = subprocess.run([str(root / "bin" / "ffprobe.exe"), "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip().split(",")[0])

v = proj / "output" / "o-campeonato-de-caes-mais-maluco-do-mundo_16x9.mp4"
dur_v = probe_dur(v)
audio_total = max((off + dur_by_scene[sid] for off, sid, _ in scenes), default=0.0)
final_len = max(dur_v, audio_total)

inputs, filters = [], []
for i, (off, sid, w) in enumerate(scenes):
    inputs += ["-i", str(w)]
    d = int(round(off * 1000))
    filters.append(f"[{i}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a{i}]")
    filters.append(f"[a{i}]adelay=delays={d}|{d}[b{i}]")
n = len(scenes)
filters.append("".join(f"[b{i}]" for i in range(n)) + f"amix=inputs={n}:duration=longest:normalize=0[aout]")

if audio_total > dur_v + 0.15:
    filters.insert(0, f"[0:v]tpad=stop_mode=clone:stop_duration={audio_total - dur_v:.3f}[vout]")
    vcodec = ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]
else:
    filters.insert(0, "[0:v]null[vout]")
    vcodec = ["-c:v", "copy"]
filters.append("[aout]apad=whole_dur={:.3f},atrim=0:{:.3f}[out]".format(final_len, final_len))

backup = root / "work" / "main16x9_old.mp4"
shutil.copy2(v, backup)
remux = root / "work" / "main16x9_remuxed.mp4"
subprocess.run([FFMPEG_EXE, "-y", "-v", "error", "-i", str(v)] + inputs +
               ["-filter_complex", ";".join(filters),
                "-map", "[vout]", "-map", "[out]"] + vcodec + ["-b:a", "192k", str(remux)], check=True)
shutil.copy2(remux, v)
print(f"16x9: video {dur_v:.3f}s + nova narrativa {audio_total:.3f}s -> dur {final_len:.3f}s | vcodec {vcodec[1]}")
print(f"backup: work/main16x5_old.mp4" if False else f"backup: work/main16x9_old.mp4")
