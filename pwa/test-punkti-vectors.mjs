import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

import {
  canonical,
  signingInput,
  computeMid,
  encodeRecord,
  decodeRecord,
  validate,
  unb64,
  b64,
  sha256Hex,
} from './punkti/carrier.js';
import {
  encode_xy,
  decode_xy,
  format_z,
  parse_z,
  parse_h,
  compare_z,
  encode_h,
  matches,
  normalize_scope,
  subscribed,
} from './punkti/spatial.js';

globalThis.nacl = createRequire(import.meta.url)('./nacl.min.js');

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..');

function readJson(relativePath) {
  return JSON.parse(readFileSync(path.resolve(__dirname, relativePath), 'utf8'));
}

function hexToBytes(hex) {
  if (hex.length % 2 !== 0) throw new Error('invalid hex');
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = Number.parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  return out;
}

function bytesToHex(bytes) {
  return Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
}

function lp(bytes) {
  const out = new Uint8Array(4 + bytes.length);
  new DataView(out.buffer).setUint32(0, bytes.length);
  out.set(bytes, 4);
  return out;
}

function concat(...parts) {
  const total = parts.reduce((sum, part) => sum + part.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const part of parts) {
    out.set(part, offset);
    offset += part.length;
  }
  return out;
}

const carrierVectors = readJson('./punkti/test-vectors/carrier-vectors.json');
const spatialVectors = readJson('./punkti/test-vectors/spatial-vectors.json');
const fixtureEntries = Object.entries(carrierVectors.fixtures);

const seed = hexToBytes(carrierVectors.seed_hex);
const signingKey = globalThis.nacl.sign.keyPair.fromSeed(seed);
const secondSeed = Uint8Array.from(seed, (byte, index) => byte ^ (index % 5 === 0 ? 0x5a : 0xa5));
const secondKey = globalThis.nacl.sign.keyPair.fromSeed(secondSeed);

let carrierAssertions = 0;
for (const [name, fixture] of fixtureEntries) {
  assert.equal(b64(signingKey.publicKey), fixture.atom.pk, `seed-derived pk mismatch for fixture ${name}`);
  carrierAssertions++;

  const body = canonical(fixture.atom);
  assert.equal(bytesToHex(body), fixture.C, `C mismatch for fixture ${name}`);
  carrierAssertions++;

  const signBytes = signingInput(body);
  assert.equal(bytesToHex(signBytes), fixture.S, `S mismatch for fixture ${name}`);
  carrierAssertions++;

  const mid = await computeMid(body);
  assert.equal(mid, fixture.MID.toLowerCase(), `MID mismatch for fixture ${name}`);
  carrierAssertions++;

  assert.equal(`punkti/0.6:${mid}`, fixture.address, `address mismatch for fixture ${name}`);
  carrierAssertions++;

  let recordBytes;
  if (fixture.atom.alg === 'ed25519') {
    const encoded = await encodeRecord(fixture.atom, signingKey.secretKey);
    recordBytes = encoded.record;
    assert.equal(encoded.mid, fixture.MID.toLowerCase(), `encoded MID mismatch for fixture ${name}`);
    carrierAssertions++;
    assert.equal(encoded.address, fixture.address, `encoded address mismatch for fixture ${name}`);
    carrierAssertions++;
  } else {
    recordBytes = concat(lp(body), lp(unb64(fixture.atom.sig)));
  }

  assert.equal(b64(recordBytes), fixture.R, `R mismatch for fixture ${name}`);
  carrierAssertions++;

  const digest = await sha256Hex(recordBytes);
  assert.equal(digest, fixture.sha256_R, `SHA256(R) mismatch for fixture ${name}`);
  carrierAssertions++;

  const decoded = decodeRecord(recordBytes);
  assert.equal(bytesToHex(decoded.body), fixture.C, `decoded body mismatch for fixture ${name}`);
  carrierAssertions++;

  const outcome = await validate(recordBytes);
  assert.equal(outcome.state, fixture.state, `state mismatch for fixture ${name}`);
  carrierAssertions++;

  if (fixture.atom.alg === 'ed25519') {
    const reencoded = await encodeRecord(decoded.atom, signingKey.secretKey);
    assert.equal(bytesToHex(reencoded.record), bytesToHex(recordBytes), `re-encode mismatch for fixture ${name}`);
    carrierAssertions++;
  }
}

const canonicalFixture = carrierVectors.fixtures.canonical;
const canonicalBody = canonical(canonicalFixture.atom);
const firstSig = globalThis.nacl.sign.detached(signingInput(canonicalBody), signingKey.secretKey);
const secondSig = globalThis.nacl.sign.detached(signingInput(canonicalBody), secondKey.secretKey);
const firstRecord = concat(lp(canonicalBody), lp(firstSig));
const secondRecord = concat(lp(canonicalBody), lp(secondSig));
const firstMid = await computeMid(canonicalBody);
const secondMid = await computeMid(canonicalBody);
assert.equal(firstMid, secondMid, 'MID changed when only signature changed');
carrierAssertions++;
assert.notEqual(bytesToHex(firstRecord), bytesToHex(secondRecord), 'record did not change with different signature');
carrierAssertions++;
assert.notEqual(await sha256Hex(firstRecord), await sha256Hex(secondRecord), 'SHA256(R) did not change with different signature');
carrierAssertions++;

const pythonCode = `
import json, hashlib, sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
from punkti_node import carrier
payload = json.load(sys.stdin)
seed = bytes.fromhex(payload['seed_hex'])
key = Ed25519PrivateKey.from_private_bytes(seed)
out = {}
for name, fixture in payload['fixtures'].items():
    atom = fixture['atom']
    body = carrier.canonical(atom)
    if atom['alg'] == 'ed25519':
        signed = dict(atom)
        signed['sig'] = carrier.b64(key.sign(carrier.SIGN_DOMAIN + body))
        raw = carrier.record(signed)
    else:
        raw = carrier.record(atom)
    out[name] = {
        'C': body.hex(),
        'S': (carrier.SIGN_DOMAIN + body).hex(),
        'MID': hashlib.sha256(carrier.MID_DOMAIN + body).hexdigest(),
        'R': carrier.b64(raw),
    }
print(json.dumps(out, separators=(',', ':')))
`;

const py = spawnSync('python3', ['-c', pythonCode, repoRoot], {
  input: JSON.stringify({ seed_hex: carrierVectors.seed_hex, fixtures: carrierVectors.fixtures }),
  encoding: 'utf8',
});
assert.equal(py.status, 0, py.stderr || py.stdout);
const pythonResults = JSON.parse(py.stdout);
for (const [name, fixture] of fixtureEntries) {
  const result = pythonResults[name];
  assert.equal(result.C, fixture.C, `Python C mismatch for fixture ${name}`);
  carrierAssertions++;
  assert.equal(result.S, fixture.S, `Python S mismatch for fixture ${name}`);
  carrierAssertions++;
  assert.equal(result.MID, fixture.MID.toLowerCase(), `Python MID mismatch for fixture ${name}`);
  carrierAssertions++;
  assert.equal(result.R, fixture.R, `Python R mismatch for fixture ${name}`);
  carrierAssertions++;
}

let spatialAssertions = 0;
for (const row of spatialVectors.geohash_rows) {
  for (const precision of [4, 10, 12]) {
    const expected = row.xy.slice(0, precision);
    const encoded = encode_xy(row.lat, row.lon, precision);
    assert.equal(encoded, expected, `encode_xy mismatch for ${row.xy} p${precision}`);
    spatialAssertions++;
    const decoded = decode_xy(expected);
    assert.equal(encode_xy(decoded.lat, decoded.lon, precision), expected, `decode_xy mismatch for ${row.xy} p${precision}`);
    spatialAssertions++;
  }
}

for (const value of spatialVectors.measured_heights) {
  const z = format_z(value);
  parse_z(z);
  spatialAssertions++;
}

for (const value of spatialVectors.invalid_z) {
  assert.throws(() => parse_z(value), `invalid Z accepted: ${value}`);
  spatialAssertions++;
}

for (const value of spatialVectors.invalid_h) {
  assert.throws(() => parse_h(value), `invalid h accepted: ${value}`);
  spatialAssertions++;
}

for (let i = 0; i < spatialVectors.z_order.length; i++) {
  for (let j = 0; j < spatialVectors.z_order.length; j++) {
    assert.equal(compare_z(spatialVectors.z_order[i], spatialVectors.z_order[j]), Math.sign(i - j), 'compare_z ordering mismatch');
    spatialAssertions++;
  }
}

for (const z of ['23', '-18', '23.025']) {
  assert.equal(encode_h(55.675398, 12.561895, z), `u3butz7k9q_${z}`);
  spatialAssertions++;
}

for (const scopeCase of spatialVectors.scope_cases) {
  if (scopeCase.values) {
    const actual = scopeCase.values.map(value => matches(`u3bu_${value}`, scopeCase.scope));
    assert.deepEqual(actual, scopeCase.expected, 'scope Z case mismatch');
    spatialAssertions++;
  }
  if (scopeCase.h) {
    assert.equal(matches(scopeCase.h, scopeCase.scope), scopeCase.expected, 'scope H case mismatch');
    spatialAssertions++;
  }
  if (scopeCase.interval_cases) {
    for (const interval of scopeCase.interval_cases) {
      const h = `${interval.xy.padEnd(4, '0')}_0`;
      assert.equal(matches(h, { xy_lo: interval.xy_lo, xy_hi: interval.xy_hi }), interval.selected, `interval mismatch for ${interval.xy}`);
      spatialAssertions++;
    }
  }
}

const maxH = spatialVectors.max_h;
assert.equal(encode_h(maxH.lat, maxH.lon, maxH.z, maxH.precision_ok).length, maxH.expected_len);
spatialAssertions++;
assert.throws(() => encode_h(maxH.lat, maxH.lon, maxH.z, maxH.precision_fail));
spatialAssertions++;

for (const scope of spatialVectors.invalid_scopes) {
  assert.throws(() => normalize_scope(scope));
  spatialAssertions++;
}

assert.throws(() => matches('', {}));
spatialAssertions++;
assert.throws(() => matches('', { z_min: '0' }));
spatialAssertions++;
assert.equal(subscribed('u3bu_0', []), false);
spatialAssertions++;
assert.equal(subscribed('u3bu_0', [{ xy_hi: 'g' }, { xy_lo: 'u' }]), true);
spatialAssertions++;

const publicationVectors = readJson('./punkti/test-vectors/publication-vectors.json');
assert.equal(publicationVectors.profile, 'punkti/pub/0.6');
assert.equal(typeof publicationVectors.fixtures, 'object');
assert(Array.isArray(publicationVectors.vectors));
assert.equal(publicationVectors.vectors.length, 12);

console.log(`XY_Z: ${spatialAssertions} assertions passed; carrier: ${fixtureEntries.length} fixtures byte-identical; JS==Python: OK`);
console.log(`carrier assertions: ${carrierAssertions}`);
