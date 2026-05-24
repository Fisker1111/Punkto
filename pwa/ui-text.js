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

function _escHtml(s) {
  if (_helpers && typeof _helpers.escHtml === 'function') return _helpers.escHtml(s);
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function _extractHttpLinks(text) {
  const source = String(text == null ? '' : text);
  const re = /https?:\/\/[^\s<>"']+/gi;
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
    '  <div class="main-link-card">
' +
    '    <div class="main-link-badge">External link</div>
' +
    '    <div class="main-link-domain">' + _escHtml(_safeDomainLabel(url)) + '</div>
' +
    '    <div class="main-link-url">' + _escHtml(_shortUrlLabel(url)) + '</div>
' +
    '    <a class="main-link-open" href="' + _escHtml(url) + '" target="_blank" rel="noopener noreferrer">Open</a>
' +
    '  </div>
'
  ).join('');
}
function _deriveTitle(a){ return _helpers?.deriveTitle ? _helpers.deriveTitle(a) : 'Untitled note'; }
function _deriveCategory(a){ return _helpers?.deriveCategory ? _helpers.deriveCategory(a) : 'Talk'; }
function _isVerified(a){ return _helpers?.isVerifiedAtom ? _helpers.isVerifiedAtom(a) : Boolean(a?.sig && a?.pubkey); }
function _fmtAltLabel(alt){ return _helpers?.fmtAltitudeLabel ? _helpers.fmtAltitudeLabel(alt) : ''; }
function _fmtDistance(m){ return _helpers?.fmtDistance ? _helpers.fmtDistance(m) : ''; }
function _fmtTime(t){ return _helpers?.fmtTime ? _helpers.fmtTime(t) : ''; }
function _authorLabel(atom){ const a=String(atom?.author||atom?.f||'').trim(); return a?`by ${a}`:'by anonymous'; }
function _trustLabel(atom){ return atom?.sig ? (_isVerified(atom) ? 'verified' : 'signed') : 'unsigned'; }
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
      if (backBtn) { _selectedBoardId = null; renderTextFeed({ atoms: _mainFeedAtoms }); return; }

      const openBoardBtn = e.target.closest('[data-action="open-board"]');
      if (openBoardBtn) {
        e.stopPropagation();
        const id = openBoardBtn.dataset.id || '';
        if (id) openBoardById(id);
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

export function openBoardById(id) {
  if (!id) return;
  _selectedBoardId = stripPunktoPrefix(id);
  if (_onOpenBoard) _onOpenBoard(_selectedBoardId);
  renderTextFeed({ atoms: _mainFeedAtoms });
}

function renderBoardDetail(atom) {
  const cat = _categoryBadge(atom.category || atom.kind || _deriveCategory(atom));
  const raw = String(atom.x || '').trim();
  const title = _escHtml(_deriveTitle(atom));
  const author = _authorLabel(atom);
  const trust = _trustLabel(atom);
  const altLabel = Number.isFinite(Number(atom.alt)) ? _fmtAltLabel(Number(atom.alt)) : '';
  const dist = Number.isFinite(atom.distance) ? _fmtDistance(atom.distance) : '';
  const time = atom.t ? _fmtTime(atom.t) : '';
  const meta = [dist, altLabel, time].filter(Boolean).join(' · ');
  const atomId = stripPunktoPrefix(atom.punkto || _selectedBoardId || '');
  return '<section class="board-detail">
' +
    '  <button class="board-back" data-action="board-back">← Visible atoms</button>
' +
    '  <div class="main-card board-root">
' +
    '    <div class="main-card-badges"><span class="main-card-type">Board</span><span class="main-card-cat ' + _escHtml(cat.cls) + '">' + _escHtml(cat.code) + ' · ' + _escHtml(cat.label) + '</span></div>
' +
    '    <h3 class="main-card-title">' + title + '</h3>
' +
    (raw ? '    <p class="main-card-preview board-body">' + _escHtml(raw) + '</p>
' : '') +
    (_buildLinkCards(raw) || '') +
    (meta ? '    <div class="main-card-meta"><span>' + _escHtml(meta) + '</span></div>
' : '') +
    '    <div class="main-card-meta"><span>' + _escHtml(author) + ' · ' + _escHtml(trust) + '</span></div>
' +
    '    <div class="main-card-actions"><button class="main-card-show3d" data-action="show-in-3d" data-id="' + _escHtml(atomId) + '">Show on map</button></div>
' +
    '  </div>
' +
    '  <div class="main-card board-replies"><h4>Replies</h4><p>No replies loaded yet.</p></div>
' +
    '  <div class="main-card board-compose"><label for="board-reply-placeholder">Public reply</label><textarea id="board-reply-placeholder" placeholder="Write a public reply…" disabled></textarea><p>Replies will be public and may be signed.</p></div>
' +
    '</section>';
}

export function renderTextFeed({ atoms = [], locationDenied = false } = {}) {
  _mainFeedAtoms = Array.isArray(atoms) ? atoms : [];
  const list = document.getElementById('main-feed-list');
  const emptyEl = document.getElementById('main-empty-notes');
  const countEl = document.getElementById('main-atom-count');
  const statusCountEl = document.getElementById('main-status-count');
  const locEl = document.getElementById('main-empty-location');
  if (!list) return;

  if (_selectedBoardId) {
    const atom = _mainFeedAtoms.find((a) => stripPunktoPrefix(a.punkto) === _selectedBoardId);
    if (atom) {
      if (locEl) locEl.style.display = 'none';
      if (emptyEl) emptyEl.style.display = 'none';
      if (countEl) countEl.textContent = _mainFeedAtoms.length + ' nearby';
      if (statusCountEl) statusCountEl.textContent = _mainFeedAtoms.length + ' nearby';
      list.innerHTML = renderBoardDetail(atom);
      return;
    }
    _selectedBoardId = null;
  }

  if (!_mainFeedAtoms.length) {
    list.innerHTML = '';
    if (countEl) countEl.textContent = '';
    if (statusCountEl) statusCountEl.textContent = '0 nearby';
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
  if (countEl) countEl.textContent = _mainFeedAtoms.length + ' nearby';
  if (statusCountEl) statusCountEl.textContent = _mainFeedAtoms.length + ' nearby';

  list.innerHTML = _mainFeedAtoms.map((atom) => {
    const title = _escHtml(_deriveTitle(atom));
    const cat = _categoryBadge(atom.category || atom.kind || _deriveCategory(atom));
    const raw = String(atom.x || '').trim();
    const preview = raw.length > 120 ? raw.slice(0, 120) + '…' : raw;
    const linkCards = _buildLinkCards(raw);
    const altLabel = Number.isFinite(Number(atom.alt)) ? _fmtAltLabel(Number(atom.alt)) : '';
    const dist = Number.isFinite(atom.distance) ? _fmtDistance(atom.distance) : '';
    const time = atom.t ? _fmtTime(atom.t) : '';
    const meta = [dist, altLabel, time].filter(Boolean).join(' · ');
    const atomId = stripPunktoPrefix(atom.punkto);
    return '<div class="main-card" data-atom-id="' + _escHtml(atomId) + '">
' +
      '<div class="main-card-badges"><span class="main-card-icon">⌁</span><span class="main-card-type">Punkti</span><span class="main-card-cat ' + _escHtml(cat.cls) + '">' + _escHtml(cat.code) + ' · ' + _escHtml(cat.label) + '</span></div>
' +
      '<h3 class="main-card-title">' + title + '</h3>
' +
      (preview && _escHtml(preview) !== title ? '<p class="main-card-preview">' + _escHtml(preview) + '</p>
' : '') +
      (linkCards || '') +
      (meta ? '<div class="main-card-meta"><span>' + _escHtml(meta) + '</span></div>
' : '') +
      '<div class="main-card-footer"><div class="main-card-meta-group"><div class="main-card-meta"><span>' + _escHtml(_authorLabel(atom)) + ' · ' + _escHtml(_trustLabel(atom)) + '</span></div><div class="main-card-meta"><span>0 replies</span></div></div>' +
      '<div class="main-card-actions"><button class="main-card-show3d" data-action="open-board" data-id="' + _escHtml(atomId) + '">Open board</button><button class="main-card-reply" data-action="show-in-3d" data-id="' + _escHtml(atomId) + '">Show on map</button></div></div></div>';
  }).join('
');
}
