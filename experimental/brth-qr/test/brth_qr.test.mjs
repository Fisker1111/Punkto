import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomBytes, hkdfSync } from 'node:crypto';
import { brth, b32, capsule, uncapsule, descriptor, require } from '../tools/capsule.mjs';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const read = p => readFileSync(resolve(root, p), 'utf8');
const measured = JSON.parse(read('out/measurements.json'));
const python = process.env.QR_PYTHON || '/home/hermes/.hermes/tools/python-3.14.9+20261021-linux-x64/bin/python3';
const find = (name, ec = 'L') => measured.cases.find(r => r.name === name && r.error_correction === ec);

test('24 words, entropy and capsule reproduce identical canonical Birth and IdentityID', () => {
  for (const entropy of [Buffer.alloc(32), randomBytes(32)]) {
    const words = brth.entropyToWords(entropy);
    assert.equal(words.split(' ').length, 24);
    const recovered = uncapsule(capsule(brth.wordsToEntropy(words)));
    assert.deepEqual(recovered, entropy);
    const original = brth.buildBirth(brth.deriveRootKeys(entropy));
    const restored = brth.buildBirth(brth.deriveRootKeys(recovered));
    assert.deepEqual(brth.encode(restored), brth.encode(original));
    assert.equal(brth.identityIdOf(restored), brth.identityIdOf(original));
  }
});

test('capsule parser rejects truncation, extension and wrong type/version', () => {
  const valid = capsule(randomBytes(32));
  for (const bad of [valid.subarray(1), Buffer.concat([valid, Buffer.alloc(1)]),
    Buffer.concat([Buffer.from('BRQ2S'), valid.subarray(5)])]) assert.throws(() => uncapsule(bad));
  assert.throws(() => capsule(Buffer.alloc(31)));
});

test('all public descriptor encodings exclude phrase, entropy, seeds and private keys', () => {
  for (const entropy of [Buffer.alloc(32), randomBytes(32)]) {
    const roots = brth.deriveRootKeys(entropy);
    const ml = require('../../brth-layer4/node_modules/@noble/post-quantum/ml-dsa.js').ml_dsa87;
    const slhSeed = Buffer.from(hkdfSync('sha512', entropy, Buffer.from('BRTH/1/root/salt'),
      Buffer.from('BRTH/1/root/SLH-DSA-SHAKE-256s'), 96));
    const secrets = [entropy, roots.ml.skSeed, slhSeed, roots.slh.sk,
      Buffer.from(ml.keygen(roots.ml.skSeed).secretKey), Buffer.from(brth.entropyToWords(entropy))];
    for (const dual of [false, true]) {
      const raw = descriptor(roots, dual);
      for (const encoded of [raw, Buffer.from(raw.toString('base64')), Buffer.from(b32(raw).toUpperCase())])
        for (const secret of secrets)
          for (const needle of [secret, Buffer.from(secret.toString('base64')), Buffer.from(secret.toString('base64url')),
            Buffer.from(secret.toString('hex')), Buffer.from(b32(secret)), Buffer.from(b32(secret).toUpperCase())])
            assert.equal(encoded.includes(needle), false, 'private material must be absent');
    }
  }
});

test('compact dual descriptor reconstructs canonical Birth and checks its digest', () => {
  const roots = brth.deriveRootKeys(Buffer.alloc(32));
  const raw = descriptor(roots);
  assert.equal(raw.length, 5 + 32 + roots.ml.pk.length + roots.slh.pk.length);
  const birth = brth.buildBirth([
    { alg: brth.ML, pk: raw.subarray(37, 2629).toString('base64url') },
    { alg: brth.SLH, pk: raw.subarray(2629).toString('base64url') },
  ]);
  assert.deepEqual(brth.digest(birth), raw.subarray(5, 37));
  const tampered = Buffer.from(raw); tampered[37] ^= 1;
  const changed = brth.buildBirth([
    { alg: brth.ML, pk: tampered.subarray(37, 2629).toString('base64url') },
    { alg: brth.SLH, pk: tampered.subarray(2629).toString('base64url') },
  ]);
  assert.notDeepEqual(brth.digest(changed), raw.subarray(5, 37));
});

test('required measured feasibility facts and exact arithmetic', () => {
  assert.equal(find('root-dual-public-keys-base64').fits, false);
  for (const alg of ['ML-DSA-44', 'ML-DSA-65']) assert.equal(find(alg + '-pk-signature').fits, false);
  assert.equal(find('public-dual-descriptor-raw').fits, true);
  for (const row of measured.cases) {
    assert.equal(row.fits, row.payload_bytes <= measured.capacities[row.mode][row.error_correction]);
    assert.equal(row.shortfall_bytes, Math.max(0, row.payload_bytes - measured.capacities[row.mode][row.error_correction]));
    assert.equal(typeof row.decode_ok, 'boolean');
    for (const decoder of ['cvp2', 'zxingcpp']) {
      const key = 'decode_' + decoder;
      assert.equal(typeof row[key], 'boolean');
      const attempts = (row.decode_attempts || []).filter(a => a.decoder === decoder);
      assert.equal(row[key], attempts.some(a => a.ok));
      if (row.fits) {
        assert.ok(attempts.length > 0);
        if (!row[key]) assert.deepEqual(attempts.map(a => a.scale), [5, 9]);
      } else assert.equal(row[key], false);
    }
    assert.equal(row.decode_ok, row.decode_cvp2 || row.decode_zxingcpp);
    if (row.fits) assert.ok(row.decode_attempts.length > 0);
    else assert.equal(row.decode_result, 'not encodable');
  }
  for (const size of measured.sizes) assert.equal(size.verified, true);
});

test('live QR encoder accepts measured boundary and rejects boundary plus one at every EC', () => {
  for (const ec of 'LMQH') for (const delta of [0, 1]) {
    const n = measured.capacities.byte[ec] + delta;
    const result = spawnSync(python, [resolve(root, 'tools/measure_qr.py'), '--probe', String(n), ec], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(JSON.parse(result.stdout).fits, delta === 0);
  }
});

test('report embeds exact generated measurement tables and public offline evidence', () => {
  const report = read('docs/BRTH_QR_R1_REPORT.md');
  assert.ok(report.includes(read('out/measurements.md').trim()));
  assert.ok(report.includes(read('out/offline_proof.json').trim()));
  const fit = measured.cases.filter(r => r.fits).length;
  const passed = measured.cases.filter(r => r.decode_ok).length;
  assert.ok(report.includes(`${measured.cases.length} payload/EC cases, ${fit} fit, ${passed} successful`));
  assert.ok(report.includes(`${fit - passed} cases read by neither decoder`));
  assert.ok(report.includes(`public descriptor PNG decode:\n${find('public-dual-descriptor-raw').decode_result}`));

  for (const [mode, levels] of Object.entries(measured.capacities)) {
    assert.ok(report.includes('| ' + mode + ' | ' + [...'LMQH'].map(l => levels[l]).join(' | ') + ' |'));
  }
  for (const size of measured.sizes) {
    const fields = ['public_key', 'signature', 'public_key_base64', 'public_key_base32', 'signature_base64', 'signature_base32'];
    assert.ok(report.includes('| ' + size.algorithm + ' | ' + fields.map(k => size[k]).join(' | ') + ' |'));
  }
  for (const row of measured.cases) {
    const keys = ['name','mode','error_correction','raw_bytes','payload_bytes','encoded_characters','version','modules','verdict','shortfall_bytes','decode_result'];
    assert.ok(report.includes('| ' + keys.map(k => row[k] === null ? 'N/A' : String(row[k])).join(' | ') + ' |'));
  }
});

test('fresh offline proof contains only successful cryptographic verdicts', () => {
  const proof = JSON.parse(read('out/offline_proof.json'));
  for (const verdict of Object.values(proof.verdicts)) assert.equal(verdict, true);
  assert.match(proof.openssl, /^OpenSSL 3\.5\.5 /);
  assert.equal(proof.signature_bytes[0].bytes, measured.sizes.find(s => s.algorithm === brth.ML).signature);
  assert.equal(proof.signature_bytes[1].bytes, measured.sizes.find(s => s.algorithm === brth.SLH).signature);
  assert.equal(proof.capsule_bytes, find('private-capsule-raw').payload_bytes);
});

test('dense public descriptor succeeds with zxing-cpp despite cv2 limitation', () => {
  const row = find('public-dual-descriptor-raw');
  assert.equal(row.payload_bytes, 2693);
  assert.equal(row.decode_cvp2, false);
  assert.equal(row.decode_zxingcpp, true);
  assert.equal(row.decode_ok, true);
  assert.match(row.decode_result, /zxing-cpp: byte-identical PNG decode/);
  assert.match(measured.decoders.cvp2, /^OpenCV /);
  assert.match(measured.decoders.zxingcpp, /^zxing-cpp /);
});

test('independent live decoders check dense v40-L byte payloads', () => {
  const script = `
import io
import cv2
import numpy as np
import segno
import zxingcpp
for n in (1500, 2693, 2900, 2953):
    data = bytes(i % 256 for i in range(n))
    qr = segno.make(data, error='L', mode='byte', version=40, micro=False, boost_error=False)
    buf = io.BytesIO()
    qr.save(buf, kind='png', scale=5, border=4)
    png = cv2.imdecode(np.frombuffer(buf.getvalue(), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    decoded, _, _ = cv2.QRCodeDetector().detectAndDecodeBytes(png)
    assert decoded != data, n
    assert any(result.bytes == data for result in zxingcpp.read_barcodes(png)), n
    print(f'{n} bytes v40-L: cv2=False zxing-cpp=True')
`;
  const result = spawnSync(python, ['-c', script], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  console.log(result.stdout.trim());
});
