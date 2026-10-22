// caption.js — the fixed lyric caption: one line, drawn on the overlay layer
// that sits on top of the finished picture. One style, one geometry, every film.
// project.env tunes only SUB_STYLE (plate | bubble | plain), SUB_DENS (0..1), SUB_FADE (s).
import { C, OW, OH, CAP_MAXW, CAP_CJK, CAP_BASE, CAP_MINSEG, bayer, ss } from './px.js';
import { text, textW } from './font.js';

const INK = C.ink;      // 底板 / 1 层像素投影
const DROP = C.night;   // bubble 实底描边，与 plate 区分用
const PAD = 6;          // 底板相对文字的外扩（层像素）
const RAD = 5;          // 底板圆角半径
const LAT = 2;          // 拉丁在层上的字号：7×2=14，与 16 的汉字视觉等高
export const PLATE_PAD = PAD;

// 行首不落标点：把紧跟的标点并入上一行，避免出现一行以「，」开头。
const PUNCT = new Set('，。、！？；：）》”’…—,.!?;:)');

export const hasCJK = s => [...s].some(ch => ch.codePointAt(0) >= 0x2e80);

export function captionCfg(env = {}, zh = null) {
  const num = (v, d) => { const x = parseFloat(v); return Number.isFinite(x) ? x : d; };
  const style = ['plate', 'bubble', 'plain'].includes(env.SUB_STYLE) ? env.SUB_STYLE : 'plate';
  return {
    style,
    dens: Math.min(0.8, Math.max(0, num(env.SUB_DENS, 0.45))),
    fade: Math.max(0.04, num(env.SUB_FADE, 0.18)),
    zh,
  };
}

const isCjk = (s, cfg) => Boolean(cfg.zh) && hasCJK(s);
export const lineWidth = (s, cfg) => (isCjk(s, cfg) ? cfg.zh.zhTextW(s, 1) : textW(s, LAT));
export const lineHeight = (s, cfg) => (isCjk(s, cfg) ? 16 : 7 * LAT);

// —— 切行：一条歌词只画一行，长了切成先后的单行段 ——
// 汉字按字打包（标点不落行首），拉丁按词打包；两者都以像素宽为限。
function packCjk(body, cfg, maxChars) {
  const chars = [...body];
  const lines = [];
  let cur = '';
  for (let i = 0; i < chars.length; i++) {
    const t = cur + chars[i];
    if (cur && (lineWidth(t, cfg) > CAP_MAXW || [...t].length > maxChars)) {
      let line = cur;
      // 标点不落行首：能塞进本行余量就带走
      while (i < chars.length && PUNCT.has(chars[i]) && lineWidth(line + chars[i], cfg) <= CAP_MAXW + 34) line += chars[i++];
      lines.push(line);
      cur = i < chars.length ? chars[i] : '';
    } else cur = t;
  }
  if (cur) lines.push(cur);
  return lines;
}

function packLatin(body) {
  const lines = [];
  const put = s => {
    let rest = s;
    while (textW(rest, LAT) > CAP_MAXW) {          // 超长单词硬切
      let cut = rest.length;
      while (cut > 1 && textW(rest.slice(0, cut), LAT) > CAP_MAXW) cut--;
      lines.push(rest.slice(0, cut));
      rest = rest.slice(cut);
    }
    const last = lines[lines.length - 1];
    if (last !== undefined && textW(`${last} ${rest}`, LAT) <= CAP_MAXW) lines[lines.length - 1] = `${last} ${rest}`;
    else lines.push(rest);
  };
  for (const word of body.split(' ')) if (word) put(word);
  return lines;
}

// 单行的分段文本；null = 这条歌词连切都切不下，改 lyrics.json
export function captionLines(cue, cfg) {
  const body = String(cue.text).replace(/\s+/g, ' ').trim();
  if (!body) return null;
  const lines = (hasCJK(body) && cfg.zh) ? packCjk(body, cfg, CAP_CJK) : packLatin(body);
  if (!lines.length || lines.length > 8) return null;
  if (lines.some(l => lineWidth(l, cfg) > CAP_MAXW)) return null;
  return lines;
}

// 时长按字数比例分配；每段不得短于 CAP_MINSEG，否则返回 null。
const segCache = new WeakMap();

export function segmentsOf(cue, cfg) {
  const lines = captionLines(cue, cfg);
  if (!lines) return null;
  const t0 = Number(cue.t0), t1 = Number(cue.t1), dur = t1 - t0;
  if (!(dur > 0)) return null;
  if (lines.length === 1) return [{ text: lines[0], t0, t1, i: 0, n: 1 }];
  if (dur < lines.length * CAP_MINSEG) return null;
  const w = lines.map(l => [...l].length), total = w.reduce((a, b) => a + b, 0);
  const segs = []; let acc = 0;
  for (let i = 0; i < lines.length; i++) {
    const from = Math.round((t0 + dur * (acc / total)) * 1000) / 1000;
    acc += w[i];
    const to = i === lines.length - 1 ? t1 : Math.round((t0 + dur * (acc / total)) * 1000) / 1000;
    segs.push({ text: lines[i], t0: from, t1: to, i, n: lines.length });
  }
  return segs.some(s => s.t1 - s.t0 < CAP_MINSEG - 1e-9) ? null : segs;
}

export function flattenSegments(subs, cfg) {
  const cached = segCache.get(subs);
  if (cached && cached.key === cacheKey(cfg)) return cached.segs;
  const segs = [];
  for (const cue of subs) {
    const list = segmentsOf(cue, cfg);
    // 切不下的条目占位保留：渲染时抛错，而不是悄悄没有字幕
    if (list) segs.push(...list);
    else segs.push({ bad: true, cue, t0: Number(cue.t0), t1: Number(cue.t1) });
  }
  segs.sort((a, b) => a.t0 - b.t0 || a.t1 - b.t1);
  segCache.set(subs, { key: cacheKey(cfg), segs });
  return segs;
}
const cacheKey = cfg => `${cfg.zh ? 'zh' : 'la'}`;

export function captionAt(t, subs, cfg) {
  for (const s of flattenSegments(subs, cfg)) if (t >= s.t0 && t < s.t1) return s;
  return null;
}

// —— 绘制 ——
function plate(ov, x, y, w, h, cfg, a) {
  const x0 = x - PAD, y0 = y - PAD, x1 = x + w + PAD - 1, y1 = y + h + PAD - 1;
  const solid = cfg.style === 'bubble', col = solid ? DROP : INK;
  const dens = cfg.dens * a;
  for (let py = Math.max(0, y0); py <= Math.min(OH - 1, y1); py++) {
    for (let px = Math.max(0, x0); px <= Math.min(OW - 1, x1); px++) {
      const cx = Math.max(x0 + RAD, Math.min(px, x1 - RAD));
      const cy = Math.max(y0 + RAD, Math.min(py, y1 - RAD));
      if ((px - cx) ** 2 + (py - cy) ** 2 > RAD * RAD) continue;
      if (solid || bayer(px, py) < dens) ov.px(px, py, col);
    }
  }
}

function drawLine(ov, line, x, y, col, cfg) {
  if (isCjk(line, cfg)) cfg.zh.zhText(ov, line, x, y, col, INK, 1);
  else text(ov, line, x, y, col, INK, LAT);
}

// 单行字幕放不下时的返回值；渲染器必须抛错，不能悄悄漏字。
export const OVERFLOW = { overflow: true };

// boot 时先过一遍：返回切不开的歌词，交给 main.js 报错。
export function unsegmentable(subs, cfg) {
  return subs.filter(cue => !segmentsOf(cue, cfg));
}

// 返回 { seg, x, y, w, h }；画面只认一个位置：水平居中，底边锚在 CAP_BASE。
export function drawCaption(ov, t, subs, cfg) {
  const seg = captionAt(t, subs, cfg);
  if (!seg) return null;
  if (seg.bad) return OVERFLOW;
  const a = ss(0, cfg.fade, t - seg.t0);
  if (a < 0.05) return null;
  const w = Math.round(lineWidth(seg.text, cfg)), h = lineHeight(seg.text, cfg);
  const x = Math.round((OW - w) / 2), y = CAP_BASE;
  if (cfg.style !== 'plain') plate(ov, x, y, w, h, cfg, a);
  const col = a > .75 ? C.bwhite : a > .4 ? C.silver : C.steel;
  drawLine(ov, seg.text, x, y, col, cfg);
  return { seg, x, y, w, h };
}
