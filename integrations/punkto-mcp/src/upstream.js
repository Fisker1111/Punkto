import { sha256Hex } from './hash.js';

export const FETCH_BUDGET = 20;
export const ORIGINS = Object.freeze(['https://punkto.xyz', 'https://test2.punkto.xyz']);
const CAP = 1048576;
export class ToolError extends Error {
  constructor(code, message, fallback = false) {
    super(message);
    this.code = code;
    this.fallback = fallback;
  }
}
export const fail = (code, message) => { throw new ToolError(code, message); };
export function digest(value) {
  if (typeof value !== 'string' || value.length !== 64 || !/^[0-9a-f]{64}$/.test(value)) fail('invalid_sha256', 'Supply a lowercase SHA-256 digest.');
  return value;
}
function objectPath(kind, sha, prefix) {
  if (kind === 'root') return '/publication/root.json';
  digest(sha);
  if (kind === 'manifest') return `/publication/manifests/${sha}.json`;
  if (kind === 'record') return `/publication/records/${sha.slice(0, 2)}/${sha}`;
  if (kind === 'shard' && typeof prefix === 'string' && prefix.length >= 2 && prefix.length <= 10 && !/[^0-9bcdefghjkmnpqrstuvwxyz]/.test(prefix)) {
    return `/publication/h/${[...prefix].join('/')}/${sha}.json`;
  }
  fail('corrupt_object', 'Invalid publication object reference.');
}
async function boundedBytes(response) {
  if (Number(response.headers.get('content-length')) > CAP) {
    await response.body?.cancel();
    fail('object_too_large', 'Publication object exceeds 1 MiB.');
  }
  const chunks = [];
  let size = 0;
  const reader = response.body?.getReader();
  if (!reader) return new Uint8Array();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > CAP) {
        await reader.cancel();
        fail('object_too_large', 'Publication object exceeds 1 MiB.');
      }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return bytes;
}
// One client belongs to exactly one origin attempt. Budget injection is test-only.
export function createUpstream({ origin, fetchImpl = globalThis.fetch, budget = FETCH_BUDGET } = {}) {
  if (!ORIGINS.includes(origin)) fail('unsupported_origin', 'Use a configured publication origin.');
  if (!Number.isInteger(budget) || budget < 0 || budget > FETCH_BUDGET) throw new RangeError('budget');
  let fetchCount = 0;
  let verifiedObjects = 0;
  // All callers share this semaphore, including any future parallel record reads.
  let active = 0;
  const queue = [];
  async function locked(fn) {
    if (active >= 4) await new Promise(resolve => queue.push(resolve));
    else active++;
    try { return await fn(); }
    finally { const next = queue.shift(); if (next) next(); else active--; }
  }
  const url = (kind, sha, prefix) => origin + objectPath(kind, sha, prefix);
  return {
    origin, url,
    stats: () => ({ fetch_count: fetchCount, verified_objects: verifiedObjects, budget: { per_attempt: budget, used: fetchCount } }),
    async get(kind, sha, prefix, mismatch = 'corrupt_object') {
      const address = url(kind, sha, prefix);
      return locked(async () => {
        let bytes;
        if (kind !== 'root') {
          try {
            const cached = await globalThis.caches?.default?.match(address);
            if (cached) bytes = await boundedBytes(cached);
          } catch { /* Cache is optional; failed reads use the origin. */ }
        }
        const hit = bytes !== undefined;
        if (!hit) {
          if (fetchCount >= budget) fail('fetch_budget_exceeded', 'Publication fetch budget exhausted.');
          fetchCount++;
          try {
            const response = await fetchImpl(address, { method: 'GET', redirect: 'manual', signal: AbortSignal.timeout(4000) });
            if (response.status >= 300 && response.status < 400) fail('upstream_redirect_refused', 'Publication redirects are refused.');
            if (response.status === 404) fail('upstream_missing_object', 'Required publication object is missing.');
            // Rate limits do not trigger fallback: only transport failures and 5xx do.
            if (response.status === 429) fail('upstream_unavailable', 'Publication rate limited; retry later.');
            if (response.status >= 500) throw new ToolError('upstream_unavailable', 'Publication origin unavailable; retry later.', true);
            if (!response.ok) fail('upstream_unavailable', 'Publication origin rejected the request.');
            bytes = await boundedBytes(response);
          } catch (error) {
            if (error instanceof ToolError) throw error;
            if (error?.name === 'TimeoutError' || error?.name === 'AbortError') throw new ToolError('upstream_timeout', 'Publication request timed out; retry later.', true);
            throw new ToolError('upstream_unavailable', 'Publication origin unreachable; retry later.', true);
          }
        }
        if (kind !== 'root') {
          if (await sha256Hex(bytes) !== sha) fail(mismatch, 'Object digest differs from its reference.');
          verifiedObjects++;
          if (!hit) {
            try {
              await globalThis.caches?.default?.put(address, new Response(bytes, { headers: { 'Cache-Control': 'public, max-age=31536000, immutable' } }));
            } catch { /* Cache failure cannot change publication results. */ }
          }
        }
        return bytes;
      });
    },
  };
}
export async function withOrigin(operation, options = {}) {
  let total = 0;
  for (let attempt = 0; attempt < ORIGINS.length; attempt++) {
    const client = createUpstream({ ...options, origin: ORIGINS[attempt] });
    try {
      const result = await operation(client);
      const stats = client.stats();
      return { ...result, origin: client.origin, ...stats,
        fetch_count: total + stats.fetch_count,
        budget: { ...stats.budget, attempts: attempt + 1, max_attempts: 2, total_fetches: total + stats.fetch_count } };
    } catch (error) {
      total += client.stats().fetch_count;
      if (attempt === ORIGINS.length - 1 || !error.fallback) throw error;
    }
  }
}
