// Punkti L3 transport. L4 JSON remains opaque to the node.
const enc = new TextEncoder();
const dec = new TextDecoder('utf-8', { fatal: true });
export const VERSION = 'punkti/0.6';
export const ALPHABET = '0123456789bcdefghjkmnpqrstuvwxyz';
const SIGN = enc.encode('PUNKTI-L3-SIGN\0');
const MID = enc.encode('PUNKTI-L3-MID\0');
const concat = (...parts) => {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let offset = 0;
  for (const p of parts) { out.set(p, offset); offset += p.length; }
  return out;
};
const uint = n => { const b = new Uint8Array(4); new DataView(b.buffer).setUint32(0, n); return b; };
const lp = b => concat(uint(b.length), b);
const text = s => lp(enc.encode(s));
const b64 = b => { let s = ''; for (const c of b) s += String.fromCharCode(c); return btoa(s); };
const unb64 = s => { const b = Uint8Array.from(atob(s), c => c.charCodeAt(0)); if (b64(b) !== s) throw Error('Noncanonical base64'); return b; };
const hash = async b => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', b)), c => c.toString(16).padStart(2, '0')).join('');
export function canonicalJson(v) {
  if (Array.isArray(v)) return '[' + v.map(canonicalJson).join(',') + ']';
  if (v && typeof v === 'object') return '{' + Object.keys(v).sort().filter(k => v[k] !== undefined).map(k => JSON.stringify(k) + ':' + canonicalJson(v[k])).join(',') + '}';
  return JSON.stringify(v);
}
export function geohash3d(lon, lat, alt) {
  const values = [lat, lon, alt];
  const bounds = [[-90, 90], [-180, 180], [-500, 8500]];
  if (values.some((v, i) => !Number.isFinite(v) || v < bounds[i][0] || v > bounds[i][1])) throw Error('Location outside supported bounds');
  let h = '', digit = 0;
  for (let bit = 0; bit < 60; bit++) {
    const axis = bit % 3, mid = (bounds[axis][0] + bounds[axis][1]) / 2;
    const high = values[axis] >= mid;
    bounds[axis][high ? 0 : 1] = mid;
    digit = digit * 2 + Number(high);
    if (bit % 5 === 4) { h += ALPHABET[digit]; digit = 0; }
  }
  return h;
}
export async function encodeRecord(atom, identity) {
  if (!identity?.secretKey) throw Error('Create or import an identity before publishing.');
  if (!Number.isSafeInteger(atom.t) || atom.t < 0) throw Error('Invalid timestamp');
  const key = new Uint8Array(identity.secretKey);
  if (key.length !== 64) throw Error('Invalid signing key');
  const pk = nacl.sign.keyPair.fromSecretKey(key).publicKey;
  // Older L4 atoms encode the exact location only in their p: address.
  const h = atom.lon != null && atom.lat != null
    ? geohash3d(atom.lon, atom.lat, atom.altitude_m ?? atom.alt ?? atom.z ?? 0)
    : String(atom.punkto || '').replace(/^p:/, '');
  if (!/^[0123456789bcdefghjkmnpqrstuvwxyz]{12}$/.test(h)) throw Error('Invalid spatial address');
  const body = concat(text(VERSION), text(String(atom.t)), text(h), text(canonicalJson(atom)), text('ed25519'), lp(pk), uint(0), lp(new Uint8Array()));
  if (body.length > 1048576) throw Error('Record exceeds body limit');
  const raw = concat(lp(body), lp(nacl.sign.detached(concat(SIGN, body), key)));
  return { address: VERSION + ':' + await hash(concat(MID, body)), sha256: await hash(raw), record: b64(raw) };
}
class Reader {
  constructor(raw) { this.raw = raw; this.pos = 0; }
  take(n) { if (n > this.raw.length - this.pos) throw Error('Truncated record'); const b = this.raw.slice(this.pos, this.pos + n); this.pos += n; return b; }
  count() { return new DataView(this.take(4).buffer).getUint32(0); }
  field() { return this.take(this.count()); }
  text() { return dec.decode(this.field()); }
  end() { if (this.pos !== this.raw.length) throw Error('Trailing bytes'); }
}
export async function decodeRecord(item) {
  const raw = unb64(item.record);
  if (raw.length > 2097152 || await hash(raw) !== item.sha256) throw Error('Record digest mismatch');
  const outer = new Reader(raw), body = outer.field(), sig = outer.field(); outer.end();
  if (body.length > 1048576 || sig.length !== 64) throw Error('Record size');
  const r = new Reader(body);
  if (r.text() !== VERSION) throw Error('Version');
  const t = r.text();
  if (!/^(0|[1-9][0-9]{0,15})$/.test(t) || !Number.isSafeInteger(Number(t))) throw Error('Timestamp');
  const h = r.text();
  if (h !== '' && !/^[0123456789bcdefghjkmnpqrstuvwxyz]{12}$/.test(h)) throw Error('Location');
  const x = r.text();
  if (r.text() !== 'ed25519') throw Error('Algorithm');
  const pk = r.field(), count = r.count();
  if (pk.length !== 32 || count > 256) throw Error('Key or references');
  for (let i = 0; i < count; i++) {
    const target = r.text(), rel = r.field();
    if (!/^[A-Za-z0-9./_-]{1,128}:([0-9a-f]{2})+$/.test(target) || (/^punkti\/0\.(6|5\.1):/.test(target) && target.split(':')[1].length !== 64) || rel.length > 1024) throw Error('Reference');
    dec.decode(rel);
  }
  r.field(); r.end();
  if (item.address !== VERSION + ':' + await hash(concat(MID, body)) || !nacl.sign.detached.verify(concat(SIGN, body), sig, pk)) throw Error('Invalid envelope signature/address');
  return { x, h, t: Number(t) };
}
export function createPunktiClient({ baseUrl = '', apiPrefix = '/api', identity } = {}) {
  const stats = { skipped: 0 };
  async function request(path, body) {
    const res = await fetch(baseUrl.replace(/\/$/, '') + apiPrefix + path, {
      signal: AbortSignal.timeout(15000),
      ...(body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}),
    });
    const data = await res.json();
    if (!res.ok) throw Error(data.error || `HTTP ${res.status}`);
    return data;
  }
  return {
    stats,
    async pushAtom(atom) {
      if (!globalThis.window?.verifyAtom?.(atom)) throw Error('A valid signed message is required.');
      const item = await encodeRecord(atom, typeof identity === 'function' ? await identity() : identity);
      const data = await request('/push', { records: [item] });
      const result = data.results?.[0];
      if (!result?.admitted && result?.reason !== 'duplicate') throw Error(`Node did not store the message: ${result?.reason || result?.state || 'unknown response'}`);
      return result;
    },
    async pullAll({ scope = {}, limit = 32, maxPages = 10000 } = {}) {
      const atoms = []; let cursor = null; stats.skipped = 0;
      for (let page = 0; page < maxPages; page++) {
        const data = await request('/pull?q=' + encodeURIComponent(JSON.stringify({ scope, limit, cursor })));
        for (const item of data.records) {
          try {
            const { x } = await decodeRecord(item), atom = JSON.parse(x);
            if (!globalThis.window?.verifyAtom?.(atom)) throw Error('Invalid L4 signature');
            atoms.push(atom);
          } catch { stats.skipped++; }
        }
        if (data.end) return atoms;
        if (!data.cursor || JSON.stringify(cursor) === JSON.stringify(data.cursor)) throw Error('Pull cursor did not advance');
        cursor = data.cursor;
      }
      throw Error('Pull page limit exceeded; sync incomplete');
    },
    nodeInfo: () => request('/node/info'),
    health: () => request('/health'),
  };
}
