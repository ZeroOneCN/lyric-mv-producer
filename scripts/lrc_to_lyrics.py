#!/usr/bin/env python3
"""Convert an LRC file to the lyrics.json used by the film and the SRT.

    python lrc_to_lyrics.py song.lrc -o lyrics.json --drop-first

The project timeline is the authority. If the LRC is rough, import the JSON into
a waveform editor, nudge each line, and export it again.
"""
import argparse
import json
import re
import sys
from pathlib import Path

TIME_RE = re.compile(r"\[(\d{1,3}):(\d{2})(?::(\d{2}))?(?:[.:](\d{1,3}))?\]")
CREDIT_RE = re.compile(
    r"^\s*(作词|作曲|编曲|词|曲|演唱|原唱|制作人|出品|监制|混音|母带|录音|"
    r"和声|吉他|贝斯|鼓|键盘|弦乐|OP|SP)\s*[:：]", re.I)


def read_text(path: Path) -> str:
    for enc in ("utf-8-sig", "gb18030", "big5"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    sys.exit(f"cannot decode {path} as UTF-8/GB18030/Big5")


def stamp(m: re.Match) -> float:
    a, b, c, frac = m.groups()
    if c is None:
        h, mm, ss = 0, int(a), int(b)
    else:
        h, mm, ss = int(a), int(b), int(c)
    sec = h * 3600 + mm * 60 + ss
    if frac:
        sec += int(frac) / (10 ** len(frac))
    return float(sec)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("lrc")
    ap.add_argument("-o", "--out", default="lyrics.json")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="seconds added to every timestamp (positive = later)")
    ap.add_argument("--min-dur", type=float, default=0.8)
    ap.add_argument("--max-dur", type=float, default=8.0)
    ap.add_argument("--gap", type=float, default=0.02,
                    help="silence kept before the next line")
    ap.add_argument("--drop-first", action="store_true",
                    help="drop the first cue, usually the song title")
    ap.add_argument("--keep-credits", action="store_true",
                    help="keep lines such as 作词：...")
    args = ap.parse_args()

    path = Path(args.lrc)
    if not path.exists():
        sys.exit(f"LRC not found: {path}")
    rows = []
    dropped = 0
    for raw in read_text(path).splitlines():
        stamps = [stamp(m) for m in TIME_RE.finditer(raw)]
        if not stamps:
            continue
        text = TIME_RE.sub("", raw).strip()
        if not text:
            continue
        if not args.keep_credits and CREDIT_RE.search(text):
            dropped += 1
            continue
        for t in stamps:
            rows.append((t + args.offset, text))
    rows.sort(key=lambda r: r[0])
    if args.drop_first and rows:
        rows = rows[1:]
    if not rows:
        sys.exit("no timed lyric lines found")

    cues = []
    warnings = 0
    for i, (t0, text) in enumerate(rows):
        t0 = max(0.0, t0)
        if i + 1 < len(rows):
            t1 = min(rows[i + 1][0] - args.gap, t0 + args.max_dur)
            if t1 < t0 + args.min_dur:
                t1 = max(t0 + 0.25, min(rows[i + 1][0] - 0.001, t0 + args.min_dur))
                warnings += 1
        else:
            t1 = t0 + max(args.min_dur, min(args.max_dur, 4.0))
        cues.append({"text": text, "t0": round(t0, 3), "t1": round(t1, 3)})

    for c in cues:
        if c["t1"] <= c["t0"]:
            sys.exit(f"bad cue duration at {c['t0']:.2f}s: {c['text']}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cues, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{out}: {len(cues)} cues, {cues[0]['t0']:.2f}-{cues[-1]['t1']:.2f}s, "
          f"dropped {dropped} credit lines, {warnings} tight gaps")
    if warnings:
        print("warn: some cues are shorter than --min-dur; check them against the waveform")


if __name__ == "__main__":
    main()
