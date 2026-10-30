import { createReader, hexShardedResolver } from '../punkti/reader.js';
import { createSubmitClient } from '../punkti/submit.js';
import { decode_xy, matches, normalize_scope, parse_h } from '../punkti/spatial.js';
import { encodeLocation } from '../core/location.js';

const VERSION = 'punkti/0.6';

function endpoint(base, path) {
  return `${base.replace(/\/$/, '')}${path}`;
}

async function jsonRequest(baseUrl, path, { method = 'GET', body = null } = {}) {
  const init = { method, headers: { Accept: 'application/json' } };
  if (body != null) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  const response = await fetch(endpoint(baseUrl, path), init);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload?.error || `HTTP ${response.status}`);
    error.status = response.status;
    error.code = payload?.error || null;
    error.detail = payload;
    throw error;
  }
  return payload;
}

function toUiPayload(x) {
  const raw = typeof x === 'string' ? x : String(x ?? '');
  let parsed = null;
  try {
    const candidate = JSON.parse(raw);
    if (candidate && typeof candidate === 'object' && !Array.isArray(candidate)) {
      parsed = candidate;
    }
  } catch {}
  const text = parsed && typeof parsed.text === 'string' ? parsed.text : raw;
  return {
    text,
    raw,
    meta: parsed && parsed.meta && typeof parsed.meta === 'object' ? parsed.meta : null,
  };
}

function hToCoordinates(h) {
  const parsed = parse_h(h);
  const xy = decode_xy(parsed.xy);
  const altitude = Number(parsed.z);
  return {
    lat: xy.lat,
    lon: xy.lon,
    alt: Number.isFinite(altitude) ? altitude : null,
    xy: parsed.xy,
    z: parsed.z,
  };
}

function mapRecordToAtom(record, publication) {
  const payload = toUiPayload(record.atom?.x);
  const coords = hToCoordinates(record.h);
  const category = String(payload.meta?.category || payload.meta?.kind || payload.meta?.tag || '').trim().toUpperCase();
  const author = String(payload.meta?.author || payload.meta?.handle || '').trim();
  let punkto = '';
  if (coords.lat != null && coords.lon != null && coords.alt != null) {
    try {
      punkto = encodeLocation(coords.lat, coords.lon, coords.alt);
    } catch {
      punkto = '';
    }
  }
  const atom = {
    atom_id: record.mid,
    mid: record.mid,
    sha256: record.sha256,
    h: record.h,
    t: Number(record.atom?.t || 0),
    x: payload.text,
    x_payload: payload.raw,
    f: author,
    category: category || 'TEXT',
    punkto,
    lat: coords.lat,
    lon: coords.lon,
    alt: coords.alt,
    ellipsoidal_z: coords.z || null,
    verification_state: record.state,
    publication_base_url: publication.base,
    publication_seq: publication.seq,
    publication_head: publication.head,
    sig: record.atom?.sig || '',
    pubkey: record.atom?.pk || '',
  };

  if (payload.meta?.floor !== undefined) atom.floor = payload.meta.floor;
  if (payload.meta?.height_above_ground_m !== undefined) atom.height_above_ground_m = payload.meta.height_above_ground_m;
  if (payload.meta?.place !== undefined) atom.place = payload.meta.place;
  return atom;
}

function normalizeIdentity(identity) {
  if (!identity || typeof identity !== 'object') {
    throw new Error('Create or import an identity in Settings before publishing.');
  }
  const key = identity.secretKey;
  if (key instanceof Uint8Array && key.length === 64) {
    return { secretKey: key };
  }
  if (Array.isArray(key) && key.length === 64) {
    return { secretKey: Uint8Array.from(key) };
  }
  throw new Error('Create or import an identity in Settings before publishing.');
}

function toCarrierAtom(atom) {
  const timestamp = Number(atom?.t);
  if (!Number.isSafeInteger(timestamp) || timestamp <= 0) {
    throw new Error('Invalid timestamp');
  }
  const payload = atom?.x_payload && typeof atom.x_payload === 'string'
    ? atom.x_payload
    : (typeof atom?.x === 'string' ? atom.x : JSON.stringify({ text: String(atom?.x ?? '') }));
  const h = atom?.h;
  parse_h(h);
  return {
    v: VERSION,
    t: timestamp,
    h,
    x: payload,
    alg: 'ed25519',
    refs: [],
    ext: '',
  };
}

export function createPunktiClient({ baseUrl, identity } = {}) {
  if (typeof baseUrl !== 'string' || !baseUrl) {
    throw new TypeError('baseUrl required');
  }
  if (typeof identity !== 'function') {
    throw new TypeError('identity callback required');
  }

  const publicationBase = endpoint(baseUrl, '/publication');
  const reader = createReader({ resolver: hexShardedResolver() });
  let scope = normalize_scope({});
  let lastRead = null;

  return {
    setScope(nextScope = {}) {
      scope = normalize_scope(nextScope);
      return scope;
    },

    getScope() {
      return { ...scope };
    },

    getLastRead() {
      return lastRead;
    },

    async pullAll() {
      const publication = await reader.readPublication(publicationBase, scope);
      const source = {
        base: publicationBase,
        seq: publication.seq,
        head: publication.head,
      };
      const atoms = publication.valid_records.map((record) => mapRecordToAtom(record, source));
      lastRead = {
        ...source,
        scope: publication.scope,
        valid_count: publication.valid_count,
        candidate_count: publication.candidate_count,
        rejected: publication.rejected,
        records: publication.valid_records.map((record) => ({
          mid: record.mid,
          sha256: record.sha256,
          h: record.h,
          state: record.state,
        })),
      };
      return atoms;
    },

    async pushAtom(atom) {
      const identityValue = normalizeIdentity(await identity());
      const submitClient = createSubmitClient({
        baseUrl,
        identity: identityValue,
      });
      const result = await submitClient.submit(toCarrierAtom(atom));
      if (!result.ok) {
        const error = new Error(result.message || result.error || 'submit failed');
        error.code = result.error || result.state;
        error.detail = result;
        throw error;
      }
      return {
        atom_id: result.mid,
        mid: result.mid,
        address: result.address,
        sha256: result.sha256,
        duplicate: result.duplicate,
        head: result.head,
        seq: result.seq,
      };
    },

    async nodeInfo() {
      return jsonRequest(baseUrl, '/node/info');
    },

    async publicationInfo() {
      return jsonRequest(publicationBase, '/root.json');
    },

    matchesScope(h) {
      return matches(h, scope);
    },

    publicationBase,
  };
}
