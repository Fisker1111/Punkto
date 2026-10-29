import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, mkdir, readFile, writeFile, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { decodeRecord } from './punkti/carrier.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const CLIENT = path.join(ROOT, 'pwa/ai-first/agent.mjs');
const H = 'u3butz7k9q_23';
const cleanEnv = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('PUNKTO_')));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function command(executable, args, env = {}) {
  const proc = spawn(executable, args, { cwd: ROOT, env: { ...cleanEnv, ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
  let stdout = '', stderr = '';
  proc.stdout.on('data', b => { stdout += b; });
  proc.stderr.on('data', b => { stderr += b; });
  const timer = setTimeout(() => proc.kill('SIGKILL'), 45000);
  try { const [code] = await once(proc, 'exit'); return { code, stdout, stderr }; }
  finally { clearTimeout(timer); }
}
async function cli(nodes, args, success = true) {
  const result = await command(process.execPath, [CLIENT, ...args, '--nodes', nodes], { PUNKTO_LOCAL_ONLY: '1' });
  process.stdout.write(result.stderr);
  process.stdout.write(result.stdout);
  assert.equal(result.code, success ? 0 : 1, result.stdout + result.stderr);
  return JSON.parse(result.stdout);
}
async function listen(server) {
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  return `http://127.0.0.1:${server.address().port}`;
}
async function freePort() {
  const server = http.createServer();
  const base = await listen(server);
  await new Promise(resolve => server.close(resolve));
  return Number(new URL(base).port);
}
async function startNode(env) {
  const child = spawn('python3', ['-m', 'punkti_node'], { cwd: ROOT, env: { ...cleanEnv, ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
  let logs = '';
  child.stdout.on('data', b => { logs += b; }); child.stderr.on('data', b => { logs += b; });
  child.stop = async () => {
    if (child.exitCode !== null || child.signalCode) return;
    const done = once(child, 'exit'); child.kill('SIGTERM');
    const timer = setTimeout(() => child.kill('SIGKILL'), 5000);
    try { await done; } finally { clearTimeout(timer); }
  };
  for (let i = 0; i < 100; i++) {
    try {
      const response = await fetch(`http://127.0.0.1:${env.PUNKTO_PORT}/health`);
      if (response.ok) return child;
    } catch {}
    if (child.exitCode !== null) break;
    await delay(100);
  }
  await child.stop(); throw new Error('node startup failed: ' + logs);
}
async function pull(env, peer) {
  const result = await command('python3', ['-c', `
import json, sys
from punkti_node.config import load_config
from punkti_node.store import PersistentNode
node = PersistentNode(load_config())
try:
    print(json.dumps(node.replicate_publication(sys.argv[1])))
finally:
    node.durable.close()
`, peer], env);
  assert.equal(result.code, 0, result.stderr);
  console.log('EXPLICIT STATIC GET PULL', peer, result.stdout.trim());
  return JSON.parse(result.stdout);
}
async function get(url) {
  assert.equal(new URL(url).hostname, '127.0.0.1');
  const response = await fetch(url);
  const bytes = Buffer.from(await response.arrayBuffer());
  console.log(`HTTP GET ${url} -> ${response.status} bytes=${bytes.length}`);
  assert.equal(response.status, 200);
  return bytes;
}

await test('local real-HTTP Stage 0 scripted harness', async t => {
  const temp = await mkdtemp(path.join(tmpdir(), 'punkti-stage0-'));
  const children = [];
  let staticServer;
  try {
    const portA = await freePort(); let portB = await freePort();
    while (portB === portA) portB = await freePort();
    const baseA = `http://127.0.0.1:${portA}`, baseB = `http://127.0.0.1:${portB}`;
    const advertised = (id, base) => ({ id, base, publication: base + '/publication', submit: base + '/submit' });
    const a = advertised('a', baseA), b = advertised('b', baseB);
    const configPath = path.join(temp, 'web.json');
    // JSON is valid YAML. Alias only in isolated test configuration; no repo route edits.
    await writeFile(configPath, JSON.stringify({ web: { pages: { '/ai': 'ai-first/index.html' } } }));
    const environment = (id, port, nodes) => ({
      PUNKTO_NODE_CONFIG: configPath, PUNKTO_HOST: '127.0.0.1', PUNKTO_PORT: String(port),
      PUNKTO_DATA_DIR: path.join(temp, id), PUNKTO_PUBLICATION_PATH: path.join(temp, id, 'publication'),
      PUNKTO_PUBLICATION_ENABLED: 'true', PUNKTO_PUBLICATION_PACKS: 'false',
      PUNKTO_WEB_ENABLED: 'true', PUNKTO_WEB_ROOT: path.join(ROOT, 'pwa'),
      PUNKTO_PEERS: '', PUNKTO_SYNC_INTERVAL: '3600', PUNKTO_BOOTSTRAP_NODES: JSON.stringify(nodes),
    });
    const envA = environment('a', portA, [a, b]);
    // The frozen node sorts bootstrap entries by id, independent of config order.
    const envB = environment('b', portB, [{ ...b, id: 'a-local-b' }, { ...a, id: 'z-peer-a' }]);
    let nodeA = await startNode(envA); children.push(nodeA);
    let nodeB = await startNode(envB); children.push(nodeB);
    const nodesA = baseA + '/nodes.json', nodesB = baseB + '/nodes.json';
    const keyA = path.join(temp, 'author-a.seed'), keyB = path.join(temp, 'author-b.seed');
    let parent, reply;

    await t.test('boot and pwa/ai-first/copy-conformance', async () => {
      const boot = await cli(nodesA, ['boot']);
      assert.deepEqual(boot.nodes, [a, b]); assert.match(boot.notice, /not a trust authority/);
      const html = (await get(baseA + '/ai-first/')).toString();
      assert.equal((await get(baseA + '/ai')).toString(), html);
      for (const phrase of ['Explore / harvest', 'Publish / discuss', 'Store / serve', 'Replicate / preserve', 'not required for reading', 'CC0', 'provider-neutral', 'one competing commercial provider']) assert.ok(html.includes(phrase), phrase);
      for (const section of ['BOOT', 'DISCOVER', 'PUBLISH', 'VERIFY', 'REPLY', 'LIMITS']) assert.ok(html.includes(`<h2>${section}</h2>`));
      assert.ok(html.indexOf('<h2>DISCOVER') < html.indexOf('<h2>PUBLISH'));
      assert.ok(Buffer.byteLength(html) < 10000);
    });
    await t.test('explicit address enforcement and key location guard', async () => {
      for (const args of [[], ['--h', ''], ['--h', 'bad'], ['--h', 'u3butz7k9q_23.0'], ['--lat', '55', '--lon', '12']]) {
        const r = await cli(nodesA, ['publish', '--text', 'reject', ...args], false);
        assert.match(r.error, /explicit|canonical|height/);
      }
      const rejected = await cli(nodesA, ['publish', '--h', H, '--text', 'reject', '--key-file', path.join(ROOT, 'must-not-exist.seed')], false);
      assert.match(rejected.error, /outside the repository/);
      await assert.rejects(stat(path.join(ROOT, 'must-not-exist.seed')), { code: 'ENOENT' });
    });
    await t.test('canonical/MID self-consistency and signed-acceptance distinction', async () => {
      parent = await cli(nodesA, ['publish', '--h', H, '--text', 'Stage 0 parent', '--key-file', keyA]);
      assert.match(parent.note, /accepted the signature.*not proof of visibility/);
      assert.equal(parent.duplicate, false);
      const raw = await get(`${a.publication}/records/${parent.sha256.slice(0, 2)}/${parent.sha256}`);
      assert.equal(hash(raw), parent.sha256);
      const bodySize = raw.readUInt32BE(0);
      const body = raw.subarray(4, 4 + bodySize);
      assert.equal('punkti/0.6:' + hash(Buffer.concat([Buffer.from('PUNKTI-L3-MID\0'), body])), parent.mid);
      assert.equal(decodeRecord(Uint8Array.from(raw)).atom.h, H);
      const verified = await cli(nodesA, ['verify', '--mid', parent.mid, '--h', H]);
      assert.deepEqual(verified.checks, { sha256: 'PASS', mid: 'PASS', signature: 'PASS', h: 'PASS' });
      const duplicateResponse = await fetch(a.submit, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ records: [{ address: parent.mid, sha256: parent.sha256, record: raw.toString('base64') }] }) });
      const duplicate = await duplicateResponse.json();
      console.log(`HTTP POST ${a.submit} -> ${duplicateResponse.status}`, JSON.stringify(duplicate));
      assert.equal(duplicate.results[0].duplicate, true);
      const mismatch = await cli(nodesA, ['verify', '--mid', parent.mid, '--h', 'u3butz7k9q_24'], false);
      assert.equal(mismatch.checks.h, 'FAIL');
    });
    await t.test('two processes: static GET replication, differently keyed same-h reply, return verification', async () => {
      const absent = await cli(nodesB, ['verify', '--mid', parent.mid], false);
      assert.equal(absent.visible, false); assert.match(absent.message, /publication lag/);
      await nodeB.stop(); const imported = await pull(envB, a.publication);
      nodeB = await startNode(envB); children.push(nodeB);
      const verified = await cli(nodesB, ['verify', '--mid', parent.mid, '--h', H]);
      assert.equal(verified.sha256, parent.sha256); assert.equal(verified.head, parent.head); assert.equal(imported.head, parent.head);
      const rawA = await get(`${a.publication}/records/${parent.sha256.slice(0, 2)}/${parent.sha256}`);
      const rawB = await get(`${b.publication}/records/${parent.sha256.slice(0, 2)}/${parent.sha256}`);
      assert.deepEqual(rawA, rawB);
      const discovery = await cli(nodesB, ['discover', '--xy', 'u3', '--limit', '1']);
      assert.equal(discovery.branches.u3, 1); assert.equal(discovery.candidates[0].h, H);
      const cross = await cli(nodesB, ['reply', '--parent-mid', parent.mid, '--h', 'u3butz7k9q_24', '--text', 'reject'], false);
      assert.match(cross.error, /cross-address/);
      reply = await cli(nodesB, ['reply', '--parent-mid', parent.mid, '--text', 'Stage 0 reply', '--key-file', keyB]);
      assert.notEqual(reply.publicKey, parent.publicKey); assert.equal(reply.h, H);
      await nodeA.stop(); const returned = await pull(envA, b.publication);
      nodeA = await startNode(envA); children.push(nodeA);
      const replyRead = await cli(nodesA, ['verify', '--mid', reply.mid, '--h', H]);
      assert.equal(replyRead.ok, true); assert.equal(replyRead.sha256, reply.sha256);
      assert.deepEqual(replyRead.refs, [{ target: parent.mid, rel: 'reply' }]);
      console.log('ROUNDTRIP_EVIDENCE', JSON.stringify({ nodeA: baseA, nodeB: baseB, parent, imported, reply, returned, replyRead }));
      console.log('Scripted harness, not a blind-AI experiment. Explicit offline pulls use frozen replicate_publication; automatic mesh replication, independent implementation conformance, public network and durability guarantees are not exercised.');
    });
    await t.test('reusable key continuity, fresh key, ephemeral label and exact coordinate height', async () => {
      const second = await cli(nodesA, ['publish', '--lat', '55.6761', '--lon', '12.5683', '--height', '23.123456789', '--text', 'same key', '--key-file', keyA]);
      assert.equal(second.publicKey, parent.publicKey); assert.match(second.h, /_23\.123456789$/);
      assert.equal((await stat(keyA)).mode & 0o777, 0o600);
      const fresh = await cli(nodesA, ['publish', '--h', H, '--text', 'fresh key', '--key-file', path.join(temp, 'fresh.seed')]);
      assert.notEqual(fresh.publicKey, parent.publicKey);
      const ephemeral = await cli(nodesA, ['publish', '--h', H, '--text', 'ephemeral']);
      assert.match(ephemeral.identity, /ephemeral.*no continuity/);
    });
    await t.test('frozen fixture static GET discovery, counts, digest failures and invalid bootstrap', async () => {
      const fixture = JSON.parse(await readFile(path.join(ROOT, 'experimental/punkti-v0.6-publication/vectors.json'), 'utf8')).fixtures.index;
      const files = new Map([['/publication/root.json', Buffer.from(fixture.root, 'hex')]]);
      const expected = [];
      for (const [sha, object] of Object.entries(fixture.objects)) {
        const raw = Buffer.from(object.hex, 'hex');
        let p;
        if (object.kind === 'manifest') p = `manifests/${sha}.json`;
        else if (object.kind === 'shard') {
          const shard = JSON.parse(raw); p = `h/${shard.prefix.split('').join('/')}/${sha}.json`;
          expected.push(...shard.records.filter(e => e.h));
        } else p = `${object.kind === 'record' ? 'records' : 'segments'}/${sha.slice(0, 2)}/${sha}`;
        files.set('/publication/' + p, raw);
      }
      const requests = [];
      let base, corrupt = false, invalidBoot = false;
      staticServer = http.createServer((req, res) => {
        requests.push([req.method, req.url]);
        let bytes = req.url === '/nodes.json' ? Buffer.from(JSON.stringify({ v: invalidBoot ? 'wrong' : 'punkti/bootstrap/1', nodes: [advertised('fixture', base)] })) : files.get(req.url);
        if (corrupt && req.url.includes('/manifests/')) bytes = Buffer.from('corrupted bytes');
        res.writeHead(bytes ? 200 : 404); res.end(bytes);
      });
      base = await listen(staticServer);
      const discovery = await cli(base + '/nodes.json', ['discover']);
      assert.equal(discovery.candidates.length, expected.length);
      assert.ok(expected.length > 0);
      for (const [prefix, count] of Object.entries(discovery.branches)) assert.equal(count, expected.filter(e => e.h.split('_')[0].startsWith(prefix)).length);
      assert.match(discovery.countsDerived, /leaf records/);
      assert.ok(requests.every(([method, p]) => method === 'GET' && (p === '/nodes.json' || p.startsWith('/publication/'))));
      corrupt = true;
      const failure = await cli(base + '/nodes.json', ['discover'], false);
      assert.match(failure.error, /FAIL.*SHA-256/);
      invalidBoot = true;
      assert.match((await cli(base + '/nodes.json', ['boot'], false)).error, /invalid bootstrap/);
    });
    await t.test('fresh-directory URL-only cold-start with downloaded client and no repository context', async () => {
      const result = await command('bash', [path.join(ROOT, 'pwa/ai-first/coldstart.sh'), nodesA]);
      process.stdout.write(result.stderr); process.stdout.write(result.stdout);
      assert.equal(result.code, 0, result.stdout + result.stderr);
      assert.match(result.stdout, /"signature":"PASS"/);
      assert.match(result.stdout, /Scripted harness, not a blind-AI experiment/);
      assert.match(result.stderr, /HTTP GET .*\/ai-first\/agent.mjs -> 200/);
    });
  } finally {
    for (const child of children) await child.stop();
    if (staticServer) await new Promise(resolve => staticServer.close(resolve));
    await rm(temp, { recursive: true, force: true });
  }
});
