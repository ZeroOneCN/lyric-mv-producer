#!/usr/bin/env python3
"""Check a finished lyric MV package: files, picture, sound, subtitles, cues.

    python check_delivery.py /path/to/project --slug my-film \
        --ffmpeg /path/to/ffmpeg.exe

Exit code 0 = PASS, 1 = at least one FAIL. WARNs need a human decision.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

fails = []
warns = []


def report(kind: str, message: str) -> None:
    print(f"{kind:4s} {message}")
    if kind == "FAIL":
        fails.append(message)
    elif kind == "WARN":
        warns.append(message)


def run(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout)


def probe(ffmpeg: str, path: Path) -> dict:
    p = run([ffmpeg, "-hide_banner", "-i", str(path)])
    txt = p.stderr
    out = {"duration": None, "vcodec": None, "width": None, "height": None,
           "fps": None, "acodec": None, "sample_rate": None, "channels": None}
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", txt)
    if m:
        out["duration"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    vline = next((ln for ln in txt.splitlines() if "Stream" in ln and "Video:" in ln), "")
    if vline:
        m = re.search(r"Video:\s*([A-Za-z0-9_]+)", vline)
        out["vcodec"] = m.group(1) if m else None
        m = re.search(r"(\d{2,5})x(\d{2,5})", vline)
        if m:
            out["width"], out["height"] = int(m.group(1)), int(m.group(2))
        m = re.search(r"([\d.]+)\s*fps", vline)
        if m:
            out["fps"] = float(m.group(1))
    aline = next((ln for ln in txt.splitlines() if "Stream" in ln and "Audio:" in ln), "")
    if aline:
        m = re.search(r"Audio:\s*([A-Za-z0-9_]+)", aline)
        out["acodec"] = m.group(1) if m else None
        m = re.search(r"(\d+)\s*Hz", aline)
        if m:
            out["sample_rate"] = int(m.group(1))
        m = re.search(r"Hz,\s*([^,\n]+)", aline)
        if m:
            ch = m.group(1).strip().lower()
            out["channels"] = 2 if "stereo" in ch else 1 if "mono" in ch else None
    return out


def loudness(ffmpeg: str, path: Path) -> tuple[float, float]:
    p = run([ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
             "-af", "ebur128=peak=true", "-f", "null", "-"])
    if p.returncode != 0:
        return float("nan"), float("nan")
    ints = re.findall(r"I:\s*(-?[\d.]+|-inf)\s*LUFS", p.stderr)
    peaks = re.findall(r"Peak:\s*(-?[\d.]+|-inf)\s*dBFS", p.stderr)
    if not ints or not peaks:
        return float("nan"), float("nan")
    f = lambda s: float("-inf") if s == "-inf" else float(s)
    return f(ints[-1]), f(peaks[-1])


def black_segments(ffmpeg: str, path: Path) -> list[tuple[float, float]]:
    p = run([ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-map", "0:v:0",
             "-vf", "blackdetect=d=0.2:pix_th=0.02", "-an", "-f", "null", "-"])
    segs = []
    for line in p.stderr.splitlines():
        m = re.search(r"black_start:([\d.]+)", line)
        n = re.search(r"black_end:([\d.]+)", line)
        if m and n:
            segs.append((float(m.group(1)), float(n.group(1))))
    return segs


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", lines[1])
        if not m:
            continue
        g = [int(v) for v in m.groups()]
        t0 = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        t1 = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        cues.append((t0, t1, " ".join(lines[2:]).strip()))
    return cues


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=float, default=24.0)
    ap.add_argument("--lufs", type=float, default=-14.0)
    ap.add_argument("--tp", type=float, default=-1.2)
    ap.add_argument("--max-black", type=float, default=0.5)
    ap.add_argument("--skip-loudness", action="store_true")
    ap.add_argument("--skip-black", action="store_true")
    ap.add_argument("--node", default="node", help="node binary for the caption check")
    args = ap.parse_args()

    root = Path(args.project).resolve()
    video = root / f"{args.slug}.mp4"
    poster = root / "poster.jpg"
    srt = root / f"{args.slug}.srt"
    required = {
        video: 100_000,
        poster: 10_000,
        root / "cover_4x3.jpg": 10_000,
        root / "cover_3x4.jpg": 10_000,
        srt: 50,
        root / "TREATMENT.md": 800,
        root / "CREDITS": 100,
        root / "build.sh": 100,
        root / "lyrics.json": 20,
    }
    for path, min_size in required.items():
        if not path.exists():
            report("FAIL", f"missing {path.relative_to(root)}")
        elif path.stat().st_size < min_size:
            report("FAIL", f"{path.relative_to(root)} is too small ({path.stat().st_size} B)")
        else:
            report("PASS", f"file {path.relative_to(root)}")

    # Covers are their own compositions with the title set in, so the delivery
    # check verifies the provenance file make_covers.py wrote, not a crop.
    covers_file = root / "out" / "covers.json"
    try:
        env = dict(re.findall(r'^\s*([A-Z_]+)\s*=\s*"?([^"\n]*)"?', (root / "project.env").read_text(encoding="utf-8"), re.M))
    except OSError:
        env = {}
    title = env.get("TITLE", "").strip()
    if not covers_file.exists():
        report("FAIL", "out/covers.json missing: covers were not rendered by tools/make_covers.py; "
                       "a cover is a designed composition, not a crop of poster.jpg")
    else:
        try:
            cm = json.loads(covers_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            cm = None
            report("FAIL", f"out/covers.json is not JSON: {e}")
        if cm:
            if cm.get("mode") != "designed":
                report("FAIL", f"out/covers.json mode is {cm.get('mode')!r}, expected 'designed'")
            if not title:
                report("FAIL", "project.env has no TITLE; a cover must carry the song title")
            for name, want in (("cover_4x3.jpg", (1920, 1440)), ("cover_3x4.jpg", (1080, 1440))):
                shape = {v.get("file"): k for k, v in cm.get("covers", {}).items()}.get(name)
                entry = cm.get("covers", {}).get(shape or "", {})
                if not entry:
                    report("WARN", f"out/covers.json does not list {name}")
                    continue
                if entry.get("title") != title:
                    report("FAIL", f"{name} was drawn with title {entry.get('title')!r}, "
                                   f"but project.env says TITLE={title!r}")
                if tuple(entry.get("pixels", [])) != want:
                    report("FAIL", f"{name} claims {entry.get('pixels')}, expected {list(want)}")
                ci = probe(args.ffmpeg, root / name) if (root / name).exists() else {"width": 0, "height": 0}
                if (ci["width"], ci["height"]) != want:
                    report("FAIL", f"{name} is {ci['width']}x{ci['height']}, expected {want[0]}x{want[1]}")
                else:
                    report("PASS", f"{name} {want[0]}x{want[1]} grid {entry.get('grid')} title set in")
            if len({tuple(c.get("grid") or []) for c in cm.get("covers", {}).values()}) < 2:
                report("WARN", "both covers report the same grid: check --shapes")

    for name, ratio in (("poster.jpg", 16 / 9), ("cover_4x3.jpg", 4 / 3), ("cover_3x4.jpg", 3 / 4)):
        path = root / name
        if not path.exists():
            continue
        ci = probe(args.ffmpeg, path)
        cw, ch = ci["width"], ci["height"]
        if not cw or not ch:
            report("FAIL", f"{name} is not a readable image")
        elif abs(cw / ch - ratio) > 0.01:
            report("FAIL", f"{name} is {cw}x{ch}, not {ratio:.3f} aspect")
        elif min(cw, ch) < 720:
            report("FAIL", f"{name} is only {cw}x{ch}")
        else:
            report("PASS", f"{name} {cw}x{ch}")

    if not video.exists():
        print("\nRESULT FAIL: cannot inspect a missing film")
        sys.exit(1)
    info = probe(args.ffmpeg, video)
    if info["vcodec"] not in ("h264", "hevc"):
        report("FAIL", f"video codec is {info['vcodec']}, expected h264")
    elif (info["width"], info["height"]) != (args.width, args.height):
        report("FAIL", f"frame is {info['width']}x{info['height']}, expected {args.width}x{args.height}")
    elif info["fps"] is None or abs(info["fps"] - args.fps) > 0.01:
        report("FAIL", f"fps is {info['fps']}, expected {args.fps}")
    elif info["duration"] is None or info["duration"] < 1:
        report("FAIL", "video duration is unreadable")
    else:
        report("PASS", f"video {info['vcodec']} {info['width']}x{info['height']} "
                        f"{info['fps']:.3f} fps {info['duration']:.2f}s")
    if info["acodec"] != "aac" or info["sample_rate"] != 48000 or info["channels"] != 2:
        report("FAIL", f"audio is {info['acodec']} {info['sample_rate']} Hz "
                        f"{info['channels']}ch; expected AAC 48000 Hz stereo")
    else:
        report("PASS", "audio AAC 48000 Hz stereo")

    if not args.skip_loudness:
        i, tp = loudness(args.ffmpeg, video)
        if i != i or tp != tp:
            report("FAIL", "loudness could not be measured")
        elif abs(i - args.lufs) > 1.0:
            report("FAIL", f"integrated loudness {i:.1f} LUFS, target {args.lufs:.1f}")
        elif tp > args.tp + 0.3:
            report("FAIL", f"true peak {tp:.1f} dBTP, ceiling {args.tp:.1f}")
        else:
            report("PASS", f"loudness {i:.1f} LUFS / {tp:.1f} dBTP")

    if not args.skip_black:
        segs = black_segments(args.ffmpeg, video)
        long = [(a, b) for a, b in segs if b - a > args.max_black]
        short = [(a, b) for a, b in segs if 0.2 <= b - a <= args.max_black]
        if long:
            report("FAIL", "black segments: " + ", ".join(f"{a:.2f}-{b:.2f}s" for a, b in long))
        elif short:
            report("WARN", "short black segments: " + ", ".join(f"{a:.2f}-{b:.2f}s" for a, b in short))
        else:
            report("PASS", "no black segment >= 0.2s")

    if srt.exists():
        cues = parse_srt(srt)
        if not cues:
            report("FAIL", "SRT has no valid cues")
        else:
            bad = [i for i, (a, b, _) in enumerate(cues) if b <= a]
            overlaps = [i for i in range(1, len(cues)) if cues[i][0] < cues[i - 1][1] - 1e-6]
            last = cues[-1][1]
            if bad:
                report("FAIL", f"SRT cue {bad[0] + 1} ends before it starts")
            elif overlaps:
                report("FAIL", f"SRT cue {overlaps[0] + 1} overlaps the previous cue")
            elif info["duration"] and last > info["duration"] + 0.5:
                report("FAIL", f"SRT ends at {last:.2f}s, film ends at {info['duration']:.2f}s")
            else:
                report("PASS", f"SRT {len(cues)} cues, ends {last:.2f}s")
                longest = max(len(t) for _, _, t in cues)
                if longest > 48:
                    report("WARN", f"longest SRT line is {longest} characters; check readability")
                seg_path = root / "out" / "segments.json"
                if seg_path.exists():
                    try:
                        caps = json.loads(seg_path.read_text(encoding="utf-8"))["captions"]
                        drift = [k for k, (cap, (_, _, t)) in enumerate(zip(caps, cues))
                                 if str(cap["text"]).strip() != t.strip()]
                        if len(caps) != len(cues):
                            report("FAIL", f"SRT has {len(cues)} cues but the caption layer shows "
                                 f"{len(caps)} - regenerate the SRT from out/segments.json")
                        elif drift:
                            report("FAIL", f"SRT caption {drift[0] + 1} is not the burned-in caption")
                        else:
                            report("PASS", "SRT matches the burned-in single-line captions")
                    except (json.JSONDecodeError, KeyError) as e:
                        report("FAIL", f"out/segments.json is not caption_segments.js output: {e}")
                else:
                    report("WARN", "out/segments.json missing: the SRT was not checked against "
                                   "the captions the renderer draws")

    lyrics_path = root / "lyrics.json"
    if lyrics_path.exists():
        try:
            lyrics = json.loads(lyrics_path.read_text(encoding="utf-8"))
            bad = [c for c in lyrics if not (isinstance(c.get("t0"), (int, float))
                                             and isinstance(c.get("t1"), (int, float))
                                             and c["t1"] > c["t0"] and str(c.get("text", "")).strip())]
            if bad:
                report("FAIL", f"lyrics.json has {len(bad)} invalid cues")
            else:
                report("PASS", f"lyrics.json {len(lyrics)} cues")
                if any(ord(ch) >= 0x2E80 for c in lyrics for ch in str(c["text"])):
                    font = root / "engine" / "font_zh.js"
                    if not font.exists() or font.stat().st_size < 2000:
                        report("FAIL", "Chinese lyrics but engine/font_zh.js is missing or empty")
                    else:
                        report("PASS", "Chinese glyph table present")
        except (json.JSONDecodeError, AttributeError) as e:
            report("FAIL", f"lyrics.json is invalid: {e}")

    caption = root / "engine" / "caption.js"
    if not caption.exists():
        report("FAIL", "engine/caption.js missing: the film must use the fixed caption overlay")
    else:
        report("PASS", "file engine/caption.js")
        checker = root / "tools" / "check_subs.js"
        if not checker.exists():
            report("WARN", "tools/check_subs.js missing: the caption overlay was not re-checked")
        else:
            p = run([args.node, str(checker), str(root)])
            lines = (p.stdout + p.stderr).strip().splitlines()
            if p.returncode == 0:
                report("PASS", "caption overlay: " + (lines[-1] if lines else "ok"))
            else:
                for ln in lines:
                    if ln.startswith("FAIL"):
                        report("FAIL", f"caption overlay:{ln[4:]}")

    events_path = root / "events.json"
    if events_path.exists():
        try:
            ev = json.loads(events_path.read_text(encoding="utf-8"))
            if "dur" in ev and info["duration"] and abs(float(ev["dur"]) - info["duration"]) > 1.0:
                report("WARN", f"events.json dur {ev['dur']}s vs film {info['duration']:.2f}s")
            else:
                report("PASS", f"events.json {len(ev.get('ev', []))} cues")
        except (json.JSONDecodeError, ValueError) as e:
            report("FAIL", f"events.json is invalid: {e}")

    credits = (root / "CREDITS")
    if credits.exists():
        text = credits.read_text(encoding="utf-8", errors="replace").lower()
        if not re.search(r"music|音乐|song|歌曲", text):
            report("WARN", "CREDITS does not name the music")
        if not re.search(r"rights|版权|license|licence|许可", text):
            report("FAIL", "CREDITS has no rights / licence section")
        else:
            report("PASS", "CREDITS names music and rights")

    refs = sorted((root / "character").glob("ref_*")) if (root / "character").exists() else []
    if refs:
        if credits.exists() and not re.search(r"reference|参考", text):
            report("FAIL", f"CREDITS does not disclose the {len(refs)} character "
                           "reference image(s) kept in character/")
        elif credits.exists():
            report("PASS", f"character reference disclosed in CREDITS ({len(refs)} file(s))")
        report("PASS", "character/ holds working studies only: exclude it from the delivery")

    print(f"\nRESULT {'FAIL' if fails else 'PASS'}  "
          f"({len(fails)} fail, {len(warns)} warn)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
