# -*- coding: utf-8 -*-
"""BGM original do episodio 'O Primeiro Dia de Praia' — loop cartoon alegre, gerado em codigo."""
import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 126
BEAT = 60.0 / BPM
DUR = 32.0  # 8 compassos de 4 tempos (~15s) repetidos 2x = 32s, loop suave
OUT = Path(r"E:\videos\videomaker_v2\assets\music\primeiro-dia-de-praia_musica.wav")


def midi(n):
    return 440.0 * (2.0 ** ((n - 69) / 12.0))


def pluck(buf, freq, start, length, amp):
    i0 = int(start * SR)
    n = int(length * SR)
    if i0 < 0 or i0 + n > len(buf):
        n = max(0, len(buf) - i0)
    if n <= 0:
        return
    t = np.arange(n) / SR
    env = np.exp(-3.2 * t) * (1.0 - np.exp(-60.0 * t))
    wave = (
        np.sin(2 * np.pi * freq * t)
        + 0.30 * np.sin(4 * np.pi * freq * t)
        + 0.14 * np.sin(6 * np.pi * freq * t)
        + 0.07 * np.sin(8 * np.pi * freq * t)
    )
    buf[i0:i0 + n] += (amp * env * wave).astype(np.float64)


def bass(buf, freq, start, length, amp):
    i0 = int(start * SR)
    n = int(length * SR)
    if i0 < 0 or i0 + n > len(buf):
        n = max(0, len(buf) - i0)
    if n <= 0:
        return
    t = np.arange(n) / SR
    env = np.exp(-2.0 * t) * (1.0 - np.exp(-80.0 * t))
    buf[i0:i0 + n] += (amp * env * np.sin(2 * np.pi * freq * t)).astype(np.float64)


def shaker(buf, start, amp):
    i0 = int(start * SR)
    n = int(0.07 * SR)
    if i0 < 0 or i0 + n > len(buf):
        n = max(0, len(buf) - i0)
    if n <= 0:
        return
    rng = np.random.default_rng(int(start * 1000) % (2 ** 31))
    noise = rng.standard_normal(n)
    env = np.exp(-55.0 * np.arange(n) / SR)
    buf[i0:i0 + n] += (amp * env * noise).astype(np.float64)


sig = np.zeros(int(DUR * SR), dtype=np.float64)
# C - G - Am - F (tons alegres), 2 compassos por acorde
chords = [
    [60, 64, 67, 72],  # C
    [59, 62, 67, 71],  # G
    [53, 57, 60, 65],  # F
    [59, 62, 67, 71],  # G
]
bar = 4 * BEAT
n_bars = int(DUR / bar)
for b in range(n_bars):
    chord = chords[(b // 2) % len(chords)]
    t0 = b * bar
    # ukulele: batidas no tempo 0 e 2.5, com contratempo leve
    for beat_off, amp in ((0.0, 0.18), (1.5, 0.12), (2.5, 0.15), (3.5, 0.10)):
        for k, note in enumerate(chord):
            pluck(sig, midi(note + (12 if k == 3 else 0)), t0 + beat_off * BEAT, 1.1, amp / (1 + 0.25 * k))
    bass(sig, midi(chord[0] - 24), t0, 0.9, 0.22)
    bass(sig, midi(chord[0] - 24), t0 + 2 * BEAT, 0.7, 0.16)
    # melodia pentatonica saltitante (C D E G A)
    scale = [72, 74, 76, 79, 81, 79, 76, 74]
    for eighth in range(8):
        note = scale[(b * 3 + eighth) % len(scale)]
        pluck(sig, midi(note), t0 + eighth * BEAT / 2, 0.42, 0.085)
    for eighth in range(8):
        shaker(sig, t0 + (eighth + 0.5) * BEAT / 2, 0.055 if eighth % 2 else 0.030)

# fade nas pontas e normalizacao para -3 dBFS
fade = int(0.6 * SR)
sig[:fade] *= np.linspace(0.0, 1.0, fade)
sig[-fade:] *= np.linspace(1.0, 0.0, fade)
peak = float(np.max(np.abs(sig))) or 1.0
sig = sig * (0.708 / peak)
stereo = np.stack([sig, np.roll(sig, 47)], axis=1)
pcm = np.clip(stereo * 32767.0, -32767, 32767).astype(np.int16)

OUT.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(OUT), "wb") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(pcm.tobytes())
print(f"BGM original criada: {OUT} ({DUR:.1f}s, {OUT.stat().st_size} bytes)")
