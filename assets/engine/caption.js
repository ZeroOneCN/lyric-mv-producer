// caption.js — the fixed lyric caption. One style, one geometry, every film.
// Lane, width and line cap are law (see px.js); project.env tunes only
// SUB_STYLE (bar | bubble | plain), SUB_DENS (0..1) and SUB_FADE (s).
import { W, C, LANE_TOP, LANE_BOT, CAP_MAXW, CAP_LINES, CAP_CJK, bayer, ss } from './px.js';
import { text, textW, wrap, LINE_H } from './font.js';

const INK = C.ink;      // 抖动底栏 / 气泡 / 1 px 投影
const DROP = C.night;   // 气泡描边外缘，与底栏区分用

// 行首不落标点：把紧跟的标点并入上一行，避免出现一行以「，」开头。
const PUNCT = new Set('，。、！？；：）》”’…—,.!?;:)');

export const hasCJK = s => [...s].some(ch => ch.codePointAt(0) >= 0x2e80);

export function cjkLines(body, maxChars = CAP_CJK) {
  const chars = [...body];
  const lines = [];
  for (let i = 0; i < chars.length; i += maxChars) {
    let n = Math.min(maxChars, chars.length - i);
    while (i + n < chars.length && PUNCT.has(chars[i + n])) n++;
    lines.push(chars.slice(i, i + n).join(''));
  }
  return lines;
}

export function captionCfg(env = {}, zh = null) {
  const num = (v, d) => { const x = parseFloat(v); return Number.isFinite(x) ? x : d; };
  const style = ['bar', 'bubble', 'plain'].includes(env.SUB_STYLE) ? env.SUB_STYLE : 'bar';
  return {
    style,
    dens: Math.min(0.8, Math.max(0, num(env.SUB_DENS, 0.45))),
    fade: Math.max(0.04, num(env.SUB_FADE, 0.18)),
    zh,
  };
}

const isCjk = (s, cfg) => Boolean(cfg.zh) && hasCJK(s);
export const lineWidth = (s, cfg) => (isCjk(s, cfg) ? cfg.zh.zhTextW(s, 1) : textW(s, 1));

// Two lines maximum. null means the cue is too long: fix lyrics.json, never the lane.
export function captionLines(cue, cfg) {
  const body = String(cue.text).replace(/\s+/g, ' ').trim();
  const lines = (hasCJK(body) && cfg.zh) ? cjkLines(body) : wrap(body, CAP_MAXW);
  if (!lines.length || lines.length > CAP_LINES) return null;
  if (lines.some(l => lineWidth(l, cfg) > CAP_MAXW)) return null;
  return lines;
}

// Bottom-anchored block inside the lane: line tops relative to the block top.
export function captionBlock(lines, cfg) {
  const cjk = lines.map(l => isCjk(l, cfg));
  const hs = cjk.map(c => (c ? 16 : 9));
  const step = cjk.map(c => (c ? 17 : LINE_H));
  const h = hs[hs.length - 1] + step.slice(0, -1).reduce((a, b) => a + b, 0);
  const y = [0];
  for (let i = 1; i < lines.length; i++) y.push(y[i - 1] + step[i - 1]);
  return { hs, y, h, top: LANE_BOT - h + 1 };
}

function laneBar(fb, cfg) {
  for (let y = LANE_TOP; y <= LANE_BOT; y++)
    for (let x = 0; x < W; x++) if (bayer(x, y) < cfg.dens) fb.px(x, y, INK);
}

function bubblePlate(fb, line, x, y, h, cfg) {
  const w = Math.round(lineWidth(line, cfg)), pad = 3, r = pad + 1;
  for (let ry = y - pad; ry <= y + h - 1 + pad; ry++) {
    for (let rx = x - pad; rx <= x + w - 1 + pad; rx++) {
      const cx = Math.max(x, Math.min(rx, x + w - 1));
      const cy = Math.max(y, Math.min(ry, y + h - 1));
      if ((rx - cx) ** 2 + (ry - cy) ** 2 > r * r) continue;
      fb.px(rx, ry, cfg.style === 'bubble' ? DROP : INK);
    }
  }
}

function drawLine(fb, line, x, y, col, cfg) {
  if (isCjk(line, cfg)) cfg.zh.zhText(fb, line, x, y, col, INK, 1);
  else text(fb, line, x, y, col, INK, 1);
}

export function captionAt(t, subs) {
  for (const c of subs) if (t >= c.t0 && t < c.t1) return c;
  return null;
}

// Returns { cue, lines, top, h } when drawn, { cue, overflow: true } when the cue
// cannot fit the fixed lane, null when no cue is on screen.
export function drawCaption(fb, t, subs, cfg) {
  const cue = captionAt(t, subs);
  if (!cue) return null;
  const a = ss(0, cfg.fade, t - cue.t0);
  if (a < 0.05) return null;
  const lines = captionLines(cue, cfg);
  if (!lines) return { cue, overflow: true };
  if (cfg.style !== 'plain') laneBar(fb, cfg);
  const geo = captionBlock(lines, cfg);
  const col = a > 0.55 ? C.bwhite : C.silver;
  lines.forEach((line, i) => {
    const x = Math.round((W - lineWidth(line, cfg)) / 2), y = geo.top + geo.y[i];
    if (cfg.style === 'bubble') bubblePlate(fb, line, x, y, geo.hs[i], cfg);
    drawLine(fb, line, x, y, col, cfg);
  });
  return { cue, lines, top: geo.top, h: geo.h };
}
