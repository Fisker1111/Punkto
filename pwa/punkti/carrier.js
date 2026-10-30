import { parse_h } from './spatial.js';

const encoder = new TextEncoder();
const decoder = new TextDecoder('utf-8', { fatal: true });

export const VERSION = 'punkti/0.6';
export const BODY_LIMIT = 1024 * 1024;
export const RECORD_LIMIT = 2 * BODY_LIMIT;
export const SIGN_DOMAIN = encoder.encode('PUNKTI-L3-SIGN\0');
export const MID_DOMAIN = encoder.encode('PUNKTI-L3-MID\0');

const FIELDS = new Set(['v', 't', 'h', 'x', 'alg', 'pk', 'refs', 'ext', 'sig']);

export const State = {
  VALID: 'VALID',
  ALGORITHM: 'UNVERIFIABLE-alg',
  STRUCTURAL: 'INVALID-structural',
  PROVENANCE: 'INVALID-provenance',
  KEY: 'UNVERIFIABLE-key',
  VERSION: 'OPAQUE-version',
};

export class ResourceLimit extends Error {
  constructor(message) {
    super(message);
    this.name = 'ResourceLimit';
  }
}

function getNacl() {
  if (!globalThis.nacl?.sign?.detached?.verify || !globalThis.nacl?.sign?.keyPair?.fromSecretKey) {
    throw new Error('nacl global is required');
  }
  return globalThis.nacl;
}

function getSubtle() {
  if (!globalThis.crypto?.subtle) {
    throw new Error('crypto.subtle is required');
  }
  return globalThis.crypto.subtle;
}

function toUint8Array(value, field = 'bytes') {
  if (value instanceof Uint8Array) return value;
  if (value instanceof ArrayBuffer) return new Uint8Array(value);
  if (ArrayBuffer.isView(value)) return new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
  throw new ValueError(`${field} required`);
}

class ValueError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ValueError';
  }
}

function lp(raw) {
  const bytes = toUint8Array(raw);
  const out = new Uint8Array(4 + bytes.length);
  new DataView(out.buffer).setUint32(0, bytes.length);
  out.set(bytes, 4);
  return out;
}

function u32(value) {
  const out = new Uint8Array(4);
  new DataView(out.buffer).setUint32(0, value);
  return out;
}

function concat(...parts) {
  const total = parts.reduce((size, part) => size + part.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const part of parts) {
    out.set(part, offset);
    offset += part.length;
  }
  return out;
}

function utf8(text) {
  if (typeof text !== 'string') {
    throw new ValueError('string required');
  }
  return encoder.encode(text);
}

function fromBinaryString(value) {
  return Uint8Array.from(value, char => char.charCodeAt(0));
}

function toBinaryString(bytes) {
  let out = '';
  for (const byte of bytes) {
    out += String.fromCharCode(byte);
  }
  return out;
}

export function b64(raw) {
  const bytes = toUint8Array(raw);
  if (typeof btoa === 'function') {
    return btoa(toBinaryString(bytes));
  }
  if (typeof Buffer !== 'undefined') {
    return Buffer.from(bytes).toString('base64');
  }
  throw new Error('no base64 encoder available');
}

export function unb64(text) {
  if (typeof text !== 'string') {
    throw new ValueError('base64 string required');
  }
  let raw;
  try {
    if (typeof atob === 'function') {
      raw = fromBinaryString(atob(text));
    } else if (typeof Buffer !== 'undefined') {
      raw = new Uint8Array(Buffer.from(text, 'base64'));
    } else {
      throw new Error('no base64 decoder available');
    }
  } catch {
    throw new ValueError('base64 string required');
  }
  if (b64(raw) !== text) {
    throw new ValueError('noncanonical base64');
  }
  return raw;
}

function address_ok(address) {
  if (typeof address !== 'string') return false;
  const match = /^([A-Za-z0-9./_-]{1,128}):([0-9a-f]+)$/.exec(address);
  if (!match) return false;
  const namespace = match[1];
  const digest = match[2];
  if (digest.length % 2 !== 0) return false;
  if ((namespace === 'punkti/0.5.1' || namespace === VERSION) && digest.length !== 64) return false;
  return true;
}

export function canonical(atom) {
  if (!atom || typeof atom !== 'object' || Array.isArray(atom)) {
    throw new ValueError('envelope fields/version');
  }
  const keys = Object.keys(atom);
  if (keys.length !== FIELDS.size || !keys.every(key => FIELDS.has(key)) || atom.v !== VERSION) {
    throw new ValueError('envelope fields/version');
  }
  if (!Number.isSafeInteger(atom.t) || atom.t < 0) {
    throw new ValueError('timestamp');
  }
  const tDecimal = String(atom.t);
  if (!/^(0|[1-9][0-9]*)$/.test(tDecimal)) {
    throw new ValueError('timestamp');
  }
  // Spatial structure is mandatory before any algorithm-specific checks.
  parse_h(atom.h);
  const x = utf8(atom.x);
  const alg = utf8(atom.alg);
  if (!alg.length || alg.length > 128 || !atom.alg.split('').every(char => char.charCodeAt(0) <= 0x7f)) {
    throw new ValueError('algorithm');
  }
  const pk = unb64(atom.pk);
  const sig = unb64(atom.sig);
  const ext = unb64(atom.ext);
  if (!pk.length || !sig.length) {
    throw new ValueError('empty key/signature');
  }
  if (atom.alg === 'ed25519' && (pk.length !== 32 || sig.length !== 64)) {
    throw new ValueError('ed25519 encoding lengths');
  }
  if (!Array.isArray(atom.refs)) {
    throw new ValueError('references array');
  }
  if (atom.refs.length > 256) {
    throw new ResourceLimit('reference limit');
  }

  const chunks = [
    lp(utf8(atom.v)),
    lp(encoder.encode(tDecimal)),
    lp(utf8(atom.h)),
    lp(x),
    lp(alg),
    lp(pk),
    u32(atom.refs.length),
  ];

  for (const ref of atom.refs) {
    if (!ref || typeof ref !== 'object' || Array.isArray(ref)) {
      throw new ValueError('reference');
    }
    const refKeys = Object.keys(ref);
    if (refKeys.length !== 2 || !refKeys.includes('target') || !refKeys.includes('rel') || !address_ok(ref.target)) {
      throw new ValueError('reference');
    }
    const rel = utf8(ref.rel);
    if (rel.length > 1024) {
      throw new ResourceLimit('relation limit');
    }
    chunks.push(lp(utf8(ref.target)), lp(rel));
  }

  chunks.push(lp(ext));
  const body = concat(...chunks);
  if (body.length > BODY_LIMIT) {
    throw new ResourceLimit('body limit');
  }
  return body;
}

class Reader {
  constructor(raw) {
    this.raw = toUint8Array(raw);
    this.pos = 0;
  }

  take(size) {
    if (size > this.raw.length - this.pos) {
      throw new ValueError('truncated framing');
    }
    const result = this.raw.slice(this.pos, this.pos + size);
    this.pos += size;
    return result;
  }

  count() {
    return new DataView(this.take(4).buffer).getUint32(0);
  }

  field() {
    return this.take(this.count());
  }

  text() {
    return decoder.decode(this.field());
  }

  end() {
    if (this.pos !== this.raw.length) {
      throw new ValueError('trailing bytes');
    }
  }
}

export function signingInput(body) {
  return concat(SIGN_DOMAIN, toUint8Array(body));
}

async function sha256(raw) {
  const digest = await getSubtle().digest('SHA-256', toUint8Array(raw));
  return new Uint8Array(digest);
}

function hex(raw) {
  return Array.from(raw, byte => byte.toString(16).padStart(2, '0')).join('');
}

export async function computeMid(body) {
  return hex(await sha256(concat(MID_DOMAIN, toUint8Array(body))));
}

export async function encodeRecord(atom, secretKey) {
  const nacl = getNacl();
  const key = toUint8Array(secretKey, 'secret key');
  if (key.length !== 64) {
    throw new ValueError('ed25519 secret key required');
  }
  const publicKey = nacl.sign.keyPair.fromSecretKey(key).publicKey;
  const envelope = {
    v: atom.v ?? VERSION,
    t: atom.t,
    h: atom.h,
    x: atom.x,
    alg: atom.alg ?? 'ed25519',
    pk: b64(publicKey),
    refs: atom.refs ?? [],
    ext: atom.ext ?? '',
    sig: b64(new Uint8Array(64)),
  };
  if (atom.pk !== undefined && atom.pk !== envelope.pk) {
    throw new ValueError('public key mismatch');
  }
  const body = canonical(envelope);
  const sig = nacl.sign.detached(signingInput(body), key);
  const record = concat(lp(body), lp(sig));
  if (record.length > RECORD_LIMIT) {
    throw new ResourceLimit('record limit');
  }
  const mid = await computeMid(body);
  return {
    address: `${VERSION}:${mid}`,
    mid,
    sha256: hex(await sha256(record)),
    record,
  };
}

export function decodeRecord(raw) {
  const bytes = toUint8Array(raw);
  if (bytes.length > RECORD_LIMIT) {
    throw new ResourceLimit('record limit');
  }
  const outer = new Reader(bytes);
  const body = outer.field();
  const sig = outer.field();
  outer.end();
  if (body.length > BODY_LIMIT) {
    throw new ResourceLimit('body limit');
  }
  const reader = new Reader(body);
  const version = reader.text();
  if (version !== VERSION) {
    throw new ValueError('unsupported version requires opaque wrapper');
  }
  const decimal = reader.text();
  if (!/^(0|[1-9][0-9]{0,15})$/.test(decimal)) {
    throw new ValueError('noncanonical timestamp');
  }
  const atom = {
    v: version,
    t: Number(decimal),
    h: reader.text(),
    x: reader.text(),
    alg: reader.text(),
    pk: b64(reader.field()),
  };
  const count = reader.count();
  if (count > 256) {
    throw new ResourceLimit('reference limit');
  }
  atom.refs = [];
  for (let index = 0; index < count; index++) {
    atom.refs.push({
      target: reader.text(),
      rel: reader.text(),
    });
  }
  atom.ext = b64(reader.field());
  atom.sig = b64(sig);
  reader.end();
  const canonicalBody = canonical(atom);
  if (canonicalBody.length !== body.length || canonicalBody.some((value, index) => value !== body[index])) {
    throw new ValueError('noncanonical body');
  }
  return { atom, body, sig: toUint8Array(sig) };
}

export async function validate(raw) {
  let decoded;
  try {
    decoded = decodeRecord(raw);
  } catch (error) {
    if (error instanceof ResourceLimit) throw error;
    return { state: State.STRUCTURAL, address: null, mid: null, h: null };
  }

  const mid = await computeMid(decoded.body);
  const address = `${VERSION}:${mid}`;
  if (decoded.atom.alg !== 'ed25519') {
    return { state: State.ALGORITHM, address, mid, h: decoded.atom.h };
  }

  let pk;
  try {
    pk = unb64(decoded.atom.pk);
  } catch {
    return { state: State.PROVENANCE, address, mid, h: decoded.atom.h };
  }

  if (pk.length !== 32 || decoded.sig.length !== 64) {
    return { state: State.PROVENANCE, address, mid, h: decoded.atom.h };
  }

  const nacl = getNacl();
  if (!nacl.sign.detached.verify(signingInput(decoded.body), decoded.sig, pk)) {
    return { state: State.PROVENANCE, address, mid, h: decoded.atom.h };
  }

  return { state: State.VALID, address, mid, h: decoded.atom.h };
}

export async function sha256Hex(raw) {
  return hex(await sha256(raw));
}
