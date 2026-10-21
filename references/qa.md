# QA and delivery

A film is finished when it has been watched end to end, not when the render
exits 0. QA has four passes, in this order: stills, strips, full watch,
mechanical checks. Do not skip the watch because the numbers pass.

## 1. Look proof (before the full render)

Render 5–8 stills at the shots that carry the story, plus the poster time:

```bash
node "$LIB/core/render/still.mjs" "$PROJ" \
  1.2 10.5 43.0 87.5 133.6 167.3 178.2 --prefix look_
```

Open them at 100%. Fail the look if any of these is true:

- the character reads as a silhouette blob, or the species/character is not
  recognisable without the treatment text,
- two adjacent planes share the same value (no separation at 6× upscale),
- a subtitle overlaps a face, an eye, or the key prop,
- CJK glyphs are missing, doubled, or clipped,
- the palette has more than ~40 colours or large pure-black areas,
- the HUD is brighter than the subject.

Then prove the three poster shapes from the chosen `POSTER_T`:

```bash
node "$LIB/core/render/still.mjs" "$PROJ" "$POSTER_T" --prefix poster_
python "$PROJ/tools/make_covers.py" "$PROJ" --ffmpeg "$FF" \
  --focus "${COVER_X:-0.5}" --source "stills/poster_$POSTER_T.jpg"
```

Open `poster.jpg`, `poster_4x3.jpg`, and `poster_3x4.jpg` at 100%. Fail the
poster if any of these is true:

- the 3:4 crop cuts a face, an eye, the key prop, or an on-screen title,
- the crop leaves the subject at the edge with dead space on the other side,
- a subtitle is baked into any cover,
- the 4:3 and 3:4 covers do not come from the same frame as `poster.jpg`.

Fix stills before spending 20 minutes on 4,000 frames.

## 2. Contact sheet (whole film at a glance)

One frame every 10 s, tiled:

```bash
mkdir -p qa
ffmpeg -y -i "$SLUG.mp4" \
  -vf "fps=1/10,scale=480:-1,tile=4x5" -frames:v 1 qa/contact.jpg
```

For a 193 s film this yields ~20 frames. Scan for:

- unintended black frames or frozen sections,
- repeated compositions back to back,
- lighting that drifts without motivation,
- the poster frame being unrepresentative,
- subtitles present in every sampled frame (they should breathe).

Then sample the boundaries: every section change, every imagined/real cut,
first and last 2 s. A 0.2 s strip around a cut:

```bash
ffmpeg -y -ss 42.4 -t 2.0 -i "$SLUG.mp4" \
  -vf "fps=10,scale=480:-1,tile=5x4" -frames:v 1 qa/cut_42.jpg
```

Use strips for: title in/out, first lyric, first musical hit, dream entry,
dream collapse, vehicle door, final fade. Look for pops, one-frame flashes, palette
glitches, and text that appears before its cue.

## 3. Full watch

Watch the entire film once without pausing, at 100%, with sound. Then watch a
second time with these specific checks:

**Picture**
- Every cut lands on a beat or a lyric onset; no cut lands mid-word.
- No subtitle appears on a frame before its audio cue; no cue lingers after the
  line ends.
- The character's eyes and mouth (if any) are readable at medium/close shots.
- Transitions are motivated; a dissolve does not hide a missing shot.
- The final frame holds long enough to read the end card.

**Sound**
- Foley is audible in quiet passages and does not cloud the drop.
- Riser ends exactly on the cut; impacts do not double-trigger.
- No click at section boundaries, no tail cut by `-shortest`.
- Vocal is intelligible at −14 LUFS on phone speakers.
- Mono fold-down does not lose the heartbeat, vehicle, or latch.

**Sync**
Spot-check at least three lines: first, middle, last. If the lyric file came
from LRC, verify the chorus, where drift is most visible. A systematic offset
means fix `--offset` and regenerate; a single bad line means edit
`lyrics.json` and regenerate the SRT.

## 4. Mechanical checks

```bash
python tools/check_delivery.py "$PROJ" --slug "$SLUG" \
  --ffmpeg "/path/to/ffmpeg" --width 1920 --height 1080 --fps 24
```

The script must end with `RESULT PASS (0 fail, 0 warn)`. It checks:

| Check | Threshold |
|---|---|
| required files | video ≥ 100 kB; 16:9, 4:3, 3:4 posters ≥ 10 kB; treatment, credits, build, lyrics |
| covers | 4:3 = 1.333, 3:4 = 0.750 (±0.01), min side 720 px, readable JPEG |
| video | h264, 1920×1080, 24 fps, readable duration |
| audio | AAC, 48 kHz, stereo |
| loudness | −14 ± 1.0 LUFS, TP ≤ −0.9 dBTP |
| black | no segment ≥ 0.5 s; 0.2–0.5 s warns |
| SRT | cues valid, monotonic, no overlaps, ends before picture |
| lyrics | every cue has text, t1 > t0 |
| CJK | `font_zh.js` present when lyrics contain CJK |
| events | valid JSON, duration within 1 s of film |
| credits | names the music and contains a rights/licence section |

Extra checks worth running by hand:

```bash
# exact stream summary
ffmpeg -hide_banner -i "$SLUG.mp4" 2>&1 | grep -E "Duration|Stream"

# frame count should equal round(DUR * FPS)
ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=nb_read_frames -of csv=p=0 "$SLUG.mp4"

# last frame exists and is not black
ffmpeg -y -sseof -0.1 -i "$SLUG.mp4" -frames:v 1 qa/last.jpg

# cover dimensions and aspect
for f in poster.jpg poster_4x3.jpg poster_3x4.jpg; do
  ffmpeg -hide_banner -i "$f" 2>&1 | grep "Video:"
done
```

## 5. Delivery manifest

```
<project>/
├── <slug>.mp4          1920×1080, 24 fps, AAC 256k/48k stereo
├── poster.jpg          from POSTER_T, 16:9, no subtitle covering the subject
├── poster_4x3.jpg      4:3 cover, same frame and crop focus
├── poster_3x4.jpg      3:4 cover, same frame; subject must survive the 42% crop
├── <slug>.srt          one cue per sung line, UTF-8, same timings as lyrics.json
├── TREATMENT.md        structure, character, look, sound, rights
├── CREDITS             music, character, visuals, tools, rights paragraph
├── lyrics.json         [{ text, t0, t1 }]
├── events.json         { dur, bpm, beds, ducks, ev }
├── build.sh            one command rebuild
├── project.env         single source of truth
├── engine/             px.js, font.js, font_zh.js, main.js
├── tools/              genfont, mix, master_audio, make_srt, check_delivery
├── audio/              song.wav, mix.wav, master.wav
├── analysis/           song.json (optional)
└── stills/             look_*.jpg, poster_*.jpg
```

Never deliver the intermediate `out/video.mp4` as the final film — it has no
audio. Never deliver a poster that is a random frame with a subtitle across the
face; pick the coda or a wide shot. Never ship only the 16:9 poster, and never
ship a 3:4 crop that decapitates the subject to satisfy the aspect ratio —
reframe the poster shot instead.

## 6. Rights gate

Before handing over, confirm all of the following:

- `CREDITS` contains the verbatim rights paragraph from `references/rights.md`.
- No official character image, logo, font, voice clip, or song file is bundled
  in the skill or in the deliverable except the user-supplied song.
- The film is marked as an unofficial fan work, not endorsed by rights holders.
- If a synthesized voice was used, it is disclosed and is not a clone of a real
  performer.
- The user understands that public release requires their own sync, master,
  lyric-reprint, and character licences.

If any item is missing, delivery is blocked regardless of the technical checks.

## 7. Common failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Black frame at t=0 | `render(0)` not called after `READY` | call it in `boot()` |
| Freeze for several seconds | shot function throws and renderer reuses last frame | check console; `render` wraps errors |
| Subtitles flicker | `t0`/`t1` overlap or gap < 1 frame | enforce monotonic cues; regenerate SRT |
| Chinese shows as boxes | glyph subset stale | rerun `genfont.py`, then `--check` |
| Poster has a lyric across it | `POSTER_T` inside a cue | move to coda, `DUR - 0.3` |
| Audio ends before picture | `-shortest` with short master | master must cover `DUR`; mix pads to duration |
| Video ends before audio | dropped frames | renderer log must report expected frame count |
| Loudness OK, TP hot on AAC | codec overshoot | lower limiter to 0.80 and re-encode |
| SRT shows as `????` | missing UTF-8 BOM in some players | write UTF-8 with BOM if the target player needs it |
| Last lyric cut by fade | cue extends into the coda | trim `t1` before the fade |

## 8. Sign-off

Record in the final message:

- duration, resolution, fps, codec,
- integrated LUFS and true peak,
- cue count and last cue time,
- poster timestamp,
- `RESULT PASS` line from `check_delivery.py`,
- the rights sentence and a link to `CREDITS`.

Only then mark the delivery complete.
