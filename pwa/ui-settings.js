/**
 * ui-settings.js — Punkto Settings panel UI ownership
 *
 * Owns:
 *  - Settings panel DOM refs
 *  - rendering Settings rows (network/identity/version)
 *  - wiring settings button callbacks
 *  - settings-specific display helpers
 *
 * Does NOT own shell open/close state, storage/sync/network I/O, or key logic.
 */

let _onResetCache = null;
let _onGenerateKey = null;
let _onImportKey = null;
let _onSaveKey = null;
let _onLoadKey = null;
let _onPrintMnemonic = null;
let _onExportKey = null;
let _onNameChanged = null;

const refs = {
  atomCount: null,
  node: null,
  peers: null,
  sync: null,
  version: null,
  keyStatus: null,
  keyInfo: null,
  keyAuthorId: null,
  keyPubkey: null,
  keyMnemonic: null,
  keyHelper: null,
  writingAsRow: null,
  writingAs: null,
  nameInput: null,
  saveKeyButton: null,
  loadKeyButton: null,
};

function byId(id) {
  return document.getElementById(id);
}

function toText(v, fallback = '—') {
  if (v === null || v === undefined || v === '') return fallback;
  return String(v);
}

export function initSettingsView({
  onResetCache,
  onGenerateKey,
  onImportKey,
  onSaveKey,
  onLoadKey,
  onPrintMnemonic,
  onExportKey,
  onNameChanged,
} = {}) {
  _onResetCache = typeof onResetCache === 'function' ? onResetCache : null;
  _onGenerateKey = typeof onGenerateKey === 'function' ? onGenerateKey : null;
  _onImportKey = typeof onImportKey === 'function' ? onImportKey : null;
  _onSaveKey = typeof onSaveKey === 'function' ? onSaveKey : null;
  _onLoadKey = typeof onLoadKey === 'function' ? onLoadKey : null;
  _onPrintMnemonic = typeof onPrintMnemonic === 'function' ? onPrintMnemonic : null;
  _onExportKey = typeof onExportKey === 'function' ? onExportKey : null;
  _onNameChanged = typeof onNameChanged === 'function' ? onNameChanged : null;

  refs.atomCount = byId('settings-atom-count') || byId('settings-count');
  refs.node = byId('settings-node');
  refs.peers = byId('settings-peers');
  refs.sync = byId('settings-count');
  refs.version = byId('app-version');
  refs.keyStatus = byId('me-key-status');
  refs.keyInfo = byId('key-info');
  refs.keyAuthorId = byId('key-author-id');
  refs.keyPubkey = byId('key-pubkey');
  refs.keyMnemonic = byId('key-mnemonic');
  refs.keyHelper = byId('me-key-helper');
  refs.writingAsRow = byId('me-writing-as-row');
  refs.writingAs = byId('me-writing-as');
  refs.nameInput = byId('settings-name');
  refs.saveKeyButton = byId('btn-save-key');
  refs.loadKeyButton = byId('btn-load-key');

  const resetBtn = byId('settings-reset');
  if (resetBtn) resetBtn.addEventListener('click', () => { if (_onResetCache) _onResetCache(); });

  const clickMap = [
    ['btn-generate-key', () => _onGenerateKey && _onGenerateKey()],
    ['btn-import-key', () => _onImportKey && _onImportKey()],
    ['btn-save-key', () => _onSaveKey && _onSaveKey()],
    ['btn-load-key', () => _onLoadKey && _onLoadKey()],
    ['btn-print-mnemonic', () => _onPrintMnemonic && _onPrintMnemonic()],
    ['btn-export-key', () => _onExportKey && _onExportKey()],
  ];

  for (const [id, fn] of clickMap) {
    const btn = byId(id);
    if (btn) btn.addEventListener('click', (e) => { e.preventDefault(); fn(); });
  }
  if (refs.nameInput) {
    refs.nameInput.addEventListener('input', () => _onNameChanged && _onNameChanged(refs.nameInput.value));
  }
}

export function renderSettingsView({ network = {}, identity = {}, version = null, syncStatus = null } = {}) {
  if (refs.atomCount && network.atomCount !== undefined) refs.atomCount.textContent = toText(network.atomCount, '0');
  if (refs.node && network.nodeHtml !== undefined) refs.node.innerHTML = network.nodeHtml;
  if (refs.peers && network.peersHtml !== undefined) refs.peers.innerHTML = network.peersHtml;
  if (refs.sync && syncStatus !== undefined && syncStatus !== null) refs.sync.textContent = toText(syncStatus, '0');
  if (refs.version && version !== undefined && version !== null) refs.version.textContent = String(version);

  if (refs.nameInput && identity.name !== undefined && refs.nameInput.value !== String(identity.name || '')) {
    refs.nameInput.value = String(identity.name || '');
  }
  if (refs.keyStatus && identity.status !== undefined) refs.keyStatus.textContent = toText(identity.status, 'No key on this device');
  if (refs.keyHelper && identity.helper !== undefined) refs.keyHelper.textContent = toText(identity.helper, 'Punktis you write are unsigned.');
  if (refs.writingAsRow) refs.writingAsRow.style.display = identity.name ? 'block' : 'none';
  if (refs.writingAs && identity.name !== undefined) refs.writingAs.textContent = toText(identity.name);
  if (refs.saveKeyButton && identity.canSave !== undefined) refs.saveKeyButton.disabled = !identity.canSave;
  if (refs.loadKeyButton && identity.canLoad !== undefined) refs.loadKeyButton.disabled = !identity.canLoad;

  if (refs.keyInfo) {
    const hasIdentity = !!identity.authorId;
    refs.keyInfo.style.display = hasIdentity ? 'block' : 'none';
    if (hasIdentity) {
      if (refs.keyAuthorId && identity.authorId !== undefined) refs.keyAuthorId.textContent = toText(identity.authorId);
      if (refs.keyPubkey && identity.pubkey !== undefined) refs.keyPubkey.textContent = toText(identity.pubkey);
      if (refs.keyMnemonic && identity.mnemonic !== undefined) refs.keyMnemonic.textContent = toText(identity.mnemonic);
    }
  }
}
