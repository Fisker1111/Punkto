import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { webcrypto } from 'node:crypto';

Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });
globalThis.location = { origin: 'https://node.example' };
const require = createRequire(import.meta.url);
globalThis.qrcode = require('./lib/qrcode-generator.js');

const { isPunktiMid } = await import('./protocol/atom-id.js');
const { canonicalAtomPath, canonicalAtomUrl, parsePublicPPath } = await import('./protocol/exact-link.js');
const { qrPayloadForAtom } = await import('./print-pdf.js');

const mid = `punkti/0.6:${'a'.repeat(64)}`;
const origin = 'https://node.example';

assert.equal(isPunktiMid(mid), true, 'valid MID is recognised');

const path = canonicalAtomPath(mid);
assert.ok(path.startsWith('/p/'), 'MID canonical path starts with /p/');
assert.notEqual(path, '', 'MID canonical path is non-empty');

const url = await canonicalAtomUrl(mid, origin);
assert.ok(url.startsWith(`${origin}/p/`), 'MID canonical URL is absolute');
assert.ok(url.includes(encodeURIComponent(mid)), 'MID canonical URL contains encoded MID');

assert.deepEqual(parsePublicPPath(path), { kind: 'atom', id: mid }, 'MID deep-link round-trips through parser');

const atoms = [
  {
    atom_id: mid,
    mid,
    h: 'u3butz7k9q_23.4',
    x: 'MID-backed atom',
  },
];
const parsed = parsePublicPPath(path);
const resolved = atoms.find((atom) => String(atom?.mid || '').trim() === parsed?.id || String(atom?.atom_id || '').trim() === parsed?.id) || null;
assert.equal(resolved?.mid, mid, 'MID deep-link resolves to atom via exact identity lookup');

const stable = 'b'.repeat(64);
assert.deepEqual(parsePublicPPath(`/p/${stable}`), { kind: 'atom', id: stable }, 'legacy /p/<64-hex> still parses');
assert.deepEqual(parsePublicPPath('/p/p%3Au1xj9n8d4k2m'), { kind: 'spatial', id: 'u1xj9n8d4k2m' }, 'legacy /p/<p:12char> still parses');

const invalidMids = [
  `punkti/0.5:${'a'.repeat(64)}`,
  `punkti/0.6:${'a'.repeat(63)}`,
  `punkti/0.6:${'A'.repeat(64)}`,
  'a'.repeat(64),
];
for (const invalid of invalidMids) {
  assert.equal(isPunktiMid(invalid), false, `invalid MID rejected: ${invalid}`);
  if (invalid.startsWith('punkti/0.6:')) {
    assert.equal(parsePublicPPath(`/p/${encodeURIComponent(invalid)}`), null, `invalid MID deep-link rejected: ${invalid}`);
  }
}

const qr = await qrPayloadForAtom({ atom_id: mid, mid, x: 'MID atom' }, origin);
assert.notEqual(qr, '', 'MID QR payload is non-empty');
assert.ok(qr.includes(encodeURIComponent(mid)), 'MID QR payload contains encoded MID');

console.log('exact identity tests passed');
