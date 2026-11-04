import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { once } from 'node:events';
import { localNode, cli, ROOT } from './test-ai-coldstart.mjs';
import { run } from './punkti/cli.mjs';
import { createReader, hexShardedResolver } from './punkti/reader.js';
import { createSubmitClient } from './punkti/submit.js';
import { encodeRecord, decodeRecord, canonical, computeMid, sha256Hex, signingInput, unb64 } from './punkti/carrier.js';

const node = await localNode();
try {
  const nodesUrl = `${node.base}/nodes.json`;
  const entry = { id: 'test', base: node.base, publication: `${node.base}/publication` };
  const malformed = [
    { id: 'test', publication: entry.publication },
    { ...entry, base: 7 }, { ...entry, base: '/relative' },
    { ...entry, publication: entry.publication + '/' }, { ...entry, unknown: true },
  ];
  for (const item of malformed) {
    const filename = path.join(node.directory, 'invalid.json');
    writeFileSync(filename, JSON.stringify({ web: { enabled: false }, bootstrap: { nodes: [item] } }));
    const result = spawnSync('python3', ['-m', 'punkti_node', '--check-config', '--config', filename], { cwd: ROOT, encoding: 'utf8', env: Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('PUNKTO_'))) });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /bootstrap/);
  }
  // Stop our known local listener to obtain an unreachable endpoint without a
  // dependency on public networking or an assumed unused port.
  await node.stop();
  const unreachable = await cli(['read', '--nodes', nodesUrl]);
  assert.notEqual(unreachable.code, 0);
  assert.equal(typeof unreachable.body.error, 'string');
  await node.start();
  const identity = globalThis.nacl.sign.keyPair();
  const atom = { t: Date.now(), h: 'u3butz7k9q_23', x: JSON.stringify({ text: 'E2 duplicate' }) };
  const client = createSubmitClient({ baseUrl: node.base, identity });
  const first = await client.submit(atom);
  assert.equal(first.ok, true); assert.equal(first.duplicate, false);
  const duplicate = await client.submit(atom);
  assert.equal(duplicate.ok, true); assert.equal(duplicate.duplicate, true);
  const normal = await createReader().readPublication(entry.publication);
  assert.equal(normal.records.filter(record => record.mid === first.mid).length, 1);
  let flipped = false;
  const corruptReader = createReader({ maxRetries: 0, fetchImpl: async address => {
    const response = await fetch(address);
    if (address.includes('/records/')) {
      const bytes = new Uint8Array(await response.arrayBuffer()); bytes[bytes.length - 1] ^= 1; flipped = true;
      return new Response(bytes);
    }
    return response;
  } });
  await assert.rejects(corruptReader.readPublication(entry.publication), /corrupt object/);
  assert.equal(flipped, true);
  assert.equal(corruptReader.checkpoints.size, 0);
  // This frozen poison publication has a content-address-correct record with an
  // invalid signature, so rejection cannot be attributed to an object hash.
  const poison = JSON.parse(readFileSync(path.join(ROOT, 'experimental/punkti-v0.6-publication/vectors.json'))).fixtures.poison;
  const objects = new Map([['root.json', Buffer.from(poison.root, 'hex')]]);
  const resolver = hexShardedResolver();
  for (const [sha, object] of Object.entries(poison.objects)) {
    const raw = Buffer.from(object.hex, 'hex');
    const relative = object.kind === 'manifest' ? resolver.manifestPath(sha) : object.kind === 'shard' ? resolver.shardPath(JSON.parse(raw).prefix, sha) : object.kind === 'record' ? resolver.recordPath(sha) : resolver.segmentPath(sha);
    objects.set(relative, raw);
  }
  const poisoned = await createReader({ maxRetries: 0, fetchImpl: async address => {
    const raw = objects.get(new URL(address).pathname.slice(1));
    return new Response(raw, { status: raw ? 200 : 404 });
  } }).readPublication('http://fixture.invalid');
  assert.ok(poisoned.rejected > 0);
  assert.ok(poisoned.quarantined.some(record => record.state === 'INVALID-provenance'));
  assert.ok(poisoned.records.every(record => !poisoned.quarantined.some(bad => bad.sha256 === record.sha256)));
  const oldRoot = await (await fetch(`${entry.publication}/root.json`)).text();
  const added = await client.submit({ ...atom, t: atom.t + 1 }); assert.equal(added.ok, true);
  let stale = false;
  const reader = createReader({ maxRetries: 0, fetchImpl: address => stale && address.endsWith('/root.json') ? Promise.resolve(new Response(oldRoot)) : fetch(address) });
  const newer = await reader.readPublication(entry.publication);
  assert.ok(newer.seq > JSON.parse(oldRoot).seq);
  stale = true;
  await assert.rejects(reader.readPublication(entry.publication), /stale root/);
  const badRef = await cli(['reply', '--nodes', nodesUrl, '--ref', 'not-a-mid', '--text', 'bad']);
  assert.notEqual(badRef.code, 0); assert.match(badRef.body.error, /invalid MID/);
  const missingHeight = await cli(['write', '--nodes', nodesUrl, '--text', 'must not invent Z', '--lat', '55.675398', '--lon', '12.561895']);
  assert.notEqual(missingHeight.code, 0); assert.match(missingHeight.body.error, /--height|ellipsoidal height/);
  await assert.rejects(encodeRecord({ ...atom, refs: [{ target: 'not-a-mid', rel: 'reply' }] }, identity.secretKey), /reference/);
  let writes = 0;
  await assert.rejects(run(['write', '--nodes', nodesUrl, '--text', 'read only', '--submit', `${node.base}/submit`], async (_address, init) => {
    if (init?.method === 'POST') writes++;
    return new Response(JSON.stringify({ v: 'punkti/bootstrap/1', nodes: [entry] }));
  }), /does not accept writes/);
  assert.equal(writes, 0);
  let endpointUsed = null;
  const override = await run(['write', '--nodes', nodesUrl, '--submit', `${node.base}/custom-submit`, '--text', 'override', '--h', atom.h], async (address, init) => {
    if (init?.method === 'POST') { endpointUsed = address; return fetch(`${node.base}/submit`, init); }
    return fetch(address, init);
  });
  assert.equal(endpointUsed, `${node.base}/custom-submit`);
  assert.match(override.mid, /^punkti\/0\.6:[0-9a-f]{64}$/);
  const pageResponse = await fetch(`${node.base}/ai`);
  assert.equal(pageResponse.status, 200);
  assert.equal(pageResponse.headers.get('content-type'), 'text/html; charset=utf-8');
  assert.equal(pageResponse.headers.get('x-content-type-options'), 'nosniff');
  assert.equal(pageResponse.headers.get('cache-control'), 'no-cache, no-store, must-revalidate');
  const html = await pageResponse.text();
  const text = html.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
  // Content requirements are shared with the Python parser rather than freezing headings.
  const copy = spawnSync('python3', ['-m', 'unittest', 'discover', '-s', 'scripts/qa/tests',
    '-p', 'test_ai_entrance_copy.py'], { cwd: ROOT, encoding: 'utf8' });
  assert.equal(copy.status, 0, copy.stdout + copy.stderr);
  assert.ok(Buffer.byteLength(html) <= 7000);
  const blocks = [...html.matchAll(/<pre>([\s\S]*?)<\/pre>/g)].map(m => m[1]
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&'));
  const lines = blocks.flatMap(block => block.split('\n'));

  // (a) The client is Python stdlib HTTP + hashlib, with no Node/npm/SDK dependency.
  // Its URL comes from the page, not a hardcoded test request. Only GET is used.
  const httpOnly = spawnSync('python3', ['-c', `
import hashlib, json, re, urllib.request, urllib.error, socket, http.client
from pathlib import Path
page = Path('pwa/ai.html').read_text()
links = re.findall(r'href="(https://punkto.xyz/publication/records/([0-9a-f]{2})/([0-9a-f]{64}))"', page)
assert len(links) == 2
results, skipped = [], []
for url, prefix, sha in links:
    assert prefix == sha[:2]
    assert '/publication/records/' in url
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            raw = response.read()
            status = response.status
            content_type = response.headers.get_content_type()
    except urllib.error.HTTPError as error:
        if error.code != 429 and not 500 <= error.code <= 599:
            raise
        skipped.append(f"{url}: HTTP {error.code}")
        results.append(None)
        continue
    except (urllib.error.URLError, TimeoutError, ConnectionError,
            socket.gaierror, http.client.IncompleteRead, http.client.RemoteDisconnected) as error:
        skipped.append(f"{url}: {type(error).__name__}: {error}")
        results.append(None)
        continue
    # Content/status assertions are deliberately outside the transport catch.
    assert status == 200
    assert content_type == 'application/octet-stream'
    assert hashlib.sha256(raw).hexdigest() == sha
    results.append(dict(url=url, status=status, sha256=sha, bytes=len(raw), hex=raw.hex()))
print(json.dumps(dict(records=results, skipped=skipped)))

`], { cwd: ROOT, encoding: 'utf8', timeout: 70000 });
  assert.equal(httpOnly.status, 0, httpOnly.stderr);
  const { records: published, skipped } = JSON.parse(httpOnly.stdout);
  const rootGet = lines.find(line => line.startsWith('curl ') && line.includes('/publication/records/'));
  assert.ok(rootGet.includes('https://punkto.xyz/publication/records/24/2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d'), 'copyable GET must use the direct ROOT link');
  if (!skipped.length) console.log(`Comprehension (a): PASS — Python HTTP-only client, ROOT 1 GET / ${published[0].bytes} bytes, reply 1 GET / ${published[1].bytes} bytes; both SHA-256 match`);

  // (c) Independently check bytes, canonical body/MID, signature and reply relationship.
  const mids = [...html.matchAll(/MID: <code>(punkti\/0\.6:[a-f0-9]{64})<\/code>/g)].map(m => m[1]);
  assert.equal(mids.length, 2);
  const decoded = [];
  for (const [i, record] of published.entries()) {
    if (record === null) continue;
    const raw = new Uint8Array(Buffer.from(record.hex, 'hex'));
    assert.throws(() => JSON.parse(Buffer.from(raw).toString('utf8')), 'binary is not a JSON response');
    assert.equal(await sha256Hex(raw), record.sha256);
    const d = decodeRecord(raw); decoded[i] = d;
    assert.deepEqual(canonical(d.atom), d.body);
    assert.equal('punkti/0.6:' + await computeMid(d.body), mids[i]);
    assert.equal(d.atom.h, 's00000000000_0');
    assert.ok(globalThis.nacl.sign.detached.verify(signingInput(d.body), d.sig, unb64(d.atom.pk)));
    const damagedSig = Uint8Array.from(d.sig); damagedSig[0] ^= 1;
    assert.equal(globalThis.nacl.sign.detached.verify(signingInput(d.body), damagedSig, unb64(d.atom.pk)), false);
    const damaged = Uint8Array.from(raw); damaged[damaged.length - 1] ^= 1;
    assert.notEqual(await sha256Hex(damaged), record.sha256);
  }
  if (decoded[0]) assert.deepEqual(decoded[0].atom.refs, []);
  if (decoded[1]) assert.deepEqual(decoded[1].atom.refs, [{ target: mids[0], rel: 'reply' }]);
  if (decoded[1]) assert.equal(JSON.parse(decoded[1].atom.x).text, 'Hello from a new AI');
  assert.match(text, /no global index and no \/shards endpoint/);
  assert.doesNotMatch(lines.filter(l => l.startsWith('GET ')).join('\n'), /\/shards/);
  if (!skipped.length) console.log('Comprehension (c): PASS — both live records: SHA-256, canonical MID, Ed25519 and exact reply reference verified client-side; corrupted hashes/signatures rejected');

  console.log(skipped.length
    ? `WARNING: Public-record verification SKIPPED for ${skipped.length}/2 records: ${skipped.join('; ')}; any fetched records passed all content checks`
    : 'Public-record verification RAN: both records passed all content checks');

  // (b) Execute the actual page commands, substituting only the isolated origin
  // and local verified parent MID. A local fixture is not the public conversation.
  const guard = path.join(node.directory, 'loopback.mjs');
  const audit = path.join(node.directory, 'requests.jsonl');
  writeFileSync(guard, `import { appendFileSync } from 'node:fs';
const original = globalThis.fetch;
globalThis.fetch = (address, init = {}) => {
  const url = new URL(address);
  if (url.hostname !== '127.0.0.1' || url.protocol !== 'http:') throw new Error('non-loopback forbidden');
  appendFileSync(${JSON.stringify(audit)}, JSON.stringify({url: url.href, method: init.method ?? 'GET'}) + '\\n');
  return original(address, {...init, redirect: 'error'});
};`);
  const command = async (exe, args) => {
    const env = Object.fromEntries(Object.entries(process.env).filter(([key]) =>
      !key.startsWith('PUNKTO_') && key !== 'NODE_OPTIONS' && !/proxy/i.test(key)));
    const child = spawn(exe, args, { cwd: node.directory, env, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '', stderr = '';
    child.stdout.on('data', b => { stdout += b; }); child.stderr.on('data', b => { stderr += b; });
    const timer = setTimeout(() => child.kill('SIGKILL'), 30000);
    try { const [code] = await once(child, 'exit'); return { code, stdout, stderr }; }
    finally { clearTimeout(timer); }
  };
  // shlex parses page shell tokens without evaluating arbitrary shell text.
  const tokens = line => {
    const result = spawnSync('python3', ['-c', 'import json,shlex,sys;print(json.dumps(shlex.split(sys.argv[1])))', line], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr); return JSON.parse(result.stdout);
  };
  const download = tokens(lines.find(l => l.startsWith('curl ') && l.includes('/punkti/punkto-reply.mjs'))
    .replaceAll('https://punkto.xyz', node.base));
  assert.equal(download[0], 'curl');
  assert.ok(download.includes(node.base + '/punkti/punkto-reply.mjs'));
  const downloaded = await command(download[0], download.slice(1));
  assert.equal(downloaded.code, 0, downloaded.stderr);
  assert.equal(readFileSync(path.join(node.directory, 'punkto-reply.mjs'), 'utf8'), readFileSync(path.join(ROOT, 'pwa/punkti/punkto-reply.mjs'), 'utf8'));
  const pageArgs = action => tokens(lines.find(l => l.startsWith(`node punkto-reply.mjs ${action} `))
    .replaceAll('https://punkto.xyz', node.base).replaceAll(mids[0], first.mid)).slice(2);
  const helper = async (args, success = true) => {
    const result = await command(process.execPath, ['--import', guard, 'punkto-reply.mjs', ...args]);
    assert.equal(result.code, success ? 0 : 1, result.stdout + result.stderr);
    const receipt = JSON.parse(result.stdout); assert.equal(receipt.ok, success); return receipt;
  };
  const replyArgs = pageArgs('reply'), postArgs = pageArgs('post');
  const replied = await helper(replyArgs);
  assert.equal(replied.h, atom.h);
  assert.deepEqual(replied.parent, { mid: first.mid, h: atom.h, verified: true });
  assert.equal(replied.verified, true);
  const posted = await helper(postArgs);
  assert.equal(posted.h, postArgs[postArgs.indexOf('--h') + 1]);
  assert.equal(posted.verified, true);
  const beforeInvalid = readFileSync(audit, 'utf8').trim().split('\n').map(JSON.parse).filter(r => r.method === 'POST').length;
  const hIndex = postArgs.indexOf('--h');
  const noAddress = postArgs.filter((_, i) => i !== hIndex && i !== hIndex + 1);
  assert.match((await helper(noAddress, false)).error, /explicit --h.*--height required/);
  assert.match((await helper([...noAddress, '--lat', '0', '--lon', '0'], false)).error, /--height required/);
  assert.match((await helper([...postArgs, '--invented', '1'], false)).error, /unknown flag/);
  const requests = readFileSync(audit, 'utf8').trim().split('\n').map(JSON.parse);
  assert.ok(requests.every(r => new URL(r.url).hostname === '127.0.0.1'));
  assert.equal(requests.filter(r => r.method === 'POST').length, beforeInvalid);
  const afterCommands = await createReader().readPublication(entry.publication);
  assert.deepEqual(afterCommands.records.find(r => r.mid === replied.mid).atom.refs, [{target: first.mid, rel: 'reply'}]);
  console.log('Comprehension (b): PASS — page helper download/reply/post executed on localhost; exact parent h inherited; missing address/height and unknown flags rejected without POST; all helper traffic loopback');
  const bootstrap = await (await fetch(nodesUrl)).json();
  assert.equal(bootstrap.notice, "Recommended bootstrap list. Not a trust authority and not a completeness claim: one node's publication is one published view, not all of Punkto.");
  const index = readFileSync(path.join(ROOT, 'pwa/index.html'), 'utf8');
  for (const id of ['ai-entry-link', 'ai-entry-link-topbar']) {
    const links = [...index.matchAll(new RegExp(`<a id="${id}"[^>]*>`, 'g'))];
    assert.equal(links.length, 1);
    for (const value of [`data-testid="${id}"`, 'href="/ai"', 'target="_blank"', 'rel="noopener noreferrer"']) assert.ok(links[0][0].includes(value));
  }
  assert.match(index, /id="ai-entry-link-topbar"[^>]*pointer-events: auto/);
  console.log('E2: PASS — existing hostile cases, semantic copy contract and local comprehension scenario; public verification status reported above');
} finally { await node.close(); }
