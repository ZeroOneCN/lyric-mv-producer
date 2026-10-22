#!/usr/bin/env python3
"""Build an SRT from the captions the film actually renders.

The list comes from `node tools/caption_segments.js .` (build.sh runs it for you),
so the subtitle file and the burned-in single-line captions cannot drift apart.

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
    ap.add_argument("--segments", default="out/segments.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    root = Path(args.project).resolve()
    src = root / args.segments
    if not src.exists():
        sys.exit(f"segments not found: {src}\n"
                 f"Run: node tools/caption_segments.js {root} --out {src}")
    try:
        caps = json.loads(src.read_text(encoding="utf-8"))["captions"]
    except (json.JSONDecodeError, KeyError) as e:
        sys.exit(f"{src} is not caption_segments.js output: {e}")
    if not caps:
        sys.exit(f"{src} has no captions")

    last_end, parts = -1.0, []
    for i, cap in enumerate(caps, 1):
        try:
            t0, t1, text = float(cap["t0"]), float(cap["t1"]), str(cap["text"]).strip()
        except (KeyError, TypeError, ValueError):
            sys.exit(f"caption {i}: expected numeric t0/t1 and text")
        if not text:
            sys.exit(f"caption {i}: empty text")
        if t1 <= t0:
            sys.exit(f"caption {i}: t1 must be after t0 ({t0:.3f} -> {t1:.3f})")
        if t0 < last_end - 1e-6:
            sys.exit(f"caption {i}: overlaps the previous caption ({t0:.3f} < {last_end:.3f})")
        last_end = t1
        parts.append(f"{i}\n{ts(t0)} --> {ts(t1)}\n{text}\n")

    out = Path(args.out) if args.out else root / f"{root.name}.srt"
    if not out.is_absolute():
        out = root / out
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"{out}: {len(caps)} captions, ends {last_end:.2f}s")


if __name__ == "__main__":
    main()
