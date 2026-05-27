/**
 * ui-text.js — Punkto PWA Text feed + board-detail view
 */

import { stripPunktoPrefix } from './protocol/punkto-id.js';

let _onShowOnMap = null;
let _onLeaveNote = null;
let _onOpenBoard = null;
let _helpers = null;
let _mainFeedAtoms = [];
let _selectedBoardId = null;
let _selectedBoardAtom = null;

function _escHtml(s) {
  if (_helpers && typeof _helpers.escHtml === 'function') return _helpers.escHtml(s);
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function _extractHttpLinks(text) {
  const source = String(text == null ? `` : text);
  const re = /https?:\/\/[^\s<>"`]+/gi;
  const found = [];
  const seen = new Set();
  let match;
  while ((match = re.exec(source))) {
    let url = match[0];
    while (/[),.!?:;]$/.test(url)) url = url.slice(0, -1);
    if (!url || seen.has(url)) continue;
    seen.add(url);
    found.push({ url });
  }
  return found;
}
function _safeDomainLabel(rawUrl) { try { return new URL(rawUrl).hostname || rawUrl; } catch { return rawUrl; } }
function _shortUrlLabel(rawUrl) { return rawUrl.length <= 72 ? rawUrl : rawUrl.slice(0, 69) + '…'; }
function _buildLinkCards(rawText) {
  const links = _extractHttpLinks(rawText);
  if (!links.length) return '';
  return links.map(({ url }) =>
    `  <div class="main-link-card ui-card">
` +
    `    <div class="main-link-badge ui-badge">External link</div>
` +
    '    <div class="main-link-domain">' + _escHtml(_safeDomainLabel(url)) + `</div>
` +
    '    <div class="main-link-url">' + _escHtml(_shortUrlLabel(url)) + `</div>
` +
    '    <a class="main-link-open ui-btn" href="' + _escHtml(url) + `" target="_blank" rel="noopener noreferrer">Open</a>
` +
    `  </div>
`
  ).join('');
}
function _deriveTitle(a){ return _helpers?.deriveTitle ? _helpers.deriveTitle(a) : 'Untitled note'; }
function _deriveCategory(a){ return _helpers?.deriveCategory ? _helpers.deriveCategory(a) : 'Talk'; }
function _isVerified(a){ return _helpers?.isVerifiedAtom ? _helpers.isVerifiedAtom(a) : Boolean(a?.sig && a?.pubkey); }
function _fmtAltLabel(alt){ return _helpers?.fmtAltitudeLabel ? _helpers.fmtAltitudeLabel(alt) : ''; }
function _fmtDistance(m){ return _helpers?.fmtDistance ? _helpers.fmtDistance(m) : ''; }
function _fmtTime(t){ return _helpers?.fmtTime ? _helpers.fmtTime(t) : ''; }
function _authorLabel(atom){ const a=String(atom?.author||atom?.f||'').trim(); return a?`by ${a}`:'by anonymous'; }
function _trustLabel(atom){ return atom?.sig ? (_isVerified(atom) ? 'Verified' : 'Signed') : 'Unsigned'; }
function _categoryBadge(catRaw){
  const raw=String(catRaw||'').trim().toUpperCase();
  const map={TEXT:{code:'TEXT',label:'Talk',cls:'cat-talk'},TALK:{code:'TEXT',label:'Talk',cls:'cat-talk'},INFO:{code:'INFO',label:'Info',cls:'cat-info'},WARN:{code:'WARN',label:'Warning',cls:'cat-warn'},EMGC:{code:'EMGC',label:'Emergency',cls:'cat-emgc'},EVNT:{code:'EVNT',label:'Event',cls:'cat-evnt'},LOST:{code:'LOST',label:'Lost/Found',cls:'cat-lost'}};
  return map[raw] || map.TEXT;
}

export function initTextView({ onShowOnMap, onLeaveNote, onOpenBoard, helpers } = {}) {
  _onShowOnMap = typeof onShowOnMap === 'function' ? onShowOnMap : null;
  _onLeaveNote = typeof onLeaveNote === 'function' ? onLeaveNote : null;
  _onOpenBoard = typeof onOpenBoard === 'function' ? onOpenBoard : null;
  _helpers = helpers || null;

  const list = document.getElementById('main-feed-list');
  if (list) {
    list.addEventListener('click', (e) => {
      const backBtn = e.target.closest('[data-action="board-back"]');
      if (backBtn) { _selectedBoardId = null; _selectedBoardAtom = null; renderTextFeed({ atoms: _mainFeedAtoms }); return; }

      const openBoardBtn = e.target.closest('[data-action="open-board"]');
      if (openBoardBtn) {
        e.stopPropagation();
        const id = openBoardBtn.dataset.id || '';
        if (id) openBoardById(id);
        return;
      }

      const copyBtn = e.target.closest('[data-action="copy-board-link"]');
      if (copyBtn) {
        e.stopPropagation();
        const id = copyBtn.dataset.id || '';
        if (!id) return;
        const origin = window.location.origin || '';
        const link = origin + '/p/' + encodeURIComponent(id);
        navigator.clipboard?.writeText(link).then(() => {
          copyBtn.textContent = 'Copied';
          window.setTimeout(() => { copyBtn.textContent = 'Copy board link'; }, 1400);
        }).catch(() => {
          copyBtn.textContent = 'Copy failed';
          window.setTimeout(() => { copyBtn.textContent = 'Copy board link'; }, 1400);
        });
        return;
      }

      const showBtn = e.target.closest('[data-action="show-in-3d"]');
      if (showBtn) {
        e.stopPropagation();
        const id = showBtn.dataset.id || '';
        if (id && _onShowOnMap) _onShowOnMap(id);
        return;
      }
    });
  }

  document.addEventListener('click', (e) => {
    if (!e.target) return;
    if (e.target.id === 'main-empty-open-map-btn') return _onShowOnMap && _onShowOnMap('');
    if (e.target.id === 'main-empty-leave-btn') return _onLeaveNote && _onLeaveNote();
  });
}

export function openBoardById(id, opts = {}) {
  if (!id) return;
  _selectedBoardId = stripPunktoPrefix(id);
  _selectedBoardAtom = opts && opts.atom ? opts.atom : null;
  if (_onOpenBoard) _onOpenBoard(_selectedBoardId);
  renderTextFeed({ atoms: Array.isArray(opts?.atoms) ? opts.atoms : _mainFeedAtoms });
}

function renderBoardDetail(atom) {
  const cat = _categoryBadge(atom.category || atom.kind || _deriveCategory(atom));
  const raw = String(atom.x || '').trim();
  const title = _escHtml(_deriveTitle(atom));
  const author = String(atom?.author || atom?.f || '').trim();
  const trust = _trustLabel(atom);
  const altLabel = Number.isFinite(Number(atom.alt)) ? _fmtAltLabel(Number(atom.alt)) : '';
  const dist = Number.isFinite(atom.distance) ? _fmtDistance(atom.distance) : '';
  const time = atom.t ? _fmtTime(atom.t) : '';
  const floorMeta = altLabel || 'Floor not available';
  const distanceMeta = dist || 'Distance not available';
  const timeMeta = time || 'Time unavailable';
  const meta = [timeMeta, floorMeta, distanceMeta].filter(Boolean).join(' · ');
  const atomId = stripPunktoPrefix(atom.punkto || _selectedBoardId || '');
  const trustLine = author ? `${trust} by ${author}` : `${trust} public post`;
  const publicLine = trust === 'Unsigned' ? 'Unsigned public post' : 'Public board';
  // Future: reply threads may include "Reply to unknown atom" when parent is missing.
  const copyLinkBtn = atomId
    ? '<button class="main-card-reply ui-btn" data-action="copy-board-link" data-id="' + _escHtml(atomId) + '">Copy board link</button>'
    : '';
  return `<section class="board-detail ui-board-panel">
` +
    `  <button class="board-back ui-btn" data-action="board-back">← Visible atoms</button>
` +
    `  <div class="main-card ui-card board-root">
` +
    '    <div class="main-card-badges"><span class="main-card-cat ui-badge ' + _escHtml(cat.cls) + '">' + _escHtml(cat.code) + ' · ' + _escHtml(cat.label) + '</span><span class="main-card-type ui-badge">Public board</span></div>
' +
    '    <p class="main-card-disclaimer">Visible in this map view</p>
' +
    '    <h3 class="main-card-title">' + title + `</h3>
` +
    (raw ? '    <p class="main-card-preview board-body">' + _escHtml(raw) + `</p>
` : '') +
    (_buildLinkCards(raw) || '') +
    '    <div class="board-trust-row">' + _escHtml(trustLine) + '</div>
' +
    '    <div class="main-card-meta"><span>' + _escHtml(publicLine) + `</span></div>
` +
    (meta ? '    <div class="main-card-meta"><span>' + _escHtml(meta) + `</span></div>
` : '') +
    '    <div class="main-card-actions"><button class="main-card-show3d ui-btn" data-action="show-in-3d" data-id="' + _escHtml(atomId) + '">Show on map</button>' + copyLinkBtn + `</div>
` +
    `  </div>
` +
    `  <div class="main-card ui-card board-replies">` +
    `<h4>Replies</h4><p>No public replies yet.</p><p>Replies will be public and may be signed.</p></div>
` +
    `  <div class="main-card ui-card board-compose ui-reply-box"><label for="board-reply-placeholder">Reply</label><textarea id="board-reply-placeholder" placeholder="Write a public reply…" disabled></textarea><p>Reply posting is coming soon.</p></div>
` +
    '</section>';
}

export function renderTextFeed({ atoms = [], locationDenied = false, loadingVisibleAtoms = false } = {}) {
  _mainFeedAtoms = Array.isArray(atoms) ? atoms : [];
  const list = document.getElementById('main-feed-list');
  const emptyEl = document.getElementById('main-empty-notes');
  const countEl = document.getElementById('main-atom-count');
  const statusCountEl = document.getElementById('main-status-count');
  const locEl = document.getElementById('main-empty-location');
  if (!list) return;

  if (_selectedBoardId) {
    const atomFromList = _mainFeedAtoms.find((a) => stripPunktoPrefix(a.punkto) === _selectedBoardId);
    const atom = atomFromList || _selectedBoardAtom;
    if (atom) {
      _selectedBoardAtom = atom;
      if (locEl) locEl.style.display = 'none';
      if (emptyEl) emptyEl.style.display = 'none';
      if (countEl) countEl.textContent = loadingVisibleAtoms ? 'Loading visible atoms…' : (_mainFeedAtoms.length + ' public boards in this map view');
      if (statusCountEl) statusCountEl.textContent = loadingVisibleAtoms ? 'Loading visible atoms…' : (_mainFeedAtoms.length + ' visible');
      list.innerHTML = renderBoardDetail(atom);
      return;
    }
    _selectedBoardId = null;
    _selectedBoardAtom = null;
  }

  if (!_mainFeedAtoms.length) {
    list.innerHTML = '';
    if (countEl) countEl.textContent = loadingVisibleAtoms ? 'Loading visible atoms…' : '';
    if (statusCountEl) statusCountEl.textContent = loadingVisibleAtoms ? 'Loading visible atoms…' : '0 visible';
    if (locationDenied || !navigator.geolocation) {
      if (emptyEl) emptyEl.style.display = 'none';
      if (locEl) locEl.style.display = '';
    } else {
      if (emptyEl) emptyEl.style.display = '';
      if (locEl) locEl.style.display = 'none';
    }
    return;
  }

  if (locEl) locEl.style.display = 'none';
  if (emptyEl) emptyEl.style.display = 'none';
  if (countEl) countEl.textContent = loadingVisibleAtoms ? 'Loading visible atoms…' : (_mainFeedAtoms.length + ' public boards in this map view');
  if (statusCountEl) statusCountEl.textContent = loadingVisibleAtoms ? 'Loading visible atoms…' : (_mainFeedAtoms.length + ' visible');

  list.innerHTML = _mainFeedAtoms.map((atom) => {
    const title = _escHtml(_deriveTitle(atom));
    const cat = _categoryBadge(atom.category || atom.kind || _deriveCategory(atom));
    const raw = String(atom.x || '').trim();
    const preview = raw.length > 120 ? raw.slice(0, 120) + '…' : raw;
    const altLabel = Number.isFinite(Number(atom.alt)) ? _fmtAltLabel(Number(atom.alt)) : '';
    const dist = Number.isFinite(atom.distance) ? _fmtDistance(atom.distance) : '';
    const time = atom.t ? _fmtTime(atom.t) : '';
    const floorMeta = altLabel || 'Floor not available';
  const distanceMeta = dist || 'Distance not available';
  const timeMeta = time || 'Time unavailable';
  const meta = [timeMeta, floorMeta, distanceMeta].filter(Boolean).join(' · ');
    const atomId = stripPunktoPrefix(atom.punkto);
    return '<div class="main-card ui-card" data-atom-id="' + _escHtml(atomId) + `">
` +
      '<div class="main-card-badges"><span class="main-card-type ui-badge">Board</span><span class="main-card-cat ui-badge ' + _escHtml(cat.cls) + '">' + _escHtml(cat.code) + ' · ' + _escHtml(cat.label) + `</span></div>
` +
      '<h3 class="main-card-title">' + title + `</h3>
` +
      (preview && _escHtml(preview) !== title ? '<p class="main-card-preview">' + _escHtml(preview) + `</p>
` : '') +
      (meta ? '<div class="main-card-meta"><span>' + _escHtml(meta) + `</span></div>
` : '') +
      '<div class="main-card-footer"><div class="main-card-meta-group"><div class="main-card-meta"><span>' + _escHtml(_authorLabel(atom)) + ' · ' + _escHtml(_trustLabel(atom)) + '</span></div><div class="main-card-meta"><span>0 replies</span></div></div>' +
      '<div class="main-card-actions"><button class="main-card-show3d ui-btn" data-action="open-board" data-id="' + _escHtml(atomId) + '">Open board</button><button class="main-card-reply ui-btn" data-action="show-in-3d" data-id="' + _escHtml(atomId) + '">Show on map</button></div></div></div>';
  }).join(`
`);
}
