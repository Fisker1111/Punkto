import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { webcrypto } from 'node:crypto';

Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });
globalThis.location = { origin: 'https://test1.punkto.xyz' };
const require = createRequire(import.meta.url);
globalThis.qrcode = require('./lib/qrcode-generator.js');

const { computeAtomId } = await import('./protocol/atom-id.js');
const { canonicalAtomId, canonicalAtomUrl, parsePublicPPath } = await import('./protocol/exact-link.js');
const { generatePunktiPdfBytes, printedQrLayout, qrPayloadForAtom } = await import('./print-pdf.js');

const base = {
  punkto: 'p:u1xj9n8d4k2m',
  t: 1799150400000,
  x: 'Meet at the north gate.',
  f: 'pilot',
  category: 'TEXT',
  pubkey: 'public-key-only',
};
const samePlaceOtherAtom = { ...base, x: 'Independent Punkti at the same exact place.' };

const id = await canonicalAtomId(base);
const id2 = await canonicalAtomId(samePlaceOtherAtom);
assert.match(id, /^[0-9a-f]{64}$/);
assert.match(id2, /^[0-9a-f]{64}$/);
assert.notEqual(id, id2, 'same-location independent atoms must have distinct canonical ids');

const withLocalFields = {
  ...base,
  id: 42,
  atom_id: id,
  distance: 12.5,
  location_fields: ['lat', 'lon'],
};
assert.equal(await canonicalAtomId(withLocalFields), id, 'local helper fields must not change canonical id');
assert.equal(await computeAtomId(base), id, 'canonical helper matches relay-style atom hash for submitted atom bytes');

const url = await canonicalAtomUrl({ ...base, atom_id: id }, 'https://test1.punkto.xyz');
assert.equal(url, `https://test1.punkto.xyz/p/${id}`);
assert.deepEqual(parsePublicPPath(`/p/${id}`), { kind: 'atom', id });
assert.deepEqual(parsePublicPPath('/p/u1xj9n8d4k2m'), { kind: 'spatial', id: 'u1xj9n8d4k2m' });
assert.equal(await qrPayloadForAtom({ ...base, atom_id: id }, 'https://test1.punkto.xyz'), url);

const winAnsiSample = 'æ ø å Æ Ø Å é ü € “quotes” – dash ·';
const pdfBytes = await generatePunktiPdfBytes(
  { ...base, atom_id: id, x: winAnsiSample, mnemonic: ['never', 'print'], secretKey: [1, 2, 3], pubkey: 'public-key-only' },
  { origin: 'https://test1.punkto.xyz' }
);
const pdfText = new TextDecoder('windows-1252').decode(pdfBytes);
assert.equal(pdfText.slice(0, 4), '%PDF');
assert.match(pdfText, /MediaBox \[0 0 595\.28 841\.89\]/);
assert.match(pdfText, new RegExp(id));
assert.match(pdfText, new RegExp(url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
assert.doesNotMatch(pdfText, /never|secretKey|mnemonic|public-key-only/);
assert.match(pdfText, /æ ø å Æ Ø Å é ü € “quotes” – dash ·/);
assert.doesNotMatch(pdfText, /æ \? å|Æ \? Å|quotes\?|\? dash|dash \?/);
assert.match(pdfText, /punkto\.xyz · leave a message here/);

const qr = globalThis.qrcode(0, 'M');
qr.addData(url);
qr.make();
const qrLayout = printedQrLayout(qr.getModuleCount());
assert.equal(qrLayout.quietModules, 4);
assert.equal(qrLayout.quietZone, qrLayout.moduleSize * 4);
assert.ok(qrLayout.quietZone >= qrLayout.moduleSize * 4, 'printed QR quiet zone must be at least four modules');

console.log('slice5 helper tests passed');
