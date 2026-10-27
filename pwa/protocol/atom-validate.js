import { isPunktoId } from './punkto-id.js';
import { parse_h } from '../punkti/spatial.js';

export function getAtomValidationError(atom) {
  if (!atom || typeof atom !== 'object') return 'atom must be an object';

  const hasLegacyPunkto = isPunktoId(atom.punkto);
  let hasSpatialH = false;
  try {
    hasSpatialH = typeof atom.h === 'string' && (atom.h === '' || !!parse_h(atom.h));
  } catch {
    hasSpatialH = false;
  }
  if (!hasLegacyPunkto && !hasSpatialH) return 'invalid spatial address';

  const tNum = Number(atom.t);
  if (!Number.isFinite(tNum) || tNum <= 0) return 'invalid atom timestamp';

  return null;
}

export function isValidAtom(atom) {
  return getAtomValidationError(atom) === null;
}
