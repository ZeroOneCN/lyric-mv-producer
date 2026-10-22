#!/usr/bin/env python3
"""Mix the user's song with procedural ambience and foley.

No added melody and no drum replacement: the supplied song is the music. Beds
and events come from events.json; every sound below is synthesised with numpy,
so the project carries no sample-library licences.

    python tools/mix.py /path/to/project
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
SR = 48000


def read_env(path: Path) -> dict:
    cfg = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


CFG = read_env(ROOT / "project.env")
DUR = float(CFG.get("DUR", "180"))
N = int(round(DUR * SR))
rng = np.random.default_rng(20261021)

song_path = ROOT / "audio" / "song.wav"
if not song_path.exists():
    sys.exit("audio/song.wav missing: decode the song to 48 kHz stereo PCM first")
sr, raw = wavfile.read(song_path)
if sr != SR:
    sys.exit(f"song.wav is {sr} Hz, expected {SR}")
if raw.ndim == 1:
    raw = np.stack([raw, raw], axis=1)
elif raw.shape[1] > 2:
    raw = raw[:, :2]
if raw.dtype == np.int16:
    song = raw.astype(np.float32) / 32768.0
elif raw.dtype == np.int32:
    song = raw.astype(np.float32) / 2147483648.0
else:
    song = raw.astype(np.float32)
song = song[:N]
if len(song) < N:
    song = np.pad(song, ((0, N - len(song)), (0, 0)))

# predictable foley levels: active song RMS = -20 dBFS
mono = song.mean(axis=1)
frame = int(.05 * SR)
rms_frames = np.sqrt(np.add.reduceat(mono ** 2, np.arange(0, N, frame)) / frame)
mask = np.repeat(rms_frames > 10 ** (-45 / 20), frame)[:N]
rms = math.sqrt(float(np.mean(mono[mask] ** 2))) if np.any(mask) else math.sqrt(float(np.mean(mono ** 2)))
song *= 10 ** ((-20 - 20 * math.log10(max(rms, 1e-9))) / 20)
song = np.clip(song, -1.5, 1.5)

fx = np.zeros((N, 2), np.float32)


def add(sig, t, gain=1.0, pan=0.0):
    if sig.ndim == 1:
        a = (pan + 1) * math.pi / 4
        sig = np.stack([sig * math.cos(a), sig * math.sin(a)], axis=1)
    i = int(round(t * SR))
    if i >= N:
        return
    j = min(N, i + len(sig))
    fx[i:j] += (sig[: j - i] * gain).astype(np.float32)


def noise(n):
    return rng.standard_normal(n).astype(np.float32)


def fades(x, a=.01, d=.05):
    na, nd = min(len(x), int(a * SR)), min(len(x), int(d * SR))
    if na:
        x[:na] *= np.linspace(0, 1, na, dtype=np.float32) ** 2
    if nd:
        x[-nd:] *= np.linspace(1, 0, nd, dtype=np.float32) ** 2
    return x


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "bandpass", fs=SR, output="sos"), x).astype(np.float32)


def lp(x, fc):
    return sosfilt(butter(2, fc, "lowpass", fs=SR, output="sos"), x).astype(np.float32)


def hp(x, fc):
    return sosfilt(butter(2, fc, "highpass", fs=SR, output="sos"), x).astype(np.float32)


def set_rms(x, db):
    return x * (10 ** (db / 20) / (math.sqrt(float(np.mean(x ** 2))) + 1e-12))


def bell(f, dur):
    t = np.arange(int(dur * SR), dtype=np.float32) / SR
    e = np.exp(-t * 4.2).astype(np.float32)
    return ((np.sin(2 * np.pi * f * t) + .42 * np.sin(2 * np.pi * f * 2.01 * t) +
             .18 * np.sin(2 * np.pi * f * 2.99 * t)) * e * .5).astype(np.float32)


def blip(f, dur=.08, kind="square"):
    t = np.arange(int(dur * SR), dtype=np.float32) / SR
    e = np.minimum(1, t / .004) * np.exp(-t * 46)
    if kind == "square":
        w = np.sign(np.sin(2 * np.pi * f * t))
    elif kind == "tri":
        w = 2 * np.abs(2 * ((f * t) % 1) - 1) - 1
    else:
        w = np.sin(2 * np.pi * f * t)
    return (w * e).astype(np.float32)


def thump(f=54, dur=.6):
    t = np.arange(int(dur * SR), dtype=np.float32) / SR
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 8) * np.minimum(1, t / .012)).astype(np.float32)


def splash(dur=.55):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    return (bp(noise(n), 400, 7000) * np.minimum(1, t / .006) * np.exp(-t * 5.5) * .35).astype(np.float32)


def riser(dur=2.5):
    n = int(dur * SR)
    u = np.linspace(0, 1, n, dtype=np.float32)
    x = bp(noise(n), 200, 900) * (1 - u) ** 1.5 * .5
    x += bp(noise(n), 900, 2600) * np.sin(np.pi * np.clip(u * 1.2, 0, 1)) ** 2 * .6
    x += hp(bp(noise(n), 2500, 9000), 2500) * u ** 2.2 * .5
    return (x * np.minimum(1, u / .08) * u ** .7).astype(np.float32)


def whoosh(dur=.8):
    n = int(dur * SR)
    u = np.linspace(0, 1, n, dtype=np.float32)
    return (bp(noise(n), 350, 3000) * (.3 + .7 * u) * np.sin(np.pi * u) ** 2).astype(np.float32)


def impact(dur=1.2):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    body = np.sin(2 * np.pi * 44 * t) * np.exp(-t * 8) * .6
    hit = bp(noise(n), 300, 4500) * np.exp(-t * 20) * .35
    return (body + hit).astype(np.float32)


def bed(kind, dur):
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    if kind == "rain":
        base = hp(bp(noise(n), 1500, 9500), 1200) * .75 + lp(noise(n), 900) * .35
        base *= .8 + .2 * np.sin(2 * np.pi * .19 * t + 1.1)
    elif kind == "wind":
        base = lp(noise(n), 220) + lp(noise(n), 800) * .25
        base *= .55 + .45 * np.sin(2 * np.pi * .055 * t + 2.0) ** 2
    elif kind == "room":
        base = lp(noise(n), 300) * .5 + hp(noise(n), 2400) * .10
        base *= .8 + .2 * np.sin(2 * np.pi * .13 * t)
    else:  # sea / default water
        base = lp(noise(n), 420) * .6 + lp(noise(n), 140) * .5
        base *= .65 + .35 * np.sin(2 * np.pi * .085 * t + .4) ** 2
        base += hp(lp(noise(n), 2400), 500) * .10
    return base.astype(np.float32)


def add_bed(kind, t0, t1, gain_db):
    dur = max(0.1, t1 - t0)
    a = fades(set_rms(bed(kind, dur), gain_db), .5, .8)
    b = fades(set_rms(bed(kind, dur), gain_db), .6, .7)
    add(np.stack([a, b], axis=1), t0)


evdoc = json.loads((ROOT / "events.json").read_text(encoding="utf-8"))
for b in evdoc.get("beds", []):
    add_bed(b.get("kind", "sea"), float(b["t0"]), float(b["t1"]), float(b.get("gain", -45)))

for e in evdoc.get("ev", []):
    t, k = float(e["t"]), str(e.get("k", "tick"))
    if k == "title":
        add(thump(42, 1.8), t, .055)
        add(bell(523, 2.6), t + .05, .020)
        add(set_rms(fades(lp(noise(int(1.4 * SR)), 300), .2, .8), -45), t)
    elif k == "ui":
        add(blip(660, .07, "square"), t, .035)
        add(blip(990, .09, "square"), t + .10, .035)
    elif k == "bell":
        add(bell(880, 1.2), t, .020, -.2)
        add(bell(1320, .9), t + .18, .012, .2)
    elif k in ("hit", "impact"):
        add(impact(), t, .18)
        add(bell(1046, 1.6), t + .08, .010, -.2)
    elif k == "whoosh":
        add(whoosh(), t, .16, .15)
    elif k == "riser":
        add(riser(), t, .22)
        add(thump(38, 2.4), t + .1, .035)
    elif k == "splash":
        add(splash(), t, .24, .3)
    elif k == "heart":
        add(thump(56, .34), t, .075)
        add(thump(48, .42), t + .21, .055)
    elif k == "sparkle":
        for i, f in enumerate((2093, 2637, 3136)):
            add(bell(f, 1.2 - i * .2), t + i * .06, .018 - i * .004, -.3 + i * .3)
    elif k == "end":
        add(bell(523, 3.2), t, .014)
        add(bell(659, 2.4), t + .2, .008)
        add(set_rms(fades(lp(noise(int(2.4 * SR)), 260), .4, 1.6), -44), t)
    else:
        add(blip(1320, .03, "tri"), t, .012, .2)

# optional song treatments: {"t0","t1","lowpass","gain_db"} with smooth edges
for d in evdoc.get("ducks", []):
    a, b = float(d["t0"]), float(d["t1"])
    w = np.zeros(N, dtype=np.float32)
    i0, i1 = max(0, min(N, int(a * SR))), max(0, min(N, int(b * SR)))
    w[i0:i1] = 1.0
    ramp = int(.08 * SR)
    for i in range(ramp):
        u = i / max(1, ramp - 1)
        if i0 - ramp + i >= 0:
            w[i0 - ramp + i] = u * u * (3 - 2 * u)
        if i1 + i < N:
            w[i1 + i] = 1 - u * u * (3 - 2 * u)
    w = np.clip(w, 0, 1)[:, None]
    wet = np.stack([lp(song[:, 0], float(d.get("lowpass", 1200))),
                    lp(song[:, 1], float(d.get("lowpass", 1200)))], axis=1)
    wet *= 10 ** (float(d.get("gain_db", 0)) / 20)
    song = song * (1 - w) + wet * w

fade = int(.6 * SR)
mix = song + fx
mix[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)[:, None] ** 1.5
peak = float(np.max(np.abs(mix)))
if peak > .90:
    mix *= .90 / peak
mix = np.nan_to_num(mix, nan=0.0, posinf=0.0, neginf=0.0)
out = ROOT / "audio" / "mix.wav"
wavfile.write(out, SR, mix.astype(np.float32))
rms_db = 20 * math.log10(max(1e-12, math.sqrt(float(np.mean(mix ** 2)))))
print(f"{out.name}: {len(mix)/SR:.2f}s  peak {20*math.log10(max(peak,1e-9)):.1f} dBFS  "
      f"rms {rms_db:.1f} dBFS  events {len(evdoc.get('ev', []))}  beds {len(evdoc.get('beds', []))}")
