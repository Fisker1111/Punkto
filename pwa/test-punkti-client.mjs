import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { webcrypto, createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import vm from 'node:vm';
import { once } from 'node:events';
import { createPunktiClient, encodeRecord, decodeRecord, canonicalJson, geohash3d } from './sync/punkti-client.js';

Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });
globalThis.nacl = createRequire(import.meta.url)('./nacl.min.js');
globalThis.window = {};
vm.runInThisContext(readFileSync(new URL('./key-management.js', import.meta.url), 'utf8'));
const identity = nacl.sign.keyPair.fromSeed(new Uint8Array(32).fill(7));
const dir = mkdtempSync(join(tmpdir(), 'punkti-client-'));
const child = spawn('python3', ['-m', 'punkti_node'], {
  cwd: resolve(new URL('..', import.meta.url).pathname),
  env: { ...process.env, PUNKTO_NODE_CONFIG: '', PUNKTO_HOST: '127.0.0.1', PUNKTO_PORT: '0', PUNKTO_DATA_DIR: dir, PUNKTO_WEB_ROOT: resolve(new URL('.', import.meta.url).pathname) },
  stdio: ['ignore', 'pipe', 'pipe'],
});
let output = '';
child.stdout.on('data', b => { output += b; });
child.stderr.on('data', b => { output += b; });
try {
  let baseUrl;
  for (let i = 0; i < 100; i++) {
    baseUrl = output.match(/origin=(http:\/\/127\.0\.0\.1:\d+)/)?.[1];
    if (baseUrl) break;
    if (child.exitCode !== null) throw Error(output);
    await new Promise(r => setTimeout(r, 50));
  }
  assert.ok(baseUrl, output);
  const client = createPunktiClient({ baseUrl, identity });
  const pubkey = Buffer.from(identity.publicKey).toString('base64');
  const atom = await window.signAtom({ punkto: 'p:u1xj9n8d4k2m', lat: 55.7, lon: 12.5, alt: 42, t: 1799150400000, x: 'Hello 🌍', extra: { unknown: [1, 'æ'], sig: 'preserve nested key' } }, identity.secretKey, pubkey);
  const item = await encodeRecord(atom, identity);
  const expectedH = execFileSync('python3', ['-c', 'from core.geohash3d import encode; print(encode(55.7,12.5,42))'], { encoding: 'utf8' }).trim();
  assert.equal(geohash3d(12.5, 55.7, 42), expectedH);
  const python = JSON.parse(execFileSync('python3', ['-c', 'import sys,json; from punkti_node.carrier import decode,unb64,validate; a=json.load(sys.stdin); raw=unb64(a["record"]); d,_,_=decode(raw); print(json.dumps({"x":d["x"],"address":validate(raw).address,"h":d["h"]}))'], { input: JSON.stringify(item), encoding: 'utf8' }));
  assert.equal(python.address, item.address);
  assert.equal(python.x, canonicalJson(atom));
  assert.equal(python.h, expectedH);
  await client.pushAtom(atom);
  await client.pushAtom(atom); // duplicate is a successful idempotent publish
  for (let i = 1; i < 4; i++) await client.pushAtom(await window.signAtom({ ...atom, t: atom.t + i }, identity.secretKey, pubkey));
  const atoms = await client.pullAll({ limit: 1 });
  assert.equal(atoms.length, 4);
  assert.deepEqual(atoms.find(a => a.t === atom.t), atom);
  assert.equal((await decodeRecord(item)).x, canonicalJson(atom));
  await assert.rejects(client.pullAll({ limit: 1, maxPages: 1 }), /incomplete/);
  const tampered = Buffer.from(item.record, 'base64'); tampered[tampered.length - 1] ^= 1;
  const bad = { ...item, record: tampered.toString('base64'), sha256: createHash('sha256').update(tampered).digest('hex') };
  await assert.rejects(decodeRecord(bad));
  const post = async item => fetch(baseUrl + '/api/push', { method: 'POST', body: JSON.stringify({ records: [item] }) });
  const badResponse = await post(bad);
  const badResult = await badResponse.json();
  assert.equal(badResult.results[0].admitted, false);
  assert.equal((await post({ ...item, address: 'punkti/0.6:' + '0'.repeat(64) })).status, 400);
  // A valid L3 envelope cannot make an invalid L4 payload displayable.
  await post(await encodeRecord({ ...atom, x: 'tampered L4' }, identity));
  assert.equal((await client.pullAll()).length, 4);
  assert.ok(client.stats.skipped >= 1);
  assert.equal((await client.health()).status, 'ok');
  assert.equal((await client.nodeInfo()).store.valid, 5);
  assert.equal((await fetch(baseUrl + '/')).status, 200);
  console.log('Punkti client real-node integration passed');
} finally {
  const exited = child.exitCode !== null ? Promise.resolve() : once(child, 'exit');
  child.kill('SIGTERM');
  await exited;
  rmSync(dir, { recursive: true, force: true });
}
