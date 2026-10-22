// px.js — indexed-colour pixel engine (adapted from Lemo-Opuscar's pixel-rpg demo, MIT).
// 320×180 framebuffer of palette indices; depth / fade / collapse / flood are lookup-table swaps, like a SNES CGRAM.
export const W = 320, H = 180, SCALE = 6;
export const T = 255;                      // 透明

// —— 字幕置顶层（固定几何，全片唯一一套）——
// 字幕画在 2 倍分辨率的置顶层上，压在整幅画面之上：画面不再为字幕留底部空带。
// 一个汉字 16 层像素 = 8 画面像素 = 1080p 下 48 px；拉丁按 2 倍画，视觉同高。
export const OV = 2;                              // 置顶层相对画面的倍率
export const OW = W * OV, OH = H * OV;            // 640×360
export const CAP_MAXW = 560;                      // 一行文字可用宽（层像素，两侧各 40）
export const CAP_LINES = 1;                       // 一行一条，长了按时间切成先后两段
export const CAP_CJK = 32;                        // 单行汉字上限
export const CAP_BASE = 336;                      // 单行字幕的文字顶边（层像素，画面第 168 行）
export const CAP_MINSEG = 0.9;                    // 切段后每段最短可读时长（秒）

// —— 封面画幅（与画面同格：1 格 = 1 画面像素，方形像素不拉伸）——
// 封面不是海报的裁切，而是按画幅单独设计的构图，必须带歌名。
// 高度都取 180 格，所以同一套精灵在三张封面里的相对大小一致。
export const COVER_SHAPES = {
  '4x3': { gw: 240, gh: 180, sc: 8, out: [1920, 1440] },
  '3x4': { gw: 135, gh: 180, sc: 8, out: [1080, 1440] },
  '16x9': { gw: W, gh: H, sc: SCALE, out: [1920, 1080] },
};
export const coverShape = name => COVER_SHAPES[String(name).toLowerCase()];

// —— 主调色板：ENDESGA-32（0–31）+ 保护色（32+，褪色表不动它们）——
const HEX = [
  '#be4a2f', '#d77643', '#ead4aa', '#e4a672', '#b86f50', '#733e39', '#3e2731', '#a22633',
  '#e43b44', '#f77622', '#feae34', '#fee761', '#63c74d', '#3e8948', '#265c42', '#193c3e',
  '#124e89', '#0099db', '#2ce8f5', '#ffffff', '#c0cbdc', '#8b9bb4', '#5a6988', '#3a4466',
  '#262b44', '#181425', '#ff0044', '#68386c', '#b55088', '#f6757a', '#e8b796', '#c28569',
  // 32–38: optional accent colours; swap them for your film's own accents.
  '#4d6bfe', '#2b3ea8', '#9db4ff', '#f4f7ff', '#ffe2a8', '#cfe0ff', '#6f8cff',
];
export const C = {
  rust: 0, clay: 1, sand: 2, tan: 3, brown: 4, dbrown: 5, umber: 6, crimson: 7, red: 8, orange: 9, amber: 10, yellow: 11,
  lime: 12, green: 13, dgreen: 14, teal: 15, navy: 16, blue: 17, cyan: 18, white: 19, silver: 20, steel: 21, slate: 22,
  dslate: 23, night: 24, ink: 25, hot: 26, plum: 27, rose: 28, pink: 29, skin: 30, skinS: 31,
  deep: 32, deepD: 33, deepL: 34, bwhite: 35, warm: 36, pale: 37, deepM: 38,
};
export const NPAL = HEX.length;
export const PROTECT = new Set([32, 33, 34, 35, 36, 37, 38]);
const rgb = h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
export const RGB = HEX.map(rgb);
const lum = ([r, g, b]) => .299 * r + .587 * g + .114 * b;
const pack = ([r, g, b]) => (255 << 24) | (b << 16) | (g << 8) | r;

// 查找表 = Uint32Array(256)：索引 → ABGR
function lutFrom(fn) { const L = new Uint32Array(256); for (let i = 0; i < NPAL; i++) L[i] = pack(fn(i)); return L; }
function nearest(c, set) {
  let best = set[0], bd = 1e9;
  for (const s of set) { const d = (c[0] - s[0]) ** 2 * .3 + (c[1] - s[1]) ** 2 * .59 + (c[2] - s[2]) ** 2 * .11; if (d < bd) { bd = d; best = s; } }
  return best;
}
// 按亮度分位映射到一条色带（保证层次不丢）
function rampMap(ramp, keep) {
  const Ls = RGB.map(lum), sorted = [...Ls].sort((a, b) => a - b);
  return lutFrom(i => {
    if (keep && PROTECT.has(i)) return RGB[i];
    const q = sorted.indexOf(Ls[i]) / (sorted.length - 1);
    return rgb(ramp[Math.min(ramp.length - 1, Math.floor(q * ramp.length))]);
  });
}

export const LUT = {};
LUT.full = lutFrom(i => RGB[i]);
// Storm: cool grey-blue 10-step ramp; the protected accents stay unaffected.
const STORM_RAMP = ['#0b0f17', '#141a26', '#1c2434', '#273247', '#34425b', '#455570', '#5b6b87', '#76859e', '#94a1b6', '#b7c1d2'];
LUT.storm = rampMap(STORM_RAMP, true);
// 色彩塌缩：16 → 8 → 4 → 2（保护色始终保留）
LUT.c16 = rampMap(['#080d18', '#0d1422', '#131c2f', '#1a263d', '#22324d', '#2c3f5e', '#394d70', '#485d82', '#596e94', '#6c81a6', '#8296b8', '#9aaac8', '#b3c0d8', '#ccd5e6', '#e2e8f2', '#f4f7fb'], true);
LUT.c8 = rampMap(['#090e19', '#111a2c', '#1b2742', '#28385a', '#3a4d74', '#54688f', '#7d90af', '#b1bfd6'], true);
LUT.c4 = rampMap(['#0c1222', '#202e4f', '#4a5f8c', '#b4c1da'], true);
LUT.c2 = rampMap(['#0b1222', '#7183a6'], true);
// 旧名字保留给复用代码
LUT.faded = LUT.storm;
LUT.nes = LUT.c16;
// 淡入淡出：整体压暗 n 级（调色板步进，而不是 alpha）
export function darken(L, f) {   // f 0..1，按 4 级量化
  const q = Math.round(f * 4) / 4, O = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    const v = L[i]; if (!v) continue;
    const r = v & 255, g = v >> 8 & 255, b = v >> 16 & 255;
    O[i] = pack([r * (1 - q) | 0, g * (1 - q) | 0, b * (1 - q) | 0]);
  }
  return O;
}
export function whiten(L, f) {
  const q = Math.round(f * 4) / 4, O = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    const v = L[i]; if (!v) continue;
    const r = v & 255, g = v >> 8 & 255, b = v >> 16 & 255;
    O[i] = pack([r + (255 - r) * q | 0, g + (255 - g) * q | 0, b + (255 - b) * q | 0]);
  }
  return O;
}

// —— 4×4 Bayer ——
const B4 = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
export const bayer = (x, y) => (B4[(y & 3) * 4 + (x & 3)] + .5) / 16;
const B8 = (() => { const m = new Float32Array(64);
  const base = [0, 32, 8, 40, 2, 34, 10, 42, 48, 16, 56, 24, 50, 18, 58, 26, 12, 44, 4, 36, 14, 46, 6, 38, 60, 28, 52, 20, 62, 30, 54, 22, 3, 35, 11, 43, 1, 33, 9, 41, 51, 19, 59, 27, 49, 17, 57, 25, 15, 47, 7, 39, 13, 45, 5, 37, 63, 31, 55, 23, 61, 29, 53, 21];
  for (let i = 0; i < 64; i++) m[i] = (base[i] + .5) / 64; return m; })();
export const bayer8 = (x, y) => B8[(y & 7) * 8 + (x & 7)];

export function hash(x, y = 0, z = 0) { let h = (x * 374761393 + y * 668265263 + z * 2147483647) | 0; h = (h ^ (h >>> 13)) * 1274126177; return ((h ^ (h >>> 16)) >>> 0) / 4294967296; }
export function vnoise(x) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return hash(i) * (1 - u) + hash(i + 1) * u; }
export const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
export const lerp = (a, b, t) => a + (b - a) * t;
export const ss = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
export const eo = t => 1 - (1 - t) * (1 - t);
export const eio = t => t < .5 ? 2 * t * t : 1 - 2 * (1 - t) * (1 - t);

// —— 帧缓冲 ——
export class FB {
  constructor(w = W, h = H) { this.w = w; this.h = h; this.d = new Uint8Array(w * h); this.clip = [0, 0, w, h]; }
  clear(c = 0) { this.d.fill(c); }
  px(x, y, c) { x |= 0; y |= 0; const [cx, cy, cw, ch] = this.clip; if (x < cx || y < cy || x >= cw || y >= ch || c === T) return; this.d[y * this.w + x] = c; }
  get(x, y) { x |= 0; y |= 0; if (x < 0 || y < 0 || x >= this.w || y >= this.h) return T; return this.d[y * this.w + x]; }
  rect(x, y, w, h, c) { x = Math.round(x); y = Math.round(y); w = Math.round(w); h = Math.round(h); for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) this.px(x + i, y + j, c); }
  hline(x0, x1, y, c) { for (let x = Math.round(x0); x <= Math.round(x1); x++) this.px(x, y, c); }
  vline(x, y0, y1, c) { for (let y = Math.round(y0); y <= Math.round(y1); y++) this.px(x, y, c); }
  line(x0, y0, x1, y1, c) {
    x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1);
    const dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1; let e = dx + dy;
    for (;;) { this.px(x0, y0, c); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 >= dy) { e += dy; x0 += sx; } if (e2 <= dx) { e += dx; y0 += sy; } }
  }
  disc(cx, cy, r, c) { for (let y = Math.floor(-r); y <= r; y++) for (let x = Math.floor(-r); x <= r; x++) if (x * x + y * y <= r * r + r * .8) this.px(cx + x, cy + y, c); }
  ellipse(cx, cy, rx, ry, c) {
    for (let y = Math.ceil(cy - ry); y <= Math.floor(cy + ry); y++) {
      const dy = (y - cy) / ry; if (Math.abs(dy) > 1) continue;
      const w = rx * Math.sqrt(Math.max(0, 1 - dy * dy));
      for (let x = Math.round(cx - w); x <= Math.round(cx + w); x++) this.px(x, y, c);
    }
  }
  // 抖动填充：f(x,y) 返回 0..1，按 Bayer 在 a/b 两色之间取
  dither(x0, y0, w, h, f, a, b) { for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const X = x0 + x, Y = y0 + y; this.px(X, Y, bayer(X, Y) < f(X, Y) ? b : a); } }
  // 竖向多色抖动渐变
  gradV(x0, y0, w, h, cols) {
    const n = cols.length - 1;
    for (let y = 0; y < h; y++) {
      const v = y / Math.max(1, h - 1) * n, b = Math.min(n - 1, Math.floor(v)), f = v - b;
      for (let x = 0; x < w; x++) this.px(x0 + x, y0 + y, cols[bayer(x0 + x, y0 + y) < f ? b + 1 : b]);
    }
  }
  blit(src, dx, dy, flip = false, map = null) {   // src: {w,h,d}
    for (let y = 0; y < src.h; y++) for (let x = 0; x < src.w; x++) {
      let c = src.d[y * src.w + (flip ? src.w - 1 - x : x)]; if (c === T) continue;
      if (map) { c = map[c]; if (c === undefined || c === T) continue; }
      this.px(dx + x, dy + y, c);
    }
  }
  blitScale(src, dx, dy, s = 2, flip = false) {
    for (let y = 0; y < src.h; y++) for (let x = 0; x < src.w; x++) {
      const c = src.d[y * src.w + (flip ? src.w - 1 - x : x)]; if (c === T) continue;
      this.rect(dx + x * s, dy + y * s, s, s, c);
    }
  }
  copy(src, sx, sy, sw, sh, dx, dy) { for (let y = 0; y < sh; y++) for (let x = 0; x < sw; x++) { const c = src.get(sx + x, sy + y); if (c !== T) this.px(dx + x, dy + y, c); } }
}
export function sprFromRows(rows, map) {       // 字符串精灵 → {w,h,d}
  const h = rows.length, w = Math.max(...rows.map(r => r.length)), d = new Uint8Array(w * h).fill(T);
  rows.forEach((r, y) => { for (let x = 0; x < r.length; x++) { const ch = r[x]; if (ch === '.' || ch === ' ') continue; const c = map[ch]; if (c === undefined) throw new Error('sprite char ' + ch); d[y * w + x] = c; } });
  return { w, h, d };
}

// —— 输出：索引 → RGB（可选两张表 + 逐像素选择：回涨 / 塌缩的抖动过渡）→ 整数倍最近邻放大 ——
// 字幕置顶层是第二张 2 倍低分辨画布：先画完画面与后处理，再整层压在画面上。
// 封面模式不需要置顶层：withOv=false，整幅构图直接画在封面的格子上。
export function makeOut(canvas, gw = W, gh = H, sc = SCALE, withOv = true) {
  const lo = document.createElement('canvas'); lo.width = gw; lo.height = gh;
  const g = lo.getContext('2d'); const img = g.createImageData(gw, gh); const u32 = new Uint32Array(img.data.buffer);
  let loOv = null, gv = null, imgOv = null, u32Ov = null;
  if (withOv) {
    loOv = document.createElement('canvas'); loOv.width = OW; loOv.height = OH;
    gv = loOv.getContext('2d'); imgOv = gv.createImageData(OW, OH); u32Ov = new Uint32Array(imgOv.data.buffer);
  }
  canvas.width = gw * sc; canvas.height = gh * sc;
  const o = canvas.getContext('2d'); o.imageSmoothingEnabled = false;
  const ow = gw * sc, oh = gh * sc;
  return {
    lo, u32, gw, gh, sc, loOv, u32Ov,
    present(fb, lut, lutB = null, pick = null) {
      const d = fb.d;
      if (d.length !== gw * gh) throw new Error(`present: framebuffer is ${fb.w}x${fb.h}, output is ${gw}x${gh}`);
      if (!lutB) for (let i = 0; i < d.length; i++) u32[i] = lut[d[i]];
      else for (let y = 0, i = 0; y < gh; y++) for (let x = 0; x < gw; x++, i++) u32[i] = (pick(x, y) ? lutB : lut)[d[i]];
      g.putImageData(img, 0, 0);
    },
    // 透明像素（索引 T）写 0，其余走画面同一张 LUT：淡出与塌缩会一并作用到字幕上。
    presentOverlay(ov, lut) {
      if (!u32Ov) throw new Error('presentOverlay: this output has no overlay layer');
      const d = ov.d;
      for (let i = 0; i < d.length; i++) u32Ov[i] = d[i] === T ? 0 : lut[d[i]];
      gv.putImageData(imgOv, 0, 0);
    },
    post(fn) { fn(u32); g.putImageData(img, 0, 0); },   // RGB 级后处理（马赛克、旋涡）
    show() {
      o.drawImage(lo, 0, 0, ow, oh);
      if (loOv) o.drawImage(loOv, 0, 0, ow, oh);
    },
  };
}
// RGB 级马赛克：块 n，块取左上角颜色（对齐到屏幕中心）
export function mosaic(u32, n, gw = W, gh = H) {
  if (n <= 1) return; const src = u32.slice();
  const ox = (gw / 2) % n, oy = (gh / 2) % n;
  for (let y = 0; y < gh; y++) for (let x = 0; x < gw; x++) {
    const bx = Math.max(0, Math.floor((x - ox) / n) * n + ox), by = Math.max(0, Math.floor((y - oy) / n) * n + oy);
    u32[y * gw + x] = src[Math.min(gh - 1, by) * gw + Math.min(gw - 1, bx)];
  }
}
