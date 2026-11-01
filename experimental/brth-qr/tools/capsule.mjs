import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
export const require = createRequire(import.meta.url);
export const brth = require('../../brth-layer4/src');
export const b32 = require('../../brth-layer4/src/format').b32;
export const sha256 = data => createHash('sha256').update(data).digest('hex');
// Experimental packaging, not a new BRTH wire format. Fixed headers select BRTH-1.
export function capsule(entropy) {
  brth.entropyToWords(entropy); // Enforce 32 bytes using the original implementation.
  return Buffer.concat([Buffer.from('BRQ1S'), entropy]);
}
export function uncapsule(bytes) {
  if (bytes.length !== 37 || bytes.subarray(0, 5).toString() !== 'BRQ1S')
    throw Error('invalid private capsule');
  return Buffer.from(bytes.subarray(5));
}
export function descriptor(roots, dual = true) {
  const birth = brth.buildBirth(roots);
  return Buffer.concat([
    Buffer.from(dual ? 'BRQ1D' : 'BRQ1M'),
    brth.digest(birth), roots.ml.pk, ...(dual ? [roots.slh.pk] : []),
  ]);
}
