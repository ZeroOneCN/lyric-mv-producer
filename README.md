# Lyric MV Producer

An agent skill that produces a finished lyric music video from a song you own
and its lyrics — entirely in code. It covers the whole pipeline: tempo and
structure analysis, LRC-to-lyric sync, a 320×180 indexed-pixel engine, a written
treatment and shot list, procedural foley, mix and master to −14 LUFS, a
1080p24 render, QA, and delivery (MP4, poster, SRT, credits).

No stock footage, no image generators, no official artwork. Every frame is drawn
into a small palette-index framebuffer and scaled 6× with nearest-neighbour, so
the film stays deterministic: the same project always renders the same frames
and the same mix.

## What you get

- `song.mp4` — 1920×1080, 24 fps, H.264, AAC 48 kHz stereo, −14 LUFS
- `poster.jpg` — 16:9 still from the coda
- `poster_4x3.jpg` — 1920×1440 landscape cover
- `poster_3x4.jpg` — 1080×1440 portrait cover
- `song.srt` — generated from the same cue table as the picture
- `TREATMENT.md`, `CREDITS`, `lyrics.json`, `events.json`, `project.env`
- `build.sh` — one command from decode to finished film

All three covers derive from the same poster frame. The image is reduced to the
native 320×180 grid, cropped horizontally, and upscaled with nearest-neighbour,
so the pixel grid and aspect ratio stay exact. `COVER_X` in `project.env`
(`0 = left`, `0.5 = centre`, `1 = right`) moves the crop window; the 3:4 cover
keeps only the centre 42% of the frame, so the poster must be composed around
that column.

## Requirements

| Need | Detail |
|---|---|
| Song | Your own audio file (MP3/WAV/FLAC) |
| Lyrics | LRC with timestamps, or plain text timed manually |
| Node.js | 18+ |
| ffmpeg | Decode, loudness, mux, QA |
| Python | 3.10+ with `numpy`, `scipy`, `soundfile` |
| Browser | Chromium-based browser for the Lemo-Opuscar renderer |
| Renderer | [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) with `core/render/video.mjs` |
| CJK font | [GNU Unifont](https://unifoundry.com/unifont/) `.hex.gz`, only for Chinese/Japanese/Korean lyrics |

## Install

Setup is one-time. After it, the brief itself can be a single sentence.

```bash
# 1. Install the skill where your agent looks for skills.
git clone https://github.com/ZeroOneCN/lyric-mv-producer.git \
  ~/.qoder-cn/skills/lyric-mv-producer
# Claude Code uses ~/.claude/skills/lyric-mv-producer instead.

# 2. The renderer is a separate library.
git clone https://github.com/lemomo-ai/lemo-opuscar.git ~/lemo-opuscar

# 3. Python dependencies.
python -m pip install numpy scipy soundfile
```

Start a new session or run `/skills reload`. `node` and `ffmpeg` must be on
`PATH`. `build.sh` finds the library at `$LIB`, `../lemo-opuscar`, or
`~/lemo-opuscar`; if yours lives elsewhere, set `LIB` in the environment before
building.

For Chinese, Japanese, or Korean lyrics, download a GNU Unifont `.hex.gz` from
<https://unifoundry.com/unifont/> and pass it with `--font` when scaffolding, or
drop it at `fonts/unifont.hex.gz` inside the project. Latin-only films do not
need it.

## Use it

Put the song and its lyrics in one folder. Nothing else is required:

```
my-song/
├── song.mp3
└── song.lrc
```

Open your agent in the parent folder and send one line:

> 用 lyric-mv-producer 把 ./my-song 做成 MV。

> Make a lyric MV with lyric-mv-producer from ./my-song.

If your agent supports slash commands, `/lyric-mv-producer ./my-song` works too.

The agent reads the skill, asks once for anything the folder does not answer
(title, tone, the one image you want to remember, rights, whether you want to
review a storyboard), then runs the pipeline. The project and all deliverables
are written to a new folder inside the one you point it at.

Add specifics to the same sentence when they matter:

> 用 lyric-mv-producer 把 ./my-song 做成像素风 MV，片名《纸月亮》，主色蓝金，
> 副歌要一次大远景；封面人物放中间，方便裁 3:4。

It is not a one-click app. Setup needs Node, Python, ffmpeg, a Chromium-based
browser, and the Lemo-Opuscar library, and a full-length film takes tens of
minutes to render on a typical laptop. Once those are in place, that sentence is
the whole interface; the commands below are what the agent runs, kept here for
inspection or a manual rerun.

## Quick start (manual)

```bash
SKILL="$HOME/.qoder-cn/skills/lyric-mv-producer"
LIB="$HOME/lemo-opuscar"

# 1. Scaffold a project
python "$SKILL/scripts/scaffold.py" ./my-film \
  --title "PAPER MOON" --slug paper-moon \
  --dur 180.0 --song "/path/to/song.mp3" \
  --font "/path/to/unifont.hex.gz"

# 2. Analyze tempo and sections, then confirm by ear
python "$SKILL/scripts/analyze_song.py" "/path/to/song.mp3" \
  --ffmpeg ffmpeg --json my-film/analysis/song.json

# 3. Sync LRC to the cue table
python "$SKILL/scripts/lrc_to_lyrics.py" lyrics.lrc \
  -o my-film/lyrics.json --offset 0 --min-dur 1.2 --max-dur 8

# 4. Write the treatment, then prove the look with stills
cd my-film
node "$LIB/core/render/still.mjs" . 1.2 10.5 43.0 87.5 178.0 --prefix look_

# 5. Build and check
LIB="$LIB" PY=python sh build.sh
python tools/check_delivery.py . --slug paper-moon --ffmpeg ffmpeg
```

`check_delivery.py` must print `RESULT PASS`, and you should still watch the
film end to end. Stills, contact sheet, cut strips, sync and sound checks are
described in `references/qa.md`.

## Project layout

```
my-film/
├── project.env          # SLUG TITLE SONG DUR FPS POSTER_T COVER_X
├── lyrics.json          # [{ "text", "t0", "t1" }]
├── events.json          # { dur, bpm, beds, ducks, ev }
├── TREATMENT.md
├── CREDITS
├── build.sh
├── index.html
├── engine/              # px.js, font.js, font_zh.js, main.js
├── tools/               # genfont, mix, master_audio, make_srt,
│                        # make_covers, check_delivery
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
