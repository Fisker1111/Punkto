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

import { stripPunktoPrefix } from './protocol/punkto-id.js';

let _onShowOnMap = null;
let _onLeaveNote = null;
let _helpers     = null;

let _replyToastTimer = null;

function _showReplyComingSoon() {
  const toast = document.getElementById('reply-soon-toast');
  if (!toast) return;
  toast.style.display = 'flex';
  if (_replyToastTimer) clearTimeout(_replyToastTimer);
  _replyToastTimer = setTimeout(() => {
    toast.style.display = 'none';
    _replyToastTimer = null;
  }, 2400);
}

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
      const replyBtn = e.target.closest('[data-action="reply-placeholder"]');
      if (replyBtn) {
        e.stopPropagation();
        _showReplyComingSoon();
        return;
      }

      const btn = e.target.closest('[data-action="show-in-3d"]');
      if (!btn) return;
      e.stopPropagation();
      const id = btn.dataset.id || '';
      if (id && _onShowOnMap) _onShowOnMap(id);
    });
  }

  // Text empty-state CTAs
  document.addEventListener('click', (e) => {
    if (!e.target) return;
    if (e.target.id === 'main-empty-open-map-btn') {
      if (_onShowOnMap) _onShowOnMap('');
      return;
    }
    if (e.target.id === 'main-empty-leave-btn') {
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


function _extractHttpLinks(text) {
  const source = String(text == null ? '' : text);
  const re = /https?:\/\/[^\s<>"']+/gi;
  const found = [];
  const seen = new Set();
  let match;
  while ((match = re.exec(source))) {
    let url = match[0];
    while (/[),.!?:;]$/.test(url)) {
      url = url.slice(0, -1);
    }
    if (!url || seen.has(url)) continue;
    seen.add(url);
    found.push({ url });
  }
  return found;
}

function _safeDomainLabel(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    return parsed.hostname || rawUrl;
  } catch {
    return rawUrl;
  }
}

function _shortUrlLabel(rawUrl) {
  if (rawUrl.length <= 72) return rawUrl;
  return rawUrl.slice(0, 69) + '…';
}

function _buildLinkCards(rawText) {
  const links = _extractHttpLinks(rawText);
  if (!links.length) return '';
  return links.map(({ url }) => {
    const domain = _safeDomainLabel(url);
    const label = _shortUrlLabel(url);
    return (
      '  <div class="main-link-card">\n' +
      '    <div class="main-link-badge">External link</div>\n' +
      '    <div class="main-link-domain">' + _escHtml(domain) + '</div>\n' +
      '    <div class="main-link-url">' + _escHtml(label) + '</div>\n' +
      '    <a class="main-link-open" href="' + _escHtml(url) + '" target="_blank" rel="noopener noreferrer">Open</a>\n' +
      '  </div>\n'
    );
  }).join('');
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

function _categoryBadge(catRaw) {
  const raw = String(catRaw || '').trim().toUpperCase();
  const map = {
    TALK: { code: 'TEXT', label: 'Talk', cls: 'cat-talk' },
    TEXT: { code: 'TEXT', label: 'Talk', cls: 'cat-talk' },
    INFO: { code: 'INFO', label: 'Info', cls: 'cat-info' },
    WARN: { code: 'WARN', label: 'Warning', cls: 'cat-warn' },
    EMGC: { code: 'EMGC', label: 'Emergency', cls: 'cat-emgc' },
    EVNT: { code: 'EVNT', label: 'Event', cls: 'cat-evnt' },
    LOST: { code: 'LOST', label: 'Lost/Found', cls: 'cat-lost' },
  };
  return map[raw] || { code: 'TEXT', label: 'Talk', cls: 'cat-talk' };
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

function _authorLabel(atom) {
  const author = String(atom?.author || atom?.f || '').trim();
  return author ? `by ${author}` : 'by anonymous';
}

function _trustLabel(atom) {
  const hasSig = Boolean(atom?.sig);
  if (!hasSig) return 'unsigned';
  return _isVerified(atom) ? 'verified' : 'signed';
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
  const statusCountEl = document.getElementById('main-status-count');
  const locEl   = document.getElementById('main-empty-location');
  if (!list) return;

  if (!atoms || atoms.length === 0) {
    list.innerHTML = '';
    if (countEl) countEl.textContent = '';
    if (statusCountEl) statusCountEl.textContent = '0 nearby';
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
  if (statusCountEl) statusCountEl.textContent = atoms.length + ' nearby';

  list.innerHTML = atoms.map((atom) => {
    const title    = _escHtml(_deriveTitle(atom));
    const cat      = _categoryBadge(atom.category || atom.kind || _deriveCategory(atom));
    const raw      = String(atom.x || '').trim();
    const preview  = raw.length > 120 ? raw.slice(0, 120) + '…' : raw;
    const linkCards = _buildLinkCards(raw);
    const altLabel = Number.isFinite(Number(atom.alt)) ? _fmtAltLabel(Number(atom.alt)) : '';
    const dist     = Number.isFinite(atom.distance) ? _fmtDistance(atom.distance) : '';
    const time     = atom.t ? _fmtTime(atom.t) : '';
    const meta     = [dist, altLabel, time].filter(Boolean).join(' · ');
    const atomId   = stripPunktoPrefix(atom.punkto);
    const author   = _authorLabel(atom);
    const trust    = _trustLabel(atom);

    return '<div class="main-card" data-atom-id="' + _escHtml(atomId) + '">\n' +
      '  <div class="main-card-badges">\n' +
      '    <span class="main-card-icon">⌁</span>\n' +
      '    <span class="main-card-type">Punkti</span>\n' +
      '    <span class="main-card-cat ' + _escHtml(cat.cls) + '">' + _escHtml(cat.code) + ' · ' + _escHtml(cat.label) + '</span>\n' +
      '  </div>\n' +
      '  <h3 class="main-card-title">' + title + '</h3>\n' +
      (preview && _escHtml(preview) !== title
        ? '  <p class="main-card-preview">' + _escHtml(preview) + '</p>\n'
        : '') +
      (linkCards || '') +
      (meta ? '  <div class="main-card-meta"><span>' + _escHtml(meta) + '</span></div>\n' : '') +
      '  <div class="main-card-footer">\n' +
      '    <div class="main-card-meta-group">\n' +
      '      <div class="main-card-meta"><span>' + _escHtml(author) + ' · ' + _escHtml(trust) + '</span></div>\n' +
      '      <div class="main-card-meta"><span>0 replies</span></div>\n' +
      '    </div>\n' +
      '    <div class="main-card-actions">\n' +
      '    <button class="main-card-show3d" data-action="show-in-3d" data-id="' + _escHtml(atomId) + '">Open board on map →</button>\n' +
      '    <button class="main-card-reply" data-action="reply-placeholder" data-id="' + _escHtml(atomId) + '">Reply</button>\n' +
      '    </div>\n' +
      '  </div>\n' +
      '</div>';
  }).join('\n');
}
      (cat.code === 'EMGC'
        ? '  <p class="main-card-disclaimer">Public urgent post — not a replacement for calling emergency services.</p>\n'
        : '') +
