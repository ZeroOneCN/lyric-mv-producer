// cover.js — the designed film cover. A cover is NOT a crop of the poster:
// it is its own composition on its own grid, and it always carries the song title.
// One layout law for every film; the artwork (motif) is the film's own job.
import { C, bayer, COVER_SHAPES } from './px.js';
import { text, textW } from './font.js';

export const COVER_PAD = 8;          // 底板到画幅边缘的安全距离（格）
const RULE = C.amber;                // 细线与角标
const PLATE = C.ink;                 // 字底托板
const hasCJK = s => [...s].some(ch => ch.codePointAt(0) >= 0x2e80);

export const shapeOf = name => COVER_SHAPES[String(name || '').toLowerCase()] || null;

const adv = (s, sc, zh) => (zh && hasCJK(s) ? zh.zhTextW(s, sc) : textW(s, sc));
const glyphH = (s, sc, zh) => (zh && hasCJK(s) ? 16 * sc : 7 * sc);

// 在带内找最大的整数倍率：既不能超宽，也不能吃掉整条带
export function fitScale(s, maxW, maxH, zh) {
  for (let sc = 6; sc >= 1; sc--) if (adv(s, sc, zh) <= maxW && glyphH(s, sc, zh) <= maxH) return sc;
  return 1;
}

// —— 版式：图形区 + 底部文字带 ——
// band：图形只画在文字带以上，字带是实底；overlay：图形铺满，字带压在图上。
export function coverLayout(shape, cfg = {}) {
  const g = typeof shape === 'string' ? shapeOf(shape) : shape;
  if (!g) throw new Error(`cover: unknown shape ${shape}`);
  const mode = cfg.typeMode === 'overlay' ? 'overlay' : 'band';
  // 带高要容得下 汉字署名 + 2 倍歌名 + 一句话（汉字行 16 px 起），窄画幅再多留
  const h = Math.round(g.gh * (g.gw < 180 ? .39 : .40));
  const band = { x: COVER_PAD, y: g.gh - COVER_PAD - h, w: g.gw - 2 * COVER_PAD, h };
  const art = mode === 'overlay'
    ? { x: 0, y: 0, w: g.gw, h: g.gh }
    : { x: 0, y: 0, w: g.gw, h: band.y + 4 };
  return { ...g, mode, band, art, out: g.out };
}

function roundedPlate(fb, x, y, w, h, dens, rad = 4) {
  for (let py = y; py < y + h; py++) {
    for (let px = x; px < x + w; px++) {
      const cx = Math.max(x + rad, Math.min(px, x + w - 1 - rad));
      const cy = Math.max(y + rad, Math.min(py, y + h - 1 - rad));
      if ((px - cx) ** 2 + (py - cy) ** 2 > rad * rad) continue;
      if (bayer(px, py) < dens) fb.px(px, py, PLATE);
    }
  }
}

function cornerTicks(fb, L) {
  const t = 6;
  for (const [cx, cy, dx, dy] of [[2, 2, 1, 1], [L.gw - 3, 2, -1, 1], [2, L.gh - 3, 1, -1], [L.gw - 3, L.gh - 3, -1, -1]]) {
    for (let i = 0; i < t; i++) fb.px(cx + dx * i, cy, RULE);
    for (let i = 1; i < 3; i++) fb.px(cx, cy + dy * i, RULE);
  }
}

function center(fb, s, cx, y, sc, col, zh) {
  if (!s) return 0;
  const x = Math.round(cx - adv(s, sc, zh) / 2);
  if (zh && hasCJK(s)) zh.zhText(fb, s, x, y, col, null, sc);
  else text(fb, s, x, y, col, null, sc);
  return adv(s, sc, zh);
}

// 文字带：署名（顶）→ 歌名（中，自动倍率）→ 细线 → 一句话（底）
// 每一行的实际字高都要算进带高：汉字 16 px、拉丁 7 px，混排时不能按拉丁推。
function typeBand(fb, L, title, opts) {
  const zh = opts.zh || null;
  const { x, y, w, h } = L.band;
  const cx = L.gw / 2;
  const artist = String(opts.artist || '').trim();
  const tagline = String(opts.tagline || '').trim();
  const aH = artist ? glyphH(artist, 1, zh) : 0;
  const gH = tagline ? glyphH(tagline, 1, zh) : 0;
  const chrome = 3 + (aH ? aH + 2 : 0) + 2 + 1 + (gH ? 2 + gH : 0) + 3;
  const sc = fitScale(title, w - 6, Math.max(8, h - chrome), zh);
  if (adv(title, sc, zh) > w - 4) throw new Error(`cover: title "${title}" does not fit a ${w}px band`);

  roundedPlate(fb, x, y, w, h, opts.dens == null ? (L.mode === 'overlay' ? .62 : .9) : opts.dens);
  let ty = y + 3;
  if (artist) { center(fb, artist, cx, ty, 1, C.silver, zh); ty += aH + 2; }
  const th = glyphH(title, sc, zh);
  const zone = h - (ty - y) - (2 + 1 + (gH ? 2 + gH : 0) + 3);
  const titleY = ty + Math.max(0, Math.round((zone - th) / 2));
  center(fb, title, cx, titleY, sc, C.bwhite, zh);
  const lineY = y + h - (gH ? 2 + gH + 2 : 3);
  const rw = Math.max(24, Math.round(adv(title, sc, zh) * .55));
  fb.hline(Math.round(cx - rw / 2), Math.round(cx + rw / 2), lineY, RULE);
  if (tagline) center(fb, tagline, cx, lineY + 2, 1, C.steel, zh);
  return { titleScale: sc, titleW: adv(title, sc, zh), titleY };
}

// —— 主入口 ——
// opts: { title, artist, tagline, zh, typeMode, dens, bare, motif(fb, art, L) }
// bare=true 画一张没有字的封面，make_covers.py 用它和成图比对，证明歌名真的画上去了。
// 返回值写进 out/covers.json，交付检查靠它确认封面上确实是这首歌的名字。
export function drawCover(fb, shape, opts = {}) {
  const L = coverLayout(shape, opts);
  const title = String(opts.title || '').trim();
  if (!title) throw new Error('cover: a cover must carry the song title; TITLE is empty');
  fb.clear(C.ink);
  if (opts.motif) {
    // 图形被夹在图形区里：构图怎么画都不会溢进文字带，这是封面能固定的前提
    fb.clip = [L.art.x, L.art.y, L.art.w, L.art.h];
    opts.motif(fb, L.art, L);
    fb.clip = [0, 0, L.gw, L.gh];
  }
  const t = opts.bare ? { bare: true } : typeBand(fb, L, title, opts);
  cornerTicks(fb, L);
  return { ...t, title, band: L.band.h, mode: L.mode, grid: `${L.gw}x${L.gh}`, out: L.out };
}
