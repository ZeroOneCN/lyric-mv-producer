#!/usr/bin/env python3
"""Create a ready-to-render lyric-MV project from the skill templates.

    python scaffold.py ../my-film --title "Paper Moon" --slug paper-moon --dur 180.0 \
        --song "song.mp3" --font "unifont.hex.gz"
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ASSETS = SKILL / "assets"
SCRIPTS = SKILL / "scripts"

ENGINE = ["px.js", "font.js"]
TOOLS = {
    "genfont.py": SCRIPTS / "genfont.py",
    "mix.py": ASSETS / "templates" / "mix.py",
    "make_srt.py": SCRIPTS / "make_srt.py",
    "make_covers.py": SCRIPTS / "make_covers.py",
    "master_audio.py": SCRIPTS / "master_audio.py",
    "check_delivery.py": SCRIPTS / "check_delivery.py",
}


def env_line(k: str, v: str) -> str:
    return f"{k}={json.dumps(v, ensure_ascii=False)}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dest")
    ap.add_argument("--title", default="MY LYRIC MV")
    ap.add_argument("--subtitle", default="A CODE-DRAWN FAN FILM")
    ap.add_argument("--slug", default=None)
    ap.add_argument("--dur", type=float, default=24.0)
    ap.add_argument("--poster-t", type=float, default=None)
    ap.add_argument("--song", default=None, help="audio file to copy into the project")
    ap.add_argument("--font", default=None, help="GNU Unifont .hex.gz to copy into fonts/")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    dest = Path(args.dest).resolve()
    slug = args.slug or re.sub(r"[^a-z0-9]+", "-", args.title.lower()).strip("-")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", slug):
        sys.exit("--slug must be letters, digits, dot, underscore or hyphen")
    if dest.exists() and any(dest.iterdir()) and not args.force:
        sys.exit(f"{dest} is not empty; pass --force to add/overwrite template files")

    for d in ("engine", "tools", "audio", "analysis", "stills", "out", "fonts"):
        (dest / d).mkdir(parents=True, exist_ok=True)

    for name in ENGINE:
        shutil.copy2(ASSETS / "engine" / name, dest / "engine" / name)
    shutil.copy2(ASSETS / "templates" / "main.js", dest / "engine" / "main.js")
    shutil.copy2(ASSETS / "templates" / "index.html", dest / "index.html")
    shutil.copy2(ASSETS / "templates" / "build.sh", dest / "build.sh")
    shutil.copy2(ASSETS / "templates" / "TREATMENT.md", dest / "TREATMENT.md")
    shutil.copy2(ASSETS / "templates" / "CREDITS", dest / "CREDITS")
    shutil.copy2(ASSETS / "templates" / "lyrics.example.json", dest / "lyrics.json")
    shutil.copy2(ASSETS / "templates" / "events.example.json", dest / "events.json")
    for name, src in TOOLS.items():
        shutil.copy2(src, dest / "tools" / name)

    song_name = "song.mp3"
    if args.song:
        src = Path(args.song).resolve()
        if not src.exists():
            sys.exit(f"song not found: {src}")
        song_name = src.name
        shutil.copy2(src, dest / song_name)
    if args.font:
        src = Path(args.font).resolve()
        if not src.exists():
            sys.exit(f"font not found: {src}")
        shutil.copy2(src, dest / "fonts" / "unifont.hex.gz")

    # a coda frame after the last lyric is the safest default for the poster
    poster = args.poster_t if args.poster_t is not None else round(max(0.0, args.dur - .3), 1)
    env = [
        "# One source of truth for build.sh and engine/main.js.",
        env_line("SLUG", slug),
        env_line("TITLE", args.title),
        env_line("SUBTITLE", args.subtitle),
        env_line("SONG", song_name),
        env_line("DUR", f"{args.dur:.3f}".rstrip("0").rstrip(".")),
        env_line("FPS", "24"),
        env_line("WIDTH", "1920"),
        env_line("HEIGHT", "1080"),
        env_line("POSTER_T", f"{poster:.3f}".rstrip("0").rstrip(".")),
        env_line("COVER_X", "0.5"),
    ]
    (dest / "project.env").write_text("\n".join(env) + "\n", encoding="utf-8")

    for name in ("TREATMENT.md", "CREDITS"):
        p = dest / name
        text = p.read_text(encoding="utf-8")
        text = (text.replace("{{TITLE}}", args.title).replace("{{SLUG}}", slug)
                .replace("{{DUR}}", f"{args.dur:.2f}".rstrip("0").rstrip(".")))
        p.write_text(text, encoding="utf-8")

    if (dest / "build.sh").exists():
        try:
            (dest / "build.sh").chmod(0o755)
        except OSError:
            pass

    print(f"created {dest}")
    print(f"  slug {slug}  duration {args.dur:.2f}s  song {song_name}")
    if not args.song:
        print("  put the supplied audio in the project and set SONG in project.env")
    if not args.font:
        print("  for Chinese lyrics, download GNU Unifont to fonts/unifont.hex.gz")
    print("  edit lyrics.json and events.json, then:")
    print("    LIB=/path/to/lemo-opuscar sh build.sh")


if __name__ == "__main__":
    main()
