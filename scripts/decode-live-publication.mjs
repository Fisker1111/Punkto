// Decode live punkto.xyz publication records using the repo's own carrier module.
// Writes pwa/tests/publication-live-60.json as a deterministic test fixture.
//
//   node scripts/decode-live-publication.mjs
//
// Requires network access to https://punkto.xyz/publication (read-only GETs).
import { writeFileSync } from 'node:fs';
import { decodeRecord } from '../pwa/punkti/carrier.js';
import { parse_h, decode_xy } from '../pwa/punkti/spatial.js';

const BASE = 'https://punkto.xyz/publication';

async function getBytes(u) {
  const res = await fetch(u);
  if (!res.ok) throw new Error(`${u} -> HTTP ${res.status}`);
  return new Uint8Array(await res.arrayBuffer());
}
async function getJson(u) {
  return JSON.parse(Buffer.from(await getBytes(u)).toString('utf8'));
}

const root = await getJson(`${BASE}/root.json`);
const man = await getJson(`${BASE}/manifests/${root.head}.json`);
const entries = [];

async function walk(prefix, sha) {
  const sh = await getJson(`${BASE}/h/${prefix.split('').join('/')}/${sha}.json`);
  for (const [c, csha] of Object.entries(sh.children || {})) await walk(c, csha);
  for (const e of sh.records || []) entries.push(e);
}
for (const [p, sha] of Object.entries(man.index)) await walk(p, sha);

const records = [];
for (const e of entries) {
  const bytes = await getBytes(`${BASE}/records/${e.sha256.slice(0, 2)}/${e.sha256}`);
  const { atom } = decodeRecord(bytes);
  const parsed = parse_h(atom.h);
  const xy = decode_xy(parsed.xy);
  let payload = null;
  try { payload = JSON.parse(atom.x); } catch { payload = null; }
  records.push({
    mid: atom.mid ?? e.mid,
    sha256: e.sha256,
    h: atom.h,
    xy: parsed.xy,
    z: parsed.z,
    lat: xy.lat,
    lon: xy.lon,
    t: atom.t,
    x: atom.x,
    x_json: payload,
    refs: atom.refs,
    pk: atom.pk,
    sig: atom.sig,
  });
}

const fixture = {
  _comment:
    'Live https://punkto.xyz publication snapshot (node build dd2f8b2a, publication head c77ba862, seq 14). ' +
    'Decoded with the repo\'s own pwa/punkti/carrier.js. Used by pwa/test-pwa-m8-ux.mjs. ' +
    'Regenerate with: node scripts/decode-live-publication.mjs',
  captured_at: new Date().toISOString(),
  publication: { head: root.head, seq: root.seq, v: root.v, record_count: man.record_count },
  records,
};

const out = new URL('../pwa/tests/publication-live-60.json', import.meta.url);
writeFileSync(out, JSON.stringify(fixture, null, 2) + '\n');
console.log(`wrote ${records.length} records -> ${out.pathname}`);
