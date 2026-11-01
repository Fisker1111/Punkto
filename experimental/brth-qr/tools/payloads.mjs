// IPC only: this module's result includes private test payloads. Never log it.
import { writeFileSync } from 'node:fs';
import { brth, b32, capsule, descriptor, require } from './capsule.mjs';
const ml = require('../../brth-layer4/node_modules/@noble/post-quantum/ml-dsa.js');
const slh = require('../../brth-layer4/node_modules/@noble/post-quantum/slh-dsa.js');
export function payloads() {
  const entropy = Buffer.alloc(32); // Published Layer-4 test case; never a real identity.
  const roots = brth.deriveRootKeys(entropy);
  const cases = [], sizes = [];
  function add(name, bytes, mode = 'byte', raw = bytes.length, characters = null) {
    cases.push({ name, data: Buffer.from(bytes).toString('base64'), mode,
      raw_bytes: raw, encoded_characters: characters });
  }
  function forms(name, bytes) {
    add(name + '-raw', bytes);
    const b64 = Buffer.from(bytes).toString('base64');
    const base32 = b32(bytes).toUpperCase(); // Unpadded RFC4648; QR alphanumeric.
    add(name + '-base64', Buffer.from(b64), 'byte', bytes.length, b64.length);
    add(name + '-base32', Buffer.from(base32), 'alphanumeric', bytes.length, base32.length);
  }
  const words = Buffer.from(brth.entropyToWords(entropy));
  add('recovery-24-words', words, 'byte', words.length, words.length);
  forms('private-capsule', capsule(entropy));
  forms('public-single-descriptor', descriptor(roots, false));
  forms('public-dual-descriptor', descriptor(roots));
  forms('root-dual-public-keys', Buffer.concat([roots.ml.pk, roots.slh.pk]));
  forms('canonical-birth', brth.encode(brth.buildBirth(roots)));
  const message = Buffer.from('BRTH QR R1 parameter size measurement');
  for (const [name, suite] of [
    ['ML-DSA-44', ml.ml_dsa44], ['ML-DSA-65', ml.ml_dsa65], ['ML-DSA-87', ml.ml_dsa87],
    ...['128s', '192s', '256s', '128f', '256f'].map(p =>
      ['SLH-DSA-SHAKE-' + p, slh['slh_dsa_shake_' + p]]),
  ]) {
    const kp = suite.keygen(Buffer.alloc(name.startsWith('ML') ? 32 :
      name.includes('128') ? 48 : name.includes('192') ? 72 : 96));
    const signature = Buffer.from(suite.sign(message, kp.secretKey, { extraEntropy: false }));
    if (!suite.verify(signature, message, kp.publicKey)) throw Error('signature verification');
    sizes.push({ algorithm: name, public_key: kp.publicKey.length, signature: signature.length,
      public_key_base64: Buffer.from(kp.publicKey).toString('base64').length,
      public_key_base32: b32(kp.publicKey).length,
      signature_base64: signature.toString('base64').length,
      signature_base32: b32(signature).length, verified: true });
    forms(name + '-pk', kp.publicKey);
    forms(name + '-signature', signature);
    add(name + '-pk-signature', Buffer.concat([kp.publicKey, signature]));
  }
  return { sizes, cases };
}
// Only the measurement process reads this pipe, and stores redacted statistics.
if (process.argv[2] === '--private-ipc') {
  const fd = Number(process.env.QR_PAYLOAD_FD);
  if (!Number.isInteger(fd) || fd < 3) throw Error('private IPC descriptor required');
  writeFileSync(fd, JSON.stringify(payloads()));
}
