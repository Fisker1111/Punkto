import { ensurePunktoPrefix, normalizePunktoId } from './punkto-id.js';

/**
 * Normalize an atom-like payload into a stable local shape.
 * Does not perform I/O or enforce strict validation.
 */
export function normalizeAtomPayload(raw) {
  const src = raw && typeof raw === 'object' ? raw : {};
  const normalizedId = normalizePunktoId(src.punkto);

  return {
    punkto: normalizedId ? ensurePunktoPrefix(normalizedId) : String(src.punkto || ''),
    t: src.t,
    x: typeof src.x === 'string' ? src.x : (src.x == null ? '' : String(src.x)),
    f: typeof src.f === 'string' ? src.f : (src.f == null ? '' : String(src.f)),
    sig: src.sig,
    pubkey: src.pubkey,
  };
}
