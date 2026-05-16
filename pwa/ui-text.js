/**
 * ui-text.js — Punkto PWA Text feed view
 *
 * Owns:
 *  - renderTextFeed({ atoms, locationDenied }) main feed list rendering
 *  - text card markup generation
 *  - empty state logic (no notes vs no location)
 *  - delegation of "Show on map" + "Leave note here" via callbacks
 *
 * The atoms passed in are expected to already be sorted/limited by app.js,
 * and each atom may include a `distance` field (meters).
 */

let _onShowOnMap = null;
let _onLeaveNote = null;
let _helpers     = null;

/**
 * Initialise listeners on the static elements (#main-feed-list,
 * #main-empty-leave-btn, #main-location-btn).
 *
 * @param {Object} opts
 * @param {(id:string)=>void} opts.onShowOnMap
 * @param {()=>void}          opts.onLeaveNote
 * @param {Object}            [opts.helpers] formatting helpers from app.js
 *   { escHtml, deriveTitle, deriveCategory, isVerifiedAtom,
 *     fmtAltitudeLabel, fmtDistance, fmtTime }
 */
export function initTextView({ onShowOnMap, onLeaveNote, helpers } = {}) {
  _onShowOnMap = typeof onShowOnMap === 'function' ? onShowOnMap : null;
  _onLeaveNote = typeof onLeaveNote === 'function' ? onLeaveNote : null;
  _helpers     = helpers || null;

  const list = document.getElementById('main-feed-list');
  if (list) {
    list.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action="show-in-3d"]');
      if (!btn) return;
      e.stopPropagation();
      const id = btn.dataset.id || '';
      if (id && _onShowOnMap) _onShowOnMap(id);
    });
  }

  // "Leave note here" CTA in empty state
  document.addEventListener('click', (e) => {
    if (e.target && e.target.id === 'main-empty-leave-btn') {
      if (_onLeaveNote) _onLeaveNote();
    }
  });
}

function _escHtml(s) {
  if (_helpers && typeof _helpers.escHtml === 'function') return _helpers.escHtml(s);
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function _deriveTitle(a) {
  if (_helpers && typeof _helpers.deriveTitle === 'function') return _helpers.deriveTitle(a);
  const raw = String(a?.x || '').trim();
  if (!raw) return 'Untitled note';
  const first = raw.split(/\r?\n/).find(Boolean) || raw;
  return first.length > 40 ? first.slice(0, 40) + '…' : first;
}

function _deriveCategory(a) {
  if (_helpers && typeof _helpers.deriveCategory === 'function') return _helpers.deriveCategory(a);
  const c = String(a?.category || a?.kind || '').trim();
  return c || 'Note';
}

function _isVerified(a) {
  if (_helpers && typeof _helpers.isVerifiedAtom === 'function') return _helpers.isVerifiedAtom(a);
  return Boolean(a?.sig && a?.pubkey);
}

function _fmtAltLabel(alt) {
  if (_helpers && typeof _helpers.fmtAltitudeLabel === 'function') return _helpers.fmtAltitudeLabel(alt);
  if (!Number.isFinite(alt) || Math.abs(alt) < 1) return '';
  const floor = Math.round(alt / 3);
  if (floor >= 2) return 'Floor ' + floor;
  return '+' + Math.round(alt) + ' m';
}

function _fmtDistance(m) {
  if (_helpers && typeof _helpers.fmtDistance === 'function') return _helpers.fmtDistance(m);
  if (!Number.isFinite(m)) return '';
  if (m < 1000) return Math.round(m) + ' m away';
  return (m / 1000).toFixed(1) + ' km away';
}

function _fmtTime(t) {
  if (_helpers && typeof _helpers.fmtTime === 'function') return _helpers.fmtTime(t);
  const ms = Number(t);
  if (!ms) return '';
  return new Date(ms).toLocaleDateString();
}

/**
 * Render the main text feed.
 * Mirrors the legacy renderMainFeed() output for visual continuity.
 *
 * @param {Object} opts
 * @param {Array}  opts.atoms
 * @param {boolean} opts.locationDenied
 */
export function renderTextFeed({ atoms = [], locationDenied = false } = {}) {
  const list    = document.getElementById('main-feed-list');
  const emptyEl = document.getElementById('main-empty-notes');
  const countEl = document.getElementById('main-atom-count');
  const locEl   = document.getElementById('main-empty-location');
  if (!list) return;

  if (!atoms || atoms.length === 0) {
    list.innerHTML = '';
    if (countEl) countEl.textContent = '';
    if (locationDenied || !navigator.geolocation) {
      if (emptyEl) emptyEl.style.display = 'none';
      if (locEl)   locEl.style.display   = '';
    } else {
      if (emptyEl) emptyEl.style.display = '';
      if (locEl)   locEl.style.display   = 'none';
    }
    return;
  }

  if (locEl)   locEl.style.display   = 'none';
  if (emptyEl) emptyEl.style.display = 'none';
  if (countEl) countEl.textContent  = atoms.length + ' nearby';

  list.innerHTML = atoms.map((atom) => {
    const title    = _escHtml(_deriveTitle(atom));
    const cat      = _deriveCategory(atom);
    const verified = _isVerified(atom);
    const raw      = String(atom.x || '').trim();
    const preview  = raw.length > 120 ? raw.slice(0, 120) + '…' : raw;
    const altLabel = Number.isFinite(Number(atom.alt)) ? _fmtAltLabel(Number(atom.alt)) : '';
    const dist     = Number.isFinite(atom.distance) ? _fmtDistance(atom.distance) : '';
    const time     = atom.t ? _fmtTime(atom.t) : '';
    const meta     = [dist, altLabel, time].filter(Boolean).join(' · ');
    const atomId   = String(atom.punkto || '').replace(/^p:/, '');

    return '<div class="main-card" data-atom-id="' + _escHtml(atomId) + '">\n' +
      '  <div class="main-card-badges">\n' +
      (cat      ? '    <span class="main-card-cat">'      + _escHtml(cat) + '</span>\n' : '') +
      (verified ? '    <span class="main-card-verified">✓ Verified</span>\n' : '') +
      '  </div>\n' +
      '  <h3 class="main-card-title">' + title + '</h3>\n' +
      (preview && _escHtml(preview) !== title
        ? '  <p class="main-card-preview">' + _escHtml(preview) + '</p>\n'
        : '') +
      (meta ? '  <div class="main-card-meta"><span>' + _escHtml(meta) + '</span></div>\n' : '') +
      '  <div class="main-card-actions">\n' +
      '    <button class="main-card-show3d" data-action="show-in-3d" data-id="' + _escHtml(atomId) + '">Show on map →</button>\n' +
      '  </div>\n' +
      '</div>';
  }).join('\n');
}
