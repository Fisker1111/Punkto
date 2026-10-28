import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { localNode, cli, ROOT } from './test-ai-coldstart.mjs';
import { run } from './punkti/cli.mjs';
import { createReader, hexShardedResolver } from './punkti/reader.js';
import { createSubmitClient } from './punkti/submit.js';
import { encodeRecord } from './punkti/carrier.js';

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
  const atom = { t: Date.now(), h: '', x: JSON.stringify({ text: 'E2 duplicate' }) };
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
  await assert.rejects(encodeRecord({ ...atom, refs: [{ target: 'not-a-mid', rel: 'reply' }] }, identity.secretKey), /reference/);
  let writes = 0;
  await assert.rejects(run(['write', '--nodes', nodesUrl, '--text', 'read only', '--submit', `${node.base}/submit`], async (_address, init) => {
    if (init?.method === 'POST') writes++;
    return new Response(JSON.stringify({ v: 'punkti/bootstrap/1', nodes: [entry] }));
  }), /does not accept writes/);
  assert.equal(writes, 0);
  let endpointUsed = null;
  const override = await run(['write', '--nodes', nodesUrl, '--submit', `${node.base}/custom-submit`, '--text', 'override'], async (address, init) => {
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
  assert.deepEqual([...html.matchAll(/<h2>(.*?)<\/h2>/g)].map(match => match[1]), ['What Punkto is', 'BOOT', 'READ', 'VERIFY', 'SPACE', 'WRITE', 'REPLY', 'IDENTITY', 'Limits']);
  for (const literal of [
    'GET /nodes.json', 'punkti/bootstrap/1', 'root.json', 'manifests/<sha>.json', 'h/<prefix path>/<sha>.json', 'records/<sha2>/<sha>', '/punkti/reader.js',
    'h=<xy>_<z>', 'h=u3butz7k9q7v_0', '55.675398', '12.561895', 'ellipsoidal height in metres', 'no map and no graphical UI', 'no central place registry',
    'v, t, h, x, alg, pk, refs, ext, sig', 'punkti/0.6', 'Unix milliseconds', '{"text":"..."}', 'ed25519', 'base64', '{target, rel}', 'punkti/0.6:<64 lowercase hex>', 'body || signature', 'both length-prefixed',
    'ASCII("PUNKTI-L3-SIGN") || 0x00 || C', 'mid = lowercase_hex(SHA256(ASCII("PUNKTI-L3-MID") || 0x00 || C))', 'verified locally', 'Invalid records are quarantined',
    'POST <submit>', '"records":[{"address":', '"sha256":', '"record":', 'refs: [{"target": "<MID>", "rel": "reply"}]',
    'node cli.mjs read', 'node cli.mjs write', 'node cli.mjs reply', 'curl -fsS', '<ORIGIN>', '<TEXT>', 'https://punkto.xyz/nodes.json',
    'one protocol (Punkti v0.6)', 'ordinary node', 'no machine-only protocol', 'No account', 'no API key', 'no OAuth', 'no onboarding', 'no proprietary SDK',
    'ephemeral key is legitimate and sufficient', 'continuity of authorship', 'no registration', 'no recovery requirement',
    'One node failing does not mean Punkto is unavailable', 'try another bootstrap node', 'no submit entry', 'recommendation, not a trust authority',
  ]) assert.ok(text.includes(literal), `required page text: ${literal}`);
  assert.doesNotMatch(html, /<script\b|<link\b|<iframe\b|<img\b/i);
  const bootstrap = await (await fetch(nodesUrl)).json();
  assert.equal(bootstrap.notice, "Recommended bootstrap list. Not a trust authority and not a completeness claim: one node's publication is one published view, not all of Punkto.");
  const index = readFileSync(path.join(ROOT, 'pwa/index.html'), 'utf8');
  for (const id of ['ai-entry-link', 'ai-entry-link-topbar']) {
    const links = [...index.matchAll(new RegExp(`<a id="${id}"[^>]*>`, 'g'))];
    assert.equal(links.length, 1);
    for (const value of [`data-testid="${id}"`, 'href="/ai"', 'target="_blank"', 'rel="noopener noreferrer"']) assert.ok(links[0][0].includes(value));
  }
  assert.match(index, /id="ai-entry-link-topbar"[^>]*pointer-events: auto/);
  console.log('E2: PASS — all nine hostile/minimality cases and required page content');
} finally { await node.close(); }
