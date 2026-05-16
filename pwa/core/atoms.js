/**
 * Pure atom classification/filtering helpers.
 * No DOM, network, or storage dependencies.
 */

const HIDDEN_AUTHOR_HANDLES = new Set([
  'test',
  'sync-test',
  'cors-test',
  'browser-test',
]);

export function isVerifiedAtom(atom) {
  return Boolean(atom?.sig && atom?.pubkey);
}

export function isHiddenAtom(atom) {
  const f = typeof atom?.f === 'string' ? atom.f.trim().toLowerCase() : '';
  if (!f) return false;
  return HIDDEN_AUTHOR_HANDLES.has(f);
}
