// Offline paired process CPU; never a Cloudflare billing metric.
// node scripts/measure-cpu.mjs [output.json] [baseline-commit]
import assert from 'node:assert/strict';
import { readFile, readdir, writeFile, mkdtemp, symlink, rm } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const tree = fileURLToPath(new URL('..', import.meta.url));
const repo = resolve(tree, '../..');
const baseline_commit = execFileSync('git', ['rev-parse', process.argv[3] ?? '5c23c1a'], { cwd: repo, encoding: 'utf8' }).trim();
const temp = await mkdtemp(join(tmpdir(), 'punkto-m3-paired-'));
const originalFetch = globalThis.fetch, originalCaches = globalThis.caches;
const fixtures = new Map();
let fetches = 0;
async function load(dir, prefix = '') {
  for (const e of await readdir(dir, { withFileTypes: true })) {
    const path = `${prefix}/${e.name}`;
    if (e.isDirectory()) await load(`${dir}/${e.name}`, path);
    else fixtures.set(path, new Uint8Array(await readFile(`${dir}/${e.name}`)));
  }
}
const cpuMs = start => { const d = process.cpuUsage(start); return (d.user + d.system) / 1000; };
function summarize(samples) {
  const s = [...samples].sort((a, b) => a - b), n = s.length;
  return { min: s[0], median: (s[Math.floor((n - 1) / 2)] + s[Math.floor(n / 2)]) / 2,
    p95: s[Math.ceil(.95 * n) - 1], max: s.at(-1), over_10_ms: samples.filter(x => x > 10).length };
}
async function rpc(fetch, tool, args, id) {
  const response = await fetch(new Request('https://unit.workers.dev/mcp', {
    method: 'POST', headers: { host: 'unit.workers.dev', 'content-type': 'application/json', accept: 'application/json, text/event-stream' },
    body: JSON.stringify({ jsonrpc: '2.0', id, method: 'tools/call', params: { name: tool, arguments: args } }),
  }), {}, { waitUntil() {}, passThroughOnException() {} });
  const text = await response.text();
  assert.equal(response.status, 200);
  const envelope = JSON.parse(response.headers.get('content-type')?.includes('text/event-stream')
    ? text.split('\n').find(line => line.startsWith('data:')).slice(5) : text);
  assert.equal(envelope.id, id);
  return envelope.result;
}
async function pairs(path, tool, args, variants) {
  const raw = Object.fromEntries(Object.keys(variants).map(key => [key, { samples_ms: [], fetch_counts: [] }]));
  for (let i = 0; i < 50; i++) {
    const results = [];
    // Fixed baseline, optimized alternation: no independent before/after processes.
    for (const [key, run] of Object.entries(variants)) {
      fetches = 0;
      const start = process.cpuUsage();
      const result = await run(tool, args, i + 1);
      raw[key].samples_ms.push(cpuMs(start));
      raw[key].fetch_counts.push(fetches);
      assert.equal(result.isError, undefined);
      assert.equal(fetches, tool === 'read_place' ? 13 : 1);
      assert.equal(result.structuredContent.verified_objects, tool === 'read_place' ? 12 : 1);
      assert.deepEqual(JSON.parse(result.content[0].text), result.structuredContent);
      results.push(result.structuredContent);
      const sizes = { text_chars: result.content[0].text.length, structured_chars: JSON.stringify(result.structuredContent).length, whole_tool_result_chars: JSON.stringify(result).length };
      sizes.rough_tokens = Object.fromEntries(Object.entries(sizes).map(([k, v]) => [k, Math.ceil(v / 4)]));
      raw[key].sizes = sizes;
    }
    assert.deepEqual(results[0], results[1]);
  }
  for (const value of Object.values(raw)) value.cpu_ms = summarize(value.samples_ms);
  const [before, after] = Object.values(raw);
  const differences = after.samples_ms.map((x, i) => x - before.samples_ms[i]);
  return { path, tool, n: 50, variants: raw, paired_difference: { direction: 'optimized minus baseline', samples_ms: differences,
    cpu_ms: summarize(differences), optimized_faster_fraction: differences.filter(x => x < 0).length / differences.length } };
}
try {
  const archive = execFileSync('git', ['archive', baseline_commit, 'integrations/punkto-mcp', 'pwa/punkti/carrier.js', 'pwa/punkti/spatial.js'], { cwd: repo });
  execFileSync('tar', ['-x', '-C', temp], { input: archive });
  const baselineTree = join(temp, 'integrations/punkto-mcp');
  // Both trees use the exact installed dependency graph; no installation or network.
  assert.equal(await readFile(join(baselineTree, 'package-lock.json'), 'utf8'), await readFile(join(tree, 'package-lock.json'), 'utf8'));
  await symlink(join(tree, 'node_modules'), join(baselineTree, 'node_modules'), 'dir');
  await load(join(tree, 'test/fixtures'));
  globalThis.caches = undefined;
  globalThis.fetch = async (url, options) => {
    const u = new URL(url);
    assert.ok(['https://punkto.xyz', 'https://test2.punkto.xyz'].includes(u.origin));
    assert.equal(options.method, 'GET');
    assert.equal(options.redirect, 'manual');
    assert.ok(fixtures.has(u.pathname), `Missing fixture: ${u.pathname}`);
    fetches++;
    return new Response(fixtures.get(u.pathname));
  };
  const variants = {};
  for (const [key, dir] of [['baseline', baselineTree], ['optimized', tree]]) {
    const { default: worker } = await import(pathToFileURL(join(dir, 'src/index.js')));
    const { invoke } = await import(pathToFileURL(join(dir, 'src/tools.js')));
    variants[key] = { rpc: (tool, args, id) => rpc(worker.fetch, tool, args, id), invoke };
  }
  const runs = [];
  for (const path of ['rpc', 'invoke']) {
    for (const [tool, args] of [['read_place', {}], ['get_record', { sha256: '2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d' }]]) {
      runs.push(await pairs(path, tool, args, Object.fromEntries(Object.entries(variants).map(([k, v]) => [k, v[path]]))));
    }
  }
  // Isolate handler lifetime with identical optimized tools and SDK in both arms.
  const { createHandler, handler } = await import(pathToFileURL(join(tree, 'src/handler.js')));
  const handler_lifetime = await pairs('rpc', 'read_place', {}, {
    per_request: (tool, args, id) => rpc((...params) => createHandler()(...params), tool, args, id),
    module_scope: (tool, args, id) => rpc(handler, tool, args, id),
  });
  const report = { baseline_commit, node: process.version, recorded_at: new Date().toISOString(),
    method: 'Same process and installed SDK; archived baseline then optimized alternating for 50 pairs per path/tool; process.cpuUsage; offline fixture GETs; cache disabled; no warm-up or discarded samples; RPC includes request creation and response consumption; nearest-rank p95. Handler lifetime experiment uses identical optimized source in both arms. Fixed order and shared JIT/GC remain limitations.',
    runs, handler_lifetime };
  if (process.argv[2]) await writeFile(process.argv[2], JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, (key, value) => ['samples_ms', 'fetch_counts'].includes(key) ? undefined : value, 2));
} finally {
  globalThis.fetch = originalFetch;
  if (originalCaches === undefined) delete globalThis.caches; else globalThis.caches = originalCaches;
  await rm(temp, { recursive: true, force: true });
}
