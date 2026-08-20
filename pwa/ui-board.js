/**
 * ui-board.js - selected Map board/bottom-sheet UI
 */

import { resolveBoardAtom, renderBoardSheetHtml } from './ui-text.js';

let _sheet = null;
let _getAtoms = () => [];
let _getAtomSelectionId = null;
let _onSelectionChanged = null;
let _onSetPanelOpen = null;
let _onShowMap = null;
let _onRenderMap = null;
let _onSubmitReply = null;
let _onFocusMap = null;

let _selectedAtomId = null;
let _selectedMapAtom = null;
let _selectedBoardAtom = null;
let _selectedBoardAtoms = [];
let _replyStatus = null;
let _replyDraft = '';

export function initBoardView({
  sheet,
  getAtoms,
  getAtomSelectionId,
  onSelectionChanged,
  onSetPanelOpen,
  onShowMap,
  onRenderMap,
  onSubmitReply,
  onFocusMap,
} = {}) {
  _sheet = sheet || document.getElementById('map-board-sheet');
  _getAtoms = typeof getAtoms === 'function' ? getAtoms : _getAtoms;
  _getAtomSelectionId = typeof getAtomSelectionId === 'function' ? getAtomSelectionId : null;
  _onSelectionChanged = typeof onSelectionChanged === 'function' ? onSelectionChanged : null;
  _onSetPanelOpen = typeof onSetPanelOpen === 'function' ? onSetPanelOpen : null;
  _onShowMap = typeof onShowMap === 'function' ? onShowMap : null;
  _onRenderMap = typeof onRenderMap === 'function' ? onRenderMap : null;
  _onSubmitReply = typeof onSubmitReply === 'function' ? onSubmitReply : null;
  _onFocusMap = typeof onFocusMap === 'function' ? onFocusMap : null;

  if (!_sheet || _sheet.dataset.boardViewBound === 'true') return;
  _sheet.dataset.boardViewBound = 'true';
  _sheet.addEventListener('click', handleBoardClick);
  _sheet.addEventListener('submit', handleBoardSubmit);
}

export function getSelectedBoardState() {
  return {
    selectedAtomId: _selectedAtomId,
    selectedMapAtom: _selectedMapAtom,
    selectedBoardAtom: _selectedBoardAtom,
    selectedBoardAtoms: _selectedBoardAtoms,
  };
}

export function hasOpenBoard() {
  return Boolean(_selectedBoardAtom);
}

export function clearBoardSelectionOnly() {
  _selectedAtomId = null;
  _selectedMapAtom = null;
  notifySelection();
}

export function closeMapBoard({ clearSelection = true } = {}) {
  if (_sheet) {
    _sheet.classList.remove('open');
    _sheet.setAttribute('aria-hidden', 'true');
    _sheet.innerHTML = '';
  }
  _selectedBoardAtom = null;
  _selectedBoardAtoms = [];
  _replyStatus = null;
  _replyDraft = '';
  if (clearSelection) {
    _selectedAtomId = null;
    _selectedMapAtom = null;
    notifySelection();
    renderMap().catch((err) => console.warn('[map-board] selection refresh failed:', err));
  }
}

export function renderMapBoardSheet() {
  if (!_sheet || !_selectedBoardAtom) return;
  _sheet.innerHTML = renderBoardSheetHtml({
    atom: _selectedBoardAtom,
    atoms: _selectedBoardAtoms.length ? _selectedBoardAtoms : _getAtoms(),
    replyStatus: _replyStatus,
    replyDraft: _replyDraft,
    backLabel: 'Close board',
    backAction: 'map-board-close',
  });
  _sheet.classList.add('open');
  _sheet.setAttribute('aria-hidden', 'false');
}

export async function openMapBoardForAtom(atom, atoms = _getAtoms()) {
  if (!atom || !atom.punkto || !_getAtomSelectionId) return;
  const localAtoms = Array.isArray(atoms) && atoms.length ? atoms : _getAtoms();
  _selectedMapAtom = atom;
  _selectedAtomId = await _getAtomSelectionId(atom);
  _selectedBoardAtoms = localAtoms;
  _selectedBoardAtom = resolveBoardAtom(atom, _selectedBoardAtoms) || atom;
  _replyStatus = null;
  _replyDraft = '';
  notifySelection();
  if (_onSetPanelOpen) _onSetPanelOpen(false);
  if (_onShowMap) _onShowMap();
  renderMapBoardSheet();
  await renderMap();
}

export async function refreshMapBoardAtoms(atoms = _getAtoms()) {
  if (!_selectedBoardAtom || !_getAtomSelectionId) return;
  const selectedId = _selectedAtomId;
  _selectedBoardAtoms = Array.isArray(atoms) ? atoms : [];
  if (selectedId) {
    const pairs = await Promise.all(_selectedBoardAtoms.map(async (atom) => [atom, await _getAtomSelectionId(atom)]));
    const selectionIds = new Map(pairs);
    const refreshedSelected = _selectedBoardAtoms.find((atom) => selectionIds.get(atom) === selectedId) || _selectedMapAtom;
    _selectedMapAtom = refreshedSelected;
    _selectedBoardAtom = resolveBoardAtom(refreshedSelected, _selectedBoardAtoms) || refreshedSelected || _selectedBoardAtom;
    notifySelection();
  }
  renderMapBoardSheet();
}

function notifySelection() {
  if (_onSelectionChanged) {
    _onSelectionChanged({
      selectedAtomId: _selectedAtomId,
      selectedMapAtom: _selectedMapAtom,
    });
  }
}

async function renderMap() {
  if (_onRenderMap) await _onRenderMap();
}

function handleBoardClick(e) {
  const closeBtn = e.target.closest('[data-action="map-board-close"]');
  if (closeBtn) {
    e.preventDefault();
    closeMapBoard({ clearSelection: true });
    return;
  }

  const copyBtn = e.target.closest('[data-action="copy-board-link"]');
  if (copyBtn) {
    e.preventDefault();
    const id = copyBtn.dataset.id || '';
    if (!id) return;
    const link = (window.location.origin || '') + '/p/' + encodeURIComponent(id);
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
    e.preventDefault();
    const id = showBtn.dataset.id || '';
    if (id && _onFocusMap) _onFocusMap(id);
  }
}

async function handleBoardSubmit(e) {
  const form = e.target.closest('[data-action="board-reply-form"]');
  if (!form || !_selectedBoardAtom || !_onSubmitReply) return;
  e.preventDefault();
  const textarea = form.querySelector('#board-reply-text');
  const button = form.querySelector('#board-reply-submit');
  const text = String(textarea?.value || '').trim();
  if (!text) return;
  if (button) button.disabled = true;
  try {
    await _onSubmitReply({ boardAtom: _selectedBoardAtom, text });
    _replyDraft = '';
    _replyStatus = { type: 'success', message: 'Public reply posted.' };
    if (textarea) textarea.value = '';
  } catch (err) {
    _replyDraft = text;
    _replyStatus = { type: 'error', message: err?.message || 'Could not post public reply.' };
  } finally {
    if (button) button.disabled = false;
    renderMapBoardSheet();
  }
}
