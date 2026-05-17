/**
 * Pure helpers for canonical Punkto ID handling.
 * Canonical external form: p:<id>
 */

const BARE_ID_RE = /^[0-9a-z]{12}(?:-[a-zA-Z0-9]+)?$/;

export function stripPunktoPrefix(value) {
  return String(value || '').trim().replace(/^p:/i, '');
}

export function ensurePunktoPrefix(value) {
  const bare = stripPunktoPrefix(value);
  return bare ? `p:${bare}` : '';
}

export function isPunktoId(value) {
  const bare = stripPunktoPrefix(value);
  return BARE_ID_RE.test(bare);
}

export function normalizePunktoId(value) {
  const bare = stripPunktoPrefix(value).toLowerCase();
  return BARE_ID_RE.test(bare) ? bare : null;
}

export function parseDeepLinkPunktoId(pathname) {
  const path = String(pathname || '').trim();
  const m = /^\/p\/([^/]+)\/?$/.exec(path);
  if (!m) return null;
  return normalizePunktoId(m[1]);
}
