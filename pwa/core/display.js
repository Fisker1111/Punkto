/**
 * Pure display/formatting helpers.
 * No DOM, network, or storage dependencies.
 */

export function fmtTime(ms) {
  const t = Number(ms);
  if (!t) return '?';
  const d = new Date(t);
  const now = Date.now();
  const diff = now - t;
  if (diff < 60_000) return 'just now';
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return d.toLocaleDateString();
}

export function fmtRelativeTime(t) {
  const ms = Number(t);
  if (!ms) return '?';
  const diff = Date.now() - ms;
  if (diff < 60_000) return 'just now';
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  if (diff < 604_800_000) return `${Math.floor(diff / 86_400_000)}d ago`;
  if (diff < 2_419_200_000) return `${Math.floor(diff / 604_800_000)}w ago`;
  return fmtTime(ms);
}

export function fmtCoords(lat, lon, alt) {
  const latStr = lat.toFixed(5);
  const lonStr = lon.toFixed(5);
  const altStr = alt != null ? ` · ${Math.round(alt)}m` : '';
  return `${latStr}, ${lonStr}${altStr}`;
}

export function fmtDistance(meters) {
  if (!Number.isFinite(meters)) return '';
  if (meters < 1000) return `${Math.round(meters)} m away`;
  return `${(meters / 1000).toFixed(1)} km away`;
}

export function fmtAltitudeLabel(alt) {
  if (!Number.isFinite(alt) || Math.abs(alt) < 1) return '';
  const floor = Math.round(alt / 3);
  if (floor >= 2) return `Floor ${floor}`;
  return `+${Math.round(alt)} m`;
}

export function deriveTitle(atom) {
  const raw = String(atom?.x || '').trim();
  if (!raw) return 'Untitled note';
  const firstLine = raw.split(/\r?\n/).find(Boolean) || raw;
  return firstLine.length > 40 ? `${firstLine.slice(0, 40)}…` : firstLine;
}

export function deriveCategory(atom) {
  const raw = String(atom?.category || atom?.kind || '').trim().toUpperCase();
  const labels = {
    TEXT: 'Talk',
    INFO: 'Info',
    WARN: 'Warning',
    EMGC: 'Emergency',
    EVNT: 'Event',
    LOST: 'Lost/Found',
    GENS: 'Genesis',
    NODE: 'Node',
    BRTH: 'Origin',
  };
  if (labels[raw]) return labels[raw];
  return raw || 'Talk';
}

export function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function renderAtomText(raw) {
  if (!raw) return '';
  let s = escHtml(raw);
  s = s.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  s = s.replace(/\*([^*]+)\*/g, '<i>$1</i>');
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_m, label, url) =>
    `<a href="${url}" target="_blank" rel="noopener noreferrer nofollow">${label}</a>`);
  s = s.replace(/(^|[\s>])((?:https?:\/\/)[^\s<]+)/g, (_m, pre, url) =>
    `${pre}<a href="${url}" target="_blank" rel="noopener noreferrer nofollow">${url}</a>`);
  return s.replace(/\n/g, '<br>');
}
