/**
 * app.js — Punkto PWA main application
 * Depends on: MapLibre GL JS, deck.gl 8.9.x UMD (window.deck), Dexie.js
 */

import {
  initShell,
  showPage as shellShowPage,
  openSettings as shellOpenSettings,
  closeSettings as shellCloseSettings,
  isSettingsOpen as shellIsSettingsOpen,
  setCounts as shellSetCounts,
} from './ui-shell.js';
import { initTextView, renderTextFeed, openBoardById, isReplyAtom, isRootAtom, getAtomStableId } from './ui-text.js';
import { initMapView, showMapView } from './ui-map.js';
import { initCreateModal, openCreateModal, closeCreateModal, setCreateError, setCreateSubmitting, updateCreateCenter, isCreateModalOpen } from './ui-create.js';
import { initSettingsView, renderSettingsView } from './ui-settings.js';
import { decodeAtomLocation, encodeCurrentLocation, encodeLocation, haversineMeters, FLOOR_HEIGHT_M } from './core/location.js';
import { db } from './storage/db.js';
import { upsertAtom, getAllAtomsNewestFirst, getAllAtoms } from './storage/atom-store.js';
import { ensureNode } from './storage/node-store.js';
import { fmtTime, fmtRelativeTime, fmtCoords, fmtDistance, fmtAltitudeLabel, deriveTitle, deriveCategory, escHtml, renderAtomText } from './core/display.js';
import { isHiddenAtom, isVerifiedAtom } from './core/atoms.js';
import { ensurePunktoPrefix, stripPunktoPrefix, parseDeepLinkPunktoId as parseDeepLinkPunktoIdFromPath } from './protocol/punkto-id.js';
import { computeAtomId } from './protocol/atom-id.js';
import { createNodeRegistry } from './sync/node-registry.js';
import { postAtomToNetwork, fetchNodeInfo, fetchNodeCursor } from './sync/network-client.js';
import { createSyncEngine } from './sync/sync-engine.js';

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

// Node registry + write round-robin (extracted sync ownership)
const nodeRegistry = createNodeRegistry({ nodeUrl: NODE_URL, seedNodes: SEED_NODES });
const CATEGORY_META = {
  TEXT: { code: 'TEXT', label: 'Talk', cls: 'cat-talk' },
  INFO: { code: 'INFO', label: 'Info', cls: 'cat-info' },
  WARN: { code: 'WARN', label: 'Warning', cls: 'cat-warn' },
  EMGC: { code: 'EMGC', label: 'Emergency', cls: 'cat-emgc' },
  EVNT: { code: 'EVNT', label: 'Event', cls: 'cat-evnt' },
  LOST: { code: 'LOST', label: 'Lost/Found', cls: 'cat-lost' },
};
function getCategoryMeta(atom) {
  const key = String(atom?.category || atom?.kind || '').trim().toUpperCase();
  return CATEGORY_META[key] || CATEGORY_META.TEXT;
}
function isOfficialDmiAtom(atom) {
  const kind = String(atom?.kind || '').trim().toUpperCase();
  const source = String(atom?.source || atom?.import_source || '').trim().toUpperCase();
  return kind === 'DMI_STATION_OBSERVATION' || source === 'DMI' || source === 'OFFICIAL_DMI_METOBS';
}
function officialDmiLine(atom) {
  if (!isOfficialDmiAtom(atom)) return '';
  const station = String(atom?.source_station_name || '').trim();
  const stationId = String(atom?.source_station_id || '').trim();
  const stationPart = station || stationId ? ` · ${[station, stationId].filter(Boolean).join(' ')}` : '';
  return `Official DMI import${stationPart}`;
}
let syncEngine = null;
let lastSyncAtMs = null;

// ---------------------------------------------------------------------------
// IndexedDB (Dexie)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let map = null;
let mapInitStarted = false;
let deckOverlay = null;
let is3D = true;
let initialSyncDone = false;
let deepLinkPunkto = null; // captured at boot, consumed after first refreshUI
// ============================================================
// Two-view shell — Text / Map
// ============================================================
let currentPage = 'text'; // 'text' | 'map'
let _mainFeedAtoms  = [];       // last sorted atom batch for main feed
let _locationDenied = false;    // true when geolocation denied/unavailable
let _mapScopedFeedReady = false;
let _refreshUiTimer = null;

// ── App shell: two views (Text / Map) ─────────────────────────────────────────
// showPage — thin wrapper. Body/nav state + page lifecycle live in ui-shell.js.
// Page-specific handlers (text feed render, map init/resize) are registered
// via initShell({ onShowText, onShowMap }) in boot().
function showPage(page) {
  currentPage = page;
  shellShowPage(page);
}

function replyBelongsToRoot(reply, root) {
  if (!isReplyAtom(reply) || !root) return false;
  const rootIds = [getAtomStableId(root), root.atom_id, root.id, root.punkto, stripPunktoPrefix(root.punkto || '')]
    .map((value) => String(value || '').trim())
    .filter(Boolean);
  const rootIdSet = new Set(rootIds);
  return [reply.parent_id, reply.root_id]
    .map((value) => String(value || '').trim())
    .filter(Boolean)
    .some((id) => rootIdSet.has(id) || rootIdSet.has(stripPunktoPrefix(id)));
}

function findRootForReply(reply, atoms = _mainFeedAtoms) {
  return (Array.isArray(atoms) ? atoms : []).find((candidate) => isRootAtom(candidate) && replyBelongsToRoot(reply, candidate)) || null;
}

function openBoardForAtom(atom, atoms = _mainFeedAtoms) {
  if (!atom || !atom.punkto) return;
  const localAtoms = Array.isArray(atoms) && atoms.length ? atoms : _mainFeedAtoms;
  const boardAtom = isReplyAtom(atom) ? (findRootForReply(atom, localAtoms) || findRootForReply(atom) || atom) : atom;
  const boardId = getAtomStableId(boardAtom) || stripPunktoPrefix(boardAtom.punkto);
  if (!boardId) return;
  showPage('text');
  openBoardById(boardId, { atom: boardAtom, atoms: _mainFeedAtoms });
}

function ensureMapInitialized() {
  console.log('[map] ensure init');
  if (map) {
    console.log('[map] init skipped existing');
    requestAnimationFrame(() => {
      if (map && typeof map.resize === 'function') map.resize();
    });
    return map;
  }
  console.log('[map] init start');
  return initMap();
}

// renderMainFeed — thin wrapper that delegates to ui-text.js renderTextFeed.
// Atom sorting/filtering is handled upstream in refreshUI()/syncFeed(), which
// populates module-level _mainFeedAtoms before calling this.
function renderMainFeed() {
  renderTextFeed({
    atoms: _mainFeedAtoms,
    locationDenied: _locationDenied,
    loadingVisibleAtoms: !_mapScopedFeedReady,
  });
}

function queueRefreshUI(newAtomIds = null, delayMs = 120) {
  if (_refreshUiTimer) clearTimeout(_refreshUiTimer);
  _refreshUiTimer = setTimeout(() => {
    _refreshUiTimer = null;
    refreshUI(newAtomIds).catch((err) => console.warn('[ui] refresh failed:', err));
  }, delayMs);
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
const elMainSyncDot = document.getElementById('main-sync-indicator');
const elMainStatusCount = document.getElementById('main-status-count');
const elPanel       = document.getElementById('panel');
const elFabAdd      = document.getElementById('fab-add');
const elFabPanel    = document.getElementById('fab-panel');
const elPanelClose  = document.getElementById('panel-close');
const elAtomList    = document.getElementById('atom-list');
const elAtomEmpty   = document.getElementById('atom-list-empty');
const elMapEl       = document.getElementById('map');
const elModalLocation = document.getElementById('modal-location');
const elToggle3D    = document.getElementById('toggle-3d');
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
  if (elMainSyncDot) elMainSyncDot.className = '';
  if (state) elSyncDot.classList.add(state);
  if (state && elMainSyncDot) elMainSyncDot.classList.add(state);
}
// ── Network page renderer ─────────────────────────────────────────────────────
// Shows live node/peer/sync data. Called by showPage('network').
function renderNetworkPage() {
  const syncText = (syncEngine && syncEngine.isSyncing()) ? 'syncing' : 'idle';
  renderSettingsView({
    network: {
      currentNode: NODE_URL,
      syncStatus: syncText,
      lastSync: lastSyncAtMs ? fmtTime(lastSyncAtMs) : 'not synced yet',
    },
  });

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



/**
 * Extract the spatial part of a canonical punkto and decode to coords.
 * e.g. 'p:u4pruydqqvj3-9xk3' → decode('u4pruydqqvj3')
 */
/**
 * Return true if an atom (DB record or feed entry) should be hidden from the UI
 * because its author handle is a known test/system handle. Case-insensitive.
 */
// ---------------------------------------------------------------------------
// Deep-link: /p/<id> → open and focus a punkto
// ---------------------------------------------------------------------------

/**
 * Parse a /p/<id> pathname. id = 12 base32 chars, optional '-suffix' (alnum).
 * Returns the full punkto id (without 'p:' prefix) or null.
 */
function parseDeepLinkPunktoId() {
  return parseDeepLinkPunktoIdFromPath(location.pathname || '');
}

/**
 * Focus a punkto by id: center map, open panel, highlight matching atom if cached.
 * Safe to call when no matching atom exists locally — we still center on the coords.
 */
async function focusPunkto(id) {
  // Switch to 3D page so the map is visible
  showPage('map');
  if (!id) return;
  const punkto = ensurePunktoPrefix(id);
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

// ---------------------------------------------------------------------------
// Sync
// ---------------------------------------------------------------------------

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
 * 'N Punkti at this place' heading followed by a list. Otherwise renders
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
    const sourceLine = officialDmiLine(a);
    html = [
      isOfficialDmiAtom(a) ? '<div class="popup-source-badge">Official DMI</div>' : '',
      text ? `<div class="popup-text">${escHtml(text)}</div>` : '',
      sourceLine ? `<div class="popup-source-line">${escHtml(sourceLine)} · not user-created content</div>` : '',
      `<div class="popup-meta">${escHtml(a.f || 'anon')} · ${timeStr}</div>`,
      `<div class="popup-canon">${escHtml(a.punkto)}</div>`,
      coordStr ? `<div class="popup-coords">${coordStr}</div>` : '',
    ].filter(Boolean).join('');
  } else {
    // Multi-atom: sort newest first, show all
    const sorted = atoms.slice().sort((a, b) => (b.t || 0) - (a.t || 0));
    const head = `<div class="popup-meta" style="font-weight:600;">${sorted.length} Punkti at this place</div>`;
    const items = sorted.map(a => {
      const text = a.text || a.x || '';
      const timeStr = fmtTime(a.t);
      const sourceLine = officialDmiLine(a);
      return [
        '<div class="popup-atom" style="margin-top:8px;padding-top:6px;border-top:1px solid #333;">',
        isOfficialDmiAtom(a) ? '<div class="popup-source-badge">Official DMI</div>' : '',
        text ? `<div class="popup-text">${escHtml(text)}</div>` : '',
        sourceLine ? `<div class="popup-source-line">${escHtml(sourceLine)}</div>` : '',
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
  const atoms = (await getAllAtomsNewestFirst())
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
      if (isOfficialDmiAtom(a)) return [255, 193, 7, 245];
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
        const baseRgba = isOfficialDmiAtom(a) ? [255, 193, 7, 245] : (h != null ? hueToRgba(h) : altToColor(a.alt));
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
    ev.stopPropagation();
    // Let anchors inside markdown-rendered text behave normally.
    if (ev.target.closest('a')) return;
    // Badge has its own handler attached in updateBubbleElement.
    if (ev.target.closest('.atom-bubble-count')) return;
    const loc = decodeAtomLocation(atom.punkto);
    if (!loc) return;
    // Read the current group from the element's stashed reference so
    // re-renders (which may update the group) stay in sync.
    const currentGroup = el._punktoGroup || [atom];
    const selectedAtom = currentGroup[0] || atom;
    openBoardForAtom(selectedAtom, currentGroup);
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
  const cat = getCategoryMeta(atom);
  const isDmi = isOfficialDmiAtom(atom);

  // Phase 2: stash group on element so click handler (set once in
  // buildBubbleElement) always sees the freshest atom list.
  el._punktoGroup = group || [atom];

  const badgeHtml = count > 1
    ? `<span class="atom-bubble-count" title="${count} Punkti at this place">+${count - 1}</span>`
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
    <div class="atom-bubble-body${isDmi ? ' atom-bubble-body--official-dmi' : ''}">
      ${isDmi ? '<div class="atom-bubble-source">Official DMI</div>' : ''}
      <div class="atom-bubble-text">${textHtml || '<span style="opacity:0.5">no text</span>'}</div>
      <div class="atom-bubble-cat ${cat.cls}">${escHtml(cat.code)} · ${escHtml(cat.label)}</div>
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
    if (!isDmi && hue != null) body.style.setProperty('--author-hue', String(hue));
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
    if (z < 10) {
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
  const allAtoms = await getAllAtomsNewestFirst();
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
  const mapReadyForScope = Boolean(map && typeof map.getBounds === 'function' && map.isStyleLoaded && map.isStyleLoaded());
  let recent;
  if (mapReadyForScope) {
    const bounds = map.getBounds();
    recent = enriched
      .filter((a) => Number.isFinite(a.lat) && Number.isFinite(a.lon) && bounds.contains([a.lon, a.lat]))
      .sort((a, b) => Number(b.t) - Number(a.t))
      .slice(0, 50);
    _mapScopedFeedReady = true;
  } else {
    enriched.sort((a, b) => {
      const ad = Number.isFinite(a.distance);
      const bd = Number.isFinite(b.distance);
      if (ad && bd) return a.distance - b.distance || (Number(b.t) - Number(a.t));
      if (ad) return -1;
      if (bd) return 1;
      return Number(b.t) - Number(a.t);
    });
    recent = enriched.slice(0, 50);
    _mapScopedFeedReady = false;
  }
  // Expose to main-view feed
  _mainFeedAtoms = recent;
  if (elMainStatusCount) {
    elMainStatusCount.textContent = _mapScopedFeedReady ? `${recent.length} visible` : 'Loading visible atoms…';
  }
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
      const category = getCategoryMeta(a);
      const verified = isVerifiedAtom(a) ? '<span class="atom-verified">Verified</span>' : '';
      const meta = [fmtDistance(a.distance), altitude, fmtTime(a.t)].filter(Boolean).join(' · ');
      el.innerHTML = `
        <div class="atom-dot"></div>
        <div class="atom-body">
          <div class="atom-meta"><span class="atom-category ${category.cls}">${escHtml(category.code)} · ${escHtml(category.label)}</span>${verified}</div>
          <div class="atom-text"><strong>${title}</strong></div>
          <div class="atom-text">${preview}</div>
          ${category.code === 'EMGC' ? '<div class="atom-meta">Public urgent post — not a replacement for calling emergency services.</div>' : ''}
          <div class="atom-meta">${meta}</div>
          <div class="atom-actions"><button class="btn btn-secondary show-in-3d-btn" type="button">Open board on map</button></div>
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

/**
 * Relative time formatter for bubble meta line.
 * tSec is accepted as ms (we already store Date.now() in atom.t).
 */
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

let placementDraft = null;

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

function detectBuildingAtCenter() {
  if (!map) return { building: null };
  try {
    const center = map.getCenter();
    const screenPt = map.project(center);
    const layers = (map.getStyle().layers || []).filter(l => l.type === 'fill-extrusion' || (l.id && l.id.toLowerCase().includes('building'))).map(l => l.id);
    if (layers.length === 0) return { building: null };
    const R = 30;
    const box = [[screenPt.x - R, screenPt.y - R],[screenPt.x + R, screenPt.y + R]];
    const features = map.queryRenderedFeatures(box, { layers });
    if (!features || features.length === 0) return { building: null };
    const heightOf = (props) => { let h = Number(props.render_height); if (!Number.isFinite(h) || h <= 0) h = Number(props.height); if (!Number.isFinite(h) || h <= 0) { const levels = Number(props['building:levels']); if (Number.isFinite(levels) && levels > 0) h = levels * FLOOR_HEIGHT_M; } return Number.isFinite(h) && h > 0 ? h : 0; };
    let best = null; let bestHeight = 0;
    for (const f of features) { const h = heightOf(f.properties || {}); if (h > bestHeight) { best = f; bestHeight = h; } }
    if (!best || bestHeight < FLOOR_HEIGHT_M) return { building: null };
    const props = best.properties || {};
    const name = (props.name && String(props.name).trim()) || null;
    const maxFloor = Math.max(1, Math.floor(bestHeight / FLOOR_HEIGHT_M));
    return { building: { name, height: bestHeight, maxFloor } };
  } catch (e) {
    console.warn('[modal] detectBuildingAtCenter failed:', e);
    return { building: null };
  }
}


function selectedBoardStableId(atom) {
  return String(atom?.atom_id || atom?.id || stripPunktoPrefix(atom?.punkto || '') || '').trim();
}

function copyRootLocationFields(root, reply) {
  if (root?.punkto) reply.punkto = root.punkto;
  const explicitFields = Array.isArray(root?.location_fields) ? new Set(root.location_fields) : new Set();
  for (const field of ['lat', 'lon', 'altitude_m', 'alt', 'z', 'floor', 'level']) {
    if (root?.[field] == null) continue;
    if (!explicitFields.has(field)) continue;
    reply[field] = root[field];
  }
}

function readableReplyError(err) {
  const code = err?.code || err?.detail?.error;
  if (code === 'reply_location_mismatch') return 'Reply location did not match the board root.';
  if (code === 'invalid_parent_id') return 'Cannot reply: board id is missing.';
  return err?.message ? `Could not post public reply: ${err.message}` : 'Could not post public reply.';
}

async function submitBoardReply({ boardAtom, text }) {
  const root = boardAtom || {};
  let parentId = selectedBoardStableId(root);
  if (!parentId) {
    try { parentId = await computeAtomId(root); } catch {}
  }
  if (!parentId) throw new Error('Cannot reply: board id is missing.');

  const rootId = String(root.root_id || parentId).trim();
  const author = getStoredAuthorName();
  const reply = {
    t: Date.now(),
    x: String(text || '').trim(),
    category: String(root.category || root.kind || 'TEXT').toUpperCase(),
    relation: 'reply',
    parent_id: parentId,
    root_id: rootId,
    location_lock: true,
    location_source: 'root',
  };
  copyRootLocationFields(root, reply);
  if (author) reply.f = author;
  if (!reply.x) throw new Error('Write a public reply first.');
  if (!reply.punkto) throw new Error('Cannot reply: board location is missing.');

  try {
    const result = await postAtomToNetwork(reply, nodeRegistry);
    if (result?.atom_id) reply.atom_id = result.atom_id;
    await upsertAtom(reply);
    await refreshUI();
    setSyncStatus('ok');
  } catch (err) {
    console.error('[replyAtom]', err);
    throw new Error(readableReplyError(err));
  }
}

async function submitAtomFromModal({ text, author, category, draft }) {
  const center = draft ? { lat: draft.lat, lng: draft.lon } : map.getCenter();
  const altMeters = draft?.altitude_m || 0;
  const punkto = encodeLocation(center.lat, center.lng, altMeters);
  const t = Date.now();
  const atom = {
    punkto,
    t,
    lat: center.lat,
    lon: center.lng,
    altitude_m: altMeters,
  };
  if (draft?.floor_hint != null) atom.floor = draft.floor_hint;
  if (text) atom.x = text;
  if (author) atom.f = author;
  atom.category = String(category || draft?.category || 'TEXT').toUpperCase();
  setCreateSubmitting(true);
  setCreateError('');
  try {
    if (author) setStoredAuthorName(author);
    const result = await postAtomToNetwork(atom, nodeRegistry);
    if (result?.atom_id) atom.atom_id = result.atom_id;
    await upsertAtom(atom);
    closeCreateModal();
    await refreshUI();
    requestAnimationFrame(() => { if (map) map.resize(); });
    setSyncStatus('ok');
    const loc = decodeAtomLocation(punkto);
    if (loc && map) map.flyTo({ center: [loc.lon, loc.lat], zoom: Math.max(map.getZoom(), 14) });
  } catch (err) {
    console.error('[addAtom]', err);
    setCreateError(`Error: ${err.message}`);
  } finally {
    setCreateSubmitting(false);
  }
}

function updateCreateLocationDisplay(draft) {
  if (!elModalLocation || !draft) return;
  const punkto = encodeLocation(draft.lat, draft.lon, draft.altitude_m || 0);
  const loc = decodeAtomLocation(punkto);
  elModalLocation.textContent = loc
    ? `${punkto}  ·  ${fmtCoords(loc.lat, loc.lon, loc.alt)}`
    : punkto;
}

// ---------------------------------------------------------------------------
// Map initialisation
// ---------------------------------------------------------------------------

function initMap() {
  if (map) {
    console.log('[map] init skipped existing');
    requestAnimationFrame(() => { if (map) map.resize(); });
    return map;
  }
  if (mapInitStarted) {
    console.log('[map] init skipped existing');
    return null;
  }

  const container = document.getElementById('map');
  if (!container) {
    console.error('[map] initMap aborted: #map element not found');
    return;
  }
  mapInitStarted = true;
  const rect = elMapEl ? elMapEl.getBoundingClientRect() : null;
  if (rect) console.log('[map] container size before init', Math.round(rect.width), Math.round(rect.height));
  const { MapboxOverlay } = window.deck;

  try {
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
      console.error('[map] error:', e?.error?.message || e);
    });
  } catch (err) {
    console.error('[map] initMap failed:', err.message, err.stack);
    mapInitStarted = false;
    map = null;
    return;
  }

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

  syncEngine = createSyncEngine({
    nodeUrl: NODE_URL,
    seedNodes: SEED_NODES,
    syncIntervalMs: SYNC_INTERVAL_MS,
    nodeRegistry,
    isHiddenAtom,
    callbacks: {
      onSyncStart: () => setSyncStatus('syncing'),
      onSyncDone: ({ anyError }) => {
        setSyncStatus(anyError ? 'error' : 'ok');
        if (!anyError) lastSyncAtMs = Date.now();
      },
      onSyncError: () => setSyncStatus('error'),
      onAtomsChanged: (newAtomIds) => queueRefreshUI(newAtomIds, 50),
      onPeersChanged: () => refreshSettingsNetworkInfo().catch(() => {}),
    },
  });

  map.on('load', async () => {
    console.log('[map] loaded');

    // Update DOM bubble LOD whenever zoom or pan changes.
    map.on('zoomend', () => {
      updateBubbleVisibility();
      drawLeaderLines();
      updateCrosshairReadout();
      queueRefreshUI();
    });
    map.on('moveend', () => {
      updateBubbleVisibility();
      drawLeaderLines();
      updateCrosshairReadout();
      queueRefreshUI();
    });

    // Ensure the SVG overlay exists and is redrawn on every map render event
    // so leader lines track pan/zoom/pitch/bearing smoothly.
    ensureLeaderOverlay();
    map.on('render', drawLeaderLines);
    map.on('click', (e) => {
      if (!isCreateModalOpen()) {
        openCreateModal();
      }
      if (placementDraft) {
        placementDraft.lat = e.lngLat.lat;
        placementDraft.lon = e.lngLat.lng;
        updateCreateCenter(e.lngLat.lat, e.lngLat.lng);
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
          'fill-extrusion-color': '#8f9fb7',
          'fill-extrusion-height': ['coalesce', ['get', 'render_height'], ['get', 'height'], 5],
          'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], 0],
          'fill-extrusion-opacity': 0.58,
        },
      });
    } catch (e) {
      console.warn('[map] 3D buildings layer failed:', e);
    }

    await refreshUI();
    requestAnimationFrame(() => { if (map) map.resize(); });

    // Init load balancer registry and seed Dexie nodes table with SEED_NODES
    nodeRegistry.initNodeRegistry();
    for (const url of SEED_NODES) {
      const seeded = await ensureNode(url, 0);
      if (seeded) console.log('[lb] seeded node:', url);
    }

    // Discover peers from all known nodes, then start sync
    await syncEngine.discoverPeers();
    await syncEngine.syncFeed();
    initialSyncDone = true;
    await refreshUI();
    requestAnimationFrame(() => { if (map) map.resize(); });

    // If the user opened a /p/<id> deep-link, focus it now that atoms are loaded
    if (deepLinkPunkto) {
      await focusPunkto(deepLinkPunkto);
    }

    // Show first-visit onboarding hint (skipped for deep-link visitors and repeat users)
    showOnboarding();

    syncEngine.start();
  });
  return map;
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
 * Refresh visible atom count in settings header. Synchronous, cheap — safe to
 * call from the UI-render path.
 */
function updateSettingsCount(count) {
  if (typeof count !== 'number') return;
  renderSettingsView({ network: { atomCount: count, cachedCount: count }, syncStatus: count });
}

/**
 * Refresh the node + peer info block in the settings menu. Runs on-demand
 * (each time the menu opens) so we never poll. Updates topbar sync-indicator
 * to reflect lag status. Gracefully degrades when peers are unreachable or
 * when /info doesn't advertise a peer list.
 */


function yesNo(value) {
  if (value === true) return 'yes';
  if (value === false) return 'no';
  return 'unknown';
}

function formatBooleanMap(obj) {
  if (!obj || typeof obj !== 'object') return '—';
  const rows = Object.entries(obj).map(([key, value]) => `${key}: ${yesNo(value)}`);
  return rows.length ? rows.join('\n') : '—';
}

function formatNodeList(list) {
  return Array.isArray(list) && list.length ? list.join('\n') : 'none';
}

function formatNodeStats(stats) {
  if (!stats || typeof stats !== 'object') return '—';
  const oldest = stats.oldest_t ? fmtTime(stats.oldest_t) : 'none';
  const newest = stats.newest_t ? fmtTime(stats.newest_t) : 'none';
  return [`buffer_size: ${stats.buffer_size ?? 0}`, `oldest_t: ${oldest}`, `newest_t: ${newest}`].join('\n');
}

function nodeStatusViewFromInfo(info) {
  const node = info?.node || {};
  const software = info?.software || {};
  const config = info?.config || {};
  const domainParts = [];
  if (node.domain_dns) domainParts.push(node.domain_dns);
  if (Array.isArray(node.hostnames) && node.hostnames.length) domainParts.push(...node.hostnames);
  return {
    status: info?.ok ? 'online' : 'unavailable',
    name: node.name,
    publicUrl: node.public_url,
    domainHostnames: domainParts.length ? domainParts.join('\n') : '—',
    fingerprint: node.fingerprint,
    version: [software.name || 'Punkto', software.version || 'unknown', software.runtime ? `(${software.runtime})` : ''].filter(Boolean).join(' '),
    configLoaded: `${yesNo(config.loaded)}${config.path ? ` (${config.path})` : ''}`,
    roles: formatBooleanMap(info?.roles),
    serving: formatBooleanMap(info?.serving),
    seedNodes: formatNodeList(info?.network?.seed_nodes),
    knownNodes: formatNodeList(info?.network?.known_nodes),
    stats: formatNodeStats(info?.stats),
    health: info?.health?.status || 'unknown',
  };
}

async function refreshPublicNodeStatus() {
  renderSettingsView({ nodeStatus: { status: 'checking…' } });
  try {
    const res = await fetch(`${NODE_URL}/node/info`, { signal: AbortSignal.timeout(6000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const info = await res.json();
    renderSettingsView({ nodeStatus: nodeStatusViewFromInfo(info) });
  } catch (err) {
    renderSettingsView({
      nodeStatus: {
        status: 'unavailable',
        health: 'unreachable',
      },
    });
    console.warn('[node] public status unavailable:', err);
  }
}

function healthToNetworkStatus(health) {
  if (health === 'ok') return 'online';
  if (health === 'failing') return 'failing';
  if (health === 'recovering') return 'sleeping';
  if (health === 'unavailable') return 'stale';
  return 'unknown';
}

function buildKnownNodesHtml(localCursor, peerUrls, peerCursors) {
  const snapshot = typeof nodeRegistry.getNodeSnapshot === 'function' ? nodeRegistry.getNodeSnapshot() : [];
  const cursorByUrl = new Map([[NODE_URL, localCursor], ...peerUrls.map((url, i) => [url, peerCursors[i]])]);
  const snapshotUrls = snapshot.map((entry) => entry.url).filter(Boolean);
  const urls = [...snapshotUrls, NODE_URL, ...SEED_NODES];
  const uniqueUrls = [...new Set(urls.map((url) => String(url).replace(/\/$/, '')).filter(Boolean))];
  if (!uniqueUrls.length) return '<span class="dim">no known nodes yet</span>';
  return uniqueUrls.map((url) => {
    const nodeEntry = snapshot.find((entry) => entry.url === url);
    const health = nodeEntry?.health;
    const unavailableSince = nodeEntry?.unavailableSince;
    const status = healthToNetworkStatus(health);
    const cursor = cursorByUrl.get(url);
    const cursorText = typeof cursor === 'number' ? `cursor ${cursor}` : 'cursor unknown';
    const lastSeen = unavailableSince ? fmtRelativeTime(unavailableSince) : 'unknown';
    return [
      '<div class="settings-network-node-card">',
      `<div class="settings-network-node-url mono">${escHtml(url)}</div>`,
      `<div class="settings-network-node-meta">status: ${escHtml(status)} · ${escHtml(cursorText)} · last seen: ${escHtml(lastSeen)}</div>`,
      '</div>',
    ].join('');
  }).join('');
}
async function refreshSettingsNetworkInfo() {
  if (!elSettingsNode) return;

  // Render the node row immediately with a "…" cursor placeholder so the menu
  // feels responsive while fetches are in flight.
  renderSettingsView({
    network: {
      nodeHtml: `${escHtml(hostOf(NODE_URL))} <span class="dim">(cursor …)</span>`,
      peersHtml: '<span class="dim">checking…</span>',
      currentNode: NODE_URL,
      syncStatus: (syncEngine && syncEngine.isSyncing()) ? 'syncing' : 'idle',
      lastSync: lastSyncAtMs ? fmtTime(lastSyncAtMs) : 'not synced yet',
      peerCount: 'checking…',
      knownNodesHtml: '<span class="dim">checking…</span>',
    },
  });

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
  const nodeHtml = `${escHtml(hostOf(NODE_URL))} <span class="dim">(${localCursorStr})</span>${warnIcon}`;

  // 5. Render peers list
  if (elSettingsPeers) {
    if (peerUrls.length === 0) {
      renderSettingsView({ network: { peersHtml: '<span class="dim">none</span>' } });
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
      renderSettingsView({ network: { peersHtml: rows.join('<br>') } });
    }
  }
  const knownPeersCount = peerUrls.length ? String(peerUrls.length) : 'no peers discovered yet';
  const knownNodesHtml = buildKnownNodesHtml(localCursor, peerUrls, peerCursors);
  renderSettingsView({ network: { nodeHtml, currentNode: NODE_URL, peerCount: knownPeersCount, knownNodesHtml, syncStatus: (syncEngine && syncEngine.isSyncing()) ? 'syncing' : 'idle', lastSync: lastSyncAtMs ? fmtTime(lastSyncAtMs) : 'not synced yet' } });

  // 6. Topbar indicator: amber dot when behind, regardless of sync state
  if (elSyncDot) {
    elSyncDot.classList.toggle('lagging', lag > 0);
    if (lag > 0) elSyncDot.title = `Behind peers by ${lag} bytes`;
    else elSyncDot.title = 'sync status';
  }
}

async function openSettingsMenu() {
  shellOpenSettings();
  // Update visible atom count immediately from the DB-backed UI state
  try {
    const all = await getAllAtoms();
    updateSettingsCount(all.filter(a => !isHiddenAtom(a)).length);
  } catch {
    updateSettingsCount(0);
  }
  // Kick off read-only node/network info refreshes (no await — menu is already visible).
  refreshPublicNodeStatus();
  refreshSettingsNetworkInfo();
}

function closeSettingsMenu() {
  shellCloseSettings();
}

function toggleSettingsMenu() {
  if (shellIsSettingsOpen()) closeSettingsMenu();
  else openSettingsMenu();
}

function wireEvents() {
  initCreateModal({
    getInitialContext: () => ({ center: map ? map.getCenter() : { lat: 0, lng: 0 }, building: detectBuildingAtCenter().building }),
    onPreviewChanged: (draft) => { placementDraft = draft; updateCreateLocationDisplay(draft); renderAtoms(); },
    onSubmitCreate: submitAtomFromModal,
    onClosed: () => { placementDraft = null; renderAtoms(); },
  });
  // Panel toggle
  elFabPanel.addEventListener('click', () => setPanelOpen(!panelOpen));
  elPanelClose.addEventListener('click', () => setPanelOpen(false));

  // 3D toggle
  elToggle3D.addEventListener('click', toggle3D);

  // Close settings on outside click
  document.addEventListener('click', () => {
    if (shellIsSettingsOpen()) closeSettingsMenu();
  });

  // Add atom
  elFabAdd.addEventListener('click', () => {
    dismissOnboarding();
    openCreateModal();
  });

  // Handle keyboard escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeCreateModal();
      setPanelOpen(false);
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
  console.log('PUNKTO APP.JS LOADED v106-create-stage-2026-06-09-1');
  window.PUNKTO_APP_VERSION = 'v107-desktop-bottom-gap-2026-06-09-1';

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
    const cachedAll = await getAllAtoms();
    const cachedCount = cachedAll.filter(a => !isHiddenAtom(a)).length;
    elCountNum.textContent = cachedCount;
    if (elMainStatusCount) elMainStatusCount.textContent = `${cachedCount} visible`;
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
  renderSettingsView({ version: window.PUNKTO_APP_VERSION });

  // Wire UI modules (shell / text / map). Callbacks delegate back to app.js
  // so app.js still owns data and lifecycle; modules own DOM/markup/state.
  initShell({
    onShowText: () => renderMainFeed(),
    onShowMap: () => {
      ensureMapInitialized();
    },
    onAdd: () => { dismissOnboarding(); openCreateModal(); },
    onOpenSettings: () => {
      renderNetworkPage();
      renderMePage();
      toggleSettingsMenu();
    },
  });
  initTextView({
    onShowOnMap: (id) => focusPunkto(id),
    onOpenBoard: (id) => { showPage('text'); },
    onLeaveNote: () => { dismissOnboarding(); openCreateModal(); },
    onPostReply: submitBoardReply,
    helpers: {
      escHtml, deriveTitle, deriveCategory, isVerifiedAtom,
      fmtAltitudeLabel, fmtDistance, fmtTime,
    },
  });
  initMapView({
    getMap: () => map,
    initMap: () => initMap(),
  });

  showPage('map');
  ensureMapInitialized();
  if (deepLinkPunkto) {
    setPanelOpen(false); // panel managed by 3D view when deep-linking
  }
}

boot();


// --- Key Management ---
let currentIdentity = null;
const AUTHOR_STORAGE_KEYS = ['punkto-name', 'punkto-author'];

function getStoredAuthorName() {
  for (const key of AUTHOR_STORAGE_KEYS) {
    const value = localStorage.getItem(key);
    if (value && value.trim()) return value.trim();
  }
  return '';
}

function setStoredAuthorName(name) {
  const cleaned = (name || '').trim();
  localStorage.setItem('punkto-name', cleaned);
  localStorage.setItem('punkto-author', cleaned);
}

function shortFingerprint(pubkey) {
  if (!pubkey) return '—';
  if (pubkey.length <= 16) return pubkey;
  return `${pubkey.slice(0, 8)}…${pubkey.slice(-8)}`;
}

function displayKeyInfo(identity) {
  const name = getStoredAuthorName();
  if (!identity) {
    renderSettingsView({
      identity: {
        name,
        status: 'No key on this device',
        helper: 'Punktis you write are unsigned.',
        canSave: false,
        canLoad: !!localStorage.getItem('punkto-identity'),
      },
    });
    return;
  }
  renderSettingsView({
    identity: {
      name,
      status: 'Key loaded on this device',
      helper: 'New Punktis can be signed.',
      authorId: identity.authorId,
      pubkey: identity.pubkey ? identity.pubkey.slice(0, 20) + '...' : '—',
      shortPubkey: shortFingerprint(identity.pubkey),
      mnemonic: Array.isArray(identity.mnemonic) ? identity.mnemonic.join(' ') : '—',
      canSave: true,
      canLoad: !!localStorage.getItem('punkto-identity'),
    },
  });
  const meShort = document.getElementById('me-author-short');
  if (meShort) meShort.textContent = shortFingerprint(identity.pubkey);
}

function setupKeyManagement() {
  initSettingsView({
    onResetCache: () => {
      closeSettingsMenu();
      resetCache();
    },
    onGenerateKey: async () => {
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
    },
    onImportKey: () => {
      const input = document.createElement('input');
      input.type = 'file'; input.accept = '.json';
      input.onchange = async (ev) => {
        const file = ev.target.files[0]; if (!file) return;
        try {
          const identity = importKeyFromJson(await file.text());
          currentIdentity = identity; displayKeyInfo(identity);
        } catch (err) { console.error('[identity] import failed:', err); }
      };
      input.click();
    },
    onSaveKey: () => {
      if (!currentIdentity) return;
      if (!confirm('localStorage is not secure. Save temporarily?')) return;
      localStorage.setItem('punkto-identity', JSON.stringify(currentIdentity));
      displayKeyInfo(currentIdentity);
    },
    onLoadKey: () => {
      const saved = localStorage.getItem('punkto-identity');
      if (!saved) return;
      try {
        const identity = JSON.parse(saved);
        currentIdentity = identity; displayKeyInfo(identity);
      } catch (err) { console.error('[identity] load failed:', err); }
    },
    onNameChanged: (name) => {
      setStoredAuthorName(name);
      displayKeyInfo(currentIdentity);
    },
    onPrintMnemonic: () => {
      if (!currentIdentity) return;
      const words = currentIdentity.mnemonic.map((w, i) =>
        `<span>${i+1}. ${w}</span>`).join(' ');
      const win = window.open('', '_blank');
      win.document.write(`<!DOCTYPE html><html><head><title>Punkto Key</title>
<style>body{font-family:monospace;padding:20px;}</style></head>
<body><h1>Punkto Identity — KEEP SAFE</h1><p>${words}</p>
<p>Author: ${currentIdentity.authorId}</p></body></html>`);
      win.document.close(); win.print();
    },
    onExportKey: () => {
      if (!currentIdentity) return;
      const blob = new Blob([exportKeyJson(currentIdentity)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'punkto-key.json'; a.click();
    },
  });
  displayKeyInfo(currentIdentity);
}
// Rebuild trigger: 2026-05-25T13:16:00Z
