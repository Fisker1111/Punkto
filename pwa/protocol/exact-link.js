import { computeAtomId, isStableAtomId } from './atom-id.js';
import { normalizePunktoId, stripPunktoPrefix } from './punkto-id.js';

const LOCAL_ONLY_FIELDS = new Set(['id', 'atom_id', 'distance', 'location_fields']);

export function sanitizeAtomForCanonicalId(atom) {
  const source = atom && typeof atom === 'object' ? atom : {};
  const clean = {};
  for (const [key, value] of Object.entries(source)) {
    if (LOCAL_ONLY_FIELDS.has(key) || value === undefined) continue;
    clean[key] = value;
  }
  return clean;
}

export async function canonicalAtomId(atom) {
  const direct = String(atom?.atom_id || '').trim();
  if (isStableAtomId(direct)) return direct;
  return computeAtomId(sanitizeAtomForCanonicalId(atom));
}

export function parsePublicPPath(pathname) {
  const match = /^\/p\/([^/]+)\/?$/.exec(String(pathname || '').trim());
  if (!match) return null;
  let raw = '';
  try {
    raw = decodeURIComponent(match[1] || '').trim();
  } catch {
    return null;
  }
  if (isStableAtomId(raw)) return { kind: 'atom', id: raw };
  const spatial = normalizePunktoId(raw);
  if (spatial) return { kind: 'spatial', id: spatial };
  return null;
}

export function canonicalAtomPath(atomOrId) {
  const id = typeof atomOrId === 'string'
    ? atomOrId.trim()
    : String(atomOrId?.atom_id || '').trim();
  if (!isStableAtomId(id)) return '';
  return `/p/${encodeURIComponent(id)}`;
}

export async function canonicalAtomUrl(atomOrId, origin = globalThis.location?.origin || '') {
  const id = typeof atomOrId === 'string' ? atomOrId.trim() : await canonicalAtomId(atomOrId);
  if (!isStableAtomId(id)) return '';
  return `${String(origin || '').replace(/\/$/, '')}${canonicalAtomPath(id)}`;
}

export function legacySpatialPath(punkto) {
  const bare = stripPunktoPrefix(punkto || '');
  return bare ? `/p/${encodeURIComponent(bare)}` : '';
}
