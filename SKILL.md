---
name: lyric-mv-producer
description: Produce a finished code-drawn lyric music video from a user-supplied song and lyrics, end to end: analyze tempo and structure, sync LRC to a lyric timeline, scaffold a 320×180 indexed-pixel engine, write a treatment and shot list, synthesize foley, mix and master to −14 LUFS, render 1080p24, run QA, and deliver poster/SRT/credits. Use when asked to make a lyric MV, 音乐MV, 歌词视频, pixel or anime music film, or to turn a song plus lyrics into a finished video.
---

# Lyric MV Producer

A production pipeline and starter kit for a 2–4 minute lyric music video drawn
entirely in code: indexed-colour pixel art, frame-accurate lyric subtitles,
procedural sound design, and a one-command rebuild. The starter renders a
320×180 framebuffer at 6× nearest-neighbour to 1920×1080 / 24 fps.

The complete step-by-step procedure is in `references/sop.md`. Read it before
starting a new film. This file is the operating summary.

## Non-negotiables

1. **Rights gate first.** Use only audio the user supplies and has the right to
   use. The skill bundles no song, lyrics, character art, third-party fonts, or
   voice clips. Public release needs the user's own sync, master, lyric-reprint,
   and character licences.
2. **The song is the score.** Never add melody, re-arrange, or time-stretch it.
   Cut picture to the music. Sound work is ambience plus foley only.
3. **Code-drawn visuals.** No official character images, logos, screenshots,
   or third-party art. Fan characters are redrawn as original pixel sprites. A
   user-supplied reference image may seed that redraw through `char_ref.py`; the
   reference and its drafts never appear in the film and are disclosed in
   `CREDITS`.
4. **One house style.** The lyric caption is the fixed component in
   `engine/caption.js` (lane, width, line and character caps). Change the shot
   composition, never the caption geometry, to make room for it.
5. **No voice cloning.** A parametric timbre experiment is allowed only with
   disclosure and the user's own vocal; never imitate a real performer for
   promotion.
6. **One source of truth.** `project.env` drives duration, fps, size, song,
   poster time, cover crop focus, and caption style. `lyrics.json` drives both
   picture and SRT. `events.json` drives both picture accents and the mix.
7. **Deterministic output.** Same project → same frames and mix. No
   `Math.random`, no wall-clock time in `render(t)`.
8. **QA before delivery.** `check_delivery.py` must print `RESULT PASS`, and a
   human must watch the film end to end.

## Prerequisites

| Need | Detail |
|---|---|
| Song | The user's file (MP3/WAV/FLAC). Keep the original in the project. |
| Lyrics | LRC with timestamps preferred; plain text can be timed manually. |
| Node | 20+ for the Lemo-Opuscar renderer |
| ffmpeg | decode, loudness, mux, QA |
| Python | 3.11+ (or uv) with `numpy`, `scipy`, `soundfile` |
| Character reference | optional image for `char_ref.py`; also needs `pillow` |
| Renderer | [Lemo-Opuscar] library containing `core/render/video.mjs` |
| CJK font | `unifont.hex.gz` (GNU Unifont) only when lyrics contain Chinese |

`build.sh` finds the library at `$LIB`, `../lemo-opuscar`, or
`$HOME/lemo-opuscar`. Set `LIB` explicitly if it lives elsewhere.

If the renderer is missing, ask the user, then run `sh scripts/setup.sh` once.
It checks Node, ffmpeg and Python, installs Lemo-Opuscar into `~/lemo-opuscar`
(or `$LEMO_OPUSCAR_HOME`), and installs its npm packages, headless Chromium and
Python core tier. It does not install Node, ffmpeg, Python, or a system browser.
`sh scripts/setup.sh --check` only reports.

## Quick start

Set the skill path once (adjust if installed elsewhere):

```bash
SKILL="$HOME/.qoder-cn/skills/lyric-mv-producer"   # or ~/.qoder/skills/...
LIB="$HOME/lemo-opuscar"
```

1. **Scaffold** a project next to your working folder:

```bash
python "$SKILL/scripts/scaffold.py" ./my-film \
  --title "PAPER MOON" --slug paper-moon \
  --dur 180.0 --song "/path/to/song.mp3" \
  --font "/path/to/unifont.hex.gz" \
  --character "/path/to/hero-reference.png" --sub-style bar
```

   Omit `--font` for a Latin-only film, `--character` when every figure is an
   original design. The scaffold copies the engine (including `caption.js`),
   tools, templates, example lyrics/events, and writes `project.env`.

2. **Analyze the song** and confirm tempo/sections by ear:

```bash
python "$SKILL/scripts/analyze_song.py" "/path/to/song.mp3" \
  --ffmpeg "/path/to/ffmpeg" --json my-film/analysis/song.json
```

3. **Sync lyrics** from LRC, then check against the waveform:

```bash
python "$SKILL/scripts/lrc_to_lyrics.py" lyrics.lrc \
  -o my-film/lyrics.json --offset 0 --min-dur 1.2 --max-dur 8
```

4. **Write the treatment** in `my-film/TREATMENT.md`. Choose one structure,
   one character arc, three shot scales, and a colour script. Do not animate
   before the treatment exists.

5. **Draft the character** from the reference image, if the user supplied one:

```bash
cd my-film
"$PY" tools/char_ref.py character/ref_hero.png --project .   # needs pillow
```

   It writes palette-quantised drafts at four grids, `rows_WxH.txt` (ASCII rows
   for `sprFromRows`), and `character/lookbook.md`. Paste the smallest readable
   grid into `engine/main.js`, then redraw it into an original sprite. The
   reference and the drafts stay in `character/` and are never delivered.

6. **Prove the look** with stills before the full render:

```bash
cd my-film
node "$LIB/core/render/still.mjs" . 1.2 10.5 43.0 87.5 178.0 --prefix look_
```

   Iterate on `engine/main.js` until the stills read. See
   `references/pixel-engine.md`.

7. **Build**:

```bash
LIB="$LIB" sh build.sh
```

   The build checks every cue against the fixed caption lane, then writes the
   film, the 16:9 poster, and both the 4:3 and 3:4 covers.

8. **QA and deliver**:

```bash
python tools/check_delivery.py . --slug paper-moon --ffmpeg "/path/to/ffmpeg"
```

   Then watch the whole film. See `references/qa.md`.

## Pipeline and gates

| Stage | Do | Gate to pass |
|---|---|---|
| 0. Intake | collect song, lyrics, optional character reference image, deadline; confirm rights | user owns/has cleared the audio, lyrics and any reference image; release is non-commercial unless licensed |
| 1. Analyze | tempo, duration, energy map, quiet spans, section boundaries | BPM and section map confirmed by ear, not only by script |
| 2. Lyrics | LRC → `lyrics.json`; drop credits; fix offsets and long lines | every cue t1 > t0, no overlap, last cue before coda, `tools/check_subs.js` prints `RESULT PASS` |
| 3. Treatment | structure, character, visual rules, sound rules, timeline table | one page that a stranger could shoot from; rights paragraph included |
| 4. Look | scaffold, palette, sprite (from `char_ref` drafts, redrawn), 5–8 stills, poster crops | silhouette, values, caption inside the lane, likeness pass; subject survives 4:3 and 3:4 crops |
| 5. Sound | beds, ducks, event map, mix, master | active RMS −20; master −14 LUFS / ≤ −1.2 dBTP |
| 6. Render | 1080p24, 3 workers, mux AAC | frame count = round(DUR × FPS); no dropped sections |
| 7. QA | contact sheet, cut strips, full watch, mechanical checks | `RESULT PASS`; zero unintentional black frames |
| 8. Deliver | mp4, three posters, SRT, treatment, credits, JSON, build | manifest complete incl. 4:3 and 3:4 covers; rights paragraph present |

## Project contract

```
my-film/
├── project.env          # ... POSTER_T COVER_X SUB_STYLE CHAR_REF (cover crop focus 0–1)
├── poster.jpg           # 16:9 cover from POSTER_T
├── poster_4x3.jpg       # 4:3 cover derived from poster.jpg
├── poster_3x4.jpg       # 3:4 cover derived from poster.jpg
├── lyrics.json          # [{ "text", "t0", "t1" }]
├── events.json          # { dur, bpm, beds, ducks, ev }
├── TREATMENT.md
├── CREDITS
├── build.sh
├── index.html           # 1920×1080 canvas
├── engine/
│   ├── px.js            # 320×180 framebuffer, palette, LUTs, lane geometry
│   ├── font.js          # 5×7 variable-width Latin font
│   ├── font_zh.js       # generated CJK subset
│   ├── caption.js       # the fixed lyric caption (bar | bubble | plain)
│   └── main.js          # shots, HUD, character sprites, page contract
├── character/           # private: ref_*, drafts, rows, lookbook (gitignored)
├── tools/
│   ├── genfont.py
│   ├── char_ref.py
│   ├── check_subs.js
│   ├── mix.py
│   ├── master_audio.py
│   ├── make_srt.py
│   ├── make_covers.py
│   └── check_delivery.py
├── audio/               # song.wav, mix.wav, master.wav
├── analysis/
├── stills/
└── out/
```

The page exposes:

```js
window.DUR      // seconds
window.SUBS     // [{ t0, t1, text }]
window.EV       // [{ t, k }]
window.render   // render(t): deterministic, synchronous
window.READY    // true after assets load
```

`render(t)` must be pure and stateless. All drawing happens on a 320×180
palette-index framebuffer; `out.present()` maps indices through a LUT and
`out.show()` scales 6× with smoothing disabled.

## Lyrics and the fixed caption

The caption is a component, not a per-film design decision. `engine/caption.js`
draws every cue through the same geometry, declared once in `engine/px.js`:

- Lane `y 142–176`, full width; text max 286 px, max 2 lines, 10 CJK characters
  per line, punctuation pulled off the line head.
- 1 px ink outline; `SUB_STYLE` = `bar` (dithered lane, default) | `bubble` | `plain`.
- Fade-in only (`SUB_FADE`, default 0.18 s). No lift, no typewriter, no per-shot restyling.
- The lane is reserved: while a cue is on screen, no face, hand or key prop below
  row 142. `main.js` gives `hasCaption(t)` and `drawChar()` clamps to the lane.
- One cue per sung line. If a cue needs a third line, split the lyric in
  `lyrics.json`; never widen or move the lane.
- Latin uses `font.js`; CJK uses the baked Unifont subset. Never mix the two
  renderers in one cue.
- `build.sh` runs `tools/check_subs.js` before rendering; it imports the same
  module, so a cue that fails the check cannot reach the picture.

Generate SRT from `lyrics.json`, never independently:

```bash
python tools/make_srt.py . --out paper-moon.srt
node tools/check_subs.js .
```

`genfont.py` scans all text sources before every build. If a glyph is missing,
the build fails — add the character or the font, do not ship boxes.

## Character from a reference image

Ask once whether the user has a reference image for the lead. If they do:

```bash
cd my-film && "$PY" tools/char_ref.py character/ref_hero.png --project .
```

The tool keys a flat background, trims, quantises into the film's own palette
(top 8 entries) and writes drafts at 12×16 / 16×24 / 24×32 / 32×48 plus
`rows_WxH.txt` (ASCII rows + `C.*` map for `sprFromRows`) and `lookbook.md`.
Choose the smallest grid whose silhouette still reads, paste it into
`engine/main.js`, then redraw: fewer colours, eye line near the top third, one
identifying detail that survives 16 px.

The reference and every draft stay in `character/` (gitignored, private). The
film ships only the code-drawn sprite. `CREDITS` must disclose that a reference
image was used, and `check_delivery.py` fails if `character/ref_*` exists while
`CREDITS` says nothing about it.

## Sound defaults

- Active song RMS −20 dBFS.
- Beds: sea/room −45, rain/wind −38 to −40 dBFS.
- Foley: UI −34, paper/steps −32, whoosh/riser −24 peak, impact −18 peak.
- Duck the song only for motivated moments, with 80 ms edges.
- Master −14 LUFS integrated, true peak ≤ −1.2 dBTP, AAC 256k / 48 kHz stereo.
- Keep 0.6 s of tail; `-shortest` is safe only when master covers `DUR`.

Details and failure modes: `references/audio.md`.

## QA minimum

1. 5–8 look stills inspected at 100%.
2. Contact sheet every 10 s; scan for black/frozen/repeated frames.
3. 2 s strips around every major cut; no one-frame flashes or text pops.
4. One full watch with sound; one pass checking sync and readability.
5. Caption lane: `node tools/check_subs.js .` prints `RESULT PASS`, and no shot
   puts a face, hand or key prop under row 142 while a cue is on screen.
6. `check_delivery.py` → `RESULT PASS (0 fail, 0 warn)`.
7. Last frame checked for subtitles and safe margins; all three covers checked
   at 100%, especially that the 3:4 crop keeps the face and any title.

Details: `references/qa.md`.

## Delivery

- `<slug>.mp4` — 1920×1080, 24 fps, AAC 48 kHz stereo
- `poster.jpg` — 16:9, from a coda/wide frame without subtitle collision
- `poster_4x3.jpg` — 4:3 landscape cover, 1920×1440
- `poster_3x4.jpg` — 3:4 portrait cover, 1080×1440
- `<slug>.srt` — same timings as `lyrics.json`
- `TREATMENT.md`, `CREDITS`, `lyrics.json`, `events.json`, `project.env`
- `build.sh` plus `engine/`, `tools/`, `audio/master.wav`
- `analysis/song.json` when produced

All three covers come from one `POSTER_T` frame. `make_covers.py` reduces the
poster to the 320×180 grid, crops, then upscales with nearest-neighbour:
4:3 keeps the centre 240 px of 320, 3:4 keeps 135 px (42%). `COVER_X` in
`project.env` moves that window (0 = left, 1 = right). Compose the poster shot
so the subject stays inside the centre band; if it does not, change `POSTER_T`
or the shot itself, do not ship a crop that cuts the face or an on-screen title.

Do not deliver `out/video.mp4` (silent). Do not deliver a project whose
`CREDITS` lacks the rights section. Do not deliver `character/` — the reference
image and its drafts are private working material.

## Rights

The user must hold or clear all rights. Write the actual rights holders,
permission scope, and source of every asset into `CREDITS` and the treatment.
Never copy a notice from another production.

A generic starting point (replace every bracket):

> [Song title] — words and music by [writers], performed by [artist], recording
> owned by [label]. Used with permission for [scope]. [Character name] is owned
> by [rights holder]; this is an unofficial fan work, not endorsed by [rights
> holder]. No official artwork, logos, fonts, footage, or voice clips were used.
> Public release requires the user's own sync, master, lyric-reprint, and
> character licences.

If all characters and artwork are original, say so instead of the fan-work
sentence. See `references/rights.md` for the gate table, a Chinese template,
and the CREDITS rules.

## Troubleshooting

| Symptom | Fix |
|---|---|
| renderer missing or `build.sh: bad LIB` | run `sh scripts/setup.sh`; it installs Lemo-Opuscar and its packages |
| renderer says ffmpeg not found | pass an absolute `FF=`; `build.sh` converts Windows paths to POSIX before prepending to PATH |
| stills show fonts as boxes | rerun `tools/genfont.py .`, then `genfont.py . --check` |
| renderer 404s on `/@film/engine/font_zh.js` | the scaffold writes a stub there; rerun `scaffold.py --force` or `tools/genfont.py .` |
| `check_subs.js` FAIL: does not fit the lane | split or shorten the cue in `lyrics.json`; the lane is fixed by design |
| caption sits on the subject | move the subject above row 142 for that shot, or cut the cue earlier |
| `char_ref.py: could not read the palette` | the project's `engine/px.js` was replaced; keep `const HEX = [...]` |
| `char_ref.py` says it needs pillow | run it with the renderer venv: `$LIB/.venv/bin/python` |
| render fails on `fetch` | serve through the Lemo renderer; ES modules cannot load over `file://` |
| subtitles drift late/early | fix `--offset`, regenerate `lyrics.json` and SRT |
| audio ends early | ensure `mix.py` pads to `DUR`; check `-shortest` and master length |
| poster has a lyric across it | set `POSTER_T` in the coda, typically `DUR - 0.3` |
| 3:4 cover cuts the subject | move `COVER_X`, pick another `POSTER_T`, or reframe the coda shot so the subject sits in the centre 42% |
| loudness passes but TP fails after AAC | lower `alimiter` limit to 0.80 and re-encode |

## Resources

| Path | Contents |
|---|---|
| `references/sop.md` | full SOP, stage gates, timeline, delivery manifest |
| `references/pixel-engine.md` | framebuffer, palette/LUT, drawing, text, shot craft |
| `references/audio.md` | analysis, lyric sync, event map, levels, master, failure modes |
| `references/qa.md` | QA passes, exact commands, manifest, sign-off |
| `references/rights.md` | rights gate, CREDITS rules, verbatim paragraph |
| `assets/engine/` | `px.js`, `font.js`, `caption.js` |
| `assets/templates/` | `main.js`, `index.html`, `project.env`, `build.sh`, `TREATMENT.md`, `CREDITS`, example JSON, `mix.py` |
| `scripts/scaffold.py` | create a project from the templates |
| `scripts/setup.sh` | check the toolchain; install Lemo-Opuscar and its packages |
| `scripts/analyze_song.py` | duration, BPM candidates, energy profile |
| `scripts/lrc_to_lyrics.py` | LRC → `lyrics.json` |
| `scripts/genfont.py` | bake/check the CJK subset |
| `scripts/char_ref.py` | character reference image → palette-quantised sprite drafts + ASCII rows |
| `scripts/check_subs.js` | prove every cue fits the fixed caption lane |
| `scripts/make_srt.py` | `lyrics.json` → SRT |
| `scripts/make_covers.py` | `poster.jpg` → 4:3 and 3:4 covers |
| `scripts/master_audio.py` | two-pass loudnorm + limiter + verification |
| `scripts/check_delivery.py` | mechanical delivery gate |
| `scripts/formant_shift.py` | optional F0-preserving formant shift for a disclosed character timbre |

Attribution: the pixel engine is adapted from Lemo-Opuscar's `pixel-rpg` demo
(MIT); the palette begins with ENDESGA-32 (credit ENDESGA); CJK glyphs come
from GNU Unifont (GPL + font exception). Keep these credits in `CREDITS`.
Full licence texts are in `THIRD_PARTY_NOTICES`.
