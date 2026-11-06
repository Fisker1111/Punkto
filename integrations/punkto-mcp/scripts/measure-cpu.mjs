// Offline, uncached process CPU measurements; never a Cloudflare billing metric.
// node scripts/measure-cpu.mjs [tree-directory] [output.json] [label]
import assert from 'node:assert/strict';
import { readFile, readdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const tree = resolve(process.argv[2] ?? new URL('..', import.meta.url).pathname);
const fixtures = new Map();
async function load(dir, prefix = '') {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = `${prefix}/${entry.name}`;
    if (entry.isDirectory()) await load(`${dir}/${entry.name}`, path);
    else fixtures.set(path, new Uint8Array(await readFile(`${dir}/${entry.name}`)));
  }
}
await load(`${tree}/test/fixtures`);
const originalFetch = globalThis.fetch;
const originalCaches = globalThis.caches;
let fetches = 0;
globalThis.caches = undefined;
globalThis.fetch = async (url, options) => {
  const u = new URL(url);
  assert.ok(['https://punkto.xyz', 'https://test2.punkto.xyz'].includes(u.origin));
  assert.equal(options.method, 'GET');
  assert.equal(options.redirect, 'manual');
  assert.ok(fixtures.has(u.pathname), `Missing offline fixture: ${u.pathname}`);
  fetches++;
  return new Response(fixtures.get(u.pathname));
};
const cpuMs = start => { const d = process.cpuUsage(start); return (d.user + d.system) / 1000; };
export function summarize(samples) {
  const sorted = [...samples].sort((a, b) => a - b), n = sorted.length;
  return { min: sorted[0], median: (sorted[Math.floor((n - 1) / 2)] + sorted[Math.floor(n / 2)]) / 2,
    p95: sorted[Math.ceil(.95 * n) - 1], max: sorted.at(-1), over_10_ms: samples.filter(x => x > 10).length };
}
try {
  const start = process.cpuUsage();
  const { default: worker } = await import(pathToFileURL(`${tree}/src/index.js`));
  const { invoke } = await import(pathToFileURL(`${tree}/src/tools.js`));
  const module_import_cpu_ms = cpuMs(start);
  const runs = [];
  for (const variant of ['rpc', 'invoke']) {
    for (const [tool, args] of [['read_place', {}], ['get_record', { sha256: '2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d' }]]) {
      const samples_ms = [], fetch_counts = [];
      let result;
      for (let i = 0; i < 50; i++) {
        fetches = 0;
        const start = process.cpuUsage();
        if (variant === 'invoke') result = await invoke(tool, args);
        else {
          const response = await worker.fetch(new Request('https://unit.workers.dev/mcp', {
            method: 'POST', headers: { host: 'unit.workers.dev', 'content-type': 'application/json', accept: 'application/json, text/event-stream' },
            body: JSON.stringify({ jsonrpc: '2.0', id: i + 1, method: 'tools/call', params: { name: tool, arguments: args } }),
          }), {}, { waitUntil() {}, passThroughOnException() {} });
          const text = await response.text();
          const envelope = response.headers.get('content-type')?.includes('text/event-stream')
            ? JSON.parse(text.split('\n').find(line => line.startsWith('data:')).slice(5)) : JSON.parse(text);
          result = envelope.result;
          assert.ok(result, text);
        }
        samples_ms.push(cpuMs(start));
        fetch_counts.push(fetches);
        assert.equal(result.isError, undefined);
        assert.equal(fetches, tool === 'read_place' ? 13 : 1);
        assert.equal(result.structuredContent.verified_objects, tool === 'read_place' ? 12 : 1);
        assert.deepEqual(JSON.parse(result.content[0].text), result.structuredContent);
      }
      const sizes = { text_chars: result.content[0].text.length, structured_chars: JSON.stringify(result.structuredContent).length,
        whole_tool_result_chars: JSON.stringify(result).length };
      sizes.rough_tokens = Object.fromEntries(Object.entries(sizes).map(([key, chars]) => [key, Math.ceil(chars / 4)]));
      runs.push({ variant, tool, n: 50, cpu_ms: summarize(samples_ms), samples_ms, fetch_counts, sizes });
    }
  }
  const report = { label: process.argv[4] ?? 'measurement', node: process.version, tree, recorded_at: new Date().toISOString(),
    method: 'process.cpuUsage; mocked fixture GETs; cache disabled; no discarded samples; RPC includes request creation and response consumption; nearest-rank p95',
    module_import_cpu_ms, runs };
  if (process.argv[3]) await writeFile(process.argv[3], JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ ...report, runs: runs.map(({ samples_ms, fetch_counts, ...run }) => run) }, null, 2));
} finally {
  globalThis.fetch = originalFetch;
  if (originalCaches === undefined) delete globalThis.caches; else globalThis.caches = originalCaches;
}
