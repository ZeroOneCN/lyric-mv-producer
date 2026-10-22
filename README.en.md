# Lyric MV Producer

[简体中文](README.md) | **English**

An agent skill that produces a finished lyric music video from a song you own
and its lyrics — entirely in code. It covers the whole pipeline: tempo and
structure analysis, LRC-to-lyric sync, a 320×180 indexed-pixel engine, a written
treatment and shot list, procedural foley, mix and master to −14 LUFS, a
1080p24 render, QA, and delivery (MP4, poster, designed 4:3/3:4 covers, SRT, credits).

No stock footage, no image generators, no official artwork. Every frame is drawn
into a small palette-index framebuffer and scaled 6× with nearest-neighbour, so
the film stays deterministic: the same project always renders the same frames
and the same mix.

## Visual style

Every film is a code-drawn pixel lyric film, not a slideshow over the song:

- 320×180 indexed-colour framebuffer, 6× nearest-neighbour to 1080p24, integer coordinates only.
- One palette per film, at most ~40 colours, starting from ENDESGA-32; no large pure-black areas.
- Three shot scales: wide (figure 16–40 px tall), medium (60–90 px), close (100–150 px, kept for choruses and the ending).
- Characters are original pixel sprites; fan characters are redrawn rather than ripped. No image generators, stock art, or logos.
- You may supply one character reference image. The script quantises it into 12×16 / 16×24 / 24×32 / 32×48 drafts in the film's palette, plus pasteable ASCII rows, to settle silhouette, colours and head-to-body ratio. The reference and the drafts stay in the project's `character/`; the delivered sprite is still redrawn in code.
- The lyric caption is one fixed house style, not a per-film design decision: an **overlay layer** drawn on top of the content picture (640×360, twice the 320×180 grid). The picture keeps the whole frame; nothing is carved out for captions. One cue shows **one line**, up to 560 layer px wide and 32 CJK characters, 16 layer px tall — 48 px at 1080p. A sung line too long for one caption is split into successive single-line captions, timed by character count with a 0.9 s floor. The backing is a small Bayer-dithered ink plate sized to the text and centred with it (`bubble` and `plain` are the only switches); it never spans the frame and never reserves dead space in the composition. The layer shares the picture's colour lookup table, so fades and palette collapse act on the caption too, while RGB `post()` effects such as mosaic stay underneath it.
- Cuts land on beats or lyric onsets; dissolves are rationed; the HUD stays quiet.
- Each film gets its own treatment, palette, character, and structure; the engine is a canvas, not a fixed preset — the caption overlay is the one hard-coded rule.

## What you get

- `song.mp4` — 1920×1080, 24 fps, H.264, AAC 48 kHz stereo, −14 LUFS
- `poster.jpg` — 16:9 still from the coda
- `cover_4x3.jpg` — 1920×1440 landscape cover, designed on its own 240×180 grid
- `cover_3x4.jpg` — 1080×1440 portrait cover, designed on its own 135×180 grid
- `song.srt` — generated from the same caption segments the film burns in
- `TREATMENT.md`, `CREDITS`, `lyrics.json`, `events.json`, `project.env`
- `build.sh` — one command from decode to finished film

Only `poster.jpg` comes from the `POSTER_T` frame. The 4:3 and 3:4 covers are
not crops of it: each is its own composition on its own pixel grid (4:3 is
240×180, 3:4 is 135×180, the same cell size as the film so sprites keep their
relative scale), upscaled 8× with nearest-neighbour. `engine/cover.js` fixes the
layout law: the film's motif (`coverMotif()` in `engine/main.js`, positioned
against the art box, never hardcoded to 320×180) on top, a dithered type band
across the bottom that always carries the song title (plus optional artist and
tagline), and corner ticks. `COVER_TYPE` switches between `band` (art stops
above the title) and `overlay` (art bleeds full, the title sits on a plate).
`make_covers.py` renders each cover twice — finished and `bare=1` (no type
layer) — and fails the build if the two are identical, which proves the title
was really drawn rather than shipping a blank cover.

## Requirements

| Need | Detail |
|---|---|
| Song | Your own audio file (MP3/WAV/FLAC) |
| Lyrics | LRC with timestamps, or plain text timed manually |
| Node.js | 20+ |
| ffmpeg | Decode, loudness, mux, QA |
| Python | 3.11+ (or uv) with `numpy`, `scipy`, `soundfile`; sprite drafts from a reference image also need `pip install pillow` |
| Browser | Playwright's Chromium headless, installed by `setup.sh` |
| Renderer | [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) with `core/render/video.mjs` |
| CJK font | [GNU Unifont](https://unifoundry.com/unifont/) `.hex.gz`, only for Chinese/Japanese/Korean lyrics |

## Install

The skill has no install hook. Clone it, then run `setup.sh` once; that command
installs Lemo-Opuscar along with the skill.

```bash
# 1. Install the skill where your agent looks for skills.
git clone https://github.com/ZeroOneCN/lyric-mv-producer.git \
  ~/.qoder-cn/skills/lyric-mv-producer
# Claude Code uses ~/.claude/skills/lyric-mv-producer instead.

# 2. One-time setup: check the toolchain, install Lemo-Opuscar and its packages.
sh ~/.qoder-cn/skills/lyric-mv-producer/scripts/setup.sh
```

`setup.sh` checks **Node 20+, ffmpeg, Python 3.11+ (or uv)**, clones Lemo-Opuscar
to `~/lemo-opuscar`, then installs its npm packages, headless Chromium and Python
core tier. It does not install Node, ffmpeg, Python, or a system browser; it
reports anything missing.

- `sh scripts/setup.sh --check` — report only, change nothing
- `sh scripts/setup.sh --lib DIR` or `LEMO_OPUSCAR_HOME=DIR` — install elsewhere
- An existing Lemo library is reused; its packages are installed or updated
- Start a new session or run `/skills reload` afterwards
- `build.sh` prefers `$LIB/.venv`; override with `PY=`

For Chinese, Japanese, or Korean lyrics, download a GNU Unifont `.hex.gz` from
<https://unifoundry.com/unifont/> and pass it with `--font` when scaffolding, or
drop it at `fonts/unifont.hex.gz` inside the project. Latin-only films do not
need it.

## Use it

Put the song and its lyrics in one folder. Nothing else is required:

```
my-song/
├── song.mp3
├── song.lrc
└── hero.png        optional character reference
```

Install it, then say:

> 用 lyric-mv-producer 做一支 MV。

> Make a lyric MV with lyric-mv-producer.

If the audio and LRC are not in the current folder, add the path:

> 用 lyric-mv-producer 做一支 MV，歌曲和歌词在 ./my-song。

> Make a lyric MV with lyric-mv-producer; the song and lyrics are in ./my-song.

Slash commands work too: `/lyric-mv-producer`.

The agent reads the skill, asks once for anything it cannot find (the audio and
LRC, title, tone, the one image you want to remember, whether there is a
character reference, rights, whether you want to review a storyboard), then runs
the pipeline. The project and all deliverables are written to a new folder
inside the working folder.

Add specifics to the same sentence when they matter:

> 用 lyric-mv-producer 把 ./my-song 做成像素风 MV，片名《纸月亮》，主色蓝金，
> 副歌要一次大远景；4:3 和 3:4 封面按本片风格单独设计，歌名放进文字带。

> Make a pixel MV from ./my-song called "Paper Moon", base the protagonist on
> ./my-song/hero.png, blue and gold, one extreme wide shot at the chorus; design
> the 4:3 and 3:4 covers for this film and set the song title into their band.

You never have to ask for a caption style: one house style is fixed for every
film — a single line drawn on the overlay layer above the picture, up to 32 CJK
characters, on a dithered plate that hugs the text. To change the feel, say
`SUB_STYLE=bubble` or `plain`.

It is not a one-click app. `setup.sh` installs Lemo-Opuscar and its packages,
but Node, Python, ffmpeg, and a browser must already be on the machine, and a
full-length film takes tens of minutes to render on a typical laptop. Once those
are in place, that sentence is the whole interface; the commands below are what
the agent runs, kept here for inspection or a manual rerun.

## Quick start (manual)

```bash
SKILL="$HOME/.qoder-cn/skills/lyric-mv-producer"
LIB="$HOME/lemo-opuscar"

# 1. Scaffold a project (pass --character when you have a reference image)
python "$SKILL/scripts/scaffold.py" ./my-film \
  --title "PAPER MOON" --slug paper-moon \
  --dur 180.0 --song "/path/to/song.mp3" \
  --font "/path/to/unifont.hex.gz" \
  --character "/path/to/hero.png" --sub-style plate

# 2. Analyze tempo and sections, then confirm by ear
python "$SKILL/scripts/analyze_song.py" "/path/to/song.mp3" \
  --ffmpeg ffmpeg --json my-film/analysis/song.json

# 3. Sync LRC to the cue table
python "$SKILL/scripts/lrc_to_lyrics.py" lyrics.lrc \
  -o my-film/lyrics.json --offset 0 --min-dur 1.2 --max-dur 8

# 4. Reference image -> sprite drafts (sheet.png + rows_*.txt)
cd my-film
python tools/char_ref.py character/ref_hero.png --project .

# 5. Caption overlay check: one line per caption, out-of-geometry cues fail
node tools/check_subs.js .

# 6. Write the treatment, then prove the look with stills
node "$LIB/core/render/still.mjs" . 1.2 10.5 43.0 87.5 178.0 --prefix look_

# 7. Build and check (build.sh emits out/segments.json first, so the SRT and the
#    burned-in captions come from the same single-line segments)
LIB="$LIB" sh build.sh
python tools/check_delivery.py . --slug paper-moon --ffmpeg ffmpeg
```

Step 5 also runs inside `build.sh`; running it by hand just surfaces problems
before the render. Step 4 is done once, when the reference arrives — you paste
one rows file into `engine/main.js` and redraw it into an original sprite.
`character/` holds private working material and is never part of the delivery.

`check_delivery.py` must print `RESULT PASS`, and you should still watch the
film end to end. Stills, contact sheet, cut strips, sync and sound checks are
described in `references/qa.md`.

## Project layout

```
my-film/
├── project.env          # SLUG TITLE SONG DUR FPS POSTER_T COVER_SHAPES COVER_TYPE COVER_ARTIST SUB_STYLE CHAR_REF
├── lyrics.json          # [{ "text", "t0", "t1" }]
├── events.json          # { dur, bpm, beds, ducks, ev }
├── TREATMENT.md
├── CREDITS
├── build.sh
├── index.html
├── engine/              # px.js, font.js, caption.js, cover.js, font_zh.js, main.js
├── character/           # reference + pixel drafts (working material, not shipped)
├── tools/               # genfont, mix, master_audio, caption_segments, make_srt,
│                        # make_covers, char_ref, check_subs, check_delivery
├── audio/               # song.wav, mix.wav, master.wav
├── analysis/
├── stills/
└── out/
```

The page contract is small: `window.DUR`, `window.SUBS`, `window.EV`,
`window.render(t)`, `window.READY`. `render(t)` must be pure and stateless.

## Documentation

| File | Contents |
|---|---|
| `SKILL.md` | Operating summary, gates, delivery contract |
| `scripts/setup.sh` | One-time renderer install and tool-chain check |
| `references/sop.md` | Full procedure and stage gates |
| `references/pixel-engine.md` | Framebuffer, palette, drawing, shot craft |
| `references/audio.md` | Analysis, sync, level plan, master |
| `references/qa.md` | QA passes and exact commands |
| `references/rights.md` | Rights gate and CREDITS rules |

## Rights

This repository ships no music, lyrics, character art, or other production
assets. Use it only with audio and lyrics you have the right to use. A public
release of any film made with it requires your own synchronisation, master,
lyric-reprint, and character licences. The skill's rights gate and a CREDITS
template are in `references/rights.md`.

## Attribution

- Pixel engine adapted from **Lemo-Opuscar** (MIT), copyright LemoLab.
- Palette begins with **ENDESGA-32** by ENDESGA.
- Optional CJK glyphs come from **GNU Unifont** (GPL-2.0-or-later with font
  embedding exception); the font is read at build time, not bundled.

Full texts are in `THIRD_PARTY_NOTICES`.

## License

No license has been declared for this skill's own text and scripts. The
third-party components listed above keep their own licenses.
