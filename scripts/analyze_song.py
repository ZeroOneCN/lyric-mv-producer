#!/usr/bin/env python3
"""Decode a song and report duration, tempo candidates, energy and edit points.

Uses only numpy + ffmpeg. The output is a starting map for the treatment, not a
replacement for listening: confirm sections and downbeats by ear.

    python analyze_song.py song.mp3 --json analysis/song.json
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

WIN = 2048
HOP = 1024


def decode(path: Path, sr: int, ffmpeg: str) -> tuple[np.ndarray, float]:
    # Keep two channels: ffmpeg's mono downmix can add ~3 dB and fake a hot peak.
    cmd = [ffmpeg, "-v", "error", "-i", str(path), "-vn", "-f", "f32le",
           "-ac", "2", "-ar", str(sr), "-"]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        msg = p.stderr.decode("utf-8", "replace").strip().splitlines()
        sys.exit("ffmpeg could not decode the song" + (": " + msg[-1] if msg else ""))
    stereo = np.frombuffer(p.stdout, dtype="<f4").astype(np.float64)
    if len(stereo) < 2 * sr:
        sys.exit("decoded audio is shorter than one second")
    stereo = stereo[:len(stereo) // 2 * 2].reshape(-1, 2)
    peak = float(np.max(np.abs(stereo)))
    return stereo.mean(axis=1), peak


def db(v: float) -> float:
    return 20.0 * math.log10(max(v, 1e-12))


def autocorr(x: np.ndarray) -> np.ndarray:
    n = len(x)
    size = 1 << (2 * n - 1).bit_length()
    f = np.fft.rfft(x, size)
    ac = np.fft.irfft(f * np.conj(f), size)[:n]
    return ac / max(ac[0], 1e-12)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("song")
    ap.add_argument("--sr", type=int, default=48000)
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--json", help="write the full analysis here")
    ap.add_argument("--bpm-min", type=float, default=60.0)
    ap.add_argument("--bpm-max", type=float, default=180.0)
    args = ap.parse_args()

    path = Path(args.song)
    if not path.exists():
        sys.exit(f"song not found: {path}")
    x, peak = decode(path, args.sr, args.ffmpeg)
    sr = args.sr
    duration = len(x) / sr
    rms = float(np.sqrt(np.mean(x * x)))

    n = 1 + (len(x) - WIN) // HOP
    frames = np.lib.stride_tricks.as_strided(
        x, shape=(n, WIN), strides=(x.strides[0] * HOP, x.strides[0]),
        writeable=False)
    mag = np.abs(np.fft.rfft(frames * np.hanning(WIN), axis=1))
    flux = np.sum(np.maximum(np.diff(mag, axis=0), 0.0), axis=1)
    flux = np.concatenate([[0.0], flux])
    fps = sr / HOP

    centered = flux - flux.mean()
    ac = autocorr(centered)
    candidates = []
    for bpm in np.arange(args.bpm_min, args.bpm_max + 1e-9, 0.25):
        lag = 60.0 / bpm * fps
        j = int(lag)
        frac = lag - j
        if j + 1 >= len(ac):
            continue
        score = ac[j] * (1 - frac) + ac[j + 1] * frac
        candidates.append((float(score), float(bpm)))
    candidates.sort(reverse=True)
    peaks = []
    for score, bpm in candidates:
        if all(abs(bpm - b) > 3.0 for _, b in peaks):
            peaks.append((score, bpm))
        if len(peaks) >= 6:
            break

    # 2 s energy / brightness profile
    profile = []
    step = 2 * sr
    freqs = np.fft.rfftfreq(step, 1.0 / sr)
    for a in range(0, len(x), step):
        seg = x[a:a + step]
        if len(seg) < sr // 2:
            continue
        seg_rms = float(np.sqrt(np.mean(seg * seg)))
        spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        centroid = float(np.sum(freqs[:len(spec)] * spec) / max(np.sum(spec), 1e-12))
        profile.append({"t": round(a / sr, 2), "rms_db": round(db(seg_rms), 1),
                        "centroid_hz": round(centroid, 1)})

    quiet = []
    run = None
    for row in profile:
        if row["rms_db"] < -38:
            run = row["t"] if run is None else run
        elif run is not None:
            if row["t"] - run >= 2:
                quiet.append([run, row["t"]])
            run = None
    if run is not None and duration - run >= 2:
        quiet.append([run, duration])

    flux_peaks = []
    order = np.argsort(flux)[::-1]
    for i in order:
        t = float(i / fps)
        if all(abs(t - p) > 4.0 for p in flux_peaks):
            flux_peaks.append(round(t, 2))
        if len(flux_peaks) >= 20:
            break
    flux_peaks.sort()

    print(f"duration {duration:.2f}s   peak {db(peak):.1f} dBFS   rms {db(rms):.1f} dBFS")
    print("tempo candidates:", ", ".join(f"{bpm:.2f} ({score:.2f})" for score, bpm in peaks))
    print("  half/double-time pairs are normal; tap the pulse you want the cuts on")
    print("quiet spans:", ", ".join(f"{a:.1f}-{b:.1f}s" for a, b in quiet) or "none")
    print("spectral-flux peaks:", ", ".join(f"{t:.1f}s" for t in flux_peaks))
    print("energy profile (2s):")
    for row in profile[::max(1, len(profile) // 12)]:
        print(f"  {row['t']:7.1f}s  {row['rms_db']:6.1f} dBFS  {row['centroid_hz']:6.0f} Hz")
    print("Use the peaks as candidates only. Confirm sections and downbeats by listening.")

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "source": str(path),
            "duration": round(duration, 3),
            "sample_rate": sr,
            "peak_dbfs": round(db(peak), 2),
            "rms_dbfs": round(db(rms), 2),
            "bpm_candidates": [{"bpm": round(b, 2), "score": round(s, 3)} for s, b in peaks],
            "flux_peaks": flux_peaks,
            "quiet_spans": quiet,
            "energy_profile": profile,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
