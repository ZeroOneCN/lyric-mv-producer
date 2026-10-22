# {{TITLE}} / TREATMENT

> [One sentence: who wants what, and what stands in the way. No theme words until the story is concrete.]

- Form: code-drawn pixel lyric film, {{DUR}} s, 1920x1080, 24 fps
- Music: [track title, artist, source, duration, BPM]
- Language: [lyrics and on-screen language]
- Frame: 320x180 indexed framebuffer, 6x nearest-neighbour to 1920x1080
- Rights: [what the user supplied and what they have cleared]

## 1. Three structures

**A. Linear day** — [what happens, and where it goes flat].

**B. Memory loop** — [what alternates with what, and why it might fragment].

**C. [Chosen frame]** — [the organising device: a letter, a map, a room, a season]. [One paragraph on why this device makes the instrumental section and the ending legible without narration.]

Choose one and say why. The choice must survive the 30-second instrumental section: that is where most lyric videos lose their story.

## 2. Character and want

- Who: [name, age, work, one physical detail that can be drawn at 40 px tall].
- Want: [concrete, visible, not "to be happy"].
- Obstacle: [the thing the world will not give].
- Arc: [what changes by the last chorus; it can be small, but it must be a decision].
- Reference: [none / `character/ref_*.png` supplied by the user, cleared for this use].
  If a reference exists, run `tools/char_ref.py` and record here which grid became
  the sprite and what you redrew. The reference and the drafts never appear in the film.
- Forbidden: no official art, logos, fonts, footage, voice clips, or ripped character sprites. Draw a stand-in if the user has not cleared a character.

## 3. Visual system

**Palette** (indexed, no large pure-black areas; sample — replace with your own):
- ink `#12101a`, plum `#241d30`, slate `#334155`, moss `#4a6b5a`
- lamp `#f0b968`, paper `#f3ead6`, coral `#d9778a`, sky `#7e9cb8`

**Composition**: three shot sizes, repeated.
1. Wide: the figure is 16-40 px tall; the world is horizontal and larger than them.
2. Medium: figure plus one object that carries the story (case, cup, letter).
3. Close: eyes, hands, a key; use only at the chorus and the ending.

**HUD**: [what the interface says, where it sits, how often it appears]. The HUD is a point of view, not a border.

**Lyrics — fixed, not designed per film**: `engine/caption.js` draws one line per cue on
the 2x overlay layer above the picture (640x360 layer, line max 560 layer px, centred,
anchored at layer row 336), 1 px ink shadow, 0.18 s fade-in. A cue longer than one line is
split into successive single lines, timed by character count. `SUB_STYLE` picks plate
(dithered plate behind the line) | bubble (solid plate) | plain (outline only).
[Record here only the style you chose and any shot whose subject must stay clear of the
overlay band while a cue is on screen.]

**Transitions**: cuts on beats or lyric starts. [Name the two or three dissolves and why they are earned.]

## 4. Sound

The song is the score. Do not add melody or replace the drum groove. Everything added sits under it:

- Beds: [room / sea / rain / street / crowd], with level and where they stop.
- Foley: [five to eight sounds that the picture actually causes].
- One loud event: [the one impact or pop the film is built around].
- Silence: [the one place the beds drop out, so the loud event reads].
- Master: -14 LUFS integrated, true peak at or below -1.2 dBTP.

## 5. Timeline

Sample timings for a 3:20 song; replace every row with the actual section
boundaries from your analysis.

| Time | Section | Picture | Lyric / cue |
|---|---|---|---|
| 0:00-0:08 | cold open | [title over a moving surface] | — |
| 0:08-0:48 | verse 1 | [daily world, wide] | [first line] |
| 0:48-1:16 | chorus 1 | [first decision] | [chorus line] |
| 1:16-1:52 | instrumental | [the film's one departure from the room] | — |
| 1:52-2:32 | break / drop | [the largest image; keep one human scale detail] | — |
| 2:32-3:00 | final chorus | [the decision, without a speech] | [last line] |
| 3:00-3:20 | coda | [the empty room / the open door / the last light] | — |

## 6. Key shots

1. **[0:00] Title** — [surface, movement, type treatment].
2. **[first verse] Room** — [one object that tells the want without a caption].
3. **[chorus] First action** — [the act the whole film is waiting for].
4. **[instrumental] Departure** — [how the film leaves the room without a cut to a new character].
5. **[drop] Largest image** — [scale, light, what stays small].
6. **[collapse] Return** — [the glitch / colour collapse / match cut that brings us back].
7. **[final chorus] Decision** — [what the character does instead of waiting].
8. **[coda] Last frame** — [the image the poster will use; make it hold, and keep the subject inside the centre 42% of the width so the 3:4 cover survives].

## 7. Delivery

- `{{SLUG}}.mp4`: 1920x1080, 24 fps, H.264, AAC 48 kHz stereo, -14 LUFS
- `poster.jpg`: the coda frame, clean of subtitles
- `poster_4x3.jpg` / `poster_3x4.jpg`: 4:3 and 3:4 covers from the same frame
- `{{SLUG}}.srt`: same cue list as `lyrics.json`
- `TREATMENT.md`, `CREDITS`, `lyrics.json`, `events.json`
- `build.sh`: one command, from decoded song to muxed film

## 8. Rights

[Replace with the user's rights statement. Name every third-party asset in CREDITS. If the song, lyrics, character, or voice is not the user's, say plainly that public release needs the rights holders' permission.]
