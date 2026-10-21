#!/usr/bin/env python3
"""Derive 4:3 and 3:4 covers from the 16:9 poster.

    python tools/make_covers.py . --ffmpeg ffmpeg --focus 0.5

poster.jpg is reduced to the 320x180 framebuffer, cropped horizontally and
upscaled with nearest-neighbour, so the pixel grid stays exact:
    poster_4x3.jpg   240x180 crop -> 1920x1440
    poster_3x4.jpg   135x180 crop -> 1080x1440
--focus 0 keeps the left edge, 1 the right edge; 0.5 keeps the centre.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

FB_W, FB_H = 320, 180
COVERS = (
    ("poster_4x3.jpg", 240, 1920, 1440),
    ("poster_3x4.jpg", 135, 1080, 1440),
)


def image_size(ffmpeg: str, path: Path) -> tuple[int, int] | None:
    p = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", p.stderr)
    return (int(m.group(1)), int(m.group(2))) if m else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--source", default="poster.jpg")
    ap.add_argument("--focus", type=float, default=0.5,
                    help="horizontal crop focus: 0 = left, 0.5 = centre, 1 = right")
    args = ap.parse_args()

    root = Path(args.project).resolve()
    src = root / args.source
    if not src.exists():
        sys.exit(f"make_covers: source missing: {src}")

    size = image_size(args.ffmpeg, src)
    if not size:
        sys.exit(f"make_covers: cannot read image size: {src}")
    w, h = size
    if abs(w / h - 16 / 9) > 0.01:
        sys.exit(f"make_covers: poster is {w}x{h}; expected 16:9")

    focus = max(0.0, min(1.0, args.focus))
    for name, crop_w, out_w, out_h in COVERS:
        x = round((FB_W - crop_w) * focus)
        vf = (f"scale={FB_W}:{FB_H}:flags=neighbor,"
              f"crop={crop_w}:{FB_H}:{x}:0,"
              f"scale={out_w}:{out_h}:flags=neighbor,setsar=1")
        out = root / name
        p = subprocess.run(
            [args.ffmpeg, "-y", "-loglevel", "error", "-i", str(src),
             "-vf", vf, "-frames:v", "1", "-q:v", "2", str(out)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        )
        if p.returncode != 0:
            sys.exit(f"make_covers: ffmpeg failed for {name}\n{p.stderr.strip()}")
        print(f"{name}  {out_w}x{out_h}  crop x={x}")


if __name__ == "__main__":
    main()
