# Lyric MV production SOP

This is the stage-by-stage method behind the skill. Each stage has an output and
a gate; do not start the next stage until the gate is true. The commands assume
Git Bash on Windows or a POSIX shell, with:

```sh
SKILL=/path/to/lyric-mv-producer
LIB=/path/to/lemo-opuscar
PY=/path/to/python          # numpy + scipy
FF=/path/to/ffmpeg
PROJ=/path/to/my-film
```

## 0. Brief, inputs, rights

Ask **once**, in one message. Skip anything the request already answers.

- Topic and tone: what the song is about to this user, and the one image they
  want to remember.
- Material: the audio file, lyrics or LRC, any character or artwork, fonts,
  logos, footage, and whether they have the right to use each.
- Language for lyrics and on-screen text.
- Whether they want to review a storyboard first (default: no).
- Missing tools: Node 20+, Python 3.11+ with numpy/scipy, ffmpeg, a
  Chromium/Chrome for the renderer, and the Lemo-Opuscar library. Report; do not
  install system software without asking. If only the library is missing,
  `sh "$SKILL/scripts/setup.sh"` installs it and its packages after the user
  agrees.

Summarise the brief in a few lines and start. Record the rights answer in
`TREATMENT.md` §8 and in `CREDITS`; read `references/rights.md` before drawing
anything that resembles an existing character.

**Gate:** every input has a source and a permission status. If the song,
lyrics, or character is not cleared, say what can be delivered (private study
cut, original stand-in, licensed replacement) before production.

## 1. Scaffold and analyse the song

```sh
python "$SKILL/scripts/scaffold.py" "$PROJ" \
  --title "Paper Moon" --slug paper-moon --dur 180.0 \
  --song "/path/to/song.mp3" --font "/path/to/unifont.hex.gz"

"$PY" "$SKILL/scripts/analyze_song.py" "$PROJ/audio/song.wav" \
  --ffmpeg "$FF" --json "$PROJ/analysis/song.json"
```

`analyze_song.py` reports duration, peak/RMS, tempo candidates, 2-second energy
and brightness, quiet spans, and spectral-flux peaks. It cannot hear the song.
Listen three times:

1. Structure: intro, verse, chorus, instrumental, drop, reprise, coda. Mark the
   exact boundary times, not the nearest bar.
2. Pulse: which candidate can you clap to? Half/double-time candidates are
   normal. Write the felt BPM and the bar length into `events.json`.
3. Drama: where does the arrangement open up, drop out, or change colour? Those
   are the film's large cuts. Put the biggest visual event on the biggest audio
   event, not on a random bar.

Set `DUR` in `project.env` to the song length plus the tail the film needs.
A coda of 2-6 s is usually enough for a final card or a held last image. Do not
stretch the song to fit the picture.

**Gate:** a section table with timestamps and a felt BPM; the film's `DUR` is
decided.

## 2. One lyric timeline

If the user supplies an LRC:

```sh
"$PY" "$SKILL/scripts/lrc_to_lyrics.py" "$PROJ/song.lrc" \
  -o "$PROJ/lyrics.json" --drop-first
```

The parser drops credit lines (`作词：`, `作曲：`, etc.) and optionally the first
title cue. It derives each cue's end from the next start, capped at `--max-dur`.
If there is no LRC, align by hand in a waveform editor; do not trust raw ASR
timestamps for a sung line.

`lyrics.json` is the single source for the page and the SRT:

```json
[
  {"text": "first line", "t0": 1.72, "t1": 3.45},
  {"text": "second line", "t0": 3.50, "t1": 5.30}
]
```

Rules:

- `t1 > t0`; no overlap; keep a 20-40 ms gap between lines.
- 1-2 lines on screen; 9-10 Chinese characters per line is a comfortable width
  at 320 px. Long lines wrap or get split at a breath.
- Do not put a cue in an instrumental section. The absence of lyrics is part of
  the edit.
- Repeated choruses are repeated cues; keep them, do not merge them.
- The film's subtitle is not a karaoke wipe. A whole-line lift or a 2-frame fade
  reads better at 24 fps and avoids a second animation system.

```sh
"$PY" "$SKILL/scripts/make_srt.py" "$PROJ" --out "$PROJ/paper-moon.srt"
```

**Gate:** `lyrics.json` parses, every cue is inside `DUR`, and the SRT has the
same count as the JSON.

## 3. Treatment before code

Copy `assets/templates/TREATMENT.md` and write it in the project. Required:

- A one-sentence story with a want and an obstacle.
- Three structures, then one choice with a reason.
- A character who can be recognised at 40 px tall.
- A palette, three shot sizes, an HUD rule, a lyric rule, and a transition rule.
- A sound table: beds, foley, the one loud event, and where the beds stop.
- A timeline table covering the instrumental section and the ending.
- Eight key shots, including the poster frame.

The treatment must answer the two places lyric videos usually die:

1. **The instrumental section.** What is happening on screen, and why does it
   belong to this song rather than any song?
2. **The last chorus.** What decision does the character make? "They feel sad"
   is not a decision.

**Gate:** someone who has not heard the song can read the timeline and describe
the film. The instrumental and ending have concrete images.

## 4. Prove the look before the film

Draw with the real engine, not a mock-up:

```sh
node "$LIB/core/render/still.mjs" "$PROJ" 12.0 --prefix look_wide_
node "$LIB/core/render/still.mjs" "$PROJ" 48.0 --prefix look_medium_
node "$LIB/core/render/still.mjs" "$PROJ" 88.0 --prefix look_close_
```

Check:

- The character reads at 40 px; eyes and silhouette survive the 6x upscale.
- The palette has a light, a mid, and a dark that are distinct in a 320 px
  thumbnail. Pure black is a hole, not a shadow.
- The lyric line is legible over the busiest frame and does not cover a face.
- The HUD is a point of view, not a border. If it would appear on every frame,
  cut it back.
- The title card is readable in one second.

Build a model sheet with stills or a separate sprite page: front, side, back,
idle, walk, the one prop, and two expressions. A character that only works in
one pose is a drawing, not a cast member.

Prove the planned poster in all three shapes before animating. Render the
`POSTER_T` still, then derive the covers from it:

```sh
. "$PROJ/project.env"
node "$LIB/core/render/still.mjs" "$PROJ" "$POSTER_T" --prefix poster_
"$PY" "$PROJ/tools/make_covers.py" "$PROJ" --ffmpeg "$FF" \
  --focus "${COVER_X:-0.5}" --source "stills/poster_$POSTER_T.jpg"
```

The 3:4 cover is a centre crop of only 42% of the width. If that crop loses
the face, the key prop, or an on-screen title, reframe the coda shot now or
move `COVER_X`; do not plan a poster that only works in 16:9.

**Gate:** three approved stills (wide, medium, close), a model sheet, and a
poster still whose subject survives 4:3 and 3:4 crops. If the user asked for a
storyboard, stop here and wait for approval.

## 5. Build the engine and scenes

Start from `assets/engine/px.js`, `assets/engine/font.js`, and
`assets/templates/main.js`. The page contract is:

```js
window.DUR = 180.0;                  // seconds
window.render = t => { ... };        // deterministic frame at t
window.READY = true;                 // after fonts/data are loaded
window.SUBS = [{t0, t1, text}];      // same JSON as the SRT
window.EV = [{t, k}];                // optional audio cues
```

The renderer calls `render(t)` for every frame, in any order, in up to three
browsers. Therefore:

- No `Math.random()` without a seeded hash; no `Date.now()`; no state carried
  from the previous frame. `window.render(10)` twice must produce identical
  pixels.
- Draw the frame from `t` alone. A scene is a function of time, not a playlist
  of tweens with side effects.
- Animate character motion on twos if the pixel style wants it; keep camera and
  light smooth. A stepped camera reads as lag.
- Draw at 320x180 into an indexed framebuffer, then upscale 6x with nearest
  neighbour. Never draw UI at 1920x1080 and downscale.
- Precompute palettes, LUTs, sprites, star fields, and text layouts. Do not
  allocate large arrays per frame.
- Keep one `world -> screen` function for zooms, spotlights, and shakes.

Organise `engine/main.js` (or a `scenes.js` module it imports) as an array of
`{t0, t1, draw(fb, t, local)}` and a small transition table. One timeline drives
picture, sound, and subtitles.

**Gate:** stills at the first frame, each section boundary, the drop, the
collapse, and the last frame; no page errors; two renders of the same time are
byte-identical.

## 6. Sound design and master

The song is the score. Do not add a melody, a counter-melody, or a replacement
drum groove. Add only what the picture causes:

- Beds: room tone, sea, rain, wind, street, crowd. Keep them 25-35 dB below the
  song's active level; they should disappear when you stop listening for them.
- Foley: footsteps, paper, a cup, a latch, a key click. Short, mono-compatible,
  panned no wider than the object.
- One loud event: the impact, pop, or door that the film is built around. Give
  it a hole in the beds so it reads.
- If the song has a breakdown, duck and low-pass the song for the visual
  collapse, then let it back. Do not stop the song unless the film stops.

Use `tools/mix.py` as the starting point. It normalises the song's active RMS to
-20 dBFS, adds beds and event-driven foley from `events.json`, applies optional
`ducks`, and writes `audio/mix.wav`. Extend the event map in that file; keep all
levels in one table.

Master with `tools/master_audio.py`: two-pass `loudnorm` to -14 LUFS, true peak
at or below -1.2 dBTP, then a safety limiter. Encode AAC 256 kbps, 48 kHz stereo.
Read `references/audio.md` for the level table and the failure modes.

**Gate:** the film plays with sound; the loud event is audible without clipping;
the song is recognisably the supplied recording; `ebur128` reports the target.

## 7. Render and package

```sh
LIB="$LIB" PY="$PY" FF="$FF" WORKERS=3 sh "$PROJ/build.sh"
```

`build.sh` decodes the song, bakes the CJK subset, mixes, masters, writes the
SRT, renders at `DUR * FPS` frames, muxes H.264/AAC with faststart, writes
`poster.jpg` from `POSTER_T`, and derives `poster_4x3.jpg` (1920×1440) and
`poster_3x4.jpg` (1080×1440) from it. Choose `POSTER_T` in a coda frame with no
lyric. If the coda has a title card, either move the card or choose a clean
frame. Covers are cropped around `COVER_X` (0 = left, 0.5 = centre, 1 = right).

For a faster iteration, render one still or a short range with the Lemo tools;
do not re-render the whole film to check a colour.

**Gate:** the MP4 opens, duration matches `project.env`, and all three posters
are clean, with the subject intact in the 3:4 crop.

## 8. QA and delivery

Run the automated check first, then the human review:

```sh
"$PY" "$PROJ/tools/check_delivery.py" "$PROJ" --slug "$SLUG" --ffmpeg "$FF"
```

The checker validates required files, H.264/AAC, resolution, fps, loudness,
true peak, black segments, SRT monotonicity, Chinese glyph presence, event
count, the 4:3 / 3:4 cover aspect ratios, and the CREDITS rights section. It
does not judge the film. Then:

1. Contact sheet every 1-2 s. Look for repeated compositions, dead air, and
   sections that look like a different film.
2. 0.2 s strips around every key action and cut. Look for missed hits, pops, and
   frames where the character's face breaks.
3. One full-speed viewing with sound, start to finish, no scrubbing.
4. Subtitle pass: read every line at speed; check it does not cover a face or a
   prop; check names and punctuation.
5. Cover pass: open `poster.jpg`, `poster_4x3.jpg`, and `poster_3x4.jpg` at
   100%. Check the face, the key prop, and any title survive every crop; check
   there is no subtitle baked into any of them.
6. Rights pass: every asset in `CREDITS`; the rights paragraph matches the
   actual permission status.

Deliver in the project folder:

```
<slug>.mp4          H.264 1920x1080 24 fps, AAC 48 kHz stereo, about -14 LUFS
poster.jpg          1920x1080, coda frame, no subtitle
poster_4x3.jpg      1920x1440, 4:3 cover, same frame
poster_3x4.jpg      1080x1440, 3:4 cover, same frame
<slug>.srt          same cues as lyrics.json
TREATMENT.md        the written film
CREDITS             every asset, source, licence, rights paragraph
lyrics.json         the timeline
events.json         sound / cue map
build.sh            one-command rebuild
engine/ tools/      the source
```

Tell the user where the folder is, that `CREDITS` lists the third-party assets
and licences, and that they are responsible for the material they supplied.

## 9. Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Film feels like a slideshow | cuts not on the felt pulse; no camera motion | cut on beats or lyric starts; add a slow push or pan |
| Instrumental section is boring | no story device; literal illustration | use the treatment's frame (memory, game, letter) to change the location |
| Lyrics cover the face | subtitle safe area not reserved | compose with a lower third; move the camera |
| Tofu / missing characters | `font_zh.js` not regenerated | run `genfont.py`; check the missing list |
| Render crawls | drawing per pixel through Canvas 2D; huge per-frame allocations | draw into the indexed FB; precompute; use 3 workers |
| Audio pumps | single-pass loudnorm on a dynamic mix | use two-pass `loudnorm` or a limiter |
| A/V drift at the end | audio longer than picture or MP3 delay | master exact `DUR`; mux with `-shortest`; use WAV for timing |
| Black frames in the check | fade to black not intended | shorten the fade or cut before black |
| Character looks like the reference too closely | copied design | redesign silhouette, palette, and props; use an original stand-in |
| Rights problem at delivery | no gate at the start | stop; do not publish until cleared |

Production lessons that generalise:

- Two-pass time-stretch or "formant" tricks can drift pitch across a full song.
  If the brief needs a character timbre, shift the spectral envelope with an
  STFT while preserving phase and F0; never pitch the whole song.
- A soft clipper can behave unpredictably across ffmpeg builds. Prefer a
  measured limiter and verify true peak after encoding.
- An EQ chain without input headroom can clip a vocal at 0 dBFS. Put -3 dB
  before the chain and clean non-finite samples after filter warm-up.
- Decoding to mono through ffmpeg can add about 3 dB and fake a hot peak.
  Measure peak on the stereo decode.
- MP3 adds encoder delay; use the decoded WAV for timing.

## 10. Rights text

Write the actual rights holders, permission scope, and asset sources into
`CREDITS` and the treatment. Never copy a notice from another production.
Replace every bracket in the templates below.

English:

> [Song title] — words and music by [writers], performed by [artist], recording
> owned by [label]. Used with permission for [scope]. [Character name] is owned
> by [rights holder]; this is an unofficial fan work, not endorsed by [rights
> holder]. No official artwork, logos, fonts, footage, or voice clips were used.
> Public release requires the user's own sync, master, lyric-reprint, and
> character licences.

Chinese:

> 本片使用 [歌曲名]（词曲：[词曲作者]；表演：[演唱者]；录音版权：[录音版权方]），
> 使用范围为 [范围]。片中 [角色名] 形象版权归 [权利人] 所有；本片为非官方同人作品，
> 不使用官方素材，不暗示与权利人的关联或背书。公开发布前请自行取得词曲、录音、
> 角色形象与音乐录音的使用授权。

If all characters and artwork are original, replace the fan-work sentence with
"All characters and artwork are original."

See `references/rights.md` for the full gate and the CREDITS rules.
