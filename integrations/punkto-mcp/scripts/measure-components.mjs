// Paired component experiments, not per-request CPU or Cloudflare measurements.
// Each of 50 samples includes 1000 synchronous operations; alternate order.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { hex } from '../src/hash.js';
const fixture = new URL('../test/fixtures/publication/root.json', import.meta.url);
const bytes = new Uint8Array(await readFile(fixture));
const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
const decoder = new TextDecoder('utf-8', { fatal: true });
const oldHex = bytes => Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
const { invoke } = await import('../src/tools.js');
// Only fixture-backed GETs, same Response construction as adapter.test.mjs.
const originalFetch = globalThis.fetch;
const originalCaches = globalThis.caches;
const { readdir } = await import('node:fs/promises');
const fixtures = new Map();
async function load(dir, prefix = '') {
  for (const e of await readdir(dir, { withFileTypes: true })) {
    const path = `${prefix}/${e.name}`;
    if (e.isDirectory()) await load(`${dir}/${e.name}`, path);
    else fixtures.set(path, new Uint8Array(await readFile(`${dir}/${e.name}`)));
  }
}
await load(new URL('../test/fixtures', import.meta.url).pathname);
globalThis.caches = undefined;
globalThis.fetch = async (url, options) => {
  assert.equal(options.method, 'GET');
  assert.equal(options.redirect, 'manual');
  assert.ok(['https://punkto.xyz', 'https://test2.punkto.xyz'].includes(new URL(url).origin));
  const bytes = fixtures.get(new URL(url).pathname);
  assert.ok(bytes);
  return new Response(bytes);
};
let result;
try { result = (await invoke('read_place', {})).structuredContent; }
finally {
  globalThis.fetch = originalFetch;
  if (originalCaches === undefined) delete globalThis.caches; else globalThis.caches = originalCaches;
}
const serialize = indent => JSON.stringify({ content: [{ type: 'text', text: JSON.stringify(result, null, indent) }], structuredContent: result });
const experiments = [
  ['hex_format_32_bytes', () => oldHex(digest), () => hex(digest)],
  ['utf8_decode_root', () => new TextDecoder('utf-8', { fatal: true }).decode(bytes), () => decoder.decode(bytes)],
  ['serialize_both_read_place_representations', () => serialize(2), () => serialize(undefined)],
];
const reports = [];
let sink;
for (const [name, before, after] of experiments) {
  const raw = { before: [], after: [] };
  for (let sample = 0; sample < 50; sample++) {
    for (const key of sample % 2 ? ['after', 'before'] : ['before', 'after']) {
      const fn = key === 'before' ? before : after;
      const start = process.cpuUsage();
      for (let i = 0; i < 1000; i++) sink = fn();
      const cpu = process.cpuUsage(start);
      raw[key].push((cpu.user + cpu.system) / 1000);
    }
  }
  const summary = values => {
    const s = [...values].sort((a, b) => a - b);
    return { min: s[0], median: (s[24] + s[25]) / 2, p95: s[47], max: s[49], over_10_ms: values.filter(x => x > 10).length };
  };
  reports.push({ name, operations_per_sample: 1000, n: 50, batch_cpu_ms: { before: summary(raw.before), after: summary(raw.after) }, raw_batch_cpu_ms: raw });
}
assert.ok(sink);
const report = { node: process.version, recorded_at: new Date().toISOString(), method: '50 alternating paired batches of 1000 operations; no discarded samples; process CPU, not invocation CPU', experiments: reports };
if (process.argv[2]) await writeFile(process.argv[2], JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ ...report, experiments: reports.map(({ raw_batch_cpu_ms, ...r }) => r) }, null, 2));
