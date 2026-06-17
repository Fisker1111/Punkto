/**
 * ui-text.js — Punkto PWA Text feed + board-detail view
 */

import { stripPunktoPrefix } from './protocol/punkto-id.js';

let _onShowOnMap = null;
let _onLeaveNote = null;
let _onOpenBoard = null;
let _onPostReply = null;
let _helpers = null;
let _replyStatus = null;
let _replyDraft = '';
let _mainFeedAtoms = [];
let _selectedBoardId = null;
let _selectedBoardAtom = null;
let _activeTab = 'visible';
let _boardReturnTab = 'visible';

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
    `    <div class="main-link-domain">${_escHtml(_safeDomainLabel(url))}</div>
` +
    `    <div class="main-link-url">${_escHtml(_shortUrlLabel(url))}</div>
` +
    `    <a class="main-link-open ui-btn" href="${_escHtml(url)}" target="_blank" rel="noopener noreferrer">Open</a>
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
export function getAtomStableId(atom) {
  return String(atom?.atom_id || atom?.id || stripPunktoPrefix(atom?.punkto || '') || '').trim();
}
export function isReplyAtom(atom) {
  return String(atom?.relation || '').toLowerCase() === 'reply' || Boolean(atom?.parent_id);
}
export function isRootAtom(atom) {
  return !isReplyAtom(atom);
}
function _atomStableId(atom) { return getAtomStableId(atom); }
function _isReplyAtom(atom) { return isReplyAtom(atom); }
function _isRootAtom(atom) { return isRootAtom(atom); }
function _normalizedAtomIds(atom) {
  return [atom?.atom_id, atom?.id, atom?.punkto, stripPunktoPrefix(atom?.punkto || '')]
    .map((value) => String(value || '').trim())
    .filter(Boolean);
}
function _replyParentIds(atom) {
  return [atom?.parent_id, atom?.root_id]
    .map((value) => String(value || '').trim())
    .filter(Boolean);
}
function _replyBelongsToRoot(reply, root) {
  if (!_isReplyAtom(reply) || !root) return false;
  const rootIds = new Set(_normalizedAtomIds(root));
  return _replyParentIds(reply).some((id) => rootIds.has(id) || rootIds.has(stripPunktoPrefix(id)));
}
function _findRootForReply(reply, atoms) {
  if (!_isReplyAtom(reply)) return null;
  const list = Array.isArray(atoms) ? atoms : [];
  return list.find((atom) => _isRootAtom(atom) && _replyBelongsToRoot(reply, atom)) || null;
}
function _boardReplies(root, atoms) {
  return (Array.isArray(atoms) ? atoms : [])
    .filter((a) => a !== root && _replyBelongsToRoot(a, root))
    .sort((a, b) => _activityTimestamp(a) - _activityTimestamp(b));
}
function _replyCount(root, atoms) { return _boardReplies(root, atoms).length; }
function _shortId(id) {
  const value = String(id || '').trim();
  if (!value) return 'unknown';
  return value.length > 18 ? value.slice(0, 10) + '…' + value.slice(-6) : value;
}
function _authorLabel(atom){ const a=String(atom?.author||atom?.f||'').trim(); return a?`by ${a}`:'by anonymous'; }
function _trustLabel(atom){ return atom?.sig ? (_isVerified(atom) ? 'Verified' : 'Signed') : 'Unsigned'; }
function _categoryBadge(catRaw){
  const raw=String(catRaw||'').trim().toUpperCase();
  const map={TEXT:{code:'TEXT',label:'Talk',cls:'cat-talk'},TALK:{code:'TEXT',label:'Talk',cls:'cat-talk'},INFO:{code:'INFO',label:'Info',cls:'cat-info'},WARN:{code:'WARN',label:'Warning',cls:'cat-warn'},EMGC:{code:'EMGC',label:'Emergency',cls:'cat-emgc'},EVNT:{code:'EVNT',label:'Event',cls:'cat-evnt'},LOST:{code:'LOST',label:'Lost/Found',cls:'cat-lost'}};
  return map[raw] || map.TEXT;
}
function _isImportedSourceAtom(atom) {
  return atom?.imported === true || Boolean(String(atom?.import_source || '').trim());
}
function _importedSourceBadge(atom) {
  return _isImportedSourceAtom(atom) ? '<span class="main-card-source-badge ui-badge">Imported source</span>' : '';
}
function _importedSourceLine(atom) {
  if (!_isImportedSourceAtom(atom)) return '';
  const sourceName = String(atom?.source_name || atom?.source || '').trim();
  const station = String(atom?.source_station_name || '').trim();
  const stationId = String(atom?.source_station_id || '').trim();
  const details = [sourceName || 'Source data', [station, stationId].filter(Boolean).join(' ')].filter(Boolean);
  return `Imported source data · ${details.join(' · ')}`;
}

export function initTextView({ onShowOnMap, onLeaveNote, onOpenBoard, onPostReply, helpers } = {}) {
  _onShowOnMap = typeof onShowOnMap === 'function' ? onShowOnMap : null;
  _onLeaveNote = typeof onLeaveNote === 'function' ? onLeaveNote : null;
  _onOpenBoard = typeof onOpenBoard === 'function' ? onOpenBoard : null;
  _onPostReply = typeof onPostReply === 'function' ? onPostReply : null;
  _helpers = helpers || null;

  _syncTabUi();
  const list = document.getElementById('main-feed-list');
  if (list) {
    list.addEventListener('click', (e) => {
      const backBtn = e.target.closest('[data-action="board-back"]');
      if (backBtn) { _selectedBoardId = null; _selectedBoardAtom = null; _activeTab = _boardReturnTab || 'visible'; _syncTabUi(); renderTextFeed({ atoms: _mainFeedAtoms }); return; }


      const tabBtn = e.target.closest('[data-action="text-tab"]');
      if (tabBtn) {
        const tab = tabBtn.dataset.tab === 'activity' ? 'activity' : 'visible';
        _activeTab = tab;
        _syncTabUi();
        renderTextFeed({ atoms: _mainFeedAtoms });
        return;
      }

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

      const postReplyBtn = e.target.closest('[data-action="post-board-reply"]');
      if (postReplyBtn) {
        e.preventDefault();
        e.stopPropagation();
        submitBoardReply();
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

  list?.addEventListener('submit', (e) => {
    const form = e.target.closest('[data-action="board-reply-form"]');
    if (!form) return;
    e.preventDefault();
    submitBoardReply();
  });

  document.addEventListener('click', (e) => {
    if (!e.target) return;
    if (e.target.id === 'main-empty-open-map-btn') return _onShowOnMap && _onShowOnMap('');
    if (e.target.id === 'main-empty-leave-btn') return _onLeaveNote && _onLeaveNote();
  });
}

export function openBoardById(id, opts = {}) {
  if (!id) return;
  const atoms = Array.isArray(opts?.atoms) ? opts.atoms : _mainFeedAtoms;
  let targetId = stripPunktoPrefix(id);
  let targetAtom = opts && opts.atom ? opts.atom : null;
  if (!targetAtom) {
    targetAtom = atoms.find((atom) => _normalizedAtomIds(atom).includes(id) || _normalizedAtomIds(atom).includes(targetId)) || null;
  }
  if (_isReplyAtom(targetAtom)) {
    const root = _findRootForReply(targetAtom, atoms);
    if (root) {
      targetAtom = root;
      targetId = _atomStableId(root) || stripPunktoPrefix(root.punkto || '');
    } else {
      targetId = _atomStableId(targetAtom) || targetId;
    }
  }
  _boardReturnTab = _activeTab;
  _selectedBoardId = targetId;
  _selectedBoardAtom = targetAtom;
  _replyStatus = null;
  _replyDraft = '';
  if (_onOpenBoard) _onOpenBoard(_selectedBoardId);
  renderTextFeed({ atoms });
}

function _activityTimestamp(atom) {
  return Number(atom?.updated_at || atom?.updatedAt || atom?.created_at || atom?.createdAt || atom?.t || 0) || 0;
}

function _atomsForActiveTab(atoms) {
  const list = Array.isArray(atoms) ? atoms.slice() : [];
  if (_activeTab === 'activity') {
    return list.sort((a, b) => _activityTimestamp(b) - _activityTimestamp(a));
  }
  return list;
}

function _syncTabUi() {
  const buttons = document.querySelectorAll('[data-action="text-tab"]');
  buttons.forEach((btn) => {
    const tab = btn.dataset.tab === 'activity' ? 'activity' : 'visible';
    btn.classList.toggle('active', tab === _activeTab);
    btn.setAttribute('aria-selected', tab === _activeTab ? 'true' : 'false');
  });
}


async function submitBoardReply() {
  const textarea = document.getElementById('board-reply-text');
  const statusEl = document.getElementById('board-reply-status');
  const button = document.getElementById('board-reply-submit');
  const text = String(textarea?.value || '').trim();
  if (!text || !_selectedBoardAtom || !_onPostReply) return;
  if (statusEl) statusEl.textContent = '';
  if (button) button.disabled = true;
  try {
    await _onPostReply({ boardAtom: _selectedBoardAtom, text });
    _replyDraft = '';
    if (textarea) textarea.value = '';
    _replyStatus = { type: 'success', message: 'Public reply posted.' };
  } catch (err) {
    _replyDraft = text;
    _replyStatus = { type: 'error', message: err?.message || 'Could not post public reply.' };
  } finally {
    if (button) button.disabled = false;
    renderTextFeed({ atoms: _mainFeedAtoms });
  }
}

function renderReplyList(root, replies) {
  if (!replies.length) return '<p>No public replies yet.</p>';
  return '<div class="board-reply-list">' + replies.map((reply) => {
    const cat = _categoryBadge(reply.category || reply.kind || _deriveCategory(reply));
    const raw = String(reply.x || '').trim();
    const author = _authorLabel(reply);
    const time = reply.t ? _fmtTime(reply.t) : 'Time unavailable';
    const trust = _trustLabel(reply);
    const replyId = _atomStableId(reply);
    return `<article class="board-reply-item" data-reply-id="${_escHtml(replyId)}">
` +
      `  <div class="main-card-badges"><span class="main-card-cat ui-badge ${_escHtml(cat.cls)}">${_escHtml(cat.code)} · ${_escHtml(cat.label)}</span><span class="main-card-type ui-badge">Public reply</span></div>
` +
      (raw ? `  <p class="main-card-preview board-body">${_escHtml(raw)}</p>
` : '') +
      `  <div class="main-card-meta"><span>${_escHtml(author)} · ${_escHtml(time)} · ${_escHtml(trust)}</span></div>
` +
      `</article>`;
  }).join('') + '</div>';
}

function renderOrphanReplyDetail(reply) {
  const raw = String(reply?.x || '').trim();
  const cat = _categoryBadge(reply?.category || reply?.kind || _deriveCategory(reply));
  const author = _authorLabel(reply);
  const time = reply?.t ? _fmtTime(reply.t) : 'Time unavailable';
  const trust = _trustLabel(reply);
  const parentId = String(reply?.parent_id || reply?.root_id || '').trim();
  const atomId = stripPunktoPrefix(reply?.punkto || '');
  const backLabel = _boardReturnTab === 'activity' ? '← Back to Activity' : '← Visible here';
  return `<section class="board-detail ui-board-panel">
` +
    `  <button class="board-back ui-btn" data-action="board-back">${_escHtml(backLabel)}</button>
` +
    `  <div class="main-card ui-card board-root">
` +
    `    <div class="main-card-badges"><span class="main-card-cat ui-badge ${_escHtml(cat.cls)}">${_escHtml(cat.code)} · ${_escHtml(cat.label)}</span><span class="main-card-type ui-badge">Reply activity</span></div>
` +
    `    <h3 class="main-card-title">Reply to unknown board</h3>
` +
    `    <p class="main-card-disclaimer">The parent board is not available locally yet.</p>
` +
    (parentId ? `    <div class="main-card-meta"><span>Parent ${_escHtml(_shortId(parentId))}</span></div>
` : '') +
    (raw ? `    <p class="main-card-preview board-body">${_escHtml(raw)}</p>
` : '') +
    `    <div class="main-card-meta"><span>${_escHtml(author)} · ${_escHtml(time)} · ${_escHtml(trust)}</span></div>
` +
    `    <div class="main-card-actions"><button class="main-card-show3d ui-btn" data-action="show-in-3d" data-id="${_escHtml(atomId)}">Show in map</button></div>
` +
    `  </div>
` +
    `</section>`;
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
  const stableId = _atomStableId(atom);
  const replies = _boardReplies(atom, _mainFeedAtoms);
  const canReply = Boolean(stableId);
  const replyValue = _replyStatus?.type === 'error' ? _replyDraft : '';
  const replyStatus = _replyStatus ? `<p id="board-reply-status" class="board-reply-status ${_replyStatus.type === 'error' ? 'error' : 'success'}">${_escHtml(_replyStatus.message)}</p>` : '<p id="board-reply-status" class="board-reply-status"></p>';
  const disabledAttr = canReply ? '' : ' disabled';
  const orphanText = canReply ? '' : '<p class="board-reply-status error">Cannot reply: board id is missing.</p>';
  const trustLine = author ? `${trust} by ${author}` : `${trust} public post`;
  const importedLine = _importedSourceLine(atom);
  const publicLine = importedLine || (trust === 'Unsigned' ? 'Unsigned public post' : 'Public board');
  const sourceBadge = _importedSourceBadge(atom);
  // Future: reply threads may include "Reply to unknown atom" when parent is missing.
  const copyLinkBtn = atomId
    ? '<button class="main-card-reply ui-btn" data-action="copy-board-link" data-id="' + _escHtml(atomId) + '">Copy board link</button>'
    : '';
  const backLabel = _boardReturnTab === 'activity' ? '← Back to Activity' : '← Visible here';
  return `<section class="board-detail ui-board-panel">
` +
    `  <button class="board-back ui-btn" data-action="board-back">${_escHtml(backLabel)}</button>
` +
    `  <div class="main-card ui-card board-root${_isImportedSourceAtom(atom) ? ' main-card--imported-source' : ''}">
` +
    `    <div class="main-card-badges"><span class="main-card-cat ui-badge ${_escHtml(cat.cls)}">${_escHtml(cat.code)} · ${_escHtml(cat.label)}</span><span class="main-card-type ui-badge">Public board</span>${sourceBadge}</div>
` +
    `    <p class="main-card-disclaimer">${_escHtml(importedLine ? 'Imported source data; not user-created content.' : 'Visible in this map view')}</p>
` +
    `    <h3 class="main-card-title">${title}</h3>
` +
    (raw ? `    <p class="main-card-preview board-body">${_escHtml(raw)}</p>
` : '') +
    (_buildLinkCards(raw) || '') +
    `    <div class="board-trust-row">${_escHtml(trustLine)}</div>
` +
    `    <div class="main-card-meta"><span>${_escHtml(publicLine)}</span></div>
` +
    (meta ? `    <div class="main-card-meta"><span>${_escHtml(meta)}</span></div>
` : '') +
    `    <div class="main-card-actions"><button class="main-card-show3d ui-btn" data-action="show-in-3d" data-id="${_escHtml(atomId)}">Show on map</button>${copyLinkBtn}</div>
` +
    `  </div>
` +
    `  <div class="main-card ui-card board-replies">` +
    `<h4>Replies · ${replies.length}</h4>${renderReplyList(atom, replies)}</div>
` +
    `  <form class="main-card ui-card board-compose ui-reply-box" data-action="board-reply-form"><label for="board-reply-text">Public reply</label><textarea id="board-reply-text" placeholder="Write a public reply…"${disabledAttr}>${_escHtml(replyValue)}</textarea><p>Replies are public and anchored to this board’s exact location.</p>${orphanText}${replyStatus}<button class="main-card-show3d ui-btn" id="board-reply-submit" type="submit" data-action="post-board-reply"${disabledAttr}>Post public reply</button></form>
` +
    `</section>`;
}

export function renderTextFeed({ atoms = [], locationDenied = false, loadingVisibleAtoms = false } = {}) {
  _mainFeedAtoms = Array.isArray(atoms) ? atoms : [];
  const activeAtoms = _atomsForActiveTab(_mainFeedAtoms).filter((atom) => _activeTab === 'activity' || !_isReplyAtom(atom));
  _syncTabUi();
  const list = document.getElementById('main-feed-list');
  const emptyEl = document.getElementById('main-empty-notes');
  const countEl = document.getElementById('main-atom-count');
  const statusCountEl = document.getElementById('main-status-count');
  const locEl = document.getElementById('main-empty-location');
  if (!list) return;

  if (_selectedBoardId) {
    const atomFromList = _mainFeedAtoms.find((a) => _normalizedAtomIds(a).includes(_selectedBoardId) || _normalizedAtomIds(a).includes('p:' + _selectedBoardId));
    let atom = atomFromList || _selectedBoardAtom;
    const rootForReply = _isReplyAtom(atom) ? _findRootForReply(atom, _mainFeedAtoms) : null;
    if (rootForReply) {
      atom = rootForReply;
      _selectedBoardId = _atomStableId(rootForReply) || stripPunktoPrefix(rootForReply.punkto || '');
    }
    if (atom) {
      _selectedBoardAtom = atom;
      if (locEl) locEl.style.display = 'none';
      if (emptyEl) emptyEl.style.display = 'none';
      const rootCount = _mainFeedAtoms.filter(_isRootAtom).length;
      if (countEl) countEl.textContent = loadingVisibleAtoms ? 'Loading visible atoms…' : (rootCount + ' public boards');
      if (statusCountEl) statusCountEl.textContent = loadingVisibleAtoms ? 'Loading visible atoms…' : (rootCount + ' visible');
      list.innerHTML = _isReplyAtom(atom) ? renderOrphanReplyDetail(atom) : renderBoardDetail(atom);
      return;
    }
    _selectedBoardId = null;
    _selectedBoardAtom = null;
  }

  if (!activeAtoms.length) {
    list.innerHTML = '';
    if (countEl) countEl.textContent = loadingVisibleAtoms ? 'Loading visible atoms…' : '';
    const headingEl = document.getElementById('main-feed-heading');
    const subtitleEl = document.getElementById('main-feed-subtitle');
    if (headingEl) headingEl.textContent = _activeTab === 'activity' ? 'Activity' : 'Visible here';
    if (subtitleEl) subtitleEl.textContent = _activeTab === 'activity' ? 'Newest public roots and replies in this map view.' : 'Public boards in this map view.';
    if (statusCountEl) statusCountEl.textContent = loadingVisibleAtoms ? 'Loading visible atoms…' : '0 visible';
    if (locationDenied || !navigator.geolocation) {
      if (emptyEl) emptyEl.style.display = 'none';
      if (locEl) locEl.style.display = '';
    } else {
      if (emptyEl) {
        emptyEl.style.display = '';
        const h = emptyEl.querySelector('h3');
        const p = emptyEl.querySelector('p');
        if (_activeTab === 'activity') {
          if (h) h.textContent = 'No activity visible here yet.';
          if (p) p.textContent = 'Newest public activity in this map view will appear here.';
        } else {
          if (h) h.textContent = 'No public boards visible here.';
          if (p) p.textContent = 'Move the map or tap + to start one.';
        }
      }
      if (locEl) locEl.style.display = 'none';
    }
    return;
  }

  if (locEl) locEl.style.display = 'none';
  if (emptyEl) emptyEl.style.display = 'none';
  if (countEl) countEl.textContent = loadingVisibleAtoms ? 'Loading visible atoms…' : (activeAtoms.length + (_activeTab === 'activity' ? ' public activity items' : ' public boards'));
  if (statusCountEl) statusCountEl.textContent = loadingVisibleAtoms ? 'Loading visible atoms…' : (activeAtoms.length + (_activeTab === 'activity' ? ' activity' : ' visible'));

  const headingEl = document.getElementById('main-feed-heading');
  const subtitleEl = document.getElementById('main-feed-subtitle');
  if (headingEl) headingEl.textContent = _activeTab === 'activity' ? 'Activity' : 'Visible here';
  if (subtitleEl) subtitleEl.textContent = _activeTab === 'activity' ? 'Newest public roots and replies in this map view.' : 'Public boards in this map view.';

  list.innerHTML = activeAtoms.map((atom) => {
    const isReply = _isReplyAtom(atom);
    const root = isReply ? _findRootForReply(atom, _mainFeedAtoms) : null;
    const title = isReply
      ? _escHtml(root ? 'Reply in board' : 'Reply to unknown board')
      : _escHtml(_deriveTitle(atom));
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
    const stableId = _atomStableId(atom) || atomId;
    const rootTitle = root ? _deriveTitle(root) : '';
    const replyContext = isReply
      ? '<div class="main-card-meta"><span>' + _escHtml(rootTitle ? ('Reply to board: ' + rootTitle) : 'Reply to unknown board') + '</span></div>'
      : '';
    const replyCount = isReply ? '' : '<div class="main-card-meta"><span>' + _replyCount(atom, _mainFeedAtoms) + ' replies</span></div>';
    const importedLine = _importedSourceLine(atom);
    const importedMeta = importedLine ? '<div class="main-card-meta main-card-source-line"><span>' + _escHtml(importedLine) + '</span></div>' : '';
    return '<div class="main-card ui-card' + (_isImportedSourceAtom(atom) ? ' main-card--imported-source' : '') + '" data-atom-id="' + _escHtml(stableId) + `">
` +
      '<div class="main-card-badges"><span class="main-card-type ui-badge">' + (isReply ? 'Reply activity' : 'Board') + '</span><span class="main-card-cat ui-badge ' + _escHtml(cat.cls) + '">' + _escHtml(cat.code) + ' · ' + _escHtml(cat.label) + '</span>' + _importedSourceBadge(atom) + `</div>
` +
      '<h3 class="main-card-title">' + title + `</h3>
` +
      replyContext +
      (preview ? '<p class="main-card-preview">' + _escHtml(preview) + `</p>
` : '') +
      importedMeta +
      (meta ? '<div class="main-card-meta"><span>' + _escHtml(meta) + `</span></div>
` : '') +
      '<div class="main-card-footer"><div class="main-card-meta-group"><div class="main-card-meta"><span>' + _escHtml(_authorLabel(atom)) + ' · ' + _escHtml(_trustLabel(atom)) + '</span></div>' + replyCount + '</div>' +
      '<div class="main-card-actions"><button class="main-card-show3d ui-btn" data-action="open-board" data-id="' + _escHtml(stableId) + '">Open board</button><button class="main-card-reply ui-btn" data-action="show-in-3d" data-id="' + _escHtml(atomId) + '">Show on map</button></div></div></div>';
  }).join(`
`);
}
