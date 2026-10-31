import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { runInNewContext } from 'node:vm';
import { mkdtempSync, readFileSync, rmSync, writeFileSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { createRequire } from 'node:module';

// TweetNaCl is a browser global in the PWA (loaded via <script src="/nacl.min.js">);
// under node it is loaded here so the browser module is exercised unchanged.
globalThis.nacl ??= createRequire(import.meta.url)('./nacl.min.js');

import { createReader, flatResolver, hexShardedResolver, indexMapResolver, PublicationError } from './punkti/reader.js';

function hexToBytes(hex) {
  return new Uint8Array(Buffer.from(hex, 'hex'));
}

function bytesToHex(bytes) {
  return Buffer.from(bytes).toString('hex');
}

function shardPath(prefix, sha) {
  return `h/${prefix.split('').join('/')}/${sha}.json`;
}

function recordPath(sha) {
  return `records/${sha.slice(0, 2)}/${sha}`;
}

function segmentPath(sha) {
  return `segments/${sha.slice(0, 2)}/${sha}`;
}

function materializeFixture(fixture, directory) {
  rmSync(directory, { recursive: true, force: true });
  mkdirSync(directory, { recursive: true });
  writeFileSync(path.join(directory, 'root.json'), Buffer.from(fixture.root, 'hex'));
  for (const [sha, object] of Object.entries(fixture.objects)) {
    const raw = Buffer.from(object.hex, 'hex');
    let relative;
    if (object.kind === 'manifest') {
      relative = `manifests/${sha}.json`;
    } else if (object.kind === 'shard') {
      const parsed = object.prefix ? { prefix: object.prefix } : JSON.parse(raw.toString('utf8'));
      relative = shardPath(parsed.prefix, sha);
    } else if (object.kind === 'record') {
      relative = recordPath(sha);
    } else {
      relative = segmentPath(sha);
    }
    const target = path.join(directory, relative);
    mkdirSync(path.dirname(target), { recursive: true });
    writeFileSync(target, raw);
  }
}

async function withServer(root, run) {
  const server = http.createServer((request, response) => {
    if (!request.url) {
      response.statusCode = 400;
      response.end();
      return;
    }
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const file = path.join(root, pathname.slice(1));
    try {
      const raw = readFileSync(file);
      response.statusCode = 200;
      response.end(raw);
    } catch {
      response.statusCode = 404;
      response.end();
    }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const address = server.address();
    await run(`http://127.0.0.1:${address.port}`);
  } finally {
    await new Promise(resolve => server.close(resolve));
  }
}

function resultMap(records) {
  return Object.fromEntries(records.map(record => [record.mid, record.sha256]));
}

function candidateMap(records) {
  return Object.fromEntries(records.map(record => [record.sha256, bytesToHex(record.record)]));
}

function assertExpected(result, expected, label) {
  assert.equal(result.head, expected.head, `${label}: head`);
  assert.equal(result.seq, expected.seq, `${label}: seq`);
  assert.equal(result.valid_count, expected.valid_count, `${label}: valid_count`);
  assert.equal(result.rejected, expected.rejected, `${label}: rejected`);
  assert.equal(result.candidate_count, expected.candidate_count, `${label}: candidate_count`);
  assert.equal(result.admitted, expected.admitted, `${label}: admitted`);
  assert.deepEqual(resultMap(result.valid_records), expected.valid, `${label}: valid map`);
  assert.deepEqual(candidateMap(result.candidate_records), expected.candidates, `${label}: candidates map`);
}

function fixtureObjectsByPath(fixture, layout = 'hex') {
  const map = new Map();
  map.set(layout === 'mapped' ? 'objects/root/root.json' : 'root.json', hexToBytes(fixture.root));
  for (const [sha, object] of Object.entries(fixture.objects)) {
    const raw = hexToBytes(object.hex);
    if (object.kind === 'manifest') {
      map.set(layout === 'mapped' ? `objects/manifests/${sha}.json` : `manifests/${sha}.json`, raw);
      continue;
    }
    if (object.kind === 'shard') {
      const prefix = object.prefix || JSON.parse(Buffer.from(raw).toString('utf8')).prefix;
      if (layout === 'flat') {
        map.set(`h/${sha}.json`, raw);
      } else if (layout === 'mapped') {
        map.set(`objects/shards/${prefix}/${sha}.json`, raw);
      } else {
        map.set(shardPath(prefix, sha), raw);
      }
      continue;
    }
    if (object.kind === 'record') {
      if (layout === 'flat') {
        map.set(`records/${sha}`, raw);
      } else if (layout === 'mapped') {
        map.set(`objects/records/${sha}`, raw);
      } else {
        map.set(recordPath(sha), raw);
      }
      continue;
    }
    if (layout === 'flat') {
      map.set(`segments/${sha}`, raw);
    } else if (layout === 'mapped') {
      map.set(`objects/segments/${sha}`, raw);
    } else {
      map.set(segmentPath(sha), raw);
    }
  }
  return map;
}

function fetchFromMap(pathMap) {
  return async url => {
    const key = new URL(url).pathname.slice(1);
    const raw = pathMap.get(key);
    if (!raw) {
      return {
        ok: false,
        status: 404,
        async arrayBuffer() { return new ArrayBuffer(0); },
      };
    }
    return {
      ok: true,
      status: 200,
      async arrayBuffer() {
        return raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength);
      },
    };
  };
}

const vectors = JSON.parse(readFileSync(new URL('./punkti/test-vectors/publication-vectors.json', import.meta.url), 'utf8'));
const fixtures = vectors.fixtures;
let assertions = 0;

// Exercise the private byte guard without adding a public reader API.
const readerSource = readFileSync(new URL('./punkti/reader.js', import.meta.url), 'utf8');
const parseCanonicalJson = runInNewContext(
  readerSource.slice(readerSource.indexOf('const utf8Decoder ='), readerSource.indexOf('function ensureMembers('))
    .replace('export class PublicationError', 'class PublicationError') + '\nparseCanonicalJson;',
  { TextDecoder, TextEncoder },
);
const serverCanonical = value => execFileSync('python3', ['-c',
  'import json, sys; from punkti_node.publication import canonical; sys.stdout.buffer.write(canonical(json.load(sys.stdin)))',
], { cwd: new URL('../', import.meta.url), input: JSON.stringify(value) });

const numericIndexManifest = {
  index: { '0n': 'a'.repeat(64), '94': 'b'.repeat(64), dq: 'c'.repeat(64) },
  pack_count: 0, prev: null, record_count: 0, seq: 1, v: 'punkti/pub/0.6',
};
const manifestBytes = serverCanonical(numericIndexManifest);
assert.match(manifestBytes.toString('utf8'), /^\{"index":\{"0n":/);
assert.equal(JSON.stringify(parseCanonicalJson(manifestBytes)), JSON.stringify(numericIndexManifest));
assertions += 2;

// Python's ensure_ascii=False must match raw UTF-8, including nested arrays,
// objects, strings with escapes, integer-like keys, and the permitted scalars.
const nested = { children: { '0n': { '94': [null, true, false, -7, 'café 雪 😀', '\"\\\n'] } }, packs: [], records: [{ h: 'é' }] };
const nestedBytes = serverCanonical(nested);
assert(nestedBytes.includes(Buffer.from('café 雪 😀', 'utf8')));
assert.equal(JSON.stringify(parseCanonicalJson(nestedBytes)), JSON.stringify(nested));
assertions += 2;

for (const raw of [
  JSON.stringify(numericIndexManifest), // Integer-like key hoisted before 0n.
  manifestBytes.toString('utf8').replace(':', ': '),
  manifestBytes.toString('utf8') + '\n',
  '{"b":1,"a":2}',
  '{"a":[{"b":1,"a":2}]}',
  '{"a":1,"a":1}',
  '{"a":1.5}', '{"a":1.0}', '{"a":1e0}',
  '{"a":NaN}', '{"a":Infinity}',
  '{"a":"\\u00e9"}',
]) {
  assert.throws(() => parseCanonicalJson(Buffer.from(raw)), error =>
    error.name === 'PublicationError' && error.reason === 'invalid object' && error.error_class === 'retryable');
  assertions++;
}
console.log('canonical JSON regression: server bytes accepted; non-canonical bytes rejected');

const tempRoot = mkdtempSync(path.join(tmpdir(), 'punkti-pub-'));
try {
  await withServer(tempRoot, async base => {
    const v1 = vectors.vectors.find(vector => vector.id === 'V1').cases;
    materializeFixture(fixtures.index, tempRoot);
    const v1Index = await createReader({ resolver: hexShardedResolver() }).readPublication(base);
    assertExpected(v1Index, v1[0].expected, 'V1/index');
    assertions += 8;

    materializeFixture(fixtures.packs, tempRoot);
    const v1Packs = await createReader({ resolver: hexShardedResolver() }).readPublication(base);
    assertExpected(v1Packs, v1[1].expected, 'V1/packs');
    assertions += 8;

    for (const name of ['tamper-manifest', 'tamper-shard', 'tamper-record']) {
      materializeFixture(fixtures[name], tempRoot);
      await assert.rejects(createReader({ resolver: hexShardedResolver() }).readPublication(base), error => {
        assert(error instanceof PublicationError);
        assert.equal(error.error_class, 'retryable');
        assert.equal(error.reason, 'corrupt object');
        return true;
      });
      assertions += 3;
    }

    materializeFixture(fixtures['small-pack'], tempRoot);
    const smallPack = await createReader({ resolver: hexShardedResolver() }).readPublication(base);
    const v3 = vectors.vectors.find(vector => vector.id === 'V3').cases.find(item => item.name === 'valid').expected;
    assertExpected(smallPack, v3, 'V3/small-pack');
    assertions += 8;

    materializeFixture(fixtures['pack-count'], tempRoot);
    await assert.rejects(createReader({ resolver: hexShardedResolver() }).readPublication(base), error => {
      assert(error instanceof PublicationError);
      assert.equal(error.error_class, 'retryable');
      assert.equal(error.reason, 'invalid object');
      return true;
    });
    assertions += 3;

    for (const vector of vectors.vectors.filter(item => ['V4', 'V5', 'V6', 'V7'].includes(item.id))) {
      for (const testCase of vector.cases) {
        materializeFixture(fixtures[testCase.source || 'index'], tempRoot);
        const run = await createReader({ resolver: hexShardedResolver(), maxRetries: 0 }).readPublication(base, testCase.scope || {});
        assertExpected(run, testCase.expected, `${vector.id}/${testCase.name}`);
        assertions += 8;
      }
    }

    // Poison fixture (frozen vector V5): one VALID record, one invalid variant
    // of the SAME MID (must be rejected, not admitted), and two unverified
    // unknown-algorithm candidates. The valid variant is NOT poisoned.
    materializeFixture(fixtures.poison, tempRoot);
    const poison = await createReader({ resolver: hexShardedResolver() }).readPublication(base);
    assert.equal(poison.valid_count, 1);
    assert.equal(poison.candidate_count, 2);
    assert.equal(poison.rejected, 1);
    assert.equal(poison.valid_records.length, 1);
    const poisonValid = poison.valid_records[0];
    const poisonExpected = vectors.vectors.find(vector => vector.id === 'V5').cases[0].expected;
    assert.equal(poisonValid.mid, Object.keys(poisonExpected.valid)[0]);
    assert.equal(poisonValid.sha256, poisonExpected.valid[poisonValid.mid]);
    // The rejected variant shares that MID and must not have displaced it.
    assert.equal(poison.quarantined.length, 1);
    assert.equal(poison.quarantined[0].mid, poisonValid.mid);
    assertions += 7;

    materializeFixture(fixtures.missing, tempRoot);
    await assert.rejects(createReader({ resolver: hexShardedResolver() }).readPublication(base), error => {
      assert(error instanceof PublicationError);
      assert.equal(error.reason, 'missing object');
      assert.equal(error.error_class, 'retryable');
      return true;
    });
    assertions += 3;

    const staleReader = createReader({ resolver: hexShardedResolver(), maxRetries: 0 });
    materializeFixture(fixtures.newer, tempRoot);
    await staleReader.readPublication(base);
    assertions++;
    materializeFixture(fixtures.index, tempRoot);
    await assert.rejects(staleReader.readPublication(base), error => {
      assert(error instanceof PublicationError);
      assert.equal(error.reason, 'stale root');
      assert.equal(error.error_class, 'retryable');
      return true;
    });
    assertions += 3;

    for (const name of ['pack-duplicate', 'pack-foreign', 'pack-reversed', 'pack-trailing', 'pack-truncation']) {
      materializeFixture(fixtures[name], tempRoot);
      await assert.rejects(createReader({ resolver: hexShardedResolver(), maxRetries: 0 }).readPublication(base), error => {
        assert(error instanceof PublicationError);
        assert.equal(error.error_class, 'retryable');
        return true;
      });
      assertions += 2;
    }
  });

  const fixture = fixtures.index;
  const expected = vectors.vectors.find(vector => vector.id === 'V1').cases[0].expected.valid;
  const base = 'https://fixture.local';

  const hexReader = createReader({
    resolver: hexShardedResolver(),
    fetchImpl: fetchFromMap(fixtureObjectsByPath(fixture, 'hex')),
    maxRetries: 0,
  });
  const flatReader = createReader({
    resolver: flatResolver(),
    fetchImpl: fetchFromMap(fixtureObjectsByPath(fixture, 'flat')),
    maxRetries: 0,
  });
  const mapReader = createReader({
    resolver: indexMapResolver({
      'root.json': 'objects/root/root.json',
      'manifests/<sha>.json': 'objects/manifests/<sha>.json',
      'h/<prefixPath>/<sha>.json': 'objects/shards/<prefix>/<sha>.json',
      'records/<sha>': 'objects/records/<sha>',
      'segments/<sha>': 'objects/segments/<sha>',
    }),
    fetchImpl: fetchFromMap(fixtureObjectsByPath(fixture, 'mapped')),
    maxRetries: 0,
  });

  const [hexResult, flatResult, mapResult] = await Promise.all([
    hexReader.readPublication(base),
    flatReader.readPublication(base),
    mapReader.readPublication(base),
  ]);

  assert.deepEqual(resultMap(hexResult.valid_records), expected);
  assert.deepEqual(resultMap(flatResult.valid_records), expected);
  assert.deepEqual(resultMap(mapResult.valid_records), expected);
  assertions += 3;

  console.log(`publication vectors: ${assertions} assertions passed`);
} finally {
  rmSync(tempRoot, { recursive: true, force: true });
}
