#!/usr/bin/env python3
"""Build an SRT from the same lyrics.json the film renders.

    python make_srt.py /path/to/project --out my-film.srt
"""
import argparse
import json
import sys
from pathlib import Path


def ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--lyrics", default="lyrics.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    root = Path(args.project).resolve()
    src = root / args.lyrics
    if not src.exists():
        sys.exit(f"lyrics not found: {src}")
    cues = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(cues, list) or not cues:
        sys.exit("lyrics.json must be a non-empty array")

    last_end = -1.0
    parts = []
    for i, cue in enumerate(cues, 1):
        try:
            t0, t1, text = float(cue["t0"]), float(cue["t1"]), str(cue["text"]).strip()
        except (KeyError, TypeError, ValueError):
            sys.exit(f"cue {i}: expected numeric t0/t1 and text")
        if not text:
            sys.exit(f"cue {i}: empty text")
        if t1 <= t0:
            sys.exit(f"cue {i}: t1 must be after t0 ({t0:.3f} -> {t1:.3f})")
        if t0 < last_end - 1e-6:
            sys.exit(f"cue {i}: overlaps the previous cue ({t0:.3f} < {last_end:.3f})")
        last_end = t1
        parts.append(f"{i}\n{ts(t0)} --> {ts(t1)}\n{text}\n")

    out = Path(args.out) if args.out else root / f"{root.name}.srt"
    if not out.is_absolute():
        out = root / out
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"{out}: {len(cues)} cues, ends {last_end:.2f}s")


if __name__ == "__main__":
    main()
