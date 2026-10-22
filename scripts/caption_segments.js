// tools/caption_segments.js - dump the exact captions the renderer shows, in order.
// The burned-in caption and the SRT must come from this one list, so a sung line
// that the caption splits over time is split the same way in the subtitle file.
//   node tools/caption_segments.js [project-dir] [--out out/segments.json]
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const argv = process.argv.slice(2);
const opt = (flag, def) => { const i = argv.indexOf(flag); return i >= 0 ? argv[i + 1] : def; };
const root = resolve(argv[0] && !argv[0].startsWith('-') ? argv[0] : '.');
const out = resolve(opt('--out', resolve(root, 'out/segments.json')));
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

const cap = await import(url('engine/caption.js'));
let zh = null;
try {
  const m = await import(url('engine/font_zh.js'));
  if (m.ZH_N > 0) zh = m;
} catch { /* Latin-only film */ }

const env = parseEnv(readFileSync(resolve(root, 'project.env'), 'utf8'));
const cfg = cap.captionCfg(env, zh);
const cues = JSON.parse(readFileSync(resolve(root, 'lyrics.json'), 'utf8'));
const all = cap.flattenSegments(cues, cfg);
const bad = all.filter(s => s.bad);
if (bad.length) {
  for (const b of bad) console.error(`FAIL ${b.t0}s: cannot be captioned as one line - ${b.cue.text}`);
  process.exit(1);
}
const captions = all.map((s, i) => ({ i: i + 1, t0: s.t0, t1: s.t1, text: s.text }));
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify({ captions }, null, 1), 'utf8');
console.log(`${out}: ${captions.length} captions from ${cues.length} cues`);
