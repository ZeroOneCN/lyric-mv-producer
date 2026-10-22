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

ENGINE = ["px.js", "font.js", "caption.js"]
TOOLS = {
    "genfont.py": SCRIPTS / "genfont.py",
    "mix.py": ASSETS / "templates" / "mix.py",
    "make_srt.py": SCRIPTS / "make_srt.py",
    "make_covers.py": SCRIPTS / "make_covers.py",
    "master_audio.py": SCRIPTS / "master_audio.py",
    "check_delivery.py": SCRIPTS / "check_delivery.py",
    "check_subs.js": SCRIPTS / "check_subs.js",
    "caption_segments.js": SCRIPTS / "caption_segments.js",
    "char_ref.py": SCRIPTS / "char_ref.py",
}


def env_line(k: str, v: str) -> str:
    return f"{k}={json.dumps(v, ensure_ascii=False)}"


def _fit_events(src: Path, dest: Path, dur: float) -> None:
    """Copy the example event map and fit it to this film, so a fresh project
    builds and passes QA before anyone has edited it."""
    doc = json.loads(src.read_text(encoding="utf-8"))
    doc["dur"] = round(dur, 3)

    def span(x):
        t0 = min(max(0.0, float(x["t0"])), dur)
        t1 = min(max(t0 + 0.1, float(x["t1"])), dur)
        x["t0"], x["t1"] = round(t0, 3), round(t1, 3)
        return t1 - t0 > 0.1

    doc["beds"] = [b for b in doc.get("beds", []) if span(b)]
    doc["ducks"] = [d for d in doc.get("ducks", []) if span(d) and d["t1"] - d["t0"] > 0.2]
    doc["ev"] = [e for e in doc.get("ev", []) if 0 <= float(e["t"]) < dur]
    dest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _fit_examples(src: Path, dest: Path, dur: float) -> None:
    cues = []
    for c in json.loads(src.read_text(encoding="utf-8")):
        t0, t1 = float(c["t0"]), min(float(c["t1"]), dur - 0.1)
        if t1 - t0 >= 0.4:
            cues.append({"text": c["text"], "t0": round(t0, 3), "t1": round(t1, 3)})
    dest.write_text(json.dumps(cues, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dest")
    ap.add_argument("--title", default="MY LYRIC MV")
    ap.add_argument("--subtitle", default="A CODE-DRAWN LYRIC FILM")
    ap.add_argument("--slug", default=None)
    ap.add_argument("--dur", type=float, default=24.0)
    ap.add_argument("--poster-t", type=float, default=None)
    ap.add_argument("--song", default=None, help="audio file to copy into the project")
    ap.add_argument("--font", default=None, help="GNU Unifont .hex.gz to copy into fonts/")
    ap.add_argument("--character", default=None,
                    help="character reference image to keep in character/ (private)")
    ap.add_argument("--sub-style", default="plate", choices=("plate", "bubble", "plain"),
                    help="fixed lyric caption style (default: plate)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    dest = Path(args.dest).resolve()
    slug = args.slug or re.sub(r"[^a-z0-9]+", "-", args.title.lower()).strip("-")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", slug):
        sys.exit("--slug must be letters, digits, dot, underscore or hyphen")
    if dest.exists() and any(dest.iterdir()) and not args.force:
        sys.exit(f"{dest} is not empty; pass --force to add/overwrite template files")

    for d in ("engine", "tools", "audio", "analysis", "stills", "out", "fonts", "character"):
        (dest / d).mkdir(parents=True, exist_ok=True)

    for name in ENGINE:
        shutil.copy2(ASSETS / "engine" / name, dest / "engine" / name)
    zh_table = dest / "engine" / "font_zh.js"
    if not zh_table.exists():
        sys.path.insert(0, str(SCRIPTS))
        from genfont import STUB as ZH_STUB   # same stub genfont.py writes
        zh_table.write_text(ZH_STUB, encoding="utf-8")
    shutil.copy2(ASSETS / "templates" / "main.js", dest / "engine" / "main.js")
    shutil.copy2(ASSETS / "templates" / "index.html", dest / "index.html")
    shutil.copy2(ASSETS / "templates" / "build.sh", dest / "build.sh")
    shutil.copy2(ASSETS / "templates" / "TREATMENT.md", dest / "TREATMENT.md")
    shutil.copy2(ASSETS / "templates" / "CREDITS", dest / "CREDITS")
    _fit_examples(ASSETS / "templates" / "lyrics.example.json", dest / "lyrics.json", args.dur)
    _fit_events(ASSETS / "templates" / "events.example.json", dest / "events.json", args.dur)
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

    char_ref = ""
    if args.character:
        src = Path(args.character).resolve()
        if not src.exists():
            sys.exit(f"character reference not found: {src}")
        slug_stem = re.sub(r"[^a-z0-9-]+", "-", src.stem.lower()).strip("-")
        stem = re.sub(r"^ref[-_]*", "", slug_stem) or slug_stem or "character"
        name = f"ref_{stem}{src.suffix.lower()}"
        img = dest / "character" / name
        shutil.copy2(src, img)
        char_ref = f"character/{name}"

    # a coda frame after the last lyric is the safest default for the poster
    cues = json.loads((dest / "lyrics.json").read_text(encoding="utf-8"))
    last = max([float(c["t1"]) for c in cues] or [0.0])
    poster = args.poster_t
    if poster is None:
        poster = round(min(max(args.dur - .3, last + .1), max(0.0, args.dur - .05)), 2)
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
        env_line("SUB_STYLE", args.sub_style),
        env_line("SUB_DENS", "0.45"),
        env_line("SUB_FADE", "0.18"),
        env_line("CHAR_REF", char_ref),
        env_line("CHAR_SHEET", ""),
    ]
    (dest / "project.env").write_text("\n".join(env) + "\n", encoding="utf-8")

    for name in ("TREATMENT.md", "CREDITS"):
        p = dest / name
        text = p.read_text(encoding="utf-8")
        text = (text.replace("{{TITLE}}", args.title).replace("{{SLUG}}", slug)
                .replace("{{DUR}}", f"{args.dur:.2f}".rstrip("0").rstrip("."))
                .replace("{{CHAR_REF}}", char_ref or "[no reference image used]"))
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
    if char_ref:
        print(f"  character reference kept at {char_ref} (private). Drafts:")
        print(f"    $PY tools/char_ref.py {char_ref} --project .")
    print("  edit lyrics.json and events.json, then:")
    print("    LIB=/path/to/lemo-opuscar sh build.sh")


if __name__ == "__main__":
    main()
