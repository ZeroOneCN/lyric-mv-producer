// main.js — deterministic page for a code-drawn lyric MV.
// Renderer contract: window.DUR / window.render(t) / window.READY / window.SUBS / window.EV.
import { W, FB, C, LUT, makeOut, bayer, hash, clamp, ss } from './px.js';
import { text, textW, textOutlined, wrap } from './font.js';

const canvas = document.getElementById('c');
const fb = new FB();
const out = makeOut(canvas);

let CFG = {
  SLUG: 'my-lyric-mv', TITLE: 'MY LYRIC MV', SUBTITLE: 'A CODE-DRAWN FAN FILM',
  DUR: 24, POSTER_T: 20,
};
let SUBS = [], EV = [], ZH = null;

function parseEnv(txt) {
  const o = {};
  for (const line of txt.split(/\r?\n/)) {
    const s = line.trim();
    if (!s || s.startsWith('#') || !s.includes('=')) continue;
    const i = s.indexOf('=');
    o[s.slice(0, i).trim()] = s.slice(i + 1).trim().replace(/^["']|["']$/g, '');
  }
  return o;
}

function hasCJK(s) { return [...s].some(ch => ch.codePointAt(0) >= 0x2e80); }

function centeredLatin(s, y, col, shadow, sc = 1) {
  text(fb, s, Math.round((W - textW(s, sc)) / 2), y, col, shadow, sc);
}

function centeredText(s, y, col, shadow, sc = 1) {
  if (ZH && hasCJK(s)) {
    const lines = ZH.zhWrap(s, 286, sc);
    lines.forEach((line, i) => ZH.zhText(fb, line, Math.round((W - ZH.zhTextW(line, sc)) / 2),
      y + i * 18 * sc, col, shadow, sc));
  } else {
    centeredLatin(s, y, col, shadow, sc);
  }
}

const STARS = Array.from({ length: 54 }, (_, i) => ({
  x: Math.floor(hash(i, 101) * W),
  y: 8 + Math.floor(hash(i, 102) * 66),
  p: hash(i, 103),
}));

function skyline(seed, baseY, minH, maxH) {
  const out = [];
  let x = -8, i = 0;
  while (x < W + 8) {
    const w = 10 + Math.floor(hash(i, seed) * 16);
    const h = minH + Math.floor(hash(i, seed + 1) * (maxH - minH));
    const wins = [];
    for (let wy = baseY - h + 4; wy < baseY - 3; wy += 5)
      for (let wx = x + 3; wx < x + w - 2; wx += 4)
        if (hash(wx, wy, seed) > .55) wins.push({ x: wx, y: wy, p: hash(wx, wy, seed + 7) });
    out.push({ x, y: baseY - h, w, h, wins });
    x += w + 1 + Math.floor(hash(i, seed + 3) * 3);
    i++;
  }
  return out;
}

const FAR = skyline(11, 130, 14, 42);
const NEAR = skyline(29, 152, 22, 58);

function drawSkyline(list, body, edge, winA, winB, t, lit) {
  for (const b of list) {
    fb.rect(b.x, b.y, b.w, b.h, body);
    fb.hline(b.x, b.x + b.w - 1, b.y, edge);
    for (const win of b.wins) {
      if (hash(win.x, win.y, 5) > lit) continue;
      if (Math.sin(t * 1.7 + win.p * 9) < -.82) continue;
      fb.rect(win.x, win.y, 1, 2, win.p > .55 ? winA : winB);
    }
  }
}

function nightScene(t) {
  fb.gradV(0, 0, W, 150, [C.ink, C.night, C.navy]);
  for (const s of STARS) {
    const tw = .5 + .5 * Math.sin(t * 1.3 + s.p * 8);
    if (tw > .62) fb.px(s.x, s.y, C.bwhite);
    else if (tw > .28) fb.px(s.x, s.y, C.steel);
  }
  fb.disc(248, 34, 18, C.navy);
  fb.disc(248, 34, 14, C.pale);
  fb.disc(252, 31, 13, C.night);

  drawSkyline(FAR, C.dslate, C.slate, C.steel, C.steel, t, .22);
  drawSkyline(NEAR, C.ink, C.dslate, C.amber, C.warm, t, .52);
  fb.rect(0, 150, W, 30, C.ink);

  // window frame
  fb.rect(0, 0, 15, 180, C.umber);
  fb.rect(305, 0, 15, 180, C.umber);
  fb.rect(0, 0, W, 7, C.umber);
  fb.hline(0, W, 7, C.brown);
  fb.rect(0, 74, W, 5, C.umber);
  fb.hline(0, W, 74, C.brown);
  fb.hline(0, W, 78, C.dbrown);

  // curtain
  for (let y = 7; y < 150; y++) {
    const edge = 34 + Math.round(Math.sin(y * .09 + t * .5) * 4 + Math.sin(y * .21 - t * .3) * 2);
    fb.rect(15, y, edge - 15, 1, (y / 9 | 0) % 2 ? C.umber : C.brown);
    fb.px(edge, y, C.dbrown);
  }

  // hanging paper moon
  const sway = Math.round(Math.sin(t * .8) * 2);
  fb.vline(88 + sway, 7, 36, C.slate);
  fb.disc(88 + sway, 41, 5, C.warm);
  fb.disc(90 + sway, 39, 4, C.ink);

  // sill and plant
  fb.rect(0, 150, W, 30, C.dbrown);
  fb.hline(0, W, 150, C.brown);
  fb.hline(0, W, 151, C.umber);
  fb.rect(42, 136, 22, 14, C.brown);
  fb.rect(43, 137, 20, 12, C.umber);
  fb.rect(46, 148, 14, 2, C.dbrown);
  for (let i = 0; i < 5; i++) {
    const lx = 48 + i * 3, ly = 136 - (i % 3) * 4;
    fb.line(53, 137, lx, ly, i % 2 ? C.green : C.dgreen);
    fb.px(lx, ly, C.lime);
  }
  fb.rect(236, 138, 24, 12, C.ink);
  fb.rect(237, 139, 22, 10, C.night);
  fb.hline(240, 256, 141, C.amber);
  fb.rect(240, 144, 16, 2, C.dslate);
}

function titleCard(t) {
  const a = ss(0, .7, t) * (1 - ss(3.1, 3.8, t));
  if (a < .08) return;
  const col = a > .55 ? C.bwhite : C.silver;
  const y = 62 - Math.round((1 - a) * 3);
  if (ZH && hasCJK(CFG.TITLE)) {
    ZH.zhOutlined(fb, CFG.TITLE, Math.round((W - ZH.zhTextW(CFG.TITLE, 2)) / 2), y, col, C.ink, 2);
  } else {
    textOutlined(fb, CFG.TITLE, Math.round((W - textW(CFG.TITLE, 2)) / 2), y, col, C.ink, 2);
  }
  centeredText(CFG.SUBTITLE, y + 26, C.steel, C.ink, 1);
  fb.hline(W / 2 - 34, W / 2 + 34, y + 40, C.amber);
}

function hud(t) {
  text(fb, CFG.SLUG.toUpperCase().slice(0, 26), 20, 8, C.steel, C.ink, 1);
  const tc = `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
  text(fb, tc, W - 20 - textW(tc, 1), 8, C.steel, C.ink, 1);
  if (bayer(20, 18) < .5) fb.rect(20, 18, 3, 3, C.amber);
}

function lineAt(t) {
  for (const cue of SUBS) if (t >= cue.t0 && t < cue.t1) return cue;
  return null;
}

function lyric(t) {
  const cue = lineAt(t);
  if (!cue) return;
  const p = ss(cue.t0, cue.t0 + .22, t);
  if (p < .05) return;
  const col = p > .6 ? C.bwhite : C.silver;
  const zh = ZH && hasCJK(cue.text);
  const lines = zh ? ZH.zhWrap(cue.text, 286, 1).slice(0, 2) : wrap(cue.text, 286).slice(0, 3);
  const y0 = 158 - (lines.length - 1) * 9 + Math.round((1 - p) * 2);
  lines.forEach((line, i) => {
    if (ZH && hasCJK(cue.text)) {
      ZH.zhText(fb, line, Math.round((W - ZH.zhTextW(line, 1)) / 2), y0 + i * 18, col, C.ink, 1);
    } else {
      centeredLatin(line, y0 + i * 10, col, C.ink, 1);
    }
  });
}

function titleScene(t) {
  fb.gradV(0, 0, W, H, [C.ink, C.night, C.navy]);
  for (const s of STARS) {
    const tw = .5 + .5 * Math.sin(t * 1.1 + s.p * 8);
    if (tw > .6) fb.px(s.x, s.y + 20, C.bwhite);
    else if (tw > .25) fb.px(s.x, s.y + 20, C.steel);
  }
  fb.disc(250, 38, 18, C.navy);
  fb.disc(250, 38, 14, C.pale);
  fb.disc(254, 35, 13, C.night);
  fb.hline(0, W, 122, C.teal);
  fb.dither(0, 122, W, 58, () => .55, C.ink, C.night);
}

function renderAt(t) {
  if (t < 4) {
    titleScene(t);
    titleCard(t);
  } else {
    nightScene(t);
    hud(t);
    lyric(t);
  }
  out.present(fb, LUT.full);
  out.show();
}

async function boot() {
  try {
    const env = parseEnv(await (await fetch(new URL('../project.env', import.meta.url))).text());
    for (const k of Object.keys(CFG)) if (env[k] !== undefined) CFG[k] = env[k];
    CFG.DUR = parseFloat(CFG.DUR) || 24;
    CFG.POSTER_T = parseFloat(CFG.POSTER_T) || CFG.DUR * .8;
  } catch (e) { console.warn('project.env not loaded, using defaults', e); }
  try {
    SUBS = await (await fetch(new URL('../lyrics.json', import.meta.url))).json();
  } catch (e) { console.warn('lyrics.json not loaded', e); }
  try {
    const doc = await (await fetch(new URL('../events.json', import.meta.url))).json();
    EV = doc.ev || [];
  } catch (e) { console.warn('events.json not loaded', e); }
  try {
    const m = await import('./font_zh.js');
    if (m.ZH_N > 0) ZH = m;
  } catch (e) { /* Latin-only film */ }
  window.DUR = CFG.DUR;
  window.SUBS = SUBS.map(c => ({ t0: c.t0, t1: c.t1, text: c.text }));
  window.EV = EV;
  window.EXTRA = { slug: CFG.SLUG, title: CFG.TITLE, posterT: CFG.POSTER_T };
  window.render = t => {
    try { renderAt(clamp(t, 0, CFG.DUR - .001)); }
    catch (e) { console.error(e); throw e; }
  };
  window.READY = true;
  renderAt(0);
}

boot();
