// tools/check_subs.js - prove every lyric fits the fixed single-line caption
// drawn on the overlay layer. Run from anywhere: node tools/check_subs.js [project-dir]
// It imports the project's own engine, so the numbers checked are the numbers
// the renderer uses; there is no second copy of the geometry to drift.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const root = resolve(process.argv[2] || '.');
const url = rel => pathToFileURL(resolve(root, rel)).href;

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

const px = await import(url('engine/px.js'));
const cap = await import(url('engine/caption.js'));
let zh = null;
try {
  const m = await import(url('engine/font_zh.js'));
  if (m.ZH_N > 0) zh = m;
} catch { /* Latin-only film */ }

const env = parseEnv(readFileSync(resolve(root, 'project.env'), 'utf8'));
const cfg = cap.captionCfg(env, zh);
const cues = JSON.parse(readFileSync(resolve(root, 'lyrics.json'), 'utf8'));

const fails = [], warns = [];
if (!['plate', 'bubble', 'plain'].includes(env.SUB_STYLE || 'plate')) {
  fails.push(`SUB_STYLE="${env.SUB_STYLE}" is not plate | bubble | plain`);
}
if (!cues.length) fails.push('lyrics.json has no cues');

const PAD = cap.PLATE_PAD;
let maxSegs = 0, maxW = 0, segTotal = 0;
cues.forEach((c, i) => {
  const at = `cue ${i + 1} (${c.t0}s)`;
  if (!(c.t1 > c.t0)) fails.push(`${at}: t1 must be after t0`);
  if (i && c.t0 < cues[i - 1].t1 - 1e-6) fails.push(`${at}: overlaps the previous cue`);
  const segs = cap.segmentsOf(c, cfg);
  if (!segs) {
    fails.push(`${at}: cannot be shown as one line at a time `
      + `(width ${px.CAP_MAXW} layer px, ${px.CAP_CJK} CJK chars, ${px.CAP_MINSEG}s per line) - ${c.text}`);
    return;
  }
  segTotal += segs.length;
  maxSegs = Math.max(maxSegs, segs.length);
  for (const s of segs) {
    const w = Math.round(cap.lineWidth(s.text, cfg)), h = cap.lineHeight(s.text, cfg);
    maxW = Math.max(maxW, w);
    if (w > px.CAP_MAXW) fails.push(`${at}: line is ${w} layer px, over ${px.CAP_MAXW} - ${s.text}`);
    const x = Math.round((px.OW - w) / 2), y = px.CAP_BASE;
    const x0 = x - PAD, x1 = x + w + PAD - 1, y0 = y - PAD, y1 = y + h + PAD - 1;
    if (x0 < 0 || x1 > px.OW - 1 || y0 < 0 || y1 > px.OH - 1) {
      fails.push(`${at}: plate ${x0}..${x1} x ${y0}..${y1} leaves the overlay layer `
        + `${px.OW}x${px.OH}`);
    }
    if (segs.length > 1 && s.t1 - s.t0 < px.CAP_MINSEG - 1e-9) {
      fails.push(`${at}: line "${s.text}" shows for ${(s.t1 - s.t0).toFixed(2)}s, `
        + `under the ${px.CAP_MINSEG}s reading minimum`);
    }
  }
  if (segs.length > 1) {
    warns.push(`${at}: sung line is ${(c.t1 - c.t0).toFixed(2)}s and needs ${segs.length} `
      + `successive captions - consider splitting it in lyrics.json`);
  } else if (c.t1 - c.t0 < 0.8) {
    warns.push(`${at}: on screen ${(c.t1 - c.t0).toFixed(2)}s, under 0.8s is hard to read`);
  }
  // 每段落在本条歌词的时间窗内
  for (const s of segs) {
    if (s.t0 < c.t0 - 1e-6 || s.t1 > c.t1 + 1e-6) fails.push(`${at}: segment ${s.t0}-${s.t1} escapes the cue`);
  }
  const overlaps = segs.slice(1).some((s, k) => s.t0 < segs[k].t1 - 1e-6);
  if (overlaps) fails.push(`${at}: segments overlap`);
});

console.log(`caption: style=${cfg.style} dens=${cfg.dens} fade=${cfg.fade}s `
  + `layer=${px.OW}x${px.OH} (${px.OV}x the picture) anchor=${px.CAP_BASE} `
  + `maxw=${px.CAP_MAXW} lines=${px.CAP_LINES}/caption cjk<=${px.CAP_CJK}`);
console.log(`${cues.length} cues -> ${segTotal} captions, longest run ${maxSegs}, widest ${maxW}px`);
for (const w of warns) console.log(`WARN ${w}`);
for (const f of fails) console.log(`FAIL ${f}`);
if (fails.length) { console.log(`RESULT FAIL (${fails.length})`); process.exit(1); }
console.log(`RESULT PASS${warns.length ? ` (${warns.length} warn)` : ''}`);
