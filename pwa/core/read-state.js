import { escHtml, fmtCoords } from './display.js';

export function trustLabel(atom) {
  if (atom?.verification_state) return atom.verification_state === 'VALID' ? 'Verified signature' : 'Signature not verified';
  return atom?.sig ? 'Signed' : 'Unsigned';
}

export function heightLabel(atom) {
  const z = atom?.ellipsoidal_z ?? atom?.alt;
  const height = z != null && Number.isFinite(Number(z)) ? `${z} m absolute WGS84 ellipsoidal height` : 'Height unavailable';
  return atom?.floor != null && String(atom.floor).trim() ? `Floor ${atom.floor} · ${height}` : height;
}

export function placeHtml(atom) {
  const coords = Number.isFinite(atom?.lat) && Number.isFinite(atom?.lon) ? fmtCoords(atom.lat, atom.lon, null) : 'Coordinates unavailable';
  return `<div class="board-place">Exact address: ${escHtml(atom?.h || 'unavailable')}<br>${escHtml(coords)}<br>${escHtml(heightLabel(atom))}</div>`;
}

export function isQaRecord(atom) {
  // Explicit operator acceptance markers from the publication, never fuzzy keywords.
  let payload;
  try { payload = JSON.parse(atom?.x_payload ?? atom?.x); } catch {}
  return Boolean(payload && typeof payload === 'object' && ('run' in payload || 'case_record' in payload)) || /\bCEO-OS\b/.test(String(atom?.x || ''));
}

export function readStateHtml({ loading = false, error = false } = {}) {
  if (loading) return '<p role="status">Loading published text…</p>';
  if (error) return '<p role="alert">Could not load published text. You can try again.</p><button class="ui-btn" data-action="retry-read">Retry</button>';
  return '';
}
