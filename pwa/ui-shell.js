/**
 * ui-shell.js — Punkto PWA app shell
 *
 * Owns:
 *  - showPage(page) view toggle ('text' | 'map')
 *  - bottom nav wiring (nav-text, nav-map, nav-add, nav-settings)
 *  - settings panel open/close/toggle
 *  - body class management (page-text, page-map)
 *  - active state on nav buttons
 *  - setCounts() for nearby/atom display
 *
 * Stateless wrt atoms/network — app.js owns data and passes callbacks.
 */

let _onShowText   = null;
let _onShowMap    = null;
let _onAdd        = null;
let _onOpenSettings = null;

let _currentPage  = 'text';
let _settingsOpen = false;

/**
 * Wire the bottom navigation and settings panel.
 * Callbacks fire *after* shell state has been updated.
 */
export function initShell({ onShowText, onShowMap, onAdd, onOpenSettings } = {}) {
  _onShowText     = typeof onShowText     === 'function' ? onShowText     : null;
  _onShowMap      = typeof onShowMap      === 'function' ? onShowMap      : null;
  _onAdd          = typeof onAdd          === 'function' ? onAdd          : null;
  _onOpenSettings = typeof onOpenSettings === 'function' ? onOpenSettings : null;

  const elNavText     = document.getElementById('nav-text');
  const elNavMap      = document.getElementById('nav-map');
  const elNavAdd      = document.getElementById('nav-add');
  const elNavSettings = document.getElementById('nav-settings');

  if (elNavText) elNavText.addEventListener('click', () => showPage('text'));
  if (elNavMap)  elNavMap.addEventListener('click',  () => showPage('map'));
  if (elNavAdd) {
    elNavAdd.addEventListener('click', () => {
      if (_onAdd) _onAdd();
    });
  }
  if (elNavSettings) {
    elNavSettings.addEventListener('click', (e) => {
      e.stopPropagation();
      if (_onOpenSettings) _onOpenSettings();
      else toggleSettings();
    });
  }

  // Close settings on outside click (matches legacy behavior)
  document.addEventListener('click', () => {
    if (_settingsOpen) closeSettings();
  });

  // Escape closes settings (modal/panel escape handled by app.js)
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && _settingsOpen) closeSettings();
  });

  // Ensure settings is closed on first load
  closeSettings();
}

/**
 * Toggle between 'text' and 'map' pages.
 * Updates body classes, nav active state, then fires the matching callback
 * so app.js can run page-specific renderers (feed render, map resize, etc.).
 */
export function showPage(page) {
  if (page !== 'text' && page !== 'map') return;
  _currentPage = page;

  document.body.classList.remove('page-text', 'page-map');
  document.body.classList.add('page-' + page);

  ['text', 'map'].forEach((p) => {
    const btn = document.getElementById('nav-' + p);
    if (btn) btn.classList.toggle('active', p === page);
  });

  if (page === 'text' && _onShowText) _onShowText();
  if (page === 'map'  && _onShowMap)  _onShowMap();
}

export function getCurrentPage() {
  return _currentPage;
}

// ── Settings panel ─────────────────────────────────────────────────────────

export function openSettings() {
  _settingsOpen = true;
  const menu = document.getElementById('settings-menu');
  const bd   = document.getElementById('settings-backdrop');
  if (menu) {
    menu.classList.add('open');
    menu.setAttribute('aria-hidden', 'false');
  }
  if (bd) bd.classList.add('open');
}

export function closeSettings() {
  _settingsOpen = false;
  const menu = document.getElementById('settings-menu');
  const bd   = document.getElementById('settings-backdrop');
  if (menu) {
    menu.classList.remove('open');
    menu.setAttribute('aria-hidden', 'true');
  }
  if (bd) bd.classList.remove('open');
}

export function toggleSettings() {
  if (_settingsOpen) closeSettings();
  else openSettings();
}

export function isSettingsOpen() {
  return _settingsOpen;
}

/**
 * Update the small "N nearby" counter on the text page and the
 * cached-atoms count in the settings panel.
 * Either value may be null/undefined to skip that field.
 */
export function setCounts({ nearby, atomCount } = {}) {
  if (nearby !== undefined && nearby !== null) {
    const el = document.getElementById('main-atom-count');
    if (el) el.textContent = nearby === 0 ? '' : String(nearby) + ' nearby';
  }
  if (atomCount !== undefined && atomCount !== null) {
    const el = document.getElementById('settings-atom-count')
           || document.getElementById('settings-count');
    if (el) el.textContent = String(atomCount);
  }
}
