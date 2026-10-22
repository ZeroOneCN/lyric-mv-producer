#!/usr/bin/env python3
"""Render the designed 4:3 and 3:4 covers for a lyric-MV project.

    python tools/make_covers.py . --lib /path/to/lemo-opuscar --ffmpeg ffmpeg

A cover is its own composition on its own pixel grid with the song title set
into it. It is never a crop of poster.jpg: the page draws it when asked with
`?cover=<shape>`, on the same grid the film uses (1 cell = 1 picture pixel):

    4x3   240x180 -> 1920x1440
    3x4   135x180 -> 1080x1440
    16x9  320x180 -> 1920x1080   (only with --shapes)

Each cover is rendered twice: once finished, once with `bare=1`, which leaves
the type layer off. The two files must differ, otherwise the title was never
drawn. Deliverables land as cover_4x3.jpg / cover_3x4.jpg and the proof of
where they came from goes to out/covers.json for check_delivery.py.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# engine/px.js COVER_SHAPES is the law; these numbers are checked against it by
# probing the rendered file, so a mismatch fails loudly instead of shipping skew.
SHAPES = {
    "4x3": (240, 180, 8, 1920, 1440),
    "3x4": (135, 180, 8, 1080, 1440),
    "16x9": (320, 180, 6, 1920, 1080),
}


def env_map(project: Path) -> dict:
    txt = (project / "project.env").read_text(encoding="utf-8", errors="replace")
    out = {}
    for line in txt.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def image_size(ffmpeg: str, path: Path):
    p = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", p.stderr)
    return (int(m.group(1)), int(m.group(2))) if m else None


def render(project: Path, lib: Path, node: str, shape: str, q_extra: str, prefix: str) -> Path:
    out_dir = project / "stills" / "covers"
    out_dir.mkdir(parents=True, exist_ok=True)
    gw, gh, sc, w, h = SHAPES[shape]
    cmd = [node, str(lib / "core" / "render" / "still.mjs"), str(project), "0",
           "--q", f"cover={shape}{q_extra}", "--size", f"{w}x{h}",
           "--prefix", prefix, "--out", str(out_dir)]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        sys.exit(f"make_covers: renderer failed for {shape}\n{p.stdout}\n{p.stderr}")
    still = out_dir / f"{prefix}0.jpg"
    if not still.exists():
        hits = sorted(out_dir.glob(f"{prefix}*.jpg"), key=lambda p: p.stat().st_mtime)
        if not hits:
            sys.exit(f"make_covers: no still produced for {shape} in {out_dir}")
        still = hits[-1]
    return still


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?", default=".")
    ap.add_argument("--lib", required=True, help="Lemo-Opuscar library (holds core/render/still.mjs)")
    ap.add_argument("--node", default="node")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--shapes", default="4x3,3x4", help="comma separated: 4x3,3x4,16x9")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    lib = Path(args.lib).resolve()
    if not (lib / "core" / "render" / "still.mjs").exists():
        sys.exit(f"make_covers: bad --lib: {lib} has no core/render/still.mjs")
    if not (project / "project.env").exists():
        sys.exit(f"make_covers: project.env missing in {project}")

    env = env_map(project)
    title = env.get("TITLE", "").strip()
    if not title:
        sys.exit("make_covers: TITLE is empty; a cover must carry the song title")

    wanted = [s.strip() for s in args.shapes.split(",") if s.strip()]
    bad = [s for s in wanted if s not in SHAPES]
    if bad:
        sys.exit(f"make_covers: unknown shape(s) {bad}; pick from {sorted(SHAPES)}")

    manifest = {"mode": "designed", "title": title,
                "artist": env.get("COVER_ARTIST", ""), "tagline": env.get("COVER_TAGLINE", ""),
                "typeMode": env.get("COVER_TYPE", "band"), "covers": {}}
    for shape in wanted:
        gw, gh, sc, w, h = SHAPES[shape]
        full = render(project, lib, args.node, shape, "", f"cover_{shape}_")
        bare = render(project, lib, args.node, shape, "&bare=1", f"cover_{shape}_bare_")
        size = image_size(args.ffmpeg, full)
        if size != (w, h):
            sys.exit(f"make_covers: cover {shape} came out {size}, expected {(w, h)}; "
                     "engine/px.js COVER_SHAPES and this tool disagree")
        if full.read_bytes() == bare.read_bytes():
            sys.exit(f"make_covers: cover {shape} is identical without its type layer, "
                     f"so the title was not drawn (check engine/cover.js and TITLE={title!r})")
        bare.unlink()
        dest = project / f"cover_{shape}.jpg"
        shutil.copyfile(full, dest)
        manifest["covers"][shape] = {
            "file": dest.name, "grid": [gw, gh], "pixels": [w, h],
            "title": title, "source": "engine/cover.js",
        }
        print(f"cover_{shape}.jpg  {w}x{h}  grid {gw}x{gh}  title {title!r}")

    (project / "out").mkdir(exist_ok=True)
    (project / "out" / "covers.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
