import { isPunktoId } from './punkto-id.js';

export function getAtomValidationError(atom) {
  if (!atom || typeof atom !== 'object') return 'atom must be an object';
  if (!isPunktoId(atom.punkto)) return 'invalid punkto id';

  const tNum = Number(atom.t);
  if (!Number.isFinite(tNum) || tNum <= 0) return 'invalid atom timestamp';

  return null;
}

export function isValidAtom(atom) {
  return getAtomValidationError(atom) === null;
}
