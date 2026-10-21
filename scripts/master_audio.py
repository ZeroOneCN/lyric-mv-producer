#!/usr/bin/env python3
"""Two-pass loudness normalisation and true-peak safety for the final mix.

    python master_audio.py audio/mix.wav audio/master.wav --ffmpeg tools/ffmpeg/ffmpeg.exe
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, encoding="utf-8", errors="replace")


def loudnorm_measure(ffmpeg: str, src: Path, i: float, tp: float, lra: float) -> dict:
    af = f"loudnorm=I={i}:TP={tp}:LRA={lra}:print_format=json"
    p = run([ffmpeg, "-hide_banner", "-nostats", "-i", str(src), "-af", af, "-f", "null", "-"])
    if p.returncode != 0:
        sys.exit("loudnorm pass 1 failed:\n" + p.stderr[-2000:])
    blocks = re.findall(r"\{[\s\S]*?\}", p.stderr)
    for block in reversed(blocks):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if "input_i" in data:
            return data
    sys.exit("could not parse loudnorm JSON:\n" + p.stderr[-2000:])


def ebur128(ffmpeg: str, src: Path) -> tuple[float, float]:
    p = run([ffmpeg, "-hide_banner", "-nostats", "-i", str(src),
             "-map", "0:a:0", "-af", "ebur128=peak=true", "-f", "null", "-"])
    if p.returncode != 0:
        sys.exit("ebur128 measurement failed:\n" + p.stderr[-2000:])
    ints = re.findall(r"I:\s*(-?[\d.]+|-inf)\s*LUFS", p.stderr)
    peaks = re.findall(r"Peak:\s*(-?[\d.]+|-inf)\s*dBFS", p.stderr)
    if not ints or not peaks:
        sys.exit("could not read the ebur128 summary")
    integrate = float("-inf") if ints[-1] == "-inf" else float(ints[-1])
    true_peak = float("-inf") if peaks[-1] == "-inf" else float(peaks[-1])
    return integrate, true_peak


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--i", type=float, default=-14.0, help="integrated LUFS target")
    ap.add_argument("--tp", type=float, default=-1.2, help="true-peak ceiling, dBTP")
    ap.add_argument("--lra", type=float, default=11.0)
    args = ap.parse_args()

    src, dst = Path(args.src), Path(args.dst)
    if not src.exists():
        sys.exit(f"mix not found: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)

    m = loudnorm_measure(args.ffmpeg, src, args.i, args.tp, args.lra)
    print("pass 1:", {k: m.get(k) for k in ("input_i", "input_tp", "input_lra",
                                           "input_thresh", "target_offset")})
    if m.get("input_i") in (None, "-inf"):
        sys.exit("mix is silent or unreadable; nothing to master")

    af = (f"loudnorm=I={args.i}:TP={args.tp}:LRA={args.lra}"
          f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
          f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
          f":offset={m['target_offset']}:linear=true,"
          "alimiter=limit=0.85:level=false:latency=true,aresample=48000")
    p = run([args.ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
             "-af", af, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(dst)])
    if p.returncode != 0:
        sys.exit("mastering failed:\n" + p.stderr[-2000:])

    integrated, true_peak = ebur128(args.ffmpeg, dst)
    print(f"{dst}: {integrated:.1f} LUFS / {true_peak:.1f} dBTP")
    if abs(integrated - args.i) > 0.7:
        sys.exit(f"loudness missed the target by more than 0.7 LU")
    if true_peak > args.tp + 0.4:
        sys.exit(f"true peak {true_peak:.1f} dBTP is above the ceiling")
    print("master OK")


if __name__ == "__main__":
    main()
