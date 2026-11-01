import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, mkdir, readFile, writeFile, rm, stat, readdir, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { webcrypto } from 'node:crypto';
import { VERSION, State, encodeRecord, decodeRecord, canonical, computeMid, sha256Hex, signingInput, validate, unb64 } from './punkti/carrier.js';
import { createReader } from './punkti/reader.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const HELPER = path.join(ROOT, 'pwa/punkti/punkto-reply.mjs');
const H = 'u3butz7k9q_23.123456789';
const UNKNOWN = 'punkti/0.6:' + '0'.repeat(64);
const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('PUNKTO_') && !['NODE_OPTIONS', 'PYTHONPATH'].includes(key) && !/proxy/i.test(key)));
const nativeFetch = globalThis.fetch;
const network = [];
function loopback(address) {
  const url = new URL(address);
  assert.equal(url.hostname, '127.0.0.1', 'non-loopback request forbidden');
  assert.equal(url.protocol, 'http:');
  return url;
}
async function get(address, init = {}) {
  loopback(address);
  network.push({ url: String(address), method: init.method ?? 'GET' });
  return nativeFetch(address, { ...init, redirect: 'error', signal: AbortSignal.timeout(10000) });
}
globalThis.crypto ??= webcrypto;
globalThis.nacl = createRequire(import.meta.url)('./nacl.min.js');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function listen(server) {
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  return `http://127.0.0.1:${server.address().port}`;
}
async function freePort() {
  const server = http.createServer(); const base = await listen(server);
  await new Promise(resolve => server.close(resolve)); return new URL(base).port;
}
async function command(executable, args, cwd, extraEnv = {}) {
  const child = spawn(executable, args, { cwd, env: { ...env, ...extraEnv }, stdio: ['ignore', 'pipe', 'pipe'] });
  let stdout = '', stderr = '';
  child.stdout.on('data', b => { stdout += b; }); child.stderr.on('data', b => { stderr += b; });
  const timer = setTimeout(() => child.kill('SIGKILL'), 45000);
  try { const [code] = await once(child, 'exit'); return { code, stdout, stderr }; }
  finally { clearTimeout(timer); }
}
async function fixture(temp, name, singleWriter = false) {
  const dir = path.join(temp, name); await mkdir(dir);
  const port = await freePort(), backend = `http://127.0.0.1:${port}`;
  const requests = [], overrides = new Map(); let bootOverride = null;
  const proxy = http.createServer(async (req, res) => {
    try {
      const chunks = []; for await (const chunk of req) chunks.push(chunk);
      const body = Buffer.concat(chunks);
      const url = base + req.url; loopback(url);
      requests.push({ url, method: req.method, headers: req.headers, body: body.toString() });
      if (req.url === '/nodes.json' && bootOverride) {
        res.writeHead(200); res.end(JSON.stringify(bootOverride)); return;
      }
      if (overrides.has(req.url)) {
        res.writeHead(200); res.end(overrides.get(req.url)); return;
      }
      const response = await get(backend + req.url, { method: req.method,
        ...(body.length ? { body, headers: { 'Content-Type': req.headers['content-type'] ?? 'application/json' } } : {}) });
      res.writeHead(response.status, { 'Content-Type': response.headers.get('content-type') ?? 'application/octet-stream' });
      res.end(Buffer.from(await response.arrayBuffer()));
    } catch { res.writeHead(502); res.end('fixture proxy failure'); }
  });
  const base = await listen(proxy);
  const node = { id: 'z-local', base, publication: base + '/publication', submit: base + '/submit' };
  // First entry is deliberately read-only: selection must prefer the page origin writer.
  const nodes = singleWriter ? [node] : [{ id: 'a-read-only', base: backend, publication: backend + '/publication' }, node];
  const config = path.join(dir, 'config.json'); await writeFile(config, '{}');
  const guard = path.join(dir, 'sitecustomize.py');
  await writeFile(guard, `import socket, os\n_original = socket.socket.connect\ndef connect(self, address):\n    if isinstance(address, tuple) and address[0] != '127.0.0.1':\n        os.write(2, b'NON_LOOPBACK_ATTEMPT\\n')\n        os._exit(97)\n    return _original(self, address)\nsocket.socket.connect = connect\n`);
  const child = spawn('python3', ['-m', 'punkti_node'], { cwd: ROOT, env: { ...env,
    PYTHONPATH: dir, PUNKTO_NODE_CONFIG: config, PUNKTO_HOST: '127.0.0.1', PUNKTO_PORT: port,
    PUNKTO_DATA_DIR: path.join(dir, 'data'), PUNKTO_PUBLICATION_PATH: path.join(dir, 'publication'),
    PUNKTO_PUBLICATION_ENABLED: 'true', PUNKTO_PUBLICATION_PACKS: 'false',
    PUNKTO_WEB_ENABLED: 'true', PUNKTO_WEB_ROOT: path.join(ROOT, 'pwa'),
    PUNKTO_PEERS: '', PUNKTO_SYNC_INTERVAL: '3600', PUNKTO_BOOTSTRAP_NODES: JSON.stringify(nodes),
  }, stdio: ['ignore', 'pipe', 'pipe'] });
  let logs = '';
  child.stdout.on('data', b => { logs += b; }); child.stderr.on('data', b => { logs += b; });
  const stop = async () => {
    if (child.exitCode === null && !child.signalCode) {
      const done = once(child, 'exit'); child.kill('SIGTERM');
      const timer = setTimeout(() => child.kill('SIGKILL'), 5000);
      try { await done; } finally { clearTimeout(timer); }
    }
    proxy.closeAllConnections(); await new Promise(resolve => proxy.close(resolve));
    assert.ok(!logs.includes('NON_LOOPBACK_ATTEMPT'), 'Python attempted external contact');
    assert.notEqual(child.exitCode, 97);
  };
  for (let i = 0; i < 100; i++) {
    try { if ((await get(backend + '/health')).ok) return { base, node, requests, overrides, stop,
      bootstrap(value) { bootOverride = value; },
    }; } catch {}
    if (child.exitCode !== null) break;
    await delay(100);
  }
  await stop(); throw new Error('fixture startup failed: ' + logs);
}

// A valid static publication with a damaged signature, rebuilt using frozen SHA-256.
// Keeping the object digests valid makes the reader expose INVALID-provenance.
async function corruptedPublication(encoded) {
  const files = new Map(), raw = Uint8Array.from(encoded.record); raw[raw.length - 1] ^= 1;
  const sha = await sha256Hex(raw);
  files.set(`/publication/records/${sha.slice(0, 2)}/${sha}`, Buffer.from(raw));
  let childSha;
  const xy = H.split('_')[0];
  for (let depth = 10; depth >= 2; depth--) {
    const prefix = xy.slice(0, depth);
    const shard = { children: depth === 10 ? {} : { [xy.slice(0, depth + 1)]: childSha }, packs: [], prefix,
      records: depth === 10 ? [{ h: H, mid: encoded.address, sha256: sha }] : [], v: 'punkti/pub/0.6' };
    const bytes = Buffer.from(JSON.stringify(shard)); childSha = await sha256Hex(bytes);
    files.set(`/publication/h/${prefix.split('').join('/')}/${childSha}.json`, bytes);
  }
  const manifest = Buffer.from(JSON.stringify({ index: { [xy.slice(0, 2)]: childSha }, pack_count: 0, prev: null, record_count: 1, seq: 1, v: 'punkti/pub/0.6' }));
  const head = await sha256Hex(manifest);
  files.set(`/publication/manifests/${head}.json`, manifest);
  files.set('/publication/root.json', Buffer.from(JSON.stringify({ head, seq: 1, v: 'punkti/pub/0.6' })));
  return files;
}

await test('single-action helper with an isolated real Punkti node', async t => {
  const temp = await mkdtemp(path.join(tmpdir(), 'punkto-a1-'));
  const fixtures = [];
  const audit = path.join(temp, 'requests.jsonl'), preload = path.join(temp, 'guard.mjs');
  await writeFile(preload, `import { appendFileSync } from 'node:fs';
const original = globalThis.fetch;
globalThis.fetch = (address, init = {}) => {
  const url = new URL(address);
  if (url.hostname !== '127.0.0.1' || url.protocol !== 'http:') {
    process.stderr.write('NON_LOOPBACK_ATTEMPT\\n'); process.exit(97);
  }
  appendFileSync(${JSON.stringify(audit)}, JSON.stringify({ url: url.href, method: init.method ?? 'GET', headers: init.headers ?? {}, body: init.body ?? '', helper: process.argv[1].endsWith('punkto-reply.mjs'), redirect: init.redirect, timed: Boolean(init.signal) }) + '\\n');
  return original(address, { ...init, redirect: 'error' });
};\n`);
  const nodeRun = (file, args, cwd = ROOT) => command(process.execPath, ['--import', preload, file, ...args], cwd);
  const run = async (f, args, success = true) => {
    const result = await nodeRun(HELPER, [...args, '--origin', f.base]);
    assert.equal(result.code, success ? 0 : 1, result.stdout + result.stderr);
    assert.equal(result.stderr, '');
    const json = JSON.parse(result.stdout);
    assert.equal(json.ok, success);
    if (!success) assert.deepEqual(Object.keys(json).sort(), ['error', 'ok']);
    return json;
  };
  const snapshot = f => createReader({ fetchImpl: get, maxRetries: 0 }).readPublication(f.node.publication);
  const seed = async (f, encoded) => {
    const response = await get(f.node.submit, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ records: [{ address: encoded.address, sha256: encoded.sha256, record: Buffer.from(encoded.record).toString('base64') }] }) });
    assert.equal(response.status, 200);
  };
  try {
    const f = await fixture(temp, 'main'); fixtures.push(f);
    const welcome = await encodeRecord({ v: VERSION, t: Date.now(), h: H, x: JSON.stringify({ text: 'Welcome — local fixture conversation' }), alg: 'ed25519', refs: [], ext: '' }, globalThis.nacl.sign.keyPair().secretKey);
    await seed(f, welcome);
    let reply;

    await t.test('1. valid reads use the canonical resolver paths and output-only limit', async () => {
      const start = f.requests.length;
      const result = await run(f, ['read']);
      assert.deepEqual(result.records, [{ mid: welcome.address, h: H, text: 'Welcome — local fixture conversation', state: 'VALID' }]);
      const paths = f.requests.slice(start).map(r => new URL(r.url).pathname);
      assert.ok(paths.includes('/publication/root.json'));
      assert.equal(paths.filter(p => /^\/publication\/manifests\/[a-f0-9]{64}\.json$/.test(p)).length, 1);
      assert.equal(paths.filter(p => /^\/publication\/h\/(?:[0-9a-z]\/){2,10}[a-f0-9]{64}\.json$/.test(p)).length, 9);
      assert.ok(paths.includes(`/publication/records/${welcome.sha256.slice(0, 2)}/${welcome.sha256}`));
      const count = f.requests.length;
      assert.deepEqual((await run(f, ['read', '--limit', '0'])).records, []);
      assert.equal(f.requests.length - count, paths.length, '--limit cannot narrow verification scope');
      assert.equal((await get(f.base + '/ai')).status, 200);
    });

    await t.test('2. persistent key stays local, mode 0600, reused, repositories refused', async () => {
      const key = path.join(temp, 'identity.seed');
      const first = await run(f, ['post', 'persistent one', '--h', H, '--key-file', key]);
      const second = await run(f, ['post', 'persistent two', '--h', H, '--key-file', key]);
      assert.equal(first.public_key, second.public_key);
      assert.equal((await stat(key)).mode & 0o777, 0o600);
      const seedHex = await readFile(key, 'utf8');
      const identity = globalThis.nacl.sign.keyPair.fromSeed(new Uint8Array(Buffer.from(seedHex, 'hex')));
      const captured = await readFile(audit, 'utf8') + JSON.stringify([first, second, f.requests]);
      for (const secret of [seedHex, Buffer.from(seedHex, 'hex').toString('base64'), Buffer.from(identity.secretKey).toString('hex'), Buffer.from(identity.secretKey).toString('base64'), key]) {
        assert.ok(!captured.includes(secret), 'secret material or key path escaped local custody');
      }
      // Decode the submitted records as well, so base64 cannot hide an accidentally embedded secret.
      for (const request of f.requests.filter(r => r.method === 'POST')) {
        const raw = Buffer.from(JSON.parse(request.body).records[0].record, 'base64');
        assert.ok(!raw.includes(Buffer.from(seedHex, 'hex')), 'seed embedded in submitted record');
        assert.ok(!raw.includes(Buffer.from(identity.secretKey)), 'secret key embedded in submitted record');
      }
      const repoKey = path.join(ROOT, 'a1-must-not-exist.seed');
      assert.match((await run(f, ['post', 'reject', '--h', H, '--key-file', repoKey], false)).error, /outside any git repository/);
      await assert.rejects(stat(repoKey), { code: 'ENOENT' });
      const alias = path.join(temp, 'repo-alias'); await symlink(ROOT, alias);
      assert.match((await run(f, ['post', 'reject', '--h', H, '--key-file', path.join(alias, 'a1-must-not-exist.seed')], false)).error, /outside any git repository/);
      const nested = path.join(temp, 'other-repo'); await mkdir(nested); await writeFile(path.join(nested, '.git'), 'gitdir: elsewhere');
      assert.match((await run(f, ['post', 'reject', '--h', H, '--key-file', path.join(nested, 'identity')], false)).error, /outside any git repository/);
    });

    await t.test('3. inherit exact h/refs only from verified parent; corrupted and absent parents issue no POST', async () => {
      reply = await run(f, ['reply', welcome.address, 'exact inheritance']);
      assert.equal(reply.h, H); assert.deepEqual(reply.parent, { mid: welcome.address, h: H, verified: true });
      const record = (await snapshot(f)).records.find(r => r.mid === reply.mid);
      assert.deepEqual(record.atom.refs, [{ target: welcome.address, rel: 'reply' }]);
      for (const [p, bytes] of await corruptedPublication(welcome)) f.overrides.set(p, bytes);
      const before = f.requests.filter(r => r.method === 'POST').length;
      assert.match((await run(f, ['reply', welcome.address, 'reject'], false)).error, /parent record is not signature-verified \(state=INVALID-provenance\)/);
      assert.deepEqual((await run(f, ['read'])).records, []);
      f.overrides.clear();
      assert.match((await run(f, ['reply', UNKNOWN, 'reject'], false)).error, /parent MID not found/);
      assert.match((await run(f, ['reply', welcome.address, 'reject', '--h', H], false)).error, /unknown flag/);
      assert.equal(f.requests.filter(r => r.method === 'POST').length, before);
    });

    await t.test('4. signed reply admitted/published; explicit coordinates preserve chosen height', async () => {
      assert.equal(reply.submitted, true); assert.equal(reply.submit_state, State.VALID);
      assert.equal(reply.visible, true); assert.equal(reply.verified, true);
      assert.equal(reply.node.id, 'z-local');
      const post = await run(f, ['post', 'coordinates', '--lat', '55.6761', '--lon', '12.5683', '--height', '23.123456789']);
      assert.ok(post.h.endsWith('_23.123456789')); assert.equal(post.parent, null);
    });

    await t.test('5. exact receipt fields and independent byte/signature verification; lag/duplicates disclosed', async () => {
      assert.deepEqual(Object.keys(reply).sort(), ['ok', 'action', 'mid', 'h', 'parent', 'submitted', 'submit_state', 'duplicate', 'visible', 'verified', 'replicated', 'public_key', 'key', 'node', 'publication', 'warnings'].sort());
      const record = (await snapshot(f)).records.find(r => r.mid === reply.mid);
      const raw = new Uint8Array(await (await get(`${f.node.publication}/records/${record.sha256.slice(0, 2)}/${record.sha256}`)).arrayBuffer());
      const decoded = decodeRecord(raw);
      assert.equal(await sha256Hex(raw), record.sha256);
      assert.deepEqual(canonical(decoded.atom), decoded.body);
      assert.equal(`${VERSION}:${await computeMid(decoded.body)}`, reply.mid);
      assert.ok(globalThis.nacl.sign.detached.verify(signingInput(decoded.body), decoded.sig, unb64(decoded.atom.pk)));
      assert.equal((await validate(raw)).state, State.VALID); assert.equal(decoded.atom.h, H);
      assert.equal(reply.replicated, 'not-measured'); assert.equal(reply.key, 'ephemeral');
      assert.ok(reply.warnings.some(w => /not a durable identity/.test(w)));
      assert.ok(reply.warnings.some(w => /not post-quantum secure/.test(w)));
      // Keep serving the old immutable root while the real backend accepts a new record.
      f.overrides.set('/publication/root.json', Buffer.from(await (await get(f.base + '/publication/root.json')).arrayBuffer()));
      const lag = await run(f, ['post', 'accepted with publication lag', '--h', H]);
      assert.equal(lag.submitted, true); assert.equal(lag.visible, false); assert.equal(lag.verified, false);
      assert.ok(lag.warnings.some(w => /not visible/.test(w))); f.overrides.clear();
      // Identical timestamp, text and persistent identity produce a real duplicate admission.
      const fixed = path.join(temp, 'fixed-time.mjs'); await writeFile(fixed, `Date.now = () => ${Date.now()};`);
      const args = ['--import', preload, '--import', fixed, HELPER, 'post', 'duplicate', '--h', H, '--key-file', path.join(temp, 'identity.seed'), '--origin', f.base];
      const first = await command(process.execPath, args, ROOT), second = await command(process.execPath, args, ROOT);
      assert.equal(first.code, 0); assert.equal(second.code, 0);
      const duplicate = JSON.parse(second.stdout); assert.equal(duplicate.duplicate, true);
      assert.ok(duplicate.warnings.some(w => /duplicate/.test(w)));
    });

    await t.test('6. clear failures: missing writer, unreachable node, address and argument errors', async () => {
      f.bootstrap({ v: 'punkti/bootstrap/1', nodes: [{ ...f.node, submit: undefined }] });
      assert.match((await run(f, ['reply', welcome.address, 'reject'], false)).error, /does not accept writes/);
      f.bootstrap({ v: 'wrong', nodes: [f.node] });
      assert.match((await run(f, ['read'], false)).error, /bootstrap failed/); f.bootstrap(null);
      const port = await freePort();
      const unreachable = await nodeRun(HELPER, ['read', '--origin', `http://127.0.0.1:${port}`]);
      assert.equal(unreachable.code, 1); assert.match(JSON.parse(unreachable.stdout).error, /bootstrap failed.*unreachable/);
      for (const h of ['', 'bad', 'u3butz7k9q', 'u3butz7k9q_23.0']) {
        assert.match((await run(f, ['post', 'reject', '--h', h], false)).error, /post address: invalid --h/);
      }
      assert.match((await run(f, ['post', 'reject', '--h', H, '--lat', '55'], false)).error, /post address: choose --h or coordinates/);
      assert.match((await run(f, ['post', 'reject', '--lat', '55', '--lon', '12'], false)).error, /post address:.*--height required/);
      for (const args of [[], ['unknown'], ['reply'], ['read', '--surprise', '1'], ['read', '--limit', '-1'], ['read', '--limit']]) await run(f, args, false);
    });

    if (process.env.PUNKTO_CAPTURE_TRANSCRIPT === '1') {
      await t.test('captured fresh-directory old/new UX runs', async () => {
        await captureTranscript({ temp, fixtures, fixture, seed, welcome, nodeRun, get, snapshot });
      });
    }

    await t.test('7. every HTTP request targets 127.0.0.1; helper requests reject redirects and have timeouts', async () => {
      const logged = (await readFile(audit, 'utf8')).trim().split('\n').map(JSON.parse);
      assert.ok(logged.length > 0);
      for (const request of [...network, ...f.requests, ...logged]) loopback(request.url);
      for (const request of logged) {
        // The old CLI in the optional transcript predates these helper guarantees.
        if (request.helper) { assert.equal(request.redirect, 'error'); assert.equal(request.timed, true); }
      }
      // A hostile bootstrap entry is blocked before DNS/socket access and cannot be swallowed.
      f.bootstrap({ v: 'punkti/bootstrap/1', nodes: [{ id: 'hostile', base: 'http://forbidden.invalid', publication: 'http://forbidden.invalid/publication' }] });
      const rejected = await nodeRun(HELPER, ['read', '--origin', f.base]);
      assert.equal(rejected.code, 97); assert.match(rejected.stderr, /NON_LOOPBACK_ATTEMPT/); f.bootstrap(null);
    });
  } finally {
    try { for (const f of fixtures.reverse()) await f.stop(); }
    finally { await rm(temp, { recursive: true, force: true }); }
  }
});

async function captureTranscript({ temp, fixtures, fixture, seed, welcome, nodeRun, get, snapshot }) {
  const lines = ['# A1 single-action UX transcript', '',
    'Captured by actually running the local fixture and commands below. This is a scripted UX proof, not a blind-agent experiment. Both comparison nodes advertise a single writer and start with the same one-record welcome publication. The main test suite separately exercises the live-like read-only-first bootstrap topology. The new agent starts with only its `/ai` URL and `Hello from a new AI`; it obtains the parent MID and exact h from the HTTP read.', '',
    'The fixture runs the real `python3 -m punkti_node` with the repository `pwa/` web root. A loopback recording proxy and a Node `--import` audit guard count requests and block non-loopback contact. The displayed Node commands omit that harness-only guard; arguments and stdout are otherwise captured verbatim. Curl uses no proxy, no redirects and a 10-second timeout. All addresses below are ephemeral local ports.', ''];
  const block = value => lines.push('```text', value.trimEnd(), '```', '');
  const metrics = {};
  const shell = value => "'" + value.replaceAll("'", "'\\''") + "'";
  async function curl(f, cwd, url, filename, display = true) {
    loopback(url);
    const args = ['--noproxy', '*', '--proto', '=http', '--max-time', '10', '-fsS', url, '-o', filename, '-w', 'GET %{url_effective} -> %{http_code} bytes=%{size_download}\n'];
    const result = await command('curl', args, cwd);
    assert.equal(result.code, 0, result.stderr);
    if (display) block('$ curl ' + args.map(shell).join(' ') + '\n' + result.stdout);
    return readFile(path.join(cwd, filename));
  }
  async function independent(f, receipt, h) {
    const before = f.requests.length;
    const view = await snapshot(f);
    const record = view.records.find(r => r.mid === receipt.mid); assert.ok(record);
    const url = `${f.node.publication}/records/${record.sha256.slice(0, 2)}/${record.sha256}`;
    const response = await get(url), raw = new Uint8Array(await response.arrayBuffer());
    const decoded = decodeRecord(raw);
    const checks = {
      sha256: await sha256Hex(raw) === record.sha256 ? 'PASS' : 'FAIL',
      mid: `${VERSION}:${await computeMid(canonical(decoded.atom))}` === receipt.mid ? 'PASS' : 'FAIL',
      signature: globalThis.nacl.sign.detached.verify(signingInput(decoded.body), decoded.sig, unb64(decoded.atom.pk)) ? 'PASS' : 'FAIL',
      h: decoded.atom.h === h ? 'PASS' : 'FAIL',
    };
    assert.ok(Object.values(checks).every(value => value === 'PASS'));
    block(`Independent harness re-read: GET ${url} -> ${response.status} bytes=${raw.length}\n` + JSON.stringify({ mid: record.mid, h: decoded.atom.h, refs: decoded.atom.refs, text: JSON.parse(decoded.atom.x).text, head: view.head, seq: view.seq, checks }));
    return f.requests.length - before;
  }

  const fresh = await fixture(temp, 'transcript-new', true); fixtures.push(fresh); await seed(fresh, welcome);
  const cwd = path.join(temp, 'fresh-empty-agent'); await mkdir(cwd);
  assert.deepEqual(await readdir(cwd), []);
  lines.push('## New route: fresh directory, READ, REPLY, verify', '');
  const pwd = await command('pwd', [], cwd), listing = await command('ls', ['-A'], cwd);
  block('$ pwd\n' + pwd.stdout + '$ ls -A\n' + listing.stdout);
  await curl(fresh, cwd, fresh.base + '/ai', 'ai.html');
  const startRead = fresh.requests.length;
  const boot = JSON.parse(await curl(fresh, cwd, fresh.base + '/nodes.json', 'nodes.json'));
  const node = boot.nodes.find(n => new URL(n.base).origin === fresh.base) ?? boot.nodes[0];
  const publication = new URL(node.publication, fresh.base).href;
  const root = JSON.parse(await curl(fresh, cwd, publication + '/root.json', 'root.json'));
  const manifest = JSON.parse(await curl(fresh, cwd, `${publication}/manifests/${root.head}.json`, 'manifest.json'));
  let [prefix, sha] = Object.entries(manifest.index)[0], entry;
  for (;;) {
    const shard = JSON.parse(await curl(fresh, cwd, `${publication}/h/${prefix.split('').join('/')}/${sha}.json`, 'shard.json'));
    if (shard.records.length) { entry = shard.records[0]; break; }
    [prefix, sha] = Object.entries(shard.children)[0];
  }
  const parentRaw = await curl(fresh, cwd, `${publication}/records/${entry.sha256.slice(0, 2)}/${entry.sha256}`, 'parent.record');
  block('Discovered leaf entry:\n' + JSON.stringify(entry) + '\nDecoded text:\n' + JSON.parse(decodeRecord(Uint8Array.from(parentRaw)).atom.x).text);
  metrics.newRead = { commands: fresh.requests.length - startRead, requests: fresh.requests.length - startRead };
  const startWrite = fresh.requests.length;
  await curl(fresh, cwd, fresh.base + '/punkti/punkto-reply.mjs', 'punkto-reply.mjs');
  const args = ['reply', entry.mid, 'Hello from a new AI', '--origin', fresh.base];
  const result = await nodeRun('punkto-reply.mjs', args, cwd); assert.equal(result.code, 0, result.stdout + result.stderr);
  block('$ node punkto-reply.mjs ' + args.map(shell).join(' ') + '\n' + result.stdout);
  const receipt = JSON.parse(result.stdout); assert.equal(receipt.visible, true); assert.equal(receipt.verified, true);
  metrics.newWrite = { commands: 2, requests: fresh.requests.length - startWrite };
  const newWriteRequests = fresh.requests.slice(startWrite);
  metrics.newVerify = await independent(fresh, receipt, entry.h);
  lines.push('Failure cases, captured after the successful flow (excluded from happy-path counts):', '');
  for (const args of [['reply', UNKNOWN, 'Hello from a new AI', '--origin', fresh.base], ['post', 'Hello from a new AI', '--h', 'u3butz7k9q_23.0', '--origin', fresh.base]]) {
    const failure = await nodeRun('punkto-reply.mjs', args, cwd); assert.equal(failure.code, 1);
    block('$ node punkto-reply.mjs ' + args.map(shell).join(' ') + '\n' + failure.stdout + 'exit=1');
  }

  lines.push('## Old route: six-file setup and explicit h/ref', '');
  const old = await fixture(temp, 'transcript-old', true); fixtures.push(old); await seed(old, welcome);
  const oldCwd = path.join(temp, 'fresh-empty-old'); await mkdir(oldCwd); assert.deepEqual(await readdir(oldCwd), []);
  block('$ pwd\n' + (await command('pwd', [], oldCwd)).stdout + '$ ls -A\n' + (await command('ls', ['-A'], oldCwd)).stdout);
  await curl(old, oldCwd, old.base + '/ai', 'ai.html');
  lines.push('The current /ai response supplies the local origin. For comparison the following commands reproduce the previous six-file recipe using the unchanged old CLI; they are not claimed to be the current page copy.', '');
  const oldReadStart = old.requests.length;
  for (const name of ['cli.mjs', 'carrier.js', 'spatial.js', 'reader.js', 'submit.js']) await curl(old, oldCwd, `${old.base}/punkti/${name}`, name);
  await curl(old, oldCwd, old.base + '/nacl.min.js', 'nacl.min.js');
  const readArgs = ['read', '--nodes', old.base + '/nodes.json', '--limit', '20'];
  const readResult = await nodeRun('cli.mjs', readArgs, oldCwd); assert.equal(readResult.code, 0, readResult.stdout + readResult.stderr);
  block('$ node cli.mjs ' + readArgs.map(shell).join(' ') + '\n' + readResult.stdout);
  metrics.oldRead = { commands: 7, requests: old.requests.length - oldReadStart };
  const oldParent = JSON.parse(readResult.stdout).records[0];
  const oldWriteStart = old.requests.length;
  const oldArgs = ['reply', '--nodes', old.base + '/nodes.json', '--h', oldParent.h, '--ref', oldParent.mid, '--text', 'Hello from a new AI'];
  const oldResult = await nodeRun('cli.mjs', oldArgs, oldCwd); assert.equal(oldResult.code, 0, oldResult.stdout + oldResult.stderr);
  block('$ node cli.mjs ' + oldArgs.map(shell).join(' ') + '\n' + oldResult.stdout);
  metrics.oldWrite = { commands: 1, requests: old.requests.length - oldWriteStart };
  metrics.oldVerify = await independent(old, JSON.parse(oldResult.stdout), oldParent.h);
  lines.push('Old CLI with a read-only node first (the known live-bootstrap limitation), excluded from the successful comparison:', '');
  old.bootstrap({ v: 'punkti/bootstrap/1', nodes: [{ id: 'a-read-only', base: old.base, publication: old.node.publication }, old.node] });
  const failureStart = old.requests.length;
  const oldFailure = await nodeRun('cli.mjs', oldArgs, oldCwd);
  assert.equal(oldFailure.code, 1);
  assert.match(JSON.parse(oldFailure.stdout).error, /does not accept writes/);
  block('$ node cli.mjs ' + oldArgs.map(shell).join(' ') + '\n' + oldFailure.stdout + 'exit=1');
  lines.push(`Measured failure: 1 command, ${old.requests.length - failureStart} HTTP request, 0 POSTs.`, '');
  old.bootstrap(null);

  lines.push('## Measured counts', '',
    'Counts below include actual HTTP requests at the public loopback entrypoint, including internal CLI requests. Proxy forwarding is not counted twice. Each curl invocation counts as a command (the old loop expands to six curl invocations); parsing already downloaded bytes and fixture orchestration are not user-facing network commands. The `pwd` and `ls -A` evidence commands are excluded from both routes. Each route additionally fetched `/ai` once: 1 command / 1 GET, shown separately from READ.', '',
    '| Stage | Old commands | Old HTTP requests | New commands | New HTTP requests |',
    '| --- | ---: | ---: | ---: | ---: |',
    '| Entrance `/ai` | 1 | 1 | 1 | 1 |',
    `| READ, including required client setup | ${metrics.oldRead.commands} | ${metrics.oldRead.requests} | ${metrics.newRead.commands} | ${metrics.newRead.requests} |`,
    `| WRITE, including helper download | ${metrics.oldWrite.commands} | ${metrics.oldWrite.requests} | ${metrics.newWrite.commands} | ${metrics.newWrite.requests} |`,
    `| Independent harness re-read (outside CLI counts) | — | ${metrics.oldVerify} | — | ${metrics.newVerify} |`, '',
    'Old READ: six module downloads plus a CLI read of bootstrap, root, manifest, nine shards and one record. New READ: thirteen plain curl GETs, with no Node/npm setup. The new route reduces write inputs to a MID and text, not the total number of HTTP requests.', '',
    'Old WRITE: one command, two requests (bootstrap + POST); the old CLI does not verify the parent or re-read after submission. New WRITE: one download command plus one publish command. Within that publish command: five frozen-module GETs, one bootstrap GET, twelve parent-publication GETs, one POST, and thirteen fresh-publication GETs for the now two-record publication. The download adds one GET. The receipt reports local visibility and verification, not replication.', '',
    'New WRITE request log (actual URL and method; response status/byte counts for plain curl steps are above):', '');
  block(newWriteRequests.map(r => `${r.method} ${r.url}`).join('\n'));
  lines.push('No production publish happened. Every request in these runs targeted 127.0.0.1. The production path additionally requires PR #140 to be merged and deployed. Production currently has no welcome thread: the measured 13 records are CEO-OS #33/#35 operator/canary evidence. Creating a production welcome thread is a separate Founder publish at an explicitly chosen address, deliberately not performed here.', '',
    'The helper uses local Ed25519 signing, which is not post-quantum secure. Its default ephemeral key is not a durable identity. A signature proves control of a key, not text truth or author location. Acceptance, publication, replication and long-term preservation remain distinct; nothing is guaranteed to survive forever.', '');
  await writeFile(path.join(ROOT, 'docs/AI_SINGLE_ACTION_TRANSCRIPT.md'), lines.join('\n'));
  console.log('Measured transcript counts:', JSON.stringify(metrics));
}
