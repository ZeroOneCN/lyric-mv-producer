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

- One subtitle line: 10 characters maximum; cap at **2 lines** per cue.
- Do not mix Latin and CJK inside one line; pick one renderer per cue.

If a glyph is missing the build must fail, not silently print boxes. Run
`genfont.py --check` after any text edit.

## 4b. The fixed caption (`engine/caption.js`)

Every film draws lyrics through one component, so the subtitle presentation is a
house style rather than a per-project invention. The geometry is not
configurable and lives in `engine/px.js`:

| | |
|---|---|
| Lane | rows `LANE_TOP=142` … `LANE_BOT=176`, full width — the bottom safe area |
| Width | `CAP_MAXW=286` px (17 px of margin each side) |
| Lines | `CAP_LINES=2` maximum; a cue that needs a third line is a bad cue |
| CJK | `CAP_CJK=10` characters per line, punctuation pulled up off the line head |
| Type | 1 px ink outline; `C.bwhite` once settled, `C.silver` during the fade-in |
| Motion | `SUB_FADE` (0.18 s default) fade-in only; no lift, no typewriter |

```js
const cfg = captionCfg(env, ZH);          // from project.env + font_zh.js
drawCaption(fb, t, SUBS, cfg);            // bar | bubble | plain
captionLines(cue, cfg);                   // null = does not fit the lane
```

`SUB_STYLE` is the only look choice: `bar` (a Bayer-dithered `C.ink` lane across
the frame, density `SUB_DENS`), `bubble` (a per-line plate, no full-width band),
or `plain` (text only — the lane still belongs to the caption). `tools/check_subs.js`
validates every cue against the same module the renderer imports, and `build.sh`
runs it before rendering, so a too-long line fails the build instead of arriving
on screen.

Because the lane is reserved, a shot must not put a face, a hand or the key prop
below row 142 while a cue is on screen. `main.js` exports `hasCaption(t)` for
that test; `drawChar()` clamps a sprite's feet to the lane top by default.

## 4c. Character from a reference image

The sprite stays code-drawn; a reference image only shortens the route to it.

```bash
python tools/char_ref.py character/ref_hero.png --project .   # needs pillow
```

It keys out a flat background, trims, then quantises the figure into the film's
own palette (top `--colours`, default 8) at 12x16 / 16x24 / 24x32 / 32x48, and
writes into `character/`:

- `draft_WxH.png` (+ `@4` previews) and `sheet.png` — look at these at 100%;
- `rows_WxH.txt` — the draft as `sprFromRows` ASCII rows plus a `MAP` of `C.*`
  names, ready to paste into `engine/main.js`;
- `lookbook.md` — aspect, ink pixel count, colours used per grid.

Pick the smallest grid whose silhouette still reads, then **redraw** it: cut
colours, fix the eye line near the top third, and keep one detail that identifies
the character at 16 px. `character/ref_*`, drafts and lookbook are private
working material (the folder ships a `.gitignore`); `CREDITS` must disclose that
a reference image was used, and `check_delivery.py` fails if it does not.

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
legibility inside the lane, palette harmony, character likeness. Fix the stills
before rendering 4,000 frames. A look that only works in motion is usually hiding
a weak composition.

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
| `engine/px.js` | framebuffer, palette, LUTs, dither, sprites, output, lane geometry |
| `engine/font.js` | original Latin bitmap font |
| `engine/font_zh.js` | generated CJK subset (never hand-edit) |
| `engine/caption.js` | the fixed lyric caption: lane, wrap, bar/bubble/plain |
| `engine/main.js` | shots, HUD, character sprites, page contract |
| `index.html` | 1920×1080 canvas, module entry |
| `tools/genfont.py` | scans text, bakes subset, `--check` |
| `tools/check_subs.js` | proves every cue fits the fixed lane (same module as the render) |
| `tools/char_ref.py` | reference image → palette-quantised sprite drafts + ASCII rows |
