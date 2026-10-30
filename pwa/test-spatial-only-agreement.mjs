// Independent Python/JS carrier validation and daemon-free static replication.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdtempSync, readFileSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import { canonical, validate, unb64, sha256Hex } from './punkti/carrier.js';
import { createReader } from './punkti/reader.js';
import { replyAddress } from './ui-text.js';

globalThis.nacl = createRequire(import.meta.url)('./nacl.min.js');
const root = fileURLToPath(new URL('../', import.meta.url));
const read = name => JSON.parse(readFileSync(new URL(`./punkti/test-vectors/${name}-vectors.json`, import.meta.url)));
const publication = read('publication');
const vectors = Object.fromEntries(publication.vectors.map(v => [v.id, v]));
const cases = [...Object.entries(read('carrier').fixtures).map(([name, f]) => ({ name, kind: 'record', hex: Buffer.from(unb64(f.R)).toString('hex'), expected: f.state })), ...vectors.V10.cases, ...vectors.V12.cases];
function python(args, input) {
  return new Promise((resolve, reject) => {
    const child = spawn('python3', ['-m', 'punkti_node.test_spatial_only', ...args], { cwd: root });
    let out = '', err = '';
    child.stdout.on('data', data => { out += data; });
    child.stderr.on('data', data => { err += data; });
    child.on('error', reject);
    child.on('close', code => {
      if (code !== 0) return reject(new Error(`Python exited ${code}: ${err}${out}`));
      try { resolve(JSON.parse(out)); } catch (error) { reject(error); }
    });
    child.stdin.end(input === undefined ? '' : JSON.stringify(input));
  });
}
function lp(raw) {
  const size = Buffer.alloc(4); size.writeUInt32BE(raw.length);
  return Buffer.concat([size, raw]);
}
const pyCarrier = await python(['--agreement'], cases);
for (const [i, c] of cases.entries()) {
  let actual;
  try {
    const raw = new Uint8Array(c.kind === 'record' ? Buffer.from(c.hex, 'hex') : Buffer.concat([lp(canonical(c.input)), lp(unb64(c.input.sig))]));
    const result = await validate(raw);
    actual = { state: result.state, mid: result.address, sha256: await sha256Hex(raw), h: result.h };
  } catch (error) {
    assert.ok(['ValueError', 'RangeError', 'TypeError'].includes(error.name), `${c.name}: ${error}`);
    actual = { state: 'INVALID-structural', mid: null, sha256: null, h: null };
  }
  assert.equal(actual.state, c.expected, c.name);
  assert.deepEqual(actual, pyCarrier[i], c.name);
}

for (const h of ['u3bu_0', 'u3butz7k9q_23.025', 'u3butz7k9q7v_-18']) assert.equal(replyAddress({ h }), h);
for (const parent of [{}, { h: null }, { h: '' }, { h: 'broken' }]) assert.throws(() => replyAddress(parent), /parent has no valid spatial address/);

const directory = mkdtempSync(path.join(tmpdir(), 'punkti-agreement-'));
const primes = new Map(), rootReads = new Map();
function materialize(fixture, target) {
  mkdirSync(target, { recursive: true });
  writeFileSync(path.join(target, 'root.json'), Buffer.from(fixture.root, 'hex'));
  for (const [sha, object] of Object.entries(fixture.objects)) {
    const raw = Buffer.from(object.hex, 'hex');
    const prefix = object.kind === 'shard' ? (object.prefix ?? JSON.parse(raw).prefix) : null;
    const relative = object.kind === 'manifest' ? `manifests/${sha}.json` : object.kind === 'shard' ? `h/${[...prefix].join('/')}/${sha}.json` : `${object.kind === 'record' ? 'records' : 'segments'}/${sha.slice(0, 2)}/${sha}`;
    const targetFile = path.join(target, relative);
    mkdirSync(path.dirname(targetFile), { recursive: true });
    writeFileSync(targetFile, raw);
  }
}
function normalized(result) {
  return { state: 'OK', head: result.head, seq: result.seq, rejected: result.rejected,
    valid: Object.fromEntries(result.valid_records.map(r => [r.mid, r.sha256])),
    candidates: Object.fromEntries(result.candidate_records.map(r => [r.sha256, Buffer.from(r.record).toString('hex')])) };
}
async function readResult(reader, base, scope) {
  try { return normalized(await reader.readPublication(base, scope)); }
  catch (e) { return { state: 'ERROR', error_class: e.error_class, reason: e.reason }; }
}
const server = http.createServer((req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  const count = rootReads.get(pathname) ?? 0;
  rootReads.set(pathname, count + 1);
  try { res.end(primes.has(pathname) && count === 0 ? primes.get(pathname) : readFileSync(path.join(directory, pathname))); }
  catch { res.writeHead(404); res.end(); }
});
try {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const publications = publication.vectors.flatMap(v => v.cases.filter(c => c.source));
  const inputs = publications.map((c, i) => {
    const target = path.join(directory, String(i));
    if (c.prime) {
      materialize(publication.fixtures[c.prime], target);
      primes.set(`/${i}/root.json`, Buffer.from(publication.fixtures[c.prime].root, 'hex'));
    }
    materialize(publication.fixtures[c.source], target);
    return { base: `${base}/${i}`, scope: c.scope ?? {}, packs: !!c.packs, ...(c.prime ? { prime: `${base}/${i}` } : {}) };
  });
  const pyPublications = await python(['--publications'], inputs);
  rootReads.clear();
  for (const [i, c] of publications.entries()) {
    const reader = createReader({ maxRetries: 0 });
    if (c.prime) await reader.readPublication(inputs[i].base);
    const actual = await readResult(reader, inputs[i].base, c.scope ?? {});
    assert.deepEqual(actual, pyPublications[i], c.name);
    if (c.expected.error_class) {
      assert.equal(actual.state, 'ERROR', c.name);
      assert.equal(actual.reason, c.expected.reason, c.name);
      assert.equal(actual.error_class, c.expected.error_class, c.name);
    } else {
      assert.equal(actual.state, 'OK', c.name);
      assert.equal(actual.head, c.expected.head, c.name);
      assert.equal(actual.rejected, c.expected.rejected, c.name);
      assert.deepEqual(actual.valid, c.expected.valid, c.name);
      assert.deepEqual(actual.candidates, c.expected.candidates, c.name);
      if (c.retry) assert.deepEqual(await readResult(reader, inputs[i].base, c.scope ?? {}), actual);
    }
  }
  // Node A is only a static HTTP publication. Python replicates to B and
  // republishes; JS independently verifies B's digests, MIDs and signatures.
  let replications = 0;
  for (const packs of [false, true]) {
    const source = path.join(directory, 'source');
    materialize(publication.fixtures[packs ? 'packs' : 'index'], source);
    for (const scope of [{}, { xy_lo: 'u4', xy_hi: 'u5', z_min: '-18', z_max: '0' }]) {
      const target = `replica-${replications++}`;
      const expected = await python(['--replicate', `${base}/source`, path.join(directory, target), JSON.stringify(scope), String(packs)]);
      const actual = normalized(await createReader({ maxRetries: 0 }).readPublication(`${base}/${target}`));
      assert.deepEqual(actual.valid, expected.valid);
      assert.equal(actual.rejected, 0);
      assert.deepEqual(actual.candidates, {});
      assert.equal(Object.keys(actual.valid).length, Object.keys(scope).length ? 2 : 5);
    }
  }
  console.log(`Python/JS agreement: ${cases.length} carrier cases, ${publications.length} publication cases, ${replications} two-node static replications, 7 L4 reply checks passed`);
} finally {
  await new Promise(resolve => server.close(resolve));
  rmSync(directory, { recursive: true, force: true });
}
