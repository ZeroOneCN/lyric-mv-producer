# Pixel engine

The bundled engine is a deterministic 320×180 indexed-colour renderer. It is
adapted from Lemo-Opuscar's `pixel-rpg` demo (MIT); keep that attribution in
`px.js` if you redistribute it. Everything on screen is drawn by code — no
image assets, no sprite sheets, no fonts beyond the bundled bitmap font and a
baked GNU Unifont subset.

## 1. Page contract

The Lemo-Opuscar renderer opens `index.html`, waits for `window.READY`, then
calls `window.render(t)` for each frame and screenshots the canvas.

```js
window.DUR      // seconds, from project.env
window.SUBS     // [{ t0, t1, text }] from lyrics.json
window.EV       // [{ t, k }] from events.json
window.render   // render(t) — pure, synchronous, no await
window.READY    // true after assets load
```

Rules that keep the renderer honest:

- `render(t)` must be **stateless and deterministic**. Same `t` → same pixels.
  Use `hash(x, y, z)` and `vnoise(x)` from `px.js`; never `Math.random()`,
  `Date.now()`, audio callbacks, or CSS animation.
- No `await` inside `render`; load JSON and fonts once in `boot()`.
- Clamp `t` to `[0, DUR - 0.001]`.
- `render(0)` once after `READY` so the first screenshot is never blank.
- Draw only with integer coordinates. Sub-pixel positions turn into shimmering
  edges after the 6× upscale.

## 2. Framebuffer and palette

`W=320`, `H=180`, `SCALE=6` → 1920×1080 at 24 fps. One byte per pixel, values
are palette indices; `T=255` means transparent.

- `new FB()` owns a `Uint8Array(320*180)` and a clip rectangle.
- Always `fb.clear(C.someColour)`. `clear(T)` leaves 255s and the output LUT has
  no useful colour there.
- The palette starts as ENDESGA-32 plus seven custom colours (indices 32–38).
  `PROTECT` holds those custom indices so grading LUTs never remap them — they
  are your "always readable" lights, UI accents, and skin highlights.
- Retune the palette per film. Keep ≤ 40 colours, at least five values between
  your darkest and lightest plane, and avoid large pure-black areas. A night
  scene still needs a readable silhouette: give the subject one edge light.

### Grading without alpha

Colour grading is a palette swap, not a filter:

| LUT | Use |
|---|---|
| `LUT.full` | normal |
| `LUT.storm` | cold/rain/flashback |
| `LUT.c16`, `c8`, `c4`, `c2` | progressive collapse / signal loss |
| `darken(LUT.full, f)` | fades, quantised in 4 steps |
| `whiten(LUT.full, f)` | flash, memory, stage light |

`out.present(fb, lutA, lutB, pick)` selects per pixel, so a collapse can spread
across the frame with a Bayer threshold. `out.post(fn)` edits the packed RGBA
buffer after palette lookup (`mosaic(u32, n)` is provided). Call `out.show()`
last.

## 3. Drawing API

All coordinates are framebuffer pixels.

```js
fb.px(x, y, c)                  // skips T and clipped pixels
fb.rect(x, y, w, h, c)
fb.hline(x0, x1, y, c); fb.vline(x, y0, y1, c)
fb.line(x0, y0, x1, y1, c)      // Bresenham
fb.disc(cx, cy, r, c); fb.ellipse(cx, cy, rx, ry, c)
fb.dither(x0, y0, w, h, f, a, b)      // f(x,y) → 0..1
fb.gradV(x0, y0, w, h, [c0..cn])      // vertical Bayer gradient
fb.blit(sprite, dx, dy, flip, map)    // map: palette remap for time of day
fb.blitScale(sprite, dx, dy, s, flip)
fb.copy(src, sx, sy, sw, sh, dx, dy)
```

`sprFromRows(['..##', '.##.'], { '#': C.ink })` builds sprites from ASCII art;
`.` and space are transparent. Build sprites once at module load — not per
frame.

Order matters. A classic bug: draw the moon halo **before** the moon disc,
otherwise the halo erases it. Same for lamps, windows, and character rim light.

## 4. Text

### Latin

`font.js` is an original 5×7 variable-width bitmap font (line height 10).

```js
text(fb, s, x, y, col, shadow, scale)
textW(s, scale)
textOutlined(fb, s, x, y, col, outline, scale)
wrap(s, maxWidthPx)
```

It covers A–Z, a–z, digits, common punctuation, `♥ ▶ ▼ × ·`. Unknown
characters render as `?`. A one-pixel shadow or outline is mandatory over busy
backgrounds.

### Chinese

`genfont.py` scans `lyrics.json`, `events.json`, `TREATMENT.md`, `CREDITS`,
`project.env`, and the engine JS (excluding `font_zh.js`), then bakes exactly
those glyphs from GNU Unifont into `engine/font_zh.js`:

```js
ZH_N                 // 0 when no glyphs
zhText(fb, s, x, y, col, shadow, scale)
zhTextW(s, scale)
zhWrap(s, maxWidthPx, scale)   // CJK-aware
zhOutlined(...)
```

The template imports `font_zh.js` dynamically and only switches to the CJK path
when `ZH_N > 0`, so a Latin-only film never pays for it. Chinese glyphs are
16 px; at scale 1 that is 96 px tall on a 1080p screen. Consequences:

- One subtitle line: 9–10 characters maximum; wrap at 286 px; cap at **2 lines**.
- Place subtitles at `y ≈ 150–176`, centred, with a 1 px dark outline.
- Never subtitle over a face. Compose the shot with a bottom-safe area.
- Do not mix Latin and CJK inside one line; pick one renderer per cue.

If a glyph is missing the build must fail, not silently print boxes. Run
`genfont.py --check` after any text edit.

## 5. Shot construction

Structure `main.js` as a set of pure shot functions plus one dispatcher:

```js
function renderAt(t) {
  world(t);               // persistent world layer
  if (t < 4) titleCard(t);
  else if (t < 34) room(t);
  // ...
  lyric(t);               // always on top, except title cards
  out.present(fb, LUT.full);
  out.show();
}
```

Practical guidance:

- **Three shot scales.** Wide (character 16–40 px tall), medium (60–90 px), and
  close-up (100–150 px). Wide shots carry the world; close-ups are reserved for
  chorus and ending.
- **Cut on the beat.** 128 BPM at 24 fps = 11.25 frames per beat. Convert cue
  times to frames with `Math.round(t * 24)` and cut on multiples where possible.
- **Parallax in whole pixels.** Background 0.25×, midground 0.5×, foreground 1×
  of the camera offset; round each layer independently or it will crawl.
- **Limit full-screen loops.** 57,600 pixels is cheap, but per-pixel trig for
  water and star fields several times per frame adds up over a few thousand
  frames. Use hash tables and integer stepping; precompute static layers into
  an offscreen `FB` and blit them.
- **Transitions.** Hard cuts, palette-step fades, and `mosaic()` are enough.
  Reserve dissolves for three moments at most.
- **HUD restraint.** A 1 px border, 8 px margin, two lines of metadata. It must
  never compete with the lyric line or the character's eyes.
- **One poster frame, three shapes.** Cover variants are crops of the 16:9
  poster, never independent renders; that keeps the same frame and grade.
  `make_covers.py` returns to the 320×180 grid, crops, then upscales 8×:
  - 4:3 keeps 240 of 320 columns → 1920×1440;
  - 3:4 keeps 135 of 320 columns (42%) → 1080×1440.

  `COVER_X` (0 = left, 0.5 = centre, 1 = right) slides the window. At
  `POSTER_T`, keep the face, the key prop, and any title inside the chosen
  135-column band. A crop cannot invent pixels: if two characters stand far
  apart, the 3:4 cover will cut one of them — reframe the coda shot or use a
  tighter poster moment instead of shipping a bad crop.

## 6. Look proof before animation

Render stills at the moments that carry the film, not random times:

```bash
node "$LIB/core/render/still.mjs" "$PROJ" 1.2 10.5 43.0 87.5 178.0 --prefix look_
# → stills/look_1.2.jpg ...
```

Check, in this order: silhouette readability, value separation, subtitle
legibility, palette harmony, character likeness. Fix the stills before
rendering 4,000 frames. A look that only works in motion is usually hiding a
weak composition.

## 7. Determinism and performance checklist

- No globals mutated during `render`; caches keyed by integer frame are fine.
- No `Math.random`, no `performance.now`, no `fetch` inside `render`.
- `ctx.imageSmoothingEnabled = false` (already set by `makeOut`).
- Every frame ends with exactly one `present` + `show`.
- Text and sprites are built once at module scope.
- Reuse framebuffers; do not allocate per frame.
- If a frame takes > 60 ms, the renderer's worker throughput drops. Profile
  before adding another full-screen effect.

## 8. Files

| File | Role |
|---|---|
| `engine/px.js` | framebuffer, palette, LUTs, dither, sprites, output |
| `engine/font.js` | original Latin bitmap font |
| `engine/font_zh.js` | generated CJK subset (never hand-edit) |
| `engine/main.js` | shots, HUD, subtitles, page contract |
| `index.html` | 1920×1080 canvas, module entry |
| `tools/genfont.py` | scans text, bakes subset, `--check` |
