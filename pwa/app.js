/**
 * app.js — Punkto PWA main application
 * Depends on: MapLibre GL JS, deck.gl 8.9.x UMD (window.deck), Dexie.js
 */

import { encode, decode } from './geohash3d.js';
import {
  initShell,
  showPage as shellShowPage,
  openSettings as shellOpenSettings,
  closeSettings as shellCloseSettings,
  toggleSettings as shellToggleSettings,
  isSettingsOpen as shellIsSettingsOpen,
  setCounts as shellSetCounts,
} from './ui-shell.js';
import { initTextView, renderTextFeed } from './ui-text.js';
import { initMapView, showMapView } from './ui-map.js';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const NODE_URL = window.location.origin;
const SYNC_INTERVAL_MS = 30_000;
const MAP_STYLE = 'https://tiles.openfreemap.org/styles/liberty';

// Seed nodes for protocol-native load balancing (punkto.sync.md §5b)
const SEED_NODES = [
  'https://app1.punkto.xyz',
  'https://app2.punkto.xyz',
];

// Atoms whose author handle (case-insensitive) matches any of these are hidden
// from the UI (map dots + panel list + counters). The atoms remain in Dexie and
// on disk — the log is append-only — we just filter at render time.
const HIDDEN_AUTHOR_HANDLES = new Set([
  'test',
  'sync-test',
  'cors-test',
  'browser-test',
]);

// Node health tracking (in-memory, resets on reload)
// url -> { health: 'ok'|'failing'|'unavailable'|'recovering', failures: 0, unavailableSince: 0 }
const nodeRegistry = new Map();
let writeIndex = 0; // round-robin write pointer

function initNodeRegistry() {
  const allNodes = new Set([NODE_URL, ...SEED_NODES]);
  allNodes.forEach(url => {
    if (!nodeRegistry.has(url)) {
      nodeRegistry.set(url, { health: 'ok', failures: 0, unavailableSince: 0 });
    }
  });
}

function getHealthyNodes() {
  const now = Date.now();
  return [...nodeRegistry.entries()]
    .filter(([url, s]) => {
      if (s.health === 'ok' || s.health === 'failing') return true;
      if (s.health === 'recovering') return true;
      if (s.health === 'unavailable' && now - s.unavailableSince > 60_000) {
        s.health = 'recovering';
        return true;
      }
      return false;
    })
    .map(([url]) => url);
}

function markNodeSuccess(url) {
  const s = nodeRegistry.get(url);
  if (s) { s.health = 'ok'; s.failures = 0; s.unavailableSince = 0; }
}

function markNodeFailure(url) {
  const s = nodeRegistry.get(url);
  if (!s) return;
  s.failures++;
  if (s.failures >= 5) {
    s.health = 'unavailable';
    s.unavailableSince = Date.now();
  } else if (s.failures >= 2) {
    s.health = 'failing';
  }
}

async function postAtomToNetwork(atomBody) {
  const candidates = getHealthyNodes();
  if (candidates.length === 0) throw new Error('No healthy nodes available');
  for (let i = 0; i < candidates.length; i++) {
    const url = candidates[(writeIndex + i) % candidates.length];
    try {
      const res = await fetch(`${url}/atom`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(atomBody),
        signal: AbortSignal.timeout(10_000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      markNodeSuccess(url);
      writeIndex = (writeIndex + 1) % candidates.length;
      return await res.json();
    } catch (e) {
      console.warn(`[lb] postAtom failed for ${url}:`, e.message);
      markNodeFailure(url);
    }
  }
  throw new Error('All nodes failed');
}

// ---------------------------------------------------------------------------
// Dexie (IndexedDB)
// ---------------------------------------------------------------------------

const db = new Dexie('punkto');
db.version(1).stores({
  atoms: '++id, punkto, t, lat, lon, alt',
  meta:  'key',
});
// v2: clear stale atoms from old feed (forces re-sync from server)
db.version(2).stores({
  atoms: '++id, punkto, t, lat, lon, alt',
  meta:  'key',
}).upgrade(tx => tx.table('atoms').clear());
db.version(3).stores({
  atoms: '++id, punkto, t, lat, lon, alt',
  meta:  'key',
}).upgrade(tx => tx.table('atoms').clear());
// v4: add nodes table for per-node sync cursors and peer discovery
db.version(4).stores({
  atoms: '++id, punkto, t, lat, lon, alt',
  meta:  'key',
  nodes: 'url',
});

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let map = null;
let deckOverlay = null;
let syncTimer = null;
let isSyncing = false;
let is3D = true;
let initialSyncDone = false;
let deepLinkPunkto = null; // captured at boot, consumed after first refreshUI
// ============================================================
// Two-view shell — Text / Map
// ============================================================
let currentPage = 'text'; // 'text' | 'map'
let _mainFeedAtoms  = [];       // last sorted atom batch for main feed
let _locationDenied = false;    // true when geolocation denied/unavailable

// ── App shell: two views (Text / Map) ─────────────────────────────────────────
// showPage — thin wrapper. Body/nav state + page lifecycle live in ui-shell.js.
// Page-specific handlers (text feed render, map init/resize) are registered
// via initShell({ onShowText, onShowMap }) in boot().
function showPage(page) {
  currentPage = page;
  shellShowPage(page);
}

// renderMainFeed — thin wrapper that delegates to ui-text.js renderTextFeed.
// Atom sorting/filtering is handled upstream in refreshUI()/syncFeed(), which
// populates module-level _mainFeedAtoms before calling this.
function renderMainFeed() {
  renderTextFeed({
    atoms: _mainFeedAtoms,
    locationDenied: _locationDenied,
  });
}


// DOM bubble markers: punkto_id -> maplibregl.Marker
const atomMarkers = new Map();
// Currently focused punkto id (without 'p:') for atom-bubble--focus class
let focusedPunktoId = null;
// Phase 2: first-render fit-to-atoms flag. True after the first successful
// boot fit (or boot where there were no atoms). Subsequent renders never
// re-fit to avoid jarring viewport changes.
let hasBootFit = false;
// Phase 2: track which DB primary keys belong to atoms seen before the most
// recent syncFeed() run, so we can detect fresh arrivals and pulse them.
// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------

const elCountNum    = document.getElementById('count-num');
const elSyncDot     = document.getElementById('sync-indicator');
const elPanel       = document.getElementById('panel');
const elFabAdd      = document.getElementById('fab-add');
const elFabPanel    = document.getElementById('fab-panel');
const elPanelClose  = document.getElementById('panel-close');
const elAtomList    = document.getElementById('atom-list');
const elAtomEmpty   = document.getElementById('atom-list-empty');
const elMapEl       = document.getElementById('map');
const elModalOverlay = document.getElementById('modal-overlay');
const elModalLocation = document.getElementById('modal-location');
const elModalText   = document.getElementById('modal-text');
const elModalAuthor = document.getElementById('modal-author');
const elModalSubmit = document.getElementById('modal-submit');
const elModalCancel = document.getElementById('modal-cancel');
const elModalError  = document.getElementById('modal-error');
const elModalAltitudeSlider    = document.getElementById('modal-altitude-slider');
const elModalAltitudePrimary   = document.getElementById('modal-altitude-primary');
const elModalAltitudeSecondary = document.getElementById('modal-altitude-secondary');
const elModalAltitudeHint      = document.getElementById('modal-altitude-hint');
const elModalGroundBtn         = document.getElementById('modal-ground-btn');
const elModalRoofBtn           = document.getElementById('modal-roof-btn');
const elModalDeviceAltBtn      = document.getElementById('modal-device-alt-btn');
const elModalFloorMinus        = document.getElementById('modal-floor-minus');
const elModalFloorPlus         = document.getElementById('modal-floor-plus');
const elModalFloorValue        = document.getElementById('modal-floor-value');
const elModalManualAltitude    = document.getElementById('modal-manual-altitude-value');
const elToggle3D    = document.getElementById('toggle-3d');
const elBtnSettings = document.getElementById('btn-settings');
const elSettingsMenu = document.getElementById('settings-menu');
const elSettingsReset = document.getElementById('settings-reset');
const elSettingsNode = document.getElementById('settings-node');
const elSettingsPeers = document.getElementById('settings-peers');
const elSettingsCount = document.getElementById('settings-count');
const elOnboardingHint = document.getElementById('onboarding-hint');
const elCrosshairReadout = document.getElementById('crosshair-readout');

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

function setSyncStatus(state) {
  elSyncDot.className = '';
  if (state) elSyncDot.classList.add(state);
}
// ── Network page renderer ─────────────────────────────────────────────────────
// Shows live node/peer/sync data. Called by showPage('network').
function renderNetworkPage() {
  // Reuse data already fetched by refreshSettingsNetworkInfo()
  const srcNode   = document.getElementById('settings-node');
  const srcPeers  = document.getElementById('settings-peers');
  const srcCached = document.getElementById('settings-count');

  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el && val !== null) el.textContent = val;
  };

  setVal('net-node',   srcNode   ? srcNode.textContent   : '—');
  setVal('net-peers',  srcPeers  ? srcPeers.textContent  : '—');
  setVal('net-cached', srcCached ? srcCached.textContent : '0');

  // Sync status: derive from isSyncing flag if available
  const syncEl = document.getElementById('net-sync');
  if (syncEl) {
    syncEl.textContent = (typeof isSyncing !== 'undefined' && isSyncing) ? 'Syncing…' : 'Idle';
  }

  // Trigger a fresh network info pull in background
  if (typeof refreshSettingsNetworkInfo === 'function') {
    refreshSettingsNetworkInfo().catch(() => {});
  }
}

// ── Me page renderer ──────────────────────────────────────────────────────────
// Shows identity/key state. Called by showPage('me').
function renderMePage() {
  // Pull key data from the hidden #key-info block (populated by key-management.js)
  const authorId  = document.getElementById('key-author-id');
  const pubkey    = document.getElementById('key-pubkey');
  const mnemonic  = document.getElementById('key-mnemonic');

  const hasKey = authorId && authorId.textContent && authorId.textContent !== '—';

  const loadedEl = document.getElementById('me-identity-loaded');
  const emptyEl  = document.getElementById('me-identity-empty');
  if (loadedEl) loadedEl.style.display = hasKey ? '' : 'none';
  if (emptyEl)  emptyEl.style.display  = hasKey ? 'none' : '';

  if (hasKey) {
    const setVal = (id, src) => {
      const el = document.getElementById(id);
      if (el && src) el.textContent = src.textContent || '—';
    };
    setVal('me-author-id', authorId);
    setVal('me-pubkey',    pubkey);
    setVal('me-mnemonic',  mnemonic);
  }
}



function fmtTime(ms) {
  const t = Number(ms);
  if (!t) return '?';
  const d = new Date(t);
  const now = Date.now();
  const diff = now - t;
  if (diff < 60_000)   return 'just now';
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return d.toLocaleDateString();
}

function fmtCoords(lat, lon, alt) {
  const latStr = lat.toFixed(5);
  const lonStr = lon.toFixed(5);
  const altStr = alt != null ? ` · ${Math.round(alt)}m` : '';
  return `${latStr}, ${lonStr}${altStr}`;
}

function haversineMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = d => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function fmtDistance(meters) {
  if (!Number.isFinite(meters)) return '';
  if (meters < 1000) return `${Math.round(meters)} m away`;
  return `${(meters / 1000).toFixed(1)} km away`;
}

function deriveTitle(atom) {
  const raw = String(atom?.x || '').trim();
  if (!raw) return 'Untitled note';
  const firstLine = raw.split(/\r?\n/).find(Boolean) || raw;
  return firstLine.length > 40 ? `${firstLine.slice(0, 40)}…` : firstLine;
}

function fmtAltitudeLabel(alt) {
  if (!Number.isFinite(alt) || Math.abs(alt) < 1) return '';
  const floor = Math.round(alt / 3);
  if (floor >= 2) return `Floor ${floor}`;
  return `+${Math.round(alt)} m`;
}

function deriveCategory(atom) {
  const c = String(atom?.category || atom?.kind || '').trim();
  return c || 'Note';
}

function isVerifiedAtom(atom) {
  return Boolean(atom?.sig && atom?.pubkey);
}

/**
 * Extract the spatial part of a canonical punkto and decode to coords.
 * e.g. 'p:u4pruydqqvj3-9xk3' → decode('u4pruydqqvj3')
 */
function decodeAtomLocation(punktoStr) {
  try {
    // Strip 'p:' prefix, split on '-', take first segment = spatial hash
    const spatial = punktoStr.replace(/^p:/, '').split('-')[0];
    if (spatial.length < 1) return null;
    return decode(spatial);
  } catch {
    return null;
  }
}

/**
 * Return true if an atom (DB record or feed entry) should be hidden from the UI
 * because its author handle is a known test/system handle. Case-insensitive.
 */
function isHiddenAtom(atom) {
  const f = typeof atom?.f === 'string' ? atom.f.trim().toLowerCase() : '';
  if (!f) return false;
  return HIDDEN_AUTHOR_HANDLES.has(f);
}

// ---------------------------------------------------------------------------
// Deep-link: /p/<id> → open and focus a punkto
// ---------------------------------------------------------------------------

/**
 * Parse a /p/<id> pathname. id = 12 base32 chars, optional '-suffix' (alnum).
 * Returns the full punkto id (without 'p:' prefix) or null.
 */
function parseDeepLinkPunktoId() {
  const m = /^\/p\/([0-9a-z]{12}(?:-[a-zA-Z0-9]+)?)\/?$/.exec(location.pathname || '');
  return m ? m[1] : null;
}

/**
 * Focus a punkto by id: center map, open panel, highlight matching atom if cached.
 * Safe to call when no matching atom exists locally — we still center on the coords.
 */
async function focusPunkto(id) {
  // Switch to 3D page so the map is visible
  showPage('map');
  if (!id) return;
  const punkto = `p:${id}`;
  const loc = decodeAtomLocation(punkto);
  if (!loc || !map) return;

  // Center + zoom
  map.flyTo({ center: [loc.lon, loc.lat], zoom: 16, duration: 1200 });

  // Open panel so user sees atom list
  setPanelOpen(true);

  // Update title for shareability
  document.title = `Punkto · ${punkto}`;

  // Mark this atom's bubble as focused (amber border). Clear any prior focus.
  if (focusedPunktoId && focusedPunktoId !== id) {
    const prev = atomMarkers.get(`p:${focusedPunktoId}`);
    if (prev) prev.getElement().classList.remove('atom-bubble--focus');
  }
  focusedPunktoId = id;
  const cur = atomMarkers.get(punkto);
  if (cur) cur.getElement().classList.add('atom-bubble--focus');

  // Highlight matching atom item if present in the list (after refreshUI)
  // refreshUI repopulates children; we search on next tick.
  // NOTE: if the targeted punkto's atoms are all filtered (hidden test/system
  // handles), they won't be in the rendered list and the loop simply exits
  // without highlighting — the fly-to still works, which is the desired UX.
  requestAnimationFrame(() => {
    const items = elAtomList.querySelectorAll('.atom-item');
    for (const item of items) {
      const metaEl = item.querySelector('.atom-meta');
      if (metaEl && metaEl.textContent.includes(punkto)) {
        item.style.background = 'rgba(0, 229, 255, 0.08)';
        item.style.borderLeft = '2px solid var(--cyan)';
        item.scrollIntoView({ behavior: 'smooth', block: 'center' });
        break;
      }
    }
  });
}

// ---------------------------------------------------------------------------
// Encode current map center into canonical punkto string
// ---------------------------------------------------------------------------

function encodeCurrentLocation(mapInst, altMeters = 0) {
  const center = mapInst.getCenter();
  const lat = center.lat;
  const lon = center.lng;
  return encodeLocation(lat, lon, altMeters);
}

function encodeLocation(lat, lon, altMeters = 0) {
  // Guard against non-numeric input; fall back to ground level.
  const alt = Number.isFinite(altMeters) ? altMeters : 0;
  const hash = encode(lat, lon, alt, 12);
  return `p:${hash}`;
}

// ---------------------------------------------------------------------------
// IndexedDB helpers
// ---------------------------------------------------------------------------


async function upsertAtom(atom) {
  // Decode location from punkto field
  const loc = decodeAtomLocation(atom.punkto);
  const record = {
    punkto: atom.punkto,
    t:      atom.t,
    x:      atom.x || '',
    f:      atom.f || '',
    lat:    loc ? loc.lat : 0,
    lon:    loc ? loc.lon : 0,
    alt:    loc ? loc.alt : 0,
  };
  // Upsert by punkto+t (natural key)
  const existing = await db.atoms
    .where('punkto').equals(atom.punkto)
    .and(a => a.t === atom.t)
    .first();
  if (!existing) {
    // Return the newly assigned auto-increment id so syncFeed can flag fresh arrivals.
    const newId = await db.atoms.add(record);
    return { inserted: true, id: newId };
  }
  return { inserted: false, id: existing.id };
}

// ---------------------------------------------------------------------------
// Sync
// ---------------------------------------------------------------------------

async function syncFeed() {
  if (isSyncing) return;
  isSyncing = true;
  setSyncStatus('syncing');

  let anyError = false;
  const newAtomIds = new Set();

  try {
    // Get all known nodes from Dexie; always include DEFAULT NODE_URL
    const storedNodes = await db.nodes.toArray();
    const nodeUrls = new Set(storedNodes.map(n => n.url));
    nodeUrls.add(NODE_URL);

    for (const url of nodeUrls) {
      try {
        const latestUrl = `${url}/latest`;
        const res = await fetch(latestUrl, { signal: AbortSignal.timeout(15_000) });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (Array.isArray(data.atoms) && data.atoms.length > 0) {
          for (const atom of data.atoms) {
            if (atom.punkto && atom.t) {
              const r = await upsertAtom(atom);
              if (r && r.inserted && !isHiddenAtom(atom)) {
                newAtomIds.add(r.id);
              }
            }
          }
        }
      } catch (nodeErr) {
        console.warn(`[sync] latest error for ${url}:`, nodeErr);
        anyError = true;
      }
    }

    setSyncStatus(anyError ? 'error' : 'ok');
    await refreshUI(newAtomIds);
  } catch (err) {
    console.warn('[sync] unexpected error:', err);
    setSyncStatus('error');
  } finally {
    isSyncing = false;
  }
}

// Discover peers from /info on all known nodes and register them in the nodes table
async function discoverPeers() {
  for (const seedUrl of nodeRegistry.keys()) {
    try {
      const res = await fetch(`${seedUrl}/info`, { signal: AbortSignal.timeout(8_000) });
      if (!res.ok) continue;
      const info = await res.json();
      const peers = Array.isArray(info.peers) ? info.peers : [];
      for (const peerUrl of peers) {
        const url = peerUrl.replace(/\/$/, '');
        if (!url) continue;
        // Add to in-memory registry
        if (!nodeRegistry.has(url)) {
          nodeRegistry.set(url, { health: 'ok', failures: 0, unavailableSince: 0 });
          console.log('[lb] discovered peer:', url);
        }
        // Register in Dexie for syncFeed
        const existing = await db.nodes.get(url);
        if (!existing) {
          await db.nodes.put({ url, cursor: 0 });
        }
      }
    } catch (err) {
      console.warn(`[lb] peer discovery error for ${seedUrl}:`, err.message);
    }
  }
}

// ---------------------------------------------------------------------------
// deck.gl rendering
// ---------------------------------------------------------------------------


/**
 * Map altitude to RGBA color. Higher = brighter cyan.
 * alt range: -500 to 8500 → intensity 120–255
 */
function altToColor(alt) {
  const t = Math.max(0, Math.min(1, (alt + 500) / 9000));
  const intensity = Math.round(120 + t * 135); // 120–255 (was 40–255)
  return [0, intensity, 255, 240];
}

/**
 * Convert an integer hue (0–359) to an RGBA tuple using HSL(hue, 65%, 50%).
 * Used to tint ScatterplotLayer dots so each atom dot matches its bubble's
 * author hue, making the bubble ↔ dot pairing visually explicit.
 */
function hueToRgba(hue, alpha = 240) {
  const s = 0.65, l = 0.5;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const h = hue / 60;
  const x = c * (1 - Math.abs((h % 2) - 1));
  let r = 0, g = 0, b = 0;
  if (h < 1)      [r, g, b] = [c, x, 0];
  else if (h < 2) [r, g, b] = [x, c, 0];
  else if (h < 3) [r, g, b] = [0, c, x];
  else if (h < 4) [r, g, b] = [0, x, c];
  else if (h < 5) [r, g, b] = [x, 0, c];
  else            [r, g, b] = [c, 0, x];
  const m = l - c / 2;
  return [
    Math.round((r + m) * 255),
    Math.round((g + m) * 255),
    Math.round((b + m) * 255),
    alpha,
  ];
}

/**
 * Phase 2: deterministic author → hue mapping for subtle bubble tinting.
 * Returns an integer hue 0–360, or null for anon/empty authors (keeps
 * the default neutral hue defined in CSS).
 * Simple djb2-style hash — stable across reloads and devices.
 */
function hashAuthorHue(author) {
  if (!author) return null;
  const s = String(author).trim().toLowerCase();
  if (!s || s === 'anon') return null;
  let h = 5381;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) + h + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h) % 360;
}

/**
 * Phase 2: build and show a MapLibre popup for one or more atoms at a
 * given lngLat. If `atomOrAtoms` is an array with length > 1, renders a
 * 'N atoms at this Punkto' heading followed by a list. Otherwise renders
 * the single-atom popup (same markup the ScatterplotLayer produced).
 */
function openAtomPopup(atomOrAtoms, lngLat) {
  if (!map) return;
  const atoms = Array.isArray(atomOrAtoms) ? atomOrAtoms : [atomOrAtoms];
  if (atoms.length === 0) return;

  let html = '';
  if (atoms.length === 1) {
    const a = atoms[0];
    const loc = decodeAtomLocation(a.punkto);
    const coordStr = loc ? fmtCoords(loc.lat, loc.lon, loc.alt) : '';
    const timeStr = fmtTime(a.t);
    const text = a.text || a.x || '';
    html = [
      text ? `<div class="popup-text">${escHtml(text)}</div>` : '',
      `<div class="popup-meta">${escHtml(a.f || 'anon')} · ${timeStr}</div>`,
      `<div class="popup-canon">${escHtml(a.punkto)}</div>`,
      coordStr ? `<div class="popup-coords">${coordStr}</div>` : '',
    ].filter(Boolean).join('');
  } else {
    // Multi-atom: sort newest first, show all
    const sorted = atoms.slice().sort((a, b) => (b.t || 0) - (a.t || 0));
    const head = `<div class="popup-meta" style="font-weight:600;">${sorted.length} atoms at this Punkto</div>`;
    const items = sorted.map(a => {
      const text = a.text || a.x || '';
      const timeStr = fmtTime(a.t);
      return [
        '<div class="popup-atom" style="margin-top:8px;padding-top:6px;border-top:1px solid #333;">',
        text ? `<div class="popup-text">${escHtml(text)}</div>` : '',
        `<div class="popup-meta">${escHtml(a.f || 'anon')} · ${timeStr}</div>`,
        '</div>',
      ].filter(Boolean).join('');
    }).join('');
    const canon = sorted[0].punkto;
    const loc = decodeAtomLocation(canon);
    const coordStr = loc ? fmtCoords(loc.lat, loc.lon, loc.alt) : '';
    html = head + items +
      `<div class="popup-canon" style="margin-top:8px;">${escHtml(canon)}</div>` +
      (coordStr ? `<div class="popup-coords">${coordStr}</div>` : '');
  }

  new maplibregl.Popup({ closeButton: true, maxWidth: '280px', className: 'punkto-popup' })
    .setLngLat(lngLat)
    .setHTML(html)
    .addTo(map);
}

async function renderAtoms(newAtomIds = null) {
  if (!deckOverlay) return;

  // Filter out hidden system/test atoms so they never appear on the map either.
  const atoms = (await db.atoms.orderBy('t').reverse().toArray())
    .filter(a => !isHiddenAtom(a));

  // Phase 2: per-punkto aggregation for count badges and multi-atom popups.
  // atomsByPunkto maps a canonical punkto id → array of atoms (newest first,
  // preserving the orderBy('t').reverse() ordering above).
  const atomsByPunkto = new Map();
  for (const a of atoms) {
    if (!a.punkto) continue;
    const arr = atomsByPunkto.get(a.punkto);
    if (arr) arr.push(a);
    else atomsByPunkto.set(a.punkto, [a]);
  }

  const scatterData = atoms.map(a => ({
    position: [a.lon, a.lat, a.alt],
    // Tint each dot with its author hue so the leader line visually matches
    // the bubble sitting above. Falls back to altitude gradient when the
    // atom has no author (anon) or the hash returned null.
    color: (() => {
      const h = hashAuthorHue(a.f);
      return h != null ? hueToRgba(h) : altToColor(a.alt);
    })(),
    punkto: a.punkto,
    text: a.x,
    f: a.f,
    t: a.t,
    label: (a.x || a.f || '').slice(0, 40),
  }));
  if (placementDraft) {
    scatterData.push({
      position: [placementDraft.lon, placementDraft.lat, placementDraft.altitude_m || 0],
      color: [255, 220, 80, 255],
      punkto: 'draft',
      text: 'Placement preview',
      f: 'draft',
      t: Date.now(),
      label: 'draft',
    });
  }

  const { ScatterplotLayer, MapboxOverlay } = window.deck;

  const layers = [
    new ScatterplotLayer({
      id: 'atoms',
      data: scatterData,
      getPosition: d => d.position,
      getFillColor: d => d.color,
      getRadius: 12,
      radiusUnits: 'pixels',
      radiusMinPixels: 8,
      radiusMaxPixels: 20,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 100, 255],
      onClick: info => {
        if (!info.object || !map) return;
        const a = info.object;
        const group = atomsByPunkto.get(a.punkto) || [a];
        openAtomPopup(group.length > 1 ? group : group[0], info.coordinate.slice(0, 2));
      },
    }),
  ];

  // Iteration 1b: lollipop sticks. For each atom with altitude > 0, draw a
  // vertical line from ground up to the atom's altitude. Color matches the
  // author hue (same as the dot/bubble) so the stick visually extends the
  // bubble's identity all the way down to the surface.
  const { LineLayer } = window.deck;
  if (LineLayer) {
    const lollipopData = atoms
      .filter(a => (a.alt || 0) > 0)
      .map(a => {
        const h = hashAuthorHue(a.f);
        const baseRgba = h != null ? hueToRgba(h) : altToColor(a.alt);
        // Apply ~0.6 opacity by overriding the alpha channel.
        const color = [baseRgba[0], baseRgba[1], baseRgba[2], 153];
        return {
          source: [a.lon, a.lat, 0],
          target: [a.lon, a.lat, a.alt],
          color,
        };
      });
    if (placementDraft && (placementDraft.altitude_m || 0) > 0) {
      lollipopData.push({
        source: [placementDraft.lon, placementDraft.lat, 0],
        target: [placementDraft.lon, placementDraft.lat, placementDraft.altitude_m || 0],
        color: [255, 220, 80, 180],
      });
    }
    layers.push(
      new LineLayer({
        id: 'atom-lollipops',
        data: lollipopData,
        getSourcePosition: d => d.source,
        getTargetPosition: d => d.target,
        getColor: d => d.color,
        getWidth: 2,
        widthUnits: 'pixels',
        pickable: false,
      })
    );
  }

  deckOverlay.setProps({ layers });

  // --- DOM bubble markers (MapLibre) ------------------------------------
  // Reconcile atomMarkers map with current atom set. For Phase 1 we render
  // ALL markers at once; LOD is done via updateBubbleVisibility. With only
  // ~tens of atoms this is fine. Viewport culling = TODO Phase 2.
  if (map) {
    const seen = new Set();
    // Iterate unique punktos; render the latest atom as the visible bubble
    // (atoms array is already newest-first, so the first entry in each
    // atomsByPunkto bucket is the latest). Count badge reflects total.
    for (const [pid, group] of atomsByPunkto) {
      const a = group[0];
      seen.add(pid);
      const count = group.length;
      let marker = atomMarkers.get(pid);
      let el;
      let justCreated = false;
      if (!marker) {
        el = buildBubbleElement(a, count, group);
        // Offset pulls the bubble 16px upward so the atom dot stays visible
        // beneath it and the SVG leader line has room to connect them.
        marker = new maplibregl.Marker({ element: el, anchor: 'bottom', offset: [0, -16] })
          .setLngLat([a.lon, a.lat])
          .addTo(map);
        atomMarkers.set(pid, marker);
        justCreated = true;
      } else {
        // Update content in place so edits (t changes, etc.) refresh without
        // a DOM flicker. Position is stable per punkto so no setLngLat needed.
        el = marker.getElement();
        updateBubbleElement(el, a, count, group);
      }
      // New-atom pulse: if any atom in this group is in newAtomIds, pulse.
      if (newAtomIds && newAtomIds.size > 0 && group.some(x => newAtomIds.has(x.id))) {
        el.classList.remove('atom-bubble--new'); // restart animation if still lingering
        // Force reflow so re-adding the class replays the keyframes
        // eslint-disable-next-line no-unused-expressions
        void el.offsetWidth;
        el.classList.add('atom-bubble--new');
        setTimeout(() => el.classList.remove('atom-bubble--new'), 700);
      }
    }
    // Remove markers for atoms that disappeared (e.g. after hide-handle change)
    for (const [pid, marker] of atomMarkers) {
      if (!seen.has(pid)) {
        marker.remove();
        atomMarkers.delete(pid);
      }
    }
    updateBubbleVisibility();
    // Re-draw leader lines so newly-added or removed bubbles sync immediately,
    // even before the next MapLibre `render` event fires.
    drawLeaderLines();

    // Phase 2: fit-to-atoms on first render only. Deep-link flyTo wins.
    if (!hasBootFit) {
      hasBootFit = true;
      if (!deepLinkPunkto && atoms.length > 0) {
        try {
          let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
          for (const a of atoms) {
            if (a.lon < minLon) minLon = a.lon;
            if (a.lon > maxLon) maxLon = a.lon;
            if (a.lat < minLat) minLat = a.lat;
            if (a.lat > maxLat) maxLat = a.lat;
          }
          if (isFinite(minLon) && isFinite(minLat)) {
            map.fitBounds(
              [[minLon, minLat], [maxLon, maxLat]],
              {
                padding: { top: 80, bottom: 200, left: 40, right: 40 },
                maxZoom: 14,
                duration: 0,
              }
            );
          }
        } catch (e) {
          console.warn('[renderAtoms] fitBounds failed:', e);
        }
      }
    }
  }
}

/**
 * Build a fresh DOM element for an atom bubble. Used when a new marker is
 * created. Structure matches ui.md spec:
 *   .atom-bubble > .atom-bubble-body ( .atom-bubble-text + .atom-bubble-meta )
 *                + .atom-bubble-tail
 */
function buildBubbleElement(atom, count = 1, group = null) {
  const el = document.createElement('div');
  el.className = 'atom-bubble';
  el.dataset.punkto = atom.punkto || '';
  // Mark the focused atom if applicable (e.g. deep-link target)
  if (focusedPunktoId && atom.punkto === `p:${focusedPunktoId}`) {
    el.classList.add('atom-bubble--focus');
  }
  updateBubbleElement(el, atom, count, group);

  // Phase 2: bubble-body click → open popup. Badge click and anchor
  // clicks are handled separately (stopPropagation / early-return).
  el.addEventListener('click', (ev) => {
    // Let anchors inside markdown-rendered text behave normally.
    if (ev.target.closest('a')) return;
    // Badge has its own handler attached in updateBubbleElement.
    if (ev.target.closest('.atom-bubble-count')) return;
    const loc = decodeAtomLocation(atom.punkto);
    if (!loc) return;
    // Read the current group from the element's stashed reference so
    // re-renders (which may update the group) stay in sync.
    const currentGroup = el._punktoGroup || [atom];
    const payload = currentGroup.length > 1 ? currentGroup : currentGroup[0];
    openAtomPopup(payload, [loc.lon, loc.lat]);
  });

  return el;
}

/**
 * (Re)render the inner HTML of a bubble element from an atom record.
 */
function updateBubbleElement(el, atom, count = 1, group = null) {
  const textHtml = renderAtomText(atom.x || '');
  const author = escHtml(atom.f || 'anon');
  const timeStr = escHtml(fmtRelativeTime(atom.t));

  // Phase 2: stash group on element so click handler (set once in
  // buildBubbleElement) always sees the freshest atom list.
  el._punktoGroup = group || [atom];

  const badgeHtml = count > 1
    ? `<span class="atom-bubble-count" title="${count} atoms at this Punkto">+${count - 1}</span>`
    : '';

  // Iteration 1b: altitude badge for atoms above ground.
  // Decoded from the canonical punkto string so it matches the lollipop stick
  // and the dot's 3D position. Hidden when alt === 0 (ground level).
  let altBadgeHtml = '';
  const _loc = atom.punkto ? decodeAtomLocation(atom.punkto) : null;
  if (_loc && _loc.alt > 0) {
    const altRounded = Math.round(_loc.alt);
    altBadgeHtml = `<span class="atom-bubble-alt" title="altitude: ${altRounded} m">+${altRounded}m</span>`;
  }

  el.innerHTML = `
    <div class="atom-bubble-body">
      <div class="atom-bubble-text">${textHtml || '<span style="opacity:0.5">no text</span>'}</div>
      <div class="atom-bubble-meta">
        <span class="atom-bubble-author">${author}</span>
        <span class="atom-bubble-dot">·</span>
        <span class="atom-bubble-time">${timeStr}</span>
      </div>
      ${altBadgeHtml}
    </div>
    ${badgeHtml}
  `;

  // Phase 2: per-author hue tint. Set on the inner body element (NOT on el)
  // because MapLibre rewrites the outer element's style.cssText on every
  // pan/zoom, which would wipe the CSS custom property. The inner element
  // is untouched by MapLibre so the tint persists.
  const body = el.querySelector('.atom-bubble-body');
  if (body) {
    const hue = hashAuthorHue(atom.f);
    if (hue != null) body.style.setProperty('--author-hue', String(hue));
    else body.style.removeProperty('--author-hue');
  }

  // Wire badge click → popup with all atoms at this punkto.
  if (count > 1) {
    const badge = el.querySelector('.atom-bubble-count');
    if (badge) {
      badge.addEventListener('click', (ev) => {
        ev.stopPropagation();
        const loc = decodeAtomLocation(atom.punkto);
        if (!loc) return;
        const currentGroup = el._punktoGroup || [atom];
        openAtomPopup(currentGroup, [loc.lon, loc.lat]);
      });
    }
  }
}

/**
 * Zoom-based LOD for bubbles:
 *   zoom < 12  → hide (dots only)
 *   12 ≤ z <16 → compact (clamped 2 lines, 160px)
 *   z ≥ 16     → full (240px)
 * Called after renderAtoms and from map zoomend/moveend handlers.
 */
function updateBubbleVisibility() {
  if (!map) return;
  const z = map.getZoom();
  for (const [, marker] of atomMarkers) {
    const el = marker.getElement();
    if (z < 8) {
      el.style.display = 'none';
    } else {
      el.style.display = '';
      el.classList.toggle('atom-bubble--compact', z < 14);
    }
  }
}

// ---------------------------------------------------------------------------
// Leader lines (SVG overlay) — connect each bubble to its atom dot
// ---------------------------------------------------------------------------

let svgLeaderOverlay = null;

/**
 * Ensure the SVG overlay exists inside the map container. Called once from
 * initMap() and safe to call again (idempotent) in case the container is
 * rebuilt.
 */
function ensureLeaderOverlay() {
  if (!map) return null;
  if (svgLeaderOverlay && svgLeaderOverlay.isConnected) return svgLeaderOverlay;
  const container = map.getContainer();
  let svg = container.querySelector('#leader-lines');
  if (!svg) {
    svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('id', 'leader-lines');
    // Keep the SVG non-interactive so clicks pass through to the map/dots.
    svg.setAttribute('aria-hidden', 'true');
    container.appendChild(svg);
  }
  svgLeaderOverlay = svg;
  return svg;
}

/**
 * Draw one <line> per visible bubble from the atom dot (map-projected
 * [lon,lat]) up to the bottom-center of the bubble DOM.
 *
 * Performance: called on every map `render` event (~60 fps during pan/zoom).
 * Per-frame cost: one bounding-rect read per bubble + map.project() per
 * atom. With the current LOD cap (< 200 bubbles) this stays well under 1ms.
 *
 * Colors: matches the bubble's author hue so the line visually extends the
 * bubble down to its dot. Anon/unknown authors use neutral hue 210.
 */
function drawLeaderLines() {
  if (!map || atomMarkers.size === 0) {
    if (svgLeaderOverlay) svgLeaderOverlay.innerHTML = '';
    return;
  }
  const svg = ensureLeaderOverlay();
  if (!svg) return;

  const containerRect = map.getContainer().getBoundingClientRect();
  const parts = [];

  for (const [pid, marker] of atomMarkers) {
    const el = marker.getElement();
    // Skip hidden-by-LOD bubbles so lines disappear in lockstep with them.
    if (!el || el.style.display === 'none') continue;

    // Atom dot position: project the marker's lngLat into screen space.
    const lngLat = marker.getLngLat();
    const dotPt = map.project([lngLat.lng, lngLat.lat]);
    if (!dotPt || !isFinite(dotPt.x) || !isFinite(dotPt.y)) continue;

    // Iteration 1b fix: instead of anchoring the line at the bubble's
    // bottom-center (which makes the line visibly cross the bubble body),
    // compute the bubble's rectangle edge facing the dot via a standard
    // line-rectangle intersection from the bubble center toward the dot.
    const bubbleRect = el.getBoundingClientRect();
    if (bubbleRect.width === 0 && bubbleRect.height === 0) continue;
    const cx = bubbleRect.left + bubbleRect.width / 2 - containerRect.left;
    const cy = bubbleRect.top + bubbleRect.height / 2 - containerRect.top;
    const dx = dotPt.x - cx;
    const dy = dotPt.y - cy;
    let bubbleX = cx;
    let bubbleY = cy;
    if (dx !== 0 || dy !== 0) {
      const hw = bubbleRect.width / 2;
      const hh = bubbleRect.height / 2;
      const tx = dx !== 0 ? hw / Math.abs(dx) : Infinity;
      const ty = dy !== 0 ? hh / Math.abs(dy) : Infinity;
      const t = Math.min(tx, ty);
      bubbleX = cx + dx * t;
      bubbleY = cy + dy * t;
    }

    // Author hue via the atom attached to the element, fallback 210.
    const group = el._punktoGroup;
    const atom = group && group.length ? group[0] : null;
    const h = atom ? hashAuthorHue(atom.f) : null;
    const hue = h != null ? h : 210;

    parts.push(
      `<line x1="${dotPt.x.toFixed(1)}" y1="${dotPt.y.toFixed(1)}"` +
      ` x2="${bubbleX.toFixed(1)}" y2="${bubbleY.toFixed(1)}"` +
      ` stroke="hsl(${hue}, 55%, 55%)" stroke-width="1.5"` +
      ` stroke-opacity="0.65" stroke-linecap="round" />`
    );
  }

  svg.innerHTML = parts.join('');
}

// ---------------------------------------------------------------------------
// Panel / atom list UI
// ---------------------------------------------------------------------------

async function refreshUI(newAtomIds = null) {
  // Compute the visible-atom count (after filtering hidden system/test handles).
  // The full DB count is not exposed in the UI — users see only the clean subset.
  const allAtoms = await db.atoms.orderBy('t').reverse().toArray();
  const visibleAtoms = allAtoms.filter(a => !isHiddenAtom(a));
  const total = visibleAtoms.length;
  elCountNum.textContent = total;
  // Keep settings info (if menu is open) in sync
  if (elSettingsCount) elSettingsCount.textContent = String(total);

  // Render recent 50 visible atoms in panel, prioritizing nearby notes
  const center = map ? map.getCenter() : null;
  const enriched = visibleAtoms.map(a => ({
    ...a,
    distance: center ? haversineMeters(center.lat, center.lng, a.lat, a.lon) : NaN,
  }));
  enriched.sort((a, b) => {
    const ad = Number.isFinite(a.distance);
    const bd = Number.isFinite(b.distance);
    if (ad && bd) return a.distance - b.distance || (Number(b.t) - Number(a.t));
    if (ad) return -1;
    if (bd) return 1;
    return Number(b.t) - Number(a.t);
  });
  const recent = enriched.slice(0, 50);
  // Expose to main-view feed
  _mainFeedAtoms = recent;
  if (currentPage === 'text') renderMainFeed();

  if (recent.length === 0) {
    // Only show the empty placeholder AFTER the first sync has completed.
    // During cold boot (cache empty + sync in progress) we keep it hidden so
    // users see a clean list instead of a flash of "No atoms yet".
    if (initialSyncDone) {
      elAtomEmpty.innerHTML = '<strong>No text here yet</strong><br/>Be the first to leave something at this place.<br/><button id="empty-leave-note" class="btn btn-secondary" style="margin-top:8px">Leave note here</button>';
      requestAnimationFrame(() => { const b = document.getElementById('empty-leave-note'); if (b) b.onclick = openModal; });
      elAtomEmpty.style.display = 'block';
    } else {
      elAtomEmpty.style.display = 'none';
    }
    // Remove all items except empty placeholder
    Array.from(elAtomList.children).forEach(c => {
      if (c.id !== 'atom-list-empty') c.remove();
    });
  } else {
    elAtomEmpty.style.display = 'none';
    // Rebuild list
    Array.from(elAtomList.children).forEach(c => {
      if (c.id !== 'atom-list-empty') c.remove();
    });
    for (const a of recent) {
      const el = document.createElement('div');
      el.className = 'atom-item';
      const raw = String(a.x || '').trim();
      const title = escHtml(deriveTitle(a));
      const preview = raw ? escHtml(raw.length > 120 ? `${raw.slice(0, 120)}…` : raw) : '<span class="empty">Untitled note</span>';
      const altitude = fmtAltitudeLabel(Number(a.alt));
      const category = escHtml(deriveCategory(a));
      const verified = isVerifiedAtom(a) ? '<span class="atom-verified">Verified</span>' : '';
      const meta = [fmtDistance(a.distance), altitude, fmtTime(a.t)].filter(Boolean).join(' · ');
      el.innerHTML = `
        <div class="atom-dot"></div>
        <div class="atom-body">
          <div class="atom-meta"><span class="atom-category">${category}</span>${verified}</div>
          <div class="atom-text"><strong>${title}</strong></div>
          <div class="atom-text">${preview}</div>
          <div class="atom-meta">${meta}</div>
          <div class="atom-actions"><button class="btn btn-secondary show-in-3d-btn" type="button">Show on map</button></div>
        </div>
      `;
      const showBtn = el.querySelector('.show-in-3d-btn');
      if (showBtn) {
        showBtn.addEventListener('click', (ev) => {
          ev.stopPropagation();
          const id = String(a.punkto || '').replace(/^p:/, '');
          focusPunkto(id);
        });
      }
      elAtomList.appendChild(el);
    }
  }

  // Re-render deck.gl
  await renderAtoms(newAtomIds);
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Relative time formatter for bubble meta line.
 * tSec is accepted as ms (we already store Date.now() in atom.t).
 */
function fmtRelativeTime(t) {
  const ms = Number(t);
  if (!ms) return '?';
  const diff = Date.now() - ms;
  if (diff < 60_000)       return 'just now';
  if (diff < 3_600_000)    return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000)   return `${Math.floor(diff / 3_600_000)}h ago`;
  if (diff < 604_800_000)  return `${Math.floor(diff / 86_400_000)}d ago`;
  if (diff < 2_419_200_000)return `${Math.floor(diff / 604_800_000)}w ago`;
  return fmtTime(ms);
}

/**
 * Markdown-lite renderer for atom text. Returns HTML string safe for innerHTML.
 * Supported:
 *   **bold** → <b>bold</b>
 *   *italic* → <i>italic</i>
 *   [text](https://url) → safe anchor (rejects javascript:, data:, etc.)
 *   bare https?://… → auto-linked
 *   
 → <br>
 * Emoji render natively via system font — no special handling.
 *
 * Security: everything is HTML-escaped FIRST, then markdown is applied to
 * the escaped text. URL schemes are whitelisted to http(s) only, so a
 * payload like [click](javascript:alert(1)) simply does not match the regex
 * (which requires the url to start with http:// or https://) and remains
 * rendered as literal text.
 */
function renderAtomText(raw) {
  if (!raw) return '';
  // 1. HTML-escape everything first.
  let s = escHtml(raw);

  // 2. Bold BEFORE italic so ** isn't eaten by the italic regex.
  s = s.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  // Italic (single-star, non-greedy). After escHtml the user's * is still *.
  s = s.replace(/\*([^*]+)\*/g, '<i>$1</i>');

  // 3. Markdown links [text](http(s)://…) BEFORE bare-URL auto-link so we
  //    don't double-wrap. Note escHtml turns ] into ] untouched and ) into ).
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_m, label, url) => {
    return `<a href="${url}" target="_blank" rel="noopener noreferrer nofollow">${label}</a>`;
  });

  // 4. Bare URL auto-linker. Only http(s). Keep preceding whitespace or start.
  s = s.replace(/(^|[\s>])((?:https?:\/\/)[^\s<]+)/g, (_m, pre, url) => {
    return `${pre}<a href="${url}" target="_blank" rel="noopener noreferrer nofollow">${url}</a>`;
  });

  // 5. Newlines → <br>
  s = s.replace(/\n/g, '<br>');

  return s;
}

// ---------------------------------------------------------------------------
// Panel toggle
// ---------------------------------------------------------------------------

let panelOpen = false;

function setPanelOpen(open) {
  panelOpen = open;
  elPanel.classList.toggle('open', open);
  elMapEl.classList.toggle('panel-open', open);
  elFabAdd.classList.toggle('panel-open', open);
  elFabPanel.classList.toggle('panel-open', open);
  if (map) map.resize();
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------

// Altitude input state for the modal.
// mode: 'floor' when a building is detected at map center, 'meter' otherwise.
// In floor mode the slider value IS the floor number; in meter mode it IS metres.
const FLOOR_HEIGHT_M = 3; // default floor height (configurable later)
let modalAltitudeState = {
  mode: 'meter',   // 'floor' | 'meter'
  building: null,  // { name, height, maxFloor } | null
};
let placementDraft = null;

/**
 * Detect whether the map center is over a building feature.
 * Returns { building: {name, height, maxFloor} | null }.
 */
function detectBuildingAtCenter() {
  if (!map) return { building: null };
  try {
    const center = map.getCenter();
    const screenPt = map.project(center);
    const layers = (map.getStyle().layers || [])
      .filter(l => l.type === 'fill-extrusion'
                || (l.id && l.id.toLowerCase().includes('building')))
      .map(l => l.id);
    if (layers.length === 0) return { building: null };
    // Box query with ~30px tolerance so users don't need pixel-perfect centering.
    // If the crosshair is near a building (e.g. between towers or on a narrow gap),
    // we still detect the nearby building and offer a floor picker.
    const R = 30;
    const box = [
      [screenPt.x - R, screenPt.y - R],
      [screenPt.x + R, screenPt.y + R],
    ];
    const features = map.queryRenderedFeatures(box, { layers });
    if (!features || features.length === 0) return { building: null };
    // Among candidates, pick the one with the greatest height (most relevant for
    // a floor picker). Fall back through render_height, height, building:levels.
    const heightOf = (props) => {
      let h = Number(props.render_height);
      if (!Number.isFinite(h) || h <= 0) h = Number(props.height);
      if (!Number.isFinite(h) || h <= 0) {
        const levels = Number(props['building:levels']);
        if (Number.isFinite(levels) && levels > 0) h = levels * FLOOR_HEIGHT_M;
      }
      return Number.isFinite(h) && h > 0 ? h : 0;
    };
    let best = null;
    let bestHeight = 0;
    for (const f of features) {
      const h = heightOf(f.properties || {});
      if (h > bestHeight) {
        best = f;
        bestHeight = h;
      }
    }
    if (!best || bestHeight < FLOOR_HEIGHT_M) {
      return { building: null };
    }
    const props = best.properties || {};
    const name = (props.name && String(props.name).trim()) || null;
    const maxFloor = Math.max(1, Math.floor(bestHeight / FLOOR_HEIGHT_M));
    return { building: { name, height: bestHeight, maxFloor } };
  } catch (e) {
    console.warn('[modal] detectBuildingAtCenter failed:', e);
    return { building: null };
  }
}

/**
 * Update the live crosshair readout (the small "scope" label below the
 * crosshair). Shows the detected building's name, floors, and height, or
 * nothing if no building is beneath the crosshair.
 */
function updateCrosshairReadout() {
  if (!elCrosshairReadout) return;
  const { building } = detectBuildingAtCenter();
  if (!building) {
    elCrosshairReadout.textContent = '';
    return;
  }
  const h = Math.round(building.height);
  const parts = [];
  if (building.name) parts.push(building.name);
  parts.push(`${building.maxFloor}F`);
  parts.push(`${h}m`);
  elCrosshairReadout.textContent = parts.join(' · ');
}

/**
 * Read the altitude (in metres) currently selected in the modal.
 * Returns 0 if the slider or state is in any unexpected form.
 */
function getModalAltitudeMeters() {
  if (!elModalAltitudeSlider) return 0;
  const raw = Number(elModalAltitudeSlider.value);
  if (!Number.isFinite(raw) || raw < 0) return 0;
  if (modalAltitudeState.mode === 'floor') {
    return raw * FLOOR_HEIGHT_M;
  }
  return raw;
}

/**
 * Re-render the primary/secondary/hint labels from the current slider value
 * and the current mode. Safe to call on every 'input' event.
 */
function updateAltitudeLabels() {
  if (!elModalAltitudeSlider) return;
  const val = Number(elModalAltitudeSlider.value) || 0;
  if (modalAltitudeState.mode === 'floor') {
    const floor = Math.round(val);
    const meters = floor * FLOOR_HEIGHT_M;
    elModalAltitudePrimary.innerHTML = floor === 0
      ? 'Ground <span class="alt-cyan">(Floor 0)</span>'
      : `Floor <span class="alt-cyan">${floor}</span>`;
    elModalAltitudeSecondary.textContent = `+${meters} m above ground`;
    const b = modalAltitudeState.building;
    const name = (b && b.name) ? b.name : 'Building';
    const maxFloor = (b && b.maxFloor) ? b.maxFloor : 1;
    elModalAltitudeHint.textContent =
      `Detected: ${name} · ${maxFloor} floor${maxFloor === 1 ? '' : 's'}`;
  } else {
    const meters = Math.round(val);
    const est = Math.round(meters / FLOOR_HEIGHT_M);
    elModalAltitudePrimary.innerHTML = meters === 0
      ? 'Ground level'
      : `<span class="alt-cyan">+${meters} m</span> above ground`;
    elModalAltitudeSecondary.textContent = meters === 0
      ? '~Floor 0'
      : `~Floor ${est}`;
    elModalAltitudeHint.textContent = meters === 0
      ? ''
      : '(estimated, no building detected)';
  }
  // Keep the location display in sync with chosen altitude.
  if (placementDraft) {
    placementDraft.altitude_m = getModalAltitudeMeters();
    if (modalAltitudeState.mode === 'floor') {
      placementDraft.floor_hint = Math.round(Number(elModalAltitudeSlider.value) || 0);
    } else {
      placementDraft.floor_hint = Math.round(placementDraft.altitude_m / FLOOR_HEIGHT_M);
    }
  }
  refreshModalLocationDisplay();
  renderPlacementPreview();
}

/**
 * Recompute and display the modal location using the current altitude.
 */
function refreshModalLocationDisplay() {
  if (!map || !elModalLocation) return;
  const alt = getModalAltitudeMeters();
  const center = placementDraft ? { lat: placementDraft.lat, lng: placementDraft.lon } : map.getCenter();
  const punkto = encodeLocation(center.lat, center.lng, alt);
  const loc = decodeAtomLocation(punkto);
  let suffix = '';
  if (alt > 0) {
    if (modalAltitudeState.mode === 'floor') {
      const floor = Math.round(Number(elModalAltitudeSlider.value) || 0);
      suffix = `  ·  Floor ${floor} (+${floor * FLOOR_HEIGHT_M}m)`;
    } else {
      suffix = `  ·  +${Math.round(alt)}m`;
    }
  }
  if (loc) {
    elModalLocation.textContent =
      `${punkto}  ·  ${fmtCoords(loc.lat, loc.lon, loc.alt)}${suffix}`;
  } else {
    elModalLocation.textContent = punkto + suffix;
  }
}

/**
 * Configure the altitude slider UI for the current map context.
 * Resets the slider to 0 (ground / floor 0) — friction-free default.
 */
function setupAltitudeInput() {
  if (!elModalAltitudeSlider) return;
  const { building } = detectBuildingAtCenter();
  if (building) {
    modalAltitudeState = { mode: 'floor', building };
    elModalAltitudeSlider.min = '0';
    elModalAltitudeSlider.max = String(building.maxFloor);
    elModalAltitudeSlider.step = '1';
    elModalAltitudeSlider.value = '0';
  } else {
    modalAltitudeState = { mode: 'meter', building: null };
    elModalAltitudeSlider.min = '0';
    elModalAltitudeSlider.max = '100';
    elModalAltitudeSlider.step = '1';
    elModalAltitudeSlider.value = '0';
  }
  updateAltitudeLabels();
  if (elModalRoofBtn) elModalRoofBtn.disabled = !building;
  if (elModalDeviceAltBtn) elModalDeviceAltBtn.disabled = true;
}

function openModal() {
  elModalError.textContent = '';
  elModalText.value = '';
  // Keep author value between sessions (restore from localStorage)
  elModalAuthor.value = localStorage.getItem('punkto-author') || '';

  // Configure altitude input (building-aware) and render labels/location.
  setupAltitudeInput();
  const center = map ? map.getCenter() : { lat: 0, lng: 0 };
  placementDraft = {
    lat: center.lat,
    lon: center.lng,
    altitude_m: 0,
    floor_hint: 0,
    placement_mode: 'ground',
  };
  requestDeviceAltitude();

  elModalOverlay.classList.add('open');
  setTimeout(() => elModalText.focus(), 80);
}

function closeModal() {
  elModalOverlay.classList.remove('open');
  // Reset altitude state so next open is friction-free at ground level.
  if (elModalAltitudeSlider) elModalAltitudeSlider.value = '0';
  placementDraft = null;
  renderPlacementPreview();
}

function renderPlacementPreview() {
  renderAtoms();
}

function setAltitudeMeters(meters, mode = 'manual') {
  const v = Math.max(0, Math.round(Number(meters) || 0));
  if (modalAltitudeState.mode === 'floor') {
    const floor = Math.round(v / FLOOR_HEIGHT_M);
    elModalAltitudeSlider.value = String(floor);
    if (elModalFloorValue) elModalFloorValue.value = String(floor);
  } else {
    elModalAltitudeSlider.value = String(v);
  }
  if (elModalManualAltitude) elModalManualAltitude.value = String(v);
  if (placementDraft) placementDraft.placement_mode = mode;
  updateAltitudeLabels();
}

function requestDeviceAltitude() {
  if (!navigator.geolocation || !elModalDeviceAltBtn) return;
  navigator.geolocation.getCurrentPosition((pos) => {
    const alt = pos?.coords?.altitude;
    if (alt == null || !Number.isFinite(alt)) {
      elModalDeviceAltBtn.style.display = 'none';
      return;
    }
    elModalDeviceAltBtn.style.display = '';
    elModalDeviceAltBtn.disabled = false;
    elModalDeviceAltBtn.dataset.altitude = String(Math.round(alt));
  }, () => {
    elModalDeviceAltBtn.style.display = 'none';
  }, { enableHighAccuracy: true, timeout: 5000 });
}

async function submitAtom() {
  const text   = elModalText.value.trim();
  const author = elModalAuthor.value.trim();
  const altMeters = getModalAltitudeMeters();
  const center = placementDraft ? { lat: placementDraft.lat, lng: placementDraft.lon } : map.getCenter();
  const punkto = encodeLocation(center.lat, center.lng, altMeters);
  const t      = Date.now();

  const atom = { punkto, t };
  if (text)   atom.x = text;
  if (author) atom.f = author;

  elModalSubmit.disabled = true;
  elModalError.textContent = '';

  try {
    // Save author preference
    if (author) localStorage.setItem('punkto-author', author);

    // Post via protocol-native round-robin load balancer
    const json = await postAtomToNetwork(atom);

    // Also save locally immediately
    await upsertAtom(atom);
    // Update cursor if returned
    if (typeof json.cursor === 'number') {
    }

    closeModal();
    await refreshUI();
    setSyncStatus('ok');

    // Fly to the new atom
    const loc = decodeAtomLocation(punkto);
    if (loc && map) {
      map.flyTo({ center: [loc.lon, loc.lat], zoom: Math.max(map.getZoom(), 14) });
    }
  } catch (err) {
    console.error('[addAtom]', err);
    elModalError.textContent = `Error: ${err.message}`;
  } finally {
    elModalSubmit.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Map initialisation
// ---------------------------------------------------------------------------

function initMap() {
  const { MapboxOverlay } = window.deck;

  map = new maplibregl.Map({
    container: 'map',
    style: MAP_STYLE,
    center: [12.5, 55.7],
    zoom: 9,
    pitch: 45,
    bearing: -10,
    antialias: true,
  });

  map.on('error', e => {
    console.warn('[map] error (ignored):', e.error && e.error.message);
  });

  // Add navigation controls
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');

  // Try to geolocate
  map.addControl(
    new maplibregl.GeolocateControl({
      positionOptions: { enableHighAccuracy: true },
      trackUserLocation: false,
      showUserLocation: true,
      showAccuracyCircle: false,
    }),
    'bottom-right'
  );

  // deck.gl overlay
  deckOverlay = new MapboxOverlay({
    interleaved: false,
    layers: [],
  });
  map.addControl(deckOverlay);

  map.on('load', async () => {
    console.log('[map] loaded');

    // Update DOM bubble LOD whenever zoom or pan changes.
    map.on('zoomend', () => { updateBubbleVisibility(); drawLeaderLines(); updateCrosshairReadout(); });
    map.on('moveend', () => { updateBubbleVisibility(); drawLeaderLines(); updateCrosshairReadout(); });

    // Ensure the SVG overlay exists and is redrawn on every map render event
    // so leader lines track pan/zoom/pitch/bearing smoothly.
    ensureLeaderOverlay();
    map.on('render', drawLeaderLines);
    map.on('click', (e) => {
      if (!elModalOverlay.classList.contains('open')) {
        openModal();
      }
      if (placementDraft) {
        placementDraft.lat = e.lngLat.lat;
        placementDraft.lon = e.lngLat.lng;
        refreshModalLocationDisplay();
        renderPlacementPreview();
      }
    });

    // Add 3D building extrusion layer (OpenFreeMap has openmaptiles source)
    try {
      map.addLayer({
        id: 'buildings-3d',
        type: 'fill-extrusion',
        source: 'openmaptiles',
        'source-layer': 'building',
        minzoom: 12,
        paint: {
          'fill-extrusion-color': '#1a1a2e',
          'fill-extrusion-height': ['coalesce', ['get', 'render_height'], ['get', 'height'], 5],
          'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], 0],
          'fill-extrusion-opacity': 0.9,
        },
      });
    } catch (e) {
      console.warn('[map] 3D buildings layer failed:', e);
    }

    await refreshUI();

    // Init load balancer registry and seed Dexie nodes table with SEED_NODES
    initNodeRegistry();
    for (const url of SEED_NODES) {
      const existing = await db.nodes.get(url);
      if (!existing) {
        await db.nodes.put({ url, cursor: 0 });
        console.log('[lb] seeded node:', url);
      }
    }

    // Discover peers from all known nodes, then start sync
    await discoverPeers();
    await syncFeed();
    initialSyncDone = true;
    await refreshUI();

    // If the user opened a /p/<id> deep-link, focus it now that atoms are loaded
    if (deepLinkPunkto) {
      await focusPunkto(deepLinkPunkto);
    }

    // Show first-visit onboarding hint (skipped for deep-link visitors and repeat users)
    showOnboarding();

    syncTimer = setInterval(syncFeed, SYNC_INTERVAL_MS);
  });
}

// ---------------------------------------------------------------------------
// 3D toggle
// ---------------------------------------------------------------------------

function toggle3D() {
  is3D = !is3D;
  if (is3D) {
    map.easeTo({ pitch: 45, bearing: -10, duration: 800 });
    elToggle3D.textContent = '2D';
    elToggle3D.title = 'Switch to 2D view';
  } else {
    map.easeTo({ pitch: 0, bearing: 0, duration: 800 });
    elToggle3D.textContent = '3D';
    elToggle3D.title = 'Switch to 3D view';
  }
}

// ---------------------------------------------------------------------------
// Event wiring
// ---------------------------------------------------------------------------


// ---------------------------------------------------------------------------
// Cache reset
// ---------------------------------------------------------------------------

async function resetCache() {
  if (!confirm('This will delete all locally cached atoms and reload the app. Continue?')) return;
  try { await db.delete(); } catch(e) {}
  if ('serviceWorker' in navigator) {
    const regs = await navigator.serviceWorker.getRegistrations();
    for (const r of regs) await r.unregister();
  }
  if ('caches' in window) {
    const keys = await caches.keys();
    for (const k of keys) await caches.delete(k);
  }
  location.reload(true);
}

// ---------------------------------------------------------------------------
// First-visit onboarding hint
// ---------------------------------------------------------------------------

const ONBOARDING_KEY = 'punkto.onboarded';
const ONBOARDING_TIMEOUT_MS = 10_000;
let onboardingShown = false;
let onboardingTimer = null;
let onboardingDismissHandlers = null;

function shouldShowOnboarding() {
  if (!elOnboardingHint) return false;
  if (deepLinkPunkto) return false; // deep-link visitors already know
  try {
    return localStorage.getItem(ONBOARDING_KEY) !== '1';
  } catch {
    return false;
  }
}

function dismissOnboarding() {
  if (!onboardingShown) return;
  onboardingShown = false;
  if (elOnboardingHint) {
    elOnboardingHint.classList.remove('open');
    elOnboardingHint.setAttribute('aria-hidden', 'true');
  }
  if (onboardingTimer) { clearTimeout(onboardingTimer); onboardingTimer = null; }
  // Remove dismiss listeners
  if (onboardingDismissHandlers) {
    const { onInteract, onMapMove } = onboardingDismissHandlers;
    document.removeEventListener('pointerdown', onInteract, true);
    document.removeEventListener('keydown', onInteract, true);
    if (map) {
      map.off('movestart', onMapMove);
      map.off('zoomstart', onMapMove);
    }
    onboardingDismissHandlers = null;
  }
  try { localStorage.setItem(ONBOARDING_KEY, '1'); } catch {}
}

function showOnboarding() {
  if (!shouldShowOnboarding()) return;
  onboardingShown = true;
  elOnboardingHint.classList.add('open');
  elOnboardingHint.setAttribute('aria-hidden', 'false');

  // Auto-dismiss after timeout
  onboardingTimer = setTimeout(dismissOnboarding, ONBOARDING_TIMEOUT_MS);

  // Dismiss on any user interaction. Use capture so we catch before handlers.
  const onInteract = () => dismissOnboarding();
  const onMapMove = () => dismissOnboarding();
  onboardingDismissHandlers = { onInteract, onMapMove };
  document.addEventListener('pointerdown', onInteract, true);
  document.addEventListener('keydown', onInteract, true);
  if (map) {
    map.on('movestart', onMapMove);
    map.on('zoomstart', onMapMove);
  }
}

// ---------------------------------------------------------------------------
// Settings menu
// ---------------------------------------------------------------------------

let settingsOpen = false;

function hostOf(url) {
  try { return new URL(url).host; } catch { return url; }
}

// ---------------------------------------------------------------------------
// Mnemonic modal — shows generated key words in-app (no window.alert)
// ---------------------------------------------------------------------------
function showMnemonicModal(identity) {
  const overlay = document.getElementById('mnemonic-overlay');
  const wordsEl = document.getElementById('mnemonic-words');
  const authorEl = document.getElementById('mnemonic-author');
  if (!overlay || !wordsEl) return;
  wordsEl.innerHTML = identity.mnemonic.map((w, i) =>
    `<div class="mnemonic-word"><span class="wn">${i + 1}.</span>${w}</div>`
  ).join('');
  authorEl.textContent = `Author ID: ${identity.authorId}`;
  overlay.classList.add('open');
  const copyBtn = document.getElementById('btn-mnemonic-copy');
  const closeBtn = document.getElementById('btn-mnemonic-close');
  copyBtn.onclick = () => {
    navigator.clipboard.writeText(identity.mnemonic.join(' ')).then(() => {
      copyBtn.textContent = 'Copied!';
      setTimeout(() => { copyBtn.textContent = 'Copy words'; }, 2000);
    }).catch(() => {
      copyBtn.textContent = identity.mnemonic.join(' ');
    });
  };
  closeBtn.onclick = () => overlay.classList.remove('open');
}

/**
 * unreachably large `since` value — node.py clamps it to file_size and returns
 * `{cursor, atoms: []}`. Zero-payload, cheap, works against any Punkto node.
 * Returns a non-negative integer cursor, or null on error.
 */
async function fetchNodeCursor(url) {
  try {
    const res = await fetch(`${url}/feed?cursor=9999999999`, {
      signal: AbortSignal.timeout(6_000),
    });
    if (!res.ok) return null;
    const json = await res.json();
    return typeof json.cursor === 'number' ? json.cursor : null;
  } catch {
    return null;
  }
}

/**
 * Fetch /info for a node. Returns null on error, or the parsed JSON on success.
 */
async function fetchNodeInfo(url) {
  try {
    const res = await fetch(`${url}/info`, {
      signal: AbortSignal.timeout(6_000),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Refresh visible atom count in settings header. Synchronous, cheap — safe to
 * call from the UI-render path.
 */
function updateSettingsCount(count) {
  if (elSettingsCount && typeof count === 'number') {
    elSettingsCount.textContent = String(count);
  }
}

/**
 * Refresh the node + peer info block in the settings menu. Runs on-demand
 * (each time the menu opens) so we never poll. Updates topbar sync-indicator
 * to reflect lag status. Gracefully degrades when peers are unreachable or
 * when /info doesn't advertise a peer list.
 */
async function refreshSettingsNetworkInfo() {
  if (!elSettingsNode) return;

  // Render the node row immediately with a "…" cursor placeholder so the menu
  // feels responsive while fetches are in flight.
  elSettingsNode.innerHTML = `${escHtml(hostOf(NODE_URL))} <span class="dim">(cursor …)</span>`;
  if (elSettingsPeers) elSettingsPeers.innerHTML = '<span class="dim">checking…</span>';

  // 1. Get local /info → peer URLs (fall back to SEED_NODES if absent).
  const localInfo = await fetchNodeInfo(NODE_URL);
  let peerUrls = Array.isArray(localInfo?.peers) ? localInfo.peers.slice() : [];
  if (peerUrls.length === 0) {
    // Fall back to seed nodes minus current origin
    peerUrls = SEED_NODES.filter(u => u.replace(/\/$/, '') !== NODE_URL.replace(/\/$/, ''));
  }
  peerUrls = peerUrls.map(u => u.replace(/\/$/, ''));

  // 2. Fetch cursors in parallel: local + each peer.
  const [localCursor, ...peerCursors] = await Promise.all([
    fetchNodeCursor(NODE_URL),
    ...peerUrls.map(fetchNodeCursor),
  ]);

  // 3. Compute lag (local behind highest peer).
  const reachablePeerCursors = peerCursors.filter(c => typeof c === 'number');
  const maxPeerCursor = reachablePeerCursors.length
    ? Math.max(...reachablePeerCursors) : 0;
  const lag = (typeof localCursor === 'number' && maxPeerCursor > localCursor)
    ? (maxPeerCursor - localCursor) : 0;

  // 4. Render node row
  const warnIcon = lag > 0 ? ' <span class="lag-warn" title="This node is behind peers">⚠</span>' : '';
  const localCursorStr = typeof localCursor === 'number'
    ? `cursor ${localCursor}` : 'unreachable';
  elSettingsNode.innerHTML =
    `${escHtml(hostOf(NODE_URL))} <span class="dim">(${localCursorStr})</span>${warnIcon}`;

  // 5. Render peers list
  if (elSettingsPeers) {
    if (peerUrls.length === 0) {
      elSettingsPeers.innerHTML = '<span class="dim">none</span>';
    } else {
      const rows = peerUrls.map((url, i) => {
        const c = peerCursors[i];
        if (typeof c !== 'number') {
          return `${escHtml(hostOf(url))} <span class="dim">(unreachable)</span>`;
        }
        const diff = typeof localCursor === 'number' ? (c - localCursor) : 0;
        let diffStr = '';
        if (diff > 0) diffStr = ` <span class="lag-warn">↓${diff} behind</span>`;
        else if (diff < 0) diffStr = ` <span class="dim">↑${-diff} ahead</span>`;
        return `${escHtml(hostOf(url))} <span class="dim">(cursor ${c}${diffStr ? '' : ''})</span>${diffStr}`;
      });
      elSettingsPeers.innerHTML = rows.join('<br>');
    }
  }

  // 6. Topbar indicator: amber dot when behind, regardless of sync state
  if (elSyncDot) {
    elSyncDot.classList.toggle('lagging', lag > 0);
    if (lag > 0) elSyncDot.title = `Behind peers by ${lag} bytes`;
    else elSyncDot.title = 'sync status';
  }
}

async function openSettingsMenu() {
  settingsOpen = true;
  elSettingsMenu.classList.add('open');
  elSettingsMenu.setAttribute('aria-hidden', 'false');
  const bd = document.getElementById('settings-backdrop');
  if (bd) bd.classList.add('open');
  // Update visible atom count immediately from the DB-backed UI state
  try {
    const all = await db.atoms.toArray();
    updateSettingsCount(all.filter(a => !isHiddenAtom(a)).length);
  } catch {
    updateSettingsCount(0);
  }
  // Kick off network info refresh (no await — menu is already visible).
  refreshSettingsNetworkInfo();
}

function closeSettingsMenu() {
  settingsOpen = false;
  elSettingsMenu.classList.remove('open');
  elSettingsMenu.setAttribute('aria-hidden', 'true');
  const bd = document.getElementById('settings-backdrop');
  if (bd) bd.classList.remove('open');
}

function toggleSettingsMenu() {
  if (settingsOpen) closeSettingsMenu();
  else openSettingsMenu();
}

function wireEvents() {
  // Panel toggle
  elFabPanel.addEventListener('click', () => setPanelOpen(!panelOpen));
  elPanelClose.addEventListener('click', () => setPanelOpen(false));

  // 3D toggle
  elToggle3D.addEventListener('click', toggle3D);

  // Settings menu
  if (elBtnSettings) {
    elBtnSettings.addEventListener('click', e => {
      e.stopPropagation();
      toggleSettingsMenu();
    });
  }
  if (elSettingsMenu) {
    // Prevent clicks inside the menu from closing it
    elSettingsMenu.addEventListener('click', e => e.stopPropagation());
  }
  if (elSettingsReset) {
    elSettingsReset.addEventListener('click', () => {
      closeSettingsMenu();
      resetCache();
    });
  }
  // Close settings on outside click
  document.addEventListener('click', () => {
    if (settingsOpen) closeSettingsMenu();
  });

  // Add atom
  elFabAdd.addEventListener('click', () => {
    dismissOnboarding();
    openModal();
  });
  elModalCancel.addEventListener('click', closeModal);
  elModalOverlay.addEventListener('click', e => {
    if (e.target === elModalOverlay) closeModal();
  });
  elModalSubmit.addEventListener('click', submitAtom);
  elModalText.addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submitAtom();
  });

  // Live-update altitude labels and location as the slider moves.
  if (elModalAltitudeSlider) {
    elModalAltitudeSlider.addEventListener('input', updateAltitudeLabels);
    elModalAltitudeSlider.addEventListener('change', updateAltitudeLabels);
  }
  if (elModalGroundBtn) elModalGroundBtn.addEventListener('click', () => setAltitudeMeters(0, 'ground'));
  if (elModalRoofBtn) elModalRoofBtn.addEventListener('click', () => {
    const b = modalAltitudeState.building;
    if (!b) return;
    setAltitudeMeters(b.height, 'roof');
  });
  if (elModalFloorMinus) elModalFloorMinus.addEventListener('click', () => {
    const v = Math.max(0, (Number(elModalFloorValue?.value) || 0) - 1);
    if (elModalFloorValue) elModalFloorValue.value = String(v);
    setAltitudeMeters(v * FLOOR_HEIGHT_M, 'manual');
  });
  if (elModalFloorPlus) elModalFloorPlus.addEventListener('click', () => {
    const v = (Number(elModalFloorValue?.value) || 0) + 1;
    if (elModalFloorValue) elModalFloorValue.value = String(v);
    setAltitudeMeters(v * FLOOR_HEIGHT_M, 'manual');
  });
  if (elModalFloorValue) elModalFloorValue.addEventListener('input', () => {
    const v = Math.max(0, Number(elModalFloorValue.value) || 0);
    setAltitudeMeters(v * FLOOR_HEIGHT_M, 'manual');
  });
  if (elModalManualAltitude) elModalManualAltitude.addEventListener('input', () => {
    setAltitudeMeters(Number(elModalManualAltitude.value) || 0, 'manual');
  });
  if (elModalDeviceAltBtn) elModalDeviceAltBtn.addEventListener('click', () => {
    const alt = Number(elModalDeviceAltBtn.dataset.altitude);
    if (!Number.isFinite(alt)) return;
    setAltitudeMeters(alt, 'device');
  });

  // Handle keyboard escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeModal();
      setPanelOpen(false);
      if (settingsOpen) closeSettingsMenu();
    }
  });

  // Geolocation permission detection for location empty state
  if (navigator.permissions) {
    navigator.permissions.query({ name: 'geolocation' }).then(perm => {
      _locationDenied = perm.state === 'denied';
      perm.onchange = () => {
        _locationDenied = perm.state === 'denied';
        if (currentPage === 'text') renderMainFeed();
      };
    }).catch(() => {});
  } else if (!navigator.geolocation) {
    _locationDenied = true;
  }
  // 'Enable location' button — triggers a permission prompt
  document.addEventListener('click', e => {
    if (e.target && e.target.id === 'main-location-btn') {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          () => { _locationDenied = false; renderMainFeed(); },
          () => { _locationDenied = true;  renderMainFeed(); }
        );
      }
    }
  });

  // Bottom navigation, feed-card delegation, and "Leave note here" CTA are
  // wired by the ui-shell.js and ui-text.js modules, registered in boot().
  setupKeyManagement(); // registered here, not from atom handler
}
// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

async function boot() {
  console.log('PUNKTO APP.JS LOADED v52 HARD MARKER 2026-05-16-1');
  window.PUNKTO_APP_VERSION = 'v52-hard-marker-2026-05-16-1';

  // Global click capture — diagnostic: logs every click to console
  document.addEventListener('click', (ev) => {
    console.log('[CLICK CAPTURE]', {
      tag: ev.target?.tagName,
      id: ev.target?.id,
      cls: ev.target?.className,
      text: (ev.target?.innerText || ev.target?.textContent || '').trim().slice(0, 40),
      closestSettingsItem: ev.target?.closest?.('.settings-item')?.id,
    });
  }, true);
  console.log('[punkto] booting...');

  // Verify deck.gl UMD is available
  if (!window.deck || !window.deck.MapboxOverlay) {
    console.error('[punkto] deck.gl not loaded — check CDN script tag');
    return;
  }
  if (!window.maplibregl) {
    console.error('[punkto] MapLibre GL not loaded — check CDN script tag');
    return;
  }
  if (!window.Dexie) {
    console.error('[punkto] Dexie not loaded — check CDN script tag');
    return;
  }

  // Capture /p/<id> deep-link BEFORE wiring so map load can act on it.
  deepLinkPunkto = parseDeepLinkPunktoId();
  if (deepLinkPunkto) {
    console.log('[punkto] deep-link detected:', `p:${deepLinkPunkto}`);
  }

  // Cache-first: pre-render cached atom count and hide empty state flash.
  // This runs before the map finishes loading so users never see the
  // "No atoms yet. Syncing…" placeholder when IndexedDB already has atoms.
  try {
    // Count only visible atoms so the number matches what actually renders.
    const cachedAll = await db.atoms.toArray();
    const cachedCount = cachedAll.filter(a => !isHiddenAtom(a)).length;
    elCountNum.textContent = cachedCount;
    if (elSettingsCount) elSettingsCount.textContent = String(cachedCount);
    if (cachedCount > 0) {
      elAtomEmpty.style.display = 'none';
    } else {
      // Keep hidden until initial sync completes.
      elAtomEmpty.style.display = 'none';
    }
  } catch (e) {
    console.warn('[punkto] cache-first prerender failed:', e);
  }

  wireEvents();

  // Wire UI modules (shell / text / map). Callbacks delegate back to app.js
  // so app.js still owns data and lifecycle; modules own DOM/markup/state.
  initShell({
    onShowText: () => renderMainFeed(),
    onShowMap: () => {
      if (!map) initMap();
      else requestAnimationFrame(() => { if (map) map.resize(); });
    },
    onAdd: () => { dismissOnboarding(); openModal(); },
    onOpenSettings: () => {
      renderNetworkPage();
      renderMePage();
      shellToggleSettings();
      if (shellIsSettingsOpen()) {
        // refresh dynamic settings data when opening
        openSettingsMenu().catch(() => {});
      }
    },
  });
  initTextView({
    onShowOnMap: (id) => focusPunkto(id),
    onLeaveNote: () => { dismissOnboarding(); openModal(); },
    helpers: {
      escHtml, deriveTitle, deriveCategory, isVerifiedAtom,
      fmtAltitudeLabel, fmtDistance, fmtTime,
    },
  });
  initMapView({
    getMap: () => map,
    initMap: () => initMap(),
  });

  // Default to main view; go straight to 3D if deep-linking to a specific punkto
  showPage(deepLinkPunkto ? 'map' : 'text');
  if (deepLinkPunkto) setPanelOpen(false); // panel managed by 3D view when deep-linking
}

boot();


// --- Key Management ---
let currentIdentity = null;

function displayKeyInfo(identity) {
  const keyInfo = document.getElementById('key-info');
  const authorIdEl = document.getElementById('key-author-id');
  const pubkeyEl = document.getElementById('key-pubkey');
  const mnemonicEl = document.getElementById('key-mnemonic');
  if (!keyInfo) return;
  if (!identity) { keyInfo.style.display = 'none'; return; }
  keyInfo.style.display = 'block';
  if (authorIdEl) authorIdEl.textContent = identity.authorId;
  if (pubkeyEl)   pubkeyEl.textContent = identity.pubkey.slice(0, 20) + '...';
  if (mnemonicEl) mnemonicEl.textContent = identity.mnemonic.join(' ');
}

function setupKeyManagement() {
  // Capture-phase delegation — fires before any overlay stopPropagation
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.settings-item');
    if (!btn) return;
    const id = btn.id;

    if (id === 'btn-generate-key') {
      e.preventDefault();
      try {
        if (typeof window.generateIdentity !== 'function') {
          console.error('[identity] generateIdentity not loaded');
          return;
        }
        const identity = await window.generateIdentity();
        currentIdentity = identity;
        displayKeyInfo(identity);
        showMnemonicModal(identity);
      } catch (err) {
        console.error('[identity] generate failed:', err);
      }
      return;
    }

    if (id === 'btn-import-key') {
      const input = document.createElement('input');
      input.type = 'file'; input.accept = '.json';
      input.onchange = async (ev) => {
        const file = ev.target.files[0]; if (!file) return;
        try {
          const identity = importKeyFromJson(await file.text());
          currentIdentity = identity; displayKeyInfo(identity);
        } catch (err) { console.error('[identity] import failed:', err); }
      };
      input.click(); return;
    }

    if (id === 'btn-save-key') {
      if (!currentIdentity) return;
      if (!confirm('localStorage is not secure. Save temporarily?')) return;
      localStorage.setItem('punkto-identity', JSON.stringify(currentIdentity));
      return;
    }

    if (id === 'btn-load-key') {
      const saved = localStorage.getItem('punkto-identity');
      if (!saved) return;
      try {
        const identity = JSON.parse(saved);
        currentIdentity = identity; displayKeyInfo(identity);
      } catch (err) { console.error('[identity] load failed:', err); }
      return;
    }

    if (id === 'btn-print-mnemonic') {
      if (!currentIdentity) return;
      const words = currentIdentity.mnemonic.map((w, i) =>
        `<span>${i+1}. ${w}</span>`).join(' ');
      const win = window.open('', '_blank');
      win.document.write(`<!DOCTYPE html><html><head><title>Punkto Key</title>
<style>body{font-family:monospace;padding:20px;}</style></head>
<body><h1>Punkto Identity — KEEP SAFE</h1><p>${words}</p>
<p>Author: ${currentIdentity.authorId}</p></body></html>`);
      win.document.close(); win.print();
      return;
    }

    if (id === 'btn-export-key') {
      if (!currentIdentity) return;
      const blob = new Blob([exportKeyJson(currentIdentity)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'punkto-key.json'; a.click();
      return;
    }
  }, true);
}

