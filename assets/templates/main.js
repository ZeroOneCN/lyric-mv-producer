// main.js — deterministic page for a code-drawn lyric MV.
// Renderer contract: window.DUR / window.render(t) / window.READY / window.SUBS / window.EV.
import { W, H, FB, C, LUT, makeOut, bayer, hash, clamp, ss, sprFromRows, OW, OH, T } from './px.js';
import { text, textW, textOutlined } from './font.js';
import { captionCfg, drawCaption, unsegmentable, OVERFLOW } from './caption.js';
import { drawCover, shapeOf } from './cover.js';

const canvas = document.getElementById('c');
const fb = new FB();                 // 画面 320×180
const ov = new FB(OW, OH);           // 字幕置顶层 640×360，最后压在画面上

// 封面模式：同一个页面用 ?cover=4x3|3x4|16x9 换成封面的格子上作画。
// 渲染命令见 tools/make_covers.py；封面上必须写歌名。
const Q = new URLSearchParams(location.search);
const COVER = shapeOf(Q.get('cover'));
const cfb = COVER ? new FB(COVER.gw, COVER.gh) : null;
const out = COVER ? makeOut(canvas, COVER.gw, COVER.gh, COVER.sc, false) : makeOut(canvas);

let CFG = {
  SLUG: 'my-lyric-mv', TITLE: 'MY LYRIC MV', SUBTITLE: 'A CODE-DRAWN LYRIC FILM',
  DUR: 24, POSTER_T: 20, SUB_STYLE: 'plate', SUB_DENS: '0.45', SUB_FADE: '0.18',
  COVER_TYPE: 'band', COVER_DENS: '', COVER_ARTIST: '', COVER_TAGLINE: '',
};
let SUBS = [], EV = [], ZH = null, CAP = null;

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
  // 街面一直铺到画面底边：字幕是压在画面上的置顶层，画面本身不留底部空带
  fb.rect(0, 150, W, H - 150, C.night);
  fb.hline(0, W, 150, C.deepD);
  for (let i = 0; i < 22; i++) {
    const x = Math.floor(hash(i, 61) * W), y = 154 + Math.floor(hash(i, 62) * 22);
    fb.hline(x, x + 3 + Math.floor(hash(i, 63) * 9), y, hash(i, 64) > .6 ? C.warm : C.slate);
  }

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

function lyric(t) {
  const r = drawCaption(ov, t, SUBS, CAP);
  if (r === OVERFLOW) {
    throw new Error(`caption overflow near ${t.toFixed(2)}s: this lyric line cannot be read `
      + 'as one caption — split the cue in lyrics.json; the caption geometry is fixed');
  }
}

// —— 角色（小人）——
// 参考图只用于起草：`python tools/char_ref.py <ref> --project .` 会在 character/
// 生成量化草稿与行稿。最终精灵仍是由下面这些行字符串代码绘制的原创像素。
export const CHAR = {
  h: 24,
  poses: {
    stand: [
      '....dddd....',
      '...dddddd...',
      '...ssssss...',
      '...s.ss.....',
      '....cccc....',
      '..cccccccc..',
      '.cccccccccc.',
      '....c..c....',
      '....w..w....',
    ],
  },
  map: { d: C.dbrown, s: C.skin, c: C.crimson, w: C.ink },
};
const SPR = Object.fromEntries(
  Object.entries(CHAR.poses).map(([k, rows]) => [k, sprFromRows(rows, CHAR.map)]));

// 字幕是压在画面上的置顶层，画面不留底部空带：构图按整幅来排，
// 只是别让脸和关键道具长期停在置顶层覆盖的那几行里。
function drawChar(t, x, groundY, { pose = 'stand', face = 1, scale = 1 } = {}) {
  const spr = SPR[pose];
  if (!spr) return;
  const top = groundY - spr.h * scale;
  fb.blitScale(spr, Math.round(x - (spr.w * scale) / 2), Math.round(top), scale, face < 0);
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
  ov.clear(T);                    // 置顶层每帧清空，字幕只画在当前帧上
  if (t < 4) {
    titleScene(t);
    titleCard(t);
  } else {
    nightScene(t);
    hud(t);
    lyric(t);
  }
  out.present(fb, LUT.full);
  out.presentOverlay(ov, LUT.full);
  out.show();
}

// —— 封面构图 ——
// 每个画幅单独排：坐标用 art 的宽高（封面的格子），不要写死 320×180。
// 把本片的母题重画一遍，主体放在上半部，下半部留给固定的文字带（歌名必画）。
function coverMotif(f, art) {
  const w = art.w, h = art.h;
  f.gradV(0, 0, w, h, [C.ink, C.night, C.navy]);
  for (let i = 0; i < 70; i++) {
    const x = Math.floor(hash(i, 201) * w), y = Math.floor(hash(i, 202) * h * .6);
    if (hash(i, 203) > .55) f.px(x, y, hash(i, 204) > .7 ? C.bwhite : C.steel);
  }
  const mr = Math.max(6, Math.round(w * .1));
  const mx = Math.round(w * .76), my = Math.round(h * .28);
  f.disc(mx, my, mr, C.navy);
  f.disc(mx, my, Math.round(mr * .8), C.pale);
  f.disc(mx + Math.round(mr * .3), my - Math.round(mr * .25), Math.round(mr * .72), C.night);

  const base = Math.round(h * .8);
  let x = 0, i = 0;
  while (x < w) {
    const bw = 8 + Math.floor(hash(i, 301) * 14);
    const bh = 10 + Math.floor(hash(i, 302) * Math.max(8, Math.round(h * .2)));
    f.rect(x, base - bh, bw, bh + 2, C.dslate);
    f.hline(x, x + bw - 1, base - bh, C.slate);
    for (let wy = base - bh + 3; wy < base - 3; wy += 5)
      for (let wx = x + 2; wx < x + bw - 2; wx += 4)
        if (hash(wx, wy, 303) > .66) f.rect(wx, wy, 1, 2, hash(wx, wy, 304) > .5 ? C.amber : C.warm);
    x += bw + 1; i++;
  }
  f.rect(0, base, w, h - base, C.night);
  f.hline(0, w, base, C.deepD);

  const spr = SPR.stand, s = Math.max(1, Math.round(h / 55));
  f.blitScale(spr, Math.round(w * (w < 180 ? .44 : .3)) - Math.round(spr.w * s / 2), base - spr.h * s, s, false);
  // 倒影：湿地上拉几道窗光
  for (let k = 0; k < 10; k++) {
    const rx = Math.floor(hash(k, 401) * w);
    f.vline(rx, base + 2, base + 2 + Math.floor(hash(k, 402) * Math.max(3, h - base - 3)), hash(k, 403) > .5 ? C.warm : C.slate);
  }
}

function renderCover() {
  const proof = drawCover(cfb, COVER, {
    title: CFG.TITLE, artist: CFG.COVER_ARTIST, tagline: CFG.COVER_TAGLINE,
    zh: ZH, typeMode: CFG.COVER_TYPE, dens: CFG.COVER_DENS === '' ? null : parseFloat(CFG.COVER_DENS),
    bare: Q.get('bare') === '1',
    motif: coverMotif,
  });
  out.present(cfb, LUT.full);
  out.show();
  window.COVER = proof;
}

async function boot() {
  try {
    const env = parseEnv(await (await fetch(new URL('../project.env', import.meta.url))).text());
    for (const k of Object.keys(CFG)) if (env[k] !== undefined) CFG[k] = env[k];
    CFG.DUR = parseFloat(CFG.DUR) || 24;
    CFG.POSTER_T = parseFloat(CFG.POSTER_T) || CFG.DUR * .8;
  } catch (e) { console.warn('project.env not loaded, using defaults', e); }
  try {
    const m = await import('./font_zh.js');
    if (m.ZH_N > 0) ZH = m;
  } catch (e) { /* Latin-only film */ }

  // 封面模式：不需要歌词和音效事件，只要格子里能把歌名画对
  if (COVER) {
    window.DUR = 1;
    window.SUBS = [];
    window.EV = [];
    window.EXTRA = { slug: CFG.SLUG, title: CFG.TITLE, cover: { shape: Q.get('cover'), grid: [COVER.gw, COVER.gh], out: COVER.out } };
    window.render = () => { try { renderCover(); } catch (e) { console.error(e); throw e; } };
    window.READY = true;
    renderCover();
    return;
  }

  try {
    SUBS = await (await fetch(new URL('../lyrics.json', import.meta.url))).json();
  } catch (e) { console.warn('lyrics.json not loaded', e); }
  try {
    const doc = await (await fetch(new URL('../events.json', import.meta.url))).json();
    EV = doc.ev || [];
  } catch (e) { console.warn('events.json not loaded', e); }
  CAP = captionCfg(CFG, ZH);

  const bad = unsegmentable(SUBS, CAP);
  if (bad.length) {
    throw new Error(`caption cannot fit one line at ${bad[0].t0}s: ${bad[0].text} `
      + '- split the cue in lyrics.json; run tools/check_subs.js');
  }
  window.DUR = CFG.DUR;
  window.SUBS = SUBS.map(c => ({ t0: c.t0, t1: c.t1, text: c.text }));
  window.EV = EV;
  window.EXTRA = {
    slug: CFG.SLUG, title: CFG.TITLE, posterT: CFG.POSTER_T,
    subStyle: CAP.style, captionLayer: [OW, OH],
  };
  window.render = t => {
    try { renderAt(clamp(t, 0, CFG.DUR - .001)); }
    catch (e) { console.error(e); throw e; }
  };
  window.READY = true;
  renderAt(0);
}

boot();
