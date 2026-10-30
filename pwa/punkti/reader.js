import {
  State,
  decodeRecord,
  sha256Hex,
  validate,
} from './carrier.js';
import {
  matches,
  normalize_scope,
  parse_h,
  xy_key,
} from './spatial.js';

const PROFILE = 'punkti/pub/0.6';
const MID_PREFIX = 'punkti/0.6:';
const MAGIC = new TextEncoder().encode('PUNKTIPACK1');
const PACK_MAX = 256;
const MAX_OBJECT = 64 * 1024 * 1024;
const ROOT_MEMBERS = new Set(['head', 'seq', 'v']);
const MANIFEST_MEMBERS = new Set(['index', 'pack_count', 'prev', 'record_count', 'seq', 'v']);
const SHARD_MEMBERS = new Set(['children', 'packs', 'prefix', 'records', 'v']);
const ENTRY_MEMBERS = new Set(['h', 'mid', 'sha256']);
const KEY_LEN = 12;
const INDEX_DEPTH = 2;
const LEAF_DEPTH = 10;
const ALPHABET = '0123456789bcdefghjkmnpqrstuvwxyz';
const HEX_64 = /^[0-9a-f]{64}$/;
const MID_RE = /^punkti\/0\.6:[0-9a-f]{64}$/;

const utf8Decoder = new TextDecoder('utf-8', { fatal: true });
const utf8Encoder = new TextEncoder();

function invalidObject(message = 'invalid object') {
  return new PublicationError(message, 'retryable');
}

function retryable(reason) {
  return new PublicationError(reason, 'retryable');
}

export class PublicationError extends Error {
  constructor(reason, error_class = 'retryable') {
    super(reason);
    this.name = 'PublicationError';
    this.reason = reason;
    this.error_class = error_class;
  }
}

function sameBytes(left, right) {
  if (left.length !== right.length) return false;
  for (let index = 0; index < left.length; index++) {
    if (left[index] !== right[index]) return false;
  }
  return true;
}

function isPlainObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value);
}

function canonicalValue(value) {
  if (Array.isArray(value)) {
    return value.map(canonicalValue);
  }
  if (isPlainObject(value)) {
    const out = {};
    for (const key of Object.keys(value).sort()) {
      if (typeof key !== 'string') {
        throw invalidObject('invalid object');
      }
      out[key] = canonicalValue(value[key]);
    }
    return out;
  }
  if (value === null || typeof value === 'string' || typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value)) {
    return value;
  }
  throw invalidObject('invalid object');
}

function parseCanonicalJson(raw) {
  let text;
  try {
    text = utf8Decoder.decode(raw);
  } catch {
    throw invalidObject('invalid object');
  }
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw invalidObject('invalid object');
  }
  let canonical;
  try {
    canonical = utf8Encoder.encode(JSON.stringify(canonicalValue(parsed)));
  } catch {
    throw invalidObject('invalid object');
  }
  if (!sameBytes(canonical, raw)) {
    throw invalidObject('invalid object');
  }
  return parsed;
}

function ensureMembers(value, members) {
  if (!isPlainObject(value)) throw invalidObject('invalid object');
  const keys = Object.keys(value);
  if (keys.length !== members.size || keys.some(key => !members.has(key))) {
    throw invalidObject('invalid object');
  }
}

function ensurePrefix(prefix, depth) {
  if (typeof prefix !== 'string' || prefix.length !== depth || [...prefix].some(char => !ALPHABET.includes(char))) {
    throw invalidObject('non-conforming geographical key');
  }
}

function integer(value, minimum = 0) {
  if (!Number.isInteger(value) || value < minimum) {
    throw invalidObject('invalid object');
  }
}

function ensureHex(value) {
  if (!HEX_64.test(value)) {
    throw invalidObject('invalid object');
  }
}

function lpField(bytes, offset) {
  if (offset + 4 > bytes.length) {
    throw invalidObject('invalid object');
  }
  const size = new DataView(bytes.buffer, bytes.byteOffset + offset, 4).getUint32(0);
  const start = offset + 4;
  const end = start + size;
  if (end > bytes.length) {
    throw invalidObject('invalid object');
  }
  return { field: bytes.slice(start, end), next: end };
}

function unpackPack(raw) {
  if (raw.length < MAGIC.length + 4 || !sameBytes(raw.slice(0, MAGIC.length), MAGIC)) {
    throw invalidObject('invalid object');
  }
  const count = new DataView(raw.buffer, raw.byteOffset + MAGIC.length, 4).getUint32(0);
  if (count < 1 || count > PACK_MAX) {
    throw invalidObject('invalid object');
  }
  const records = [];
  let offset = MAGIC.length + 4;
  for (let index = 0; index < count; index++) {
    const { field, next } = lpField(raw, offset);
    if (!field.length) {
      throw invalidObject('invalid object');
    }
    records.push(field);
    offset = next;
  }
  if (offset !== raw.length) {
    throw invalidObject('invalid object');
  }
  return records;
}

function leafKey(h) {
  const parts = parse_h(h);
  return xy_key(parts.xy).slice(0, LEAF_DEPTH);
}

function scopeIsUnbounded(scope) {
  return scope.xy_lo === null && scope.xy_hi === null && scope.z_min === null && scope.z_max === null;
}

function intersectsPrefix(prefix, scope) {
  const low = prefix.padEnd(KEY_LEN, '0');
  const high = prefix.padEnd(KEY_LEN, 'z');
  return (scope.xy_hi === null || low < xy_key(scope.xy_hi)) &&
    (scope.xy_lo === null || high >= xy_key(scope.xy_lo));
}

function encodePath(base, path) {
  const normalized = base.endsWith('/') ? base.slice(0, -1) : base;
  return `${normalized}/${path}`;
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export function hexShardedResolver() {
  return {
    rootPath() { return 'root.json'; },
    manifestPath(sha) { return `manifests/${sha}.json`; },
    shardPath(prefix, sha) {
      return `h/${prefix.split('').join('/')}/${sha}.json`;
    },
    recordPath(sha) { return `records/${sha.slice(0, 2)}/${sha}`; },
    segmentPath(sha) { return `segments/${sha.slice(0, 2)}/${sha}`; },
  };
}

export function flatResolver() {
  return {
    rootPath() { return 'root.json'; },
    manifestPath(sha) { return `manifests/${sha}.json`; },
    shardPath(_prefix, sha) { return `h/${sha}.json`; },
    recordPath(sha) { return `records/${sha}`; },
    segmentPath(sha) { return `segments/${sha}`; },
  };
}

export function indexMapResolver(pathMap = {}) {
  const fallback = hexShardedResolver();
  const fill = (template, values) => template.replace(/<([A-Za-z0-9_]+)>/g, (_match, key) => values[key] ?? '');
  const mapPath = (key, values, fallbackValue) => {
    const template = pathMap[key];
    if (typeof template !== 'string' || !template.length) {
      return fallbackValue;
    }
    return fill(template, values);
  };
  return {
    rootPath() {
      return mapPath('root.json', {}, fallback.rootPath());
    },
    manifestPath(sha) {
      return mapPath('manifests/<sha>.json', { sha }, fallback.manifestPath(sha));
    },
    shardPath(prefix, sha) {
      return mapPath('h/<prefixPath>/<sha>.json', {
        sha,
        prefix,
        prefixPath: prefix.split('').join('/'),
      }, fallback.shardPath(prefix, sha));
    },
    recordPath(sha) {
      return mapPath('records/<sha>', { sha }, fallback.recordPath(sha));
    },
    segmentPath(sha) {
      return mapPath('segments/<sha>', { sha }, fallback.segmentPath(sha));
    },
  };
}

function normalizeResolver(resolver) {
  const candidate = resolver || hexShardedResolver();
  const methods = ['rootPath', 'manifestPath', 'shardPath', 'recordPath', 'segmentPath'];
  if (!candidate || typeof candidate !== 'object' || methods.some(name => typeof candidate[name] !== 'function')) {
    throw new TypeError('resolver required');
  }
  return candidate;
}

export function createReader({
  fetchImpl = globalThis.fetch?.bind(globalThis),
  resolver,
  maxRetries = 2,
  onProgress = () => {},
} = {}) {
  if (typeof fetchImpl !== 'function') {
    throw new TypeError('fetchImpl required');
  }
  const pathResolver = normalizeResolver(resolver);
  const seenHeads = new Map();
  const checkpoints = new Map();
  let lastError = null;

  const getBytes = async (base, path, sha = null) => {
    let response;
    try {
      response = await fetchImpl(encodePath(base, path));
    } catch (error) {
      throw retryable('missing object');
    }
    if (!response || !response.ok) {
      throw retryable('missing object');
    }
    const buffer = new Uint8Array(await response.arrayBuffer());
    if (buffer.length > MAX_OBJECT) {
      throw retryable('resource limit');
    }
    if (sha !== null && await sha256Hex(buffer) !== sha) {
      throw retryable('corrupt object');
    }
    return buffer;
  };

  const parseRoot = raw => {
    const root = parseCanonicalJson(raw);
    ensureMembers(root, ROOT_MEMBERS);
    if (root.v !== PROFILE) throw invalidObject('invalid object');
    integer(root.seq, 1);
    ensureHex(root.head);
    return root;
  };

  const parseManifest = raw => {
    const manifest = parseCanonicalJson(raw);
    ensureMembers(manifest, MANIFEST_MEMBERS);
    if (manifest.v !== PROFILE) throw invalidObject('invalid object');
    integer(manifest.seq, 1);
    integer(manifest.record_count, 0);
    integer(manifest.pack_count, 0);
    if (manifest.prev !== null) ensureHex(manifest.prev);
    if ((manifest.seq === 1) !== (manifest.prev === null)) {
      throw invalidObject('invalid object');
    }
    if (!isPlainObject(manifest.index) || Object.keys(manifest.index).length > 1024) {
      throw invalidObject('invalid object');
    }
    for (const [prefix, shard] of Object.entries(manifest.index)) {
      ensurePrefix(prefix, INDEX_DEPTH);
      ensureHex(shard);
    }
    return manifest;
  };

  const parseShard = (raw, expectedPrefix) => {
    const shard = parseCanonicalJson(raw);
    ensureMembers(shard, SHARD_MEMBERS);
    if (shard.v !== PROFILE) throw invalidObject('invalid object');
    ensurePrefix(shard.prefix, typeof shard.prefix === 'string' ? shard.prefix.length : 0);
    if (shard.prefix !== expectedPrefix || !isPlainObject(shard.children) || !Array.isArray(shard.records) || !Array.isArray(shard.packs)) {
      throw invalidObject('invalid object');
    }
    ensurePrefix(expectedPrefix, expectedPrefix.length);
    if (expectedPrefix.length < INDEX_DEPTH || expectedPrefix.length > LEAF_DEPTH) {
      throw invalidObject('non-conforming geographical key');
    }
    const leaf = expectedPrefix.length === LEAF_DEPTH;
    if (leaf) {
      if (Object.keys(shard.children).length !== 0 || shard.records.length === 0) {
        throw invalidObject('invalid object');
      }
    } else if (Object.keys(shard.children).length === 0 || shard.records.length !== 0 || shard.packs.length !== 0) {
      throw invalidObject('invalid object');
    }

    for (const [childPrefix, childSha] of Object.entries(shard.children)) {
      ensurePrefix(childPrefix, expectedPrefix.length + 1);
      if (!childPrefix.startsWith(expectedPrefix) || childPrefix.length > LEAF_DEPTH) {
        throw invalidObject('invalid object');
      }
      ensureHex(childSha);
    }

    const ids = [];
    for (const entry of shard.records) {
      ensureMembers(entry, ENTRY_MEMBERS);
      if (!MID_RE.test(entry.mid)) throw invalidObject('invalid object');
      ensureHex(entry.sha256);
      if (leafKey(entry.h) !== expectedPrefix) {
        throw invalidObject('invalid object');
      }
      ids.push(entry.sha256);
    }
    const sortedUnique = [...new Set(ids)].sort();
    if (sortedUnique.length !== ids.length || sortedUnique.some((sha, index) => sha !== ids[index])) {
      throw invalidObject('invalid object');
    }

    for (const packSha of shard.packs) ensureHex(packSha);
    const packSorted = [...new Set(shard.packs)].sort();
    if (packSorted.length !== shard.packs.length || packSorted.some((sha, index) => sha !== shard.packs[index])) {
      throw invalidObject('invalid object');
    }
    if (shard.packs.length && shard.packs.length !== Math.ceil(shard.records.length / PACK_MAX)) {
      throw invalidObject('invalid object');
    }

    return shard;
  };

  const attemptRead = async (base, requestedScope = {}) => {
    const scope = normalize_scope(requestedScope);
    const checkpointKey = `${base}::${JSON.stringify(scope)}`;

    const root = parseRoot(await getBytes(base, pathResolver.rootPath()));
    const known = seenHeads.get(base);
    if (known && root.seq < known.seq) {
      throw retryable('stale root');
    }
    if (known && root.seq === known.seq && root.head !== known.head) {
      throw retryable('equivocal root');
    }

    const manifest = parseManifest(await getBytes(base, pathResolver.manifestPath(root.head), root.head));
    if (manifest.seq !== root.seq) {
      throw retryable('publication race');
    }

    const validByMid = new Map();
    const candidateBySha = new Map();
    const quarantined = [];
    let rejected = 0;
    let recordCount = 0;
    let packCount = 0;

    const processRecord = async (raw, entry) => {
      const rawSha = await sha256Hex(raw);
      if (rawSha !== entry.sha256) {
        throw retryable('corrupt object');
      }
      const outcome = await validate(raw);
      if (outcome.address !== null && (outcome.address !== entry.mid || outcome.h !== entry.h)) {
        throw retryable('record metadata');
      }
      if (outcome.state === State.STRUCTURAL || outcome.state === State.PROVENANCE) {
        rejected += 1;
        quarantined.push({ sha256: entry.sha256, state: outcome.state, h: entry.h, mid: entry.mid });
        return;
      }
      if (!matches(entry.h, scope)) {
        return;
      }
      const decoded = decodeRecord(raw);
      if (outcome.state === State.VALID) {
        if (!validByMid.has(entry.mid)) {
          validByMid.set(entry.mid, {
            mid: entry.mid,
            sha256: entry.sha256,
            h: entry.h,
            state: outcome.state,
            record: raw,
            atom: decoded.atom,
          });
        }
        return;
      }
      if (!candidateBySha.has(entry.sha256)) {
        candidateBySha.set(entry.sha256, {
          mid: entry.mid,
          sha256: entry.sha256,
          h: entry.h,
          state: outcome.state,
          record: raw,
          atom: decoded.atom,
        });
      }
    };

    const walk = async (prefix, shardSha) => {
      if (!intersectsPrefix(prefix, scope)) {
        return;
      }
      const shard = parseShard(await getBytes(base, pathResolver.shardPath(prefix, shardSha), shardSha), prefix);
      const bySha = new Map(shard.records.map(entry => [entry.sha256, entry]));
      recordCount += bySha.size;
      packCount += shard.packs.length;

      if (shard.packs.length) {
        const expectedShas = shard.records.map(entry => entry.sha256);
        const groups = [];
        for (let index = 0; index < expectedShas.length; index += PACK_MAX) {
          groups.push(expectedShas.slice(index, index + PACK_MAX));
        }
        const groupKeys = new Set(groups.map(group => group.join(',')));
        const seen = new Set();
        for (const segmentSha of shard.packs) {
          const packed = unpackPack(await getBytes(base, pathResolver.segmentPath(segmentSha), segmentSha));
          const digests = [];
          for (const raw of packed) digests.push(await sha256Hex(raw));
          const key = digests.join(',');
          if (!groupKeys.has(key) || digests.some(digest => seen.has(digest))) {
            throw retryable('pack membership');
          }
          digests.forEach(digest => seen.add(digest));
          for (let index = 0; index < packed.length; index++) {
            const digest = digests[index];
            const entry = bySha.get(digest);
            if (!entry) {
              throw retryable('pack membership');
            }
            await processRecord(packed[index], entry);
          }
        }
        if (seen.size !== bySha.size) {
          throw retryable('pack membership');
        }
      } else {
        for (const [sha, entry] of bySha.entries()) {
          await processRecord(await getBytes(base, pathResolver.recordPath(sha), sha), entry);
        }
      }

      for (const [childPrefix, childSha] of Object.entries(shard.children)) {
        await walk(childPrefix, childSha);
      }
    };

    for (const [prefix, shardSha] of Object.entries(manifest.index)) {
      await walk(prefix, shardSha);
    }

    if (scopeIsUnbounded(scope) && (recordCount !== manifest.record_count || packCount !== manifest.pack_count)) {
      throw retryable('manifest counts');
    }

    const records = [...validByMid.values(), ...candidateBySha.values()];
    const result = {
      head: root.head,
      seq: root.seq,
      // `admitted` counts newly admitted VALID records only; unverified
      // candidates are reported separately (frozen reader semantics).
      admitted: validByMid.size,
      valid: validByMid.size,
      valid_count: validByMid.size,
      candidates: candidateBySha.size,
      candidate_count: candidateBySha.size,
      rejected,
      records,
      valid_records: [...validByMid.values()],
      candidate_records: [...candidateBySha.values()],
      quarantined,
      scope,
    };

    seenHeads.set(base, { seq: root.seq, head: root.head });
    checkpoints.set(checkpointKey, root.head);
    onProgress({ type: 'read-complete', base, head: root.head, seq: root.seq });
    return result;
  };

  const readPublication = async (base, scope = {}) => {
    const rootBase = base.replace(/\/$/, '');
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const result = await attemptRead(rootBase, scope);
        lastError = null;
        return result;
      } catch (error) {
        const publicationError = error instanceof PublicationError ? error : invalidObject('invalid object');
        if (!(error instanceof PublicationError)) {
          publicationError.detail = error?.message || String(error);
        }
        lastError = publicationError;
        if (attempt >= maxRetries || publicationError.error_class !== 'retryable') {
          throw publicationError;
        }
        await wait(Math.min(500, 25 * (2 ** attempt)));
      }
    }
    throw retryable('missing object');
  };

  const readRecord = async (base, sha) => {
    if (!HEX_64.test(sha)) {
      throw new TypeError('sha required');
    }
    return getBytes(base.replace(/\/$/, ''), pathResolver.recordPath(sha), sha);
  };

  return {
    readPublication,
    readRecord,
    get lastError() {
      return lastError;
    },
    get checkpoints() {
      return new Map(checkpoints);
    },
    get seenHeads() {
      return new Map(seenHeads);
    },
  };
}
