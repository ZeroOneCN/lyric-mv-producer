# Audio, mix and master

The supplied song is the score. Do not re-arrange it, do not add melody, do not
replace drums. The film's sound work is three things only:

1. procedural ambience beds under the song,
2. short foley events tied to picture and lyric cues,
3. loudness and true-peak safety at delivery.

Every sound in `tools/mix.py` is synthesised with numpy, so the project carries
no sample-library licences. Do not add a commercial sample pack without
clearing it.

## 1. Source preparation

Decode once to 48 kHz, 16-bit, stereo PCM:

```bash
ffmpeg -y -i "$SONG" -vn -ac 2 -ar 48000 -c:a pcm_s16le audio/song.wav
```

Keep the original file in the project as delivered by the user. Never process
the MP3 in place, and never time-stretch to fit the cut — cut picture to the
music instead.

Check the source before planning:

```bash
python scripts/analyze_song.py "$SONG" \
  --ffmpeg "/path/to/ffmpeg" --json analysis/song.json
```

It reports duration, tempo candidates (autocorrelation), a 2 s energy/centroid
profile, quiet spans, and flux peaks. Treat the BPM as a candidate: autocorrelation
often returns half or double time. Confirm downbeats by ear before setting the
edit grid.

Important: the script decodes staying stereo because ffmpeg's mono downmix can
add ~3 dB and fake a hot peak. It reports the peak across both channels.

## 2. Lyric timeline

`scripts/lrc_to_lyrics.py` converts an LRC into the only lyric format the
engine reads:

```json
[{ "text": "…", "t0": 1.72, "t1": 6.10 }]
```

```bash
python scripts/lrc_to_lyrics.py lyrics.lrc -o lyrics.json \
  --drop-first 2 --offset 0 --min-dur 1.2 --max-dur 8 --gap 0.12
```

- `--drop-first` removes title/credit lines (also matched by a credit regex).
- `--offset` shifts every cue when the source LRC is early/late.
- `--min-dur` / `--max-dur` clamp unusually short or long lines.
- `--gap` trims a little silence before the next line.

After conversion, listen against the waveform and nudge individual `t0`/`t1` in
`lyrics.json`. Rules:

- A cue starts on the first syllable, not before the breath.
- No cue overlaps the next.
- Do not leave a cue on screen through an instrumental break.
- 8–20 characters per Chinese cue: the caption shows one line at a time, so split
  longer sentences into cues at a breath.
- The last cue must end before `DUR`; leave at least 2 s of coda.

Generate the SRT from the captions the renderer draws, never by hand:

```bash
node tools/caption_segments.js . --out out/segments.json
python tools/make_srt.py . --segments out/segments.json --out "$SLUG.srt"
```

## 3. Event map

`events.json` is the single timeline shared by the engine and the mix:

```json
{
  "dur": 180.0,
  "bpm": 120,
  "beds": [
    { "kind": "sea", "t0": 0, "t1": 180.0, "gain": -45 }
  ],
  "ducks": [
    { "t0": 130.0, "t1": 133.6, "lowpass": 1200, "gain_db": -6 }
  ],
  "ev": [
    { "t": 5.3, "k": "alarm" },
    { "t": 20.68, "k": "diner_chime" }
  ]
}
```

- `beds` are continuous loops: `sea`, `rain`, `wind`, `room`.
- `ducks` treat the **song** itself: smooth 80 ms edges, low-pass and gain.
  Use once or twice, for a muffled memory or a "world drops away" moment.
- `ev` are one-shots. The generic template knows `title`, `ui`, `bell`,
  `hit`/`impact`, `whoosh`, `riser`, `splash`, `heart`, `sparkle`, `end`, and
  falls back to a quiet tick. Extend the `elif` chain in `tools/mix.py` for
  story-specific sounds (register, brake, paper, latch…).

Every event must be motivated by a cut, a gesture, or a lyric accent. A hit on
every downbeat is noise, not sound design.

## 4. Level map

Work with one reference: **active song RMS = −20 dBFS**. `mix.py` measures RMS
only over frames above −45 dBFS, so quiet intros do not inflate the gain. All
foley gains below are relative to that reference.

| Layer | Level | Notes |
|---|---|---|
| Song | active RMS −20 dBFS | never limited at this stage |
| Sea / room bed | −45 dBFS | barely there; felt not heard |
| Rain / wind bed | −40 to −38 dBFS | can rise in exposed intros |
| Heartbeat | −30 dBFS peak | two thumps, 210 ms apart |
| UI / register / tick | −34 dBFS | dry, centred, 30–90 ms |
| Paper / latch / steps | −32 dBFS | pan ±0.3 |
| Bell / sparkle | −34 dBFS | decays 0.9–2.6 s |
| Whoosh / riser | −24 dBFS peak | ends exactly on the cut |
| Impact / splash | −18 dBFS peak | sub body 40–60 Hz + noise transient |

Rules:

- Riser ends on the downbeat; impact starts on the same frame. No gap.
- Duck the bed under dialogue-like moments, not under the whole film.
- Keep sub energy out of the beds; leave 40–80 Hz for the song and impacts.
- Pan foley no wider than ±0.4; the song owns the centre.
- Fade the entire mix over the last 0.6 s, after the final musical event.

## 5. Mix implementation

`tools/mix.py` reads `project.env` and `events.json`, synthesises beds and
one-shots, applies ducks to the song, normalises, and writes float32
`audio/mix.wav` at 48 kHz.

Checks built into the template:

- deterministic RNG seed (same build → same mix),
- windowed fades on every one-shot and bed,
- 80 ms smooth duck edges,
- peak guard at −0.9 dBFS before mastering,
- `nan_to_num` so a filter warm-up cannot poison the file.

Do not add a limiter here. Leave headroom; `master_audio.py` owns the ceiling.

## 6. Master

```bash
python tools/master_audio.py audio/mix.wav audio/master.wav \
  --ffmpeg "/path/to/ffmpeg" --i -14 --tp -1.2
```

Two-pass `loudnorm` with `linear=true`, then `alimiter=limit=0.85:level=false`
and a final 48 kHz resample. The script verifies with `ebur128` and fails if:

- integrated loudness misses −14 LUFS by more than 0.7 LU,
- true peak exceeds −0.8 dBTP (0.4 dB over the ceiling).

Expected result for a normal song mix: **−14.2 LUFS / −1.4 dBTP**.

Mux:

```bash
ffmpeg -y -i out/video.mp4 -i audio/master.wav \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 256k -ar 48000 -ac 2 \
  -movflags +faststart -shortest "$SLUG.mp4"
```

## 7. Verification

```bash
ffmpeg -hide_banner -nostats -i "$SLUG.mp4" \
  -map 0:a:0 -af ebur128=peak=true -f null -
```

Read the **final** summary block, not an intermediate one. Check:

- integrated ≈ −14 LUFS,
- true peak ≤ −1.2 dBTP (allow −0.8),
- duration equals picture within 1 frame (`-shortest`),
- no clipping in `astats` (`Peak level dB` < 0),
- mono compatibility: sum to mono and listen for disappearing foley.

## 8. Failure modes seen in practice

| Symptom | Cause | Fix |
|---|---|---|
| Source peak reads +2.5 dBFS | ffmpeg `-ac 1` downmix | measure stereo, as `analyze_song.py` does |
| Whole mix drifts in pitch | two-pass `rubberband` time-stretch | never stretch the song; cut picture |
| Harsh clipping on impacts | `asoftclip` misuse / hot bus | leave 0.9 dB headroom, limit only at master |
| First 200 ms of a filter are NaN | IIR warm-up on zero state | discard warm-up or `nan_to_num` |
| MP3 starts late by ~25 ms | encoder delay | decode to WAV once, sync lyrics to the WAV |
| Loudness passes but sounds quiet | LRA crushed by over-limiting | keep LRA ≈ 11, limit ≤ 1 dB |
| Sub thump on every cut | low-passed noise in whoosh | high-pass the transient at 120 Hz |

## 9. Optional: character timbre

If the brief asks for a *sound-alike* vocal timbre, that is a separate,
rights-sensitive experiment. The safe technique is parametric, not a clone:

- separate the vocal with Demucs (`htdemucs`), keep the instrumental,
- shift only the **spectral envelope** with an STFT formant warp, preserving
  F0 and phase (`scripts/formant_shift.py`),
- remix at the original vocal level, then master normally.

```bash
python scripts/formant_shift.py vocal.wav vocal_shift.wav --alpha 1.12 --strength 1.0 --sr 48000
```

`alpha > 1` shortens the apparent vocal tract (smaller character); `1.0` is
neutral; `strength` blends the effect. Never publish a voice clone of a real
performer, never imitate a living actor's voice for promotion, and never use
official voice clips. Disclose synthetic processing in `CREDITS`.

## 10. Rights

The song's composition, performance, and recording belong to their respective
rights holders. The skill ships no music. The user must supply audio they have
the right to use, and must clear lyric reprint, sync, master, and character
rights before any public release. Keep the rights paragraph from
`references/rights.md` in `CREDITS` and in the treatment.
