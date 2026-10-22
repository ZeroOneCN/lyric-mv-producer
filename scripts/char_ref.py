#!/usr/bin/env python3
"""Turn a character reference image into pixel sprite drafts for the film.

The reference is working material: it quantises to the film palette at several
sprite grids, writes ASCII row drafts you can paste into engine/main.js, and
reports the colours and proportions. It never produces art that ships - the
delivered sprite is still code-drawn from those rows.

    python char_ref.py ref.png --project ../my-film
    python char_ref.py ref.png --project ../my-film --grids 24x32,32x48 --colours 6

Run it with the renderer venv (`$LIB/.venv`) if pillow is not on your system
python; build.sh already picks that python up.
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("char_ref.py needs pillow: run it with the renderer venv python "
             "($LIB/.venv/bin/python) or `python -m pip install pillow`")

ALPHA = "abcdefghijklmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
DEFAULT_GRIDS = [(12, 16), (16, 24), (24, 32), (32, 48)]
BG_TOL = 26          # per-channel tolerance for auto background keying
COVER = 0.42         # sampled coverage above which a cell is ink


def parse_palette(px_js: Path):
    text = px_js.read_text(encoding="utf-8")
    block = re.search(r"const HEX = \[(.*?)\];", text, re.S)
    pal = [h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}", block.group(1))] if block else []
    names = {}
    cmap = re.search(r"export const C = \{(.*?)\};", text, re.S)
    if cmap:
        for name, idx in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(\d+)", cmap.group(1)):
            names.setdefault(int(idx), name)
    return pal, names


def rgb(h: str):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def dist2(a, b):
    return 0.3 * (a[0] - b[0]) ** 2 + 0.59 * (a[1] - b[1]) ** 2 + 0.11 * (a[2] - b[2]) ** 2


def nearest(c, choices, pal):
    best, bd = choices[0], float("inf")
    for i in choices:
        d = dist2(c, rgb(pal[i]))
        if d < bd:
            bd, best = d, i
    return best


def key_background(img):
    """Drop a flat border colour so the sprite is not a coloured box."""
    px = img.load()
    w, h = img.size
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    if any(c[3] < 200 for c in corners):
        return img, None
    ref = corners[0]
    if all(max(abs(a - b) for a, b in zip(ref, c)) <= BG_TOL for c in corners[1:]):
        out = img.copy()
        o = out.load()
        for y in range(h):
            for x in range(w):
                r, g, b, a = o[x, y]
                if max(abs(r - ref[0]), abs(g - ref[1]), abs(b - ref[2])) <= BG_TOL:
                    o[x, y] = (r, g, b, 0)
        return out, ref
    return img, None


def trim(img):
    box = img.getbbox()
    return img.crop(box) if box else img


def fit(img, tw, th):
    w, h = img.size
    s = min(tw / w, th / h)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))
    small = img.resize((nw, nh), Image.NEAREST)
    canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    canvas.paste(small, ((tw - nw) // 2, th - nh), small)   # feet on the bottom row
    return canvas


def quantise(img, pal, choices):
    w, h = img.size
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    src, dst = img.load(), out.load()
    counts = Counter()
    for y in range(h):
        for x in range(w):
            r, g, b, a = src[x, y]
            if a / 255 < COVER:
                continue
            idx = nearest((r, g, b), choices, pal)
            dst[x, y] = (*rgb(pal[idx]), 255)
            counts[idx] += 1
    return out, counts


def upscale(img, k, bg=(24, 20, 37, 255)):
    out = Image.new("RGBA", (img.width * k + 2 * k, img.height * k + 2 * k), bg)
    big = img.resize((img.width * k, img.height * k), Image.NEAREST)
    out.paste(big, (k, k), big)
    return out


def rows_text(spr, pal, char_of):
    src = spr.load()
    rgb_of = {rgb(h): i for i, h in enumerate(pal)}
    lines = []
    for y in range(spr.height):
        row = ""
        for x in range(spr.width):
            r, g, b, a = src[x, y]
            if a == 0:
                row += "."
            else:
                row += char_of[rgb_of[(r, g, b)]]
        lines.append(row)
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ref", help="character reference image (yours or cleared for use)")
    ap.add_argument("--project", required=True)
    ap.add_argument("--grids", default=None, help="e.g. 24x32,32x48")
    ap.add_argument("--colours", type=int, default=8, help="palette entries per sprite")
    ap.add_argument("--no-env", action="store_true", help="do not touch project.env")
    args = ap.parse_args()

    ref = Path(args.ref).resolve()
    proj = Path(args.project).resolve()
    px_js = proj / "engine" / "px.js"
    if not ref.exists():
        sys.exit(f"reference image not found: {ref}")
    if not px_js.exists():
        sys.exit(f"not a lyric-MV project (engine/px.js missing): {proj}")

    grids = DEFAULT_GRIDS
    if args.grids:
        grids = [tuple(int(v) for v in g.lower().split("x")) for g in args.grids.split(",")]
    pal, names = parse_palette(px_js)
    if len(pal) < 8:
        sys.exit(f"could not read the palette from {px_js}")

    out_dir = proj / "character"
    out_dir.mkdir(exist_ok=True)
    src = Image.open(ref).convert("RGBA")
    if ref.parent == out_dir:
        stored = ref                       # scaffold already kept it in the project
    else:
        slug_stem = re.sub(r"[^a-z0-9-]+", "-", ref.stem.lower()).strip("-")
        stem = re.sub(r"^ref[-_]*", "", slug_stem) or slug_stem or "character"
        stored = out_dir / f"ref_{stem}{ref.suffix.lower()}"
        src.save(stored)
    keyed, bg = key_background(src)
    body = trim(keyed)
    if body.width < 2 or body.height < 2:
        sys.exit("reference trims to nothing - is it a flat image?")

    full = list(range(len(pal)))
    _, wide_counts = quantise(fit(body, 96, 96), pal, full)
    picks = [i for i, _ in wide_counts.most_common(args.colours)]
    if len(picks) < 2:
        sys.exit("the reference has no readable colours")
    chars = {i: ALPHA[n] for n, i in enumerate(picks)}
    legend = "  ".join(f"{chars[i]}={pal[i]}" + (f" ({names[i]})" if i in names else "")
                       for i in picks)

    sheet = []
    for tw, th in grids:
        spr, counts = quantise(fit(body, tw, th), pal, picks)
        name = f"draft_{tw}x{th}.png"
        spr.save(out_dir / name)
        upscale(spr, 4).save(out_dir / f"draft_{tw}x{th}@4.png")
        rows = rows_text(spr, pal, chars)
        row_name = f"rows_{tw}x{th}.txt"
        js_map = ", ".join(f"'{chars[i]}': " + (f"C.{names[i]}" if i in names else str(i))
                           for i in picks)
        (out_dir / row_name).write_text(
            f"// {row_name} - derived from {stored.name} by tools/char_ref.py.\n"
            f"// grid {tw}x{th}, colours {len(counts)}, legend: {legend}\n"
            f"// '.' = transparent. Edit these rows into the film's own sprite; "
            f"this draft is a likeness study, not the delivered art.\n"
            f"const MAP = {{ {js_map} }};\n"
            f"const ROWS = [\n" + "\n".join(f"  '{r}'," for r in rows) + "\n];\n",
            encoding="utf-8")
        sheet.append((tw, th, len(counts), sum(counts.values()), name, row_name))

    _contact_sheet([out_dir / f"draft_{tw}x{th}@4.png" for tw, th in grids]
                   ).save(out_dir / "sheet.png")
    look = ["# Character lookbook", "",
            f"- reference: `{stored.name}` ({src.width}x{src.height}, "
            f"trimmed to {body.width}x{body.height}, background "
            f"{'keyed' if bg else 'kept'})",
            f"- silhouette aspect (w/h): {body.width / body.height:.3f}",
            f"- palette entries chosen: {len(picks)} -> {legend}",
            "", "| grid | ink px | colours | draft | rows |", "|---|---|---|---|---|"]
    for tw, th, ncol, ink, name, row_name in sheet:
        look.append(f"| {tw}x{th} | {ink} | {ncol} | `{name}` | `{row_name}` |")
    look += ["", "Pick the smallest grid whose silhouette still reads, copy its",
             "ROWS/MAP into `engine/main.js`, then simplify: a sprite is judged by",
             "outline, value separation and where the eye line sits (about 1/3 down).",
             "The reference and these drafts stay private working material.", ""]
    (out_dir / "lookbook.md").write_text("\n".join(look), encoding="utf-8")
    (out_dir / ".gitignore").write_text(
        "# Character reference material: working studies, never delivered.\n"
        "ref_*\ndraft_*.png\nrows_*.txt\nsheet.png\nlookbook.md\n", encoding="utf-8")

    if not args.no_env:
        env_path = proj / "project.env"
        text = env_path.read_text(encoding="utf-8")
        text = _set_env(text, "CHAR_REF", f"character/{stored.name}")
        text = _set_env(text, "CHAR_SHEET", f"character/draft_{grids[-1][0]}x{grids[-1][1]}@4.png")
        env_path.write_text(text, encoding="utf-8")

    print(f"character drafts written to {out_dir}")
    print(f"  reference kept as {stored.name} (private: character/.gitignore covers it)")
    for tw, th, ncol, ink, name, row_name in sheet:
        print(f"  {tw}x{th}: {ncol} colours, {ink} ink px -> {name}, {row_name}")
    print(f"  lookbook: character/lookbook.md   sheet: character/sheet.png")
    print("  next: paste one rows_*.txt into engine/main.js as CHAR.poses, then "
          "redraw it into an original sprite before the look stills")


def _contact_sheet(paths):
    pad, top = 8, 8
    ims = [Image.open(p) for p in paths]
    w = sum(i.width for i in ims) + pad * (len(ims) + 1)
    h = max(i.height for i in ims) + pad * 2 + top
    sheet = Image.new("RGBA", (w, h), (24, 20, 37, 255))
    x = pad
    for i in ims:
        sheet.paste(i, (x, pad + top), i)
        x += i.width + pad
    return sheet


def _set_env(text: str, key: str, value: str) -> str:
    line = f'{key}="{value}"'
    if re.search(rf"^{key}=", text, re.M):
        return re.sub(rf"^{key}=.*$", line, text, flags=re.M)
    return text.rstrip("\n") + "\n" + line + "\n"


if __name__ == "__main__":
    main()
