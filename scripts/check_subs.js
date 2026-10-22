// tools/check_subs.js - prove every lyric fits the fixed caption lane.
// Run from anywhere: node tools/check_subs.js [project-dir]
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
const font = await import(url('engine/font.js'));
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
if (!['bar', 'bubble', 'plain'].includes(env.SUB_STYLE || 'bar')) {
  fails.push(`SUB_STYLE="${env.SUB_STYLE}" is not bar | bubble | plain`);
}
if (!cues.length) fails.push('lyrics.json has no cues');

let maxLines = 0, maxW = 0;
cues.forEach((c, i) => {
  const at = `cue ${i + 1} (${c.t0}s)`;
  if (!(c.t1 > c.t0)) fails.push(`${at}: t1 must be after t0`);
  if (i && c.t0 < cues[i - 1].t1 - 1e-6) fails.push(`${at}: overlaps the previous cue`);
  const lines = cap.captionLines(c, cfg);
  if (!lines) {
    fails.push(`${at}: does not fit the lane (${px.CAP_LINES} lines max, `
      + `${px.CAP_CJK} CJK chars per line, ${px.CAP_MAXW}px wide) - ${c.text}`);
    return;
  }
  const geo = cap.captionBlock(lines, cfg);
  if (geo.top < px.LANE_TOP || geo.top + geo.h - 1 > px.LANE_BOT) {
    fails.push(`${at}: block ${geo.top}..${geo.top + geo.h - 1} leaves the lane `
      + `${px.LANE_TOP}..${px.LANE_BOT}`);
  }
  maxLines = Math.max(maxLines, lines.length);
  maxW = Math.max(maxW, ...lines.map(l => cap.lineWidth(l, cfg)));
  if (c.t1 - c.t0 < 0.8) warns.push(`${at}: on screen ${(c.t1 - c.t0).toFixed(2)}s, under 0.8s is hard to read`);
});

console.log(`caption: style=${cfg.style} dens=${cfg.dens} fade=${cfg.fade}s `
  + `lane=${px.LANE_TOP}..${px.LANE_BOT} maxw=${px.CAP_MAXW} lines<=${px.CAP_LINES} `
  + `cjk<=${px.CAP_CJK}/line`);
console.log(`${cues.length} cues, longest block ${maxLines} line(s), widest ${maxW}px`);
for (const w of warns) console.log(`WARN ${w}`);
for (const f of fails) console.log(`FAIL ${f}`);
if (fails.length) { console.log(`RESULT FAIL (${fails.length})`); process.exit(1); }
console.log(`RESULT PASS${warns.length ? ` (${warns.length} warn)` : ''}`);
