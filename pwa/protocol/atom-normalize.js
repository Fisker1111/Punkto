import { ensurePunktoPrefix, normalizePunktoId } from './punkto-id.js';

/**
 * Normalize an atom-like payload into a stable local shape.
 * Does not perform I/O or enforce strict validation.
 */
export function normalizeAtomPayload(raw) {
  const src = raw && typeof raw === 'object' ? raw : {};
  const normalizedId = normalizePunktoId(src.punkto);

  const normalized = {
    ...src,
    punkto: normalizedId ? ensurePunktoPrefix(normalizedId) : String(src.punkto || ''),
    t: src.t,
    x: typeof src.x === 'string' ? src.x : (src.x == null ? '' : String(src.x)),
    x_payload: typeof src.x_payload === 'string' ? src.x_payload : (src.x_payload == null ? undefined : String(src.x_payload)),
    f: typeof src.f === 'string' ? src.f : (src.f == null ? '' : String(src.f)),
    sig: src.sig,
    pubkey: src.pubkey,
  };

  for (const field of ['relation', 'parent_id', 'root_id', 'location_source', 'category', 'kind']) {
    if (src[field] != null) normalized[field] = src[field];
  }
  for (const field of ['location_lock']) {
    if (src[field] != null) normalized[field] = src[field];
  }
  for (const field of ['atom_id', 'mid', 'sha256', 'h', 'lat', 'lon', 'altitude_m', 'alt', 'z', 'floor', 'level', 'ellipsoidal_z', 'verification_state', 'publication_base_url', 'publication_seq', 'publication_head']) {
    if (src[field] != null) normalized[field] = src[field];
  }
  return normalized;
}
