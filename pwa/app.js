/**
 * app.js — Punkto PWA main application
 * Depends on: MapLibre GL JS, deck.gl 8.9.x UMD (window.deck), Dexie.js
 */

import { encode, decode } from './geohash3d.js';

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
const elToggle3D    = document.getElementById('toggle-3d');
const elBtnSettings = document.getElementById('btn-settings');
const elSettingsMenu = document.getElementById('settings-menu');
const elSettingsReset = document.getElementById('settings-reset');
const elSettingsNode = document.getElementById('settings-node');
const elSettingsCount = document.getElementById('settings-count');
const elOnboardingHint = document.getElementById('onboarding-hint');

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

function setSyncStatus(state) {
  elSyncDot.className = '';
  if (state) elSyncDot.classList.add(state);
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

  // Highlight matching atom item if present in the list (after refreshUI)
  // refreshUI repopulates children; we search on next tick.
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

function encodeCurrentLocation(mapInst) {
  const center = mapInst.getCenter();
  const lat = center.lat;
  const lon = center.lng;
  const alt = 0; // default sea level
  const hash = encode(lat, lon, alt, 12);
  return `p:${hash}`;
}

// ---------------------------------------------------------------------------
// IndexedDB helpers
// ---------------------------------------------------------------------------

async function getNodeCursor(url) {
  const row = await db.nodes.get(url);
  if (row) return row.cursor || 0;
  // Migrate legacy single cursor from meta table on first access for NODE_URL
  if (url === NODE_URL) {
    const legacy = await db.meta.get('cursor');
    return legacy ? legacy.value : 0;
  }
  return 0;
}

async function setNodeCursor(url, cursor) {
  await db.nodes.put({ url, cursor });
}

// Keep legacy helper for submitAtom backward compat
async function setStoredCursor(cursor) {
  await setNodeCursor(NODE_URL, cursor);
}

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
    await db.atoms.add(record);
  }
}

// ---------------------------------------------------------------------------
// Sync
// ---------------------------------------------------------------------------

async function syncFeed() {
  if (isSyncing) return;
  isSyncing = true;
  setSyncStatus('syncing');

  let anyError = false;

  try {
    // Get all known nodes from Dexie; always include DEFAULT NODE_URL
    const storedNodes = await db.nodes.toArray();
    const nodeUrls = new Set(storedNodes.map(n => n.url));
    nodeUrls.add(NODE_URL);

    for (const url of nodeUrls) {
      try {
        const cursor = await getNodeCursor(url);
        const feedUrl = `${url}/feed${cursor > 0 ? `?since=${cursor}` : ''}`;
        const res = await fetch(feedUrl, { signal: AbortSignal.timeout(15_000) });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (Array.isArray(data.atoms) && data.atoms.length > 0) {
          for (const atom of data.atoms) {
            if (atom.punkto && atom.t) {
              await upsertAtom(atom);
            }
          }
        }

        if (typeof data.cursor === 'number') {
          await setNodeCursor(url, data.cursor);
        }
      } catch (nodeErr) {
        console.warn(`[sync] feed error for ${url}:`, nodeErr);
        anyError = true;
      }
    }

    setSyncStatus(anyError ? 'error' : 'ok');
    await refreshUI();
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
 * Flat ground reference grid around centroid of atoms — spatial reference for 3D cloud.
 */
function buildGroundGrid(atoms) {
  const lines = [];
  if (atoms.length === 0) return lines;
  const cLon = atoms.reduce((s, a) => s + a.lon, 0) / atoms.length;
  const cLat = atoms.reduce((s, a) => s + a.lat, 0) / atoms.length;
  const range = 0.08; // ~9km
  const step  = 0.01; // ~1km grid spacing
  const alt   = 0;
  for (let x = -range; x <= range + 1e-9; x = Math.round((x + step) * 1e9) / 1e9) {
    lines.push({ sourcePosition: [cLon + x, cLat - range, alt], targetPosition: [cLon + x, cLat + range, alt] });
  }
  for (let y = -range; y <= range + 1e-9; y = Math.round((y + step) * 1e9) / 1e9) {
    lines.push({ sourcePosition: [cLon - range, cLat + y, alt], targetPosition: [cLon + range, cLat + y, alt] });
  }
  return lines;
}

/**
 * Map altitude to RGBA color. Higher = brighter cyan.
 * alt range: -500 to 8500 → intensity 120–255
 */
function altToColor(alt) {
  const t = Math.max(0, Math.min(1, (alt + 500) / 9000));
  const intensity = Math.round(120 + t * 135); // 120–255 (was 40–255)
  return [0, intensity, 255, 240];
}

async function renderAtoms() {
  if (!deckOverlay) return;

  const atoms = await db.atoms.orderBy('t').reverse().toArray();

  const scatterData = atoms.map(a => ({
    position: [a.lon, a.lat, a.alt],
    color: altToColor(a.alt),
    punkto: a.punkto,
    text: a.x,
    f: a.f,
    t: a.t,
    label: (a.x || a.f || '').slice(0, 40),
  }));

  const { ScatterplotLayer, LineLayer, TextLayer, MapboxOverlay } = window.deck;

  const layers = [
    new LineLayer({
      id: 'ground-grid',
      data: buildGroundGrid(atoms),
      getSourcePosition: d => d.sourcePosition,
      getTargetPosition: d => d.targetPosition,
      getColor: [0, 140, 160, 140],
      getWidth: 1,
      widthUnits: 'pixels',
      pickable: false,
    }),
    new ScatterplotLayer({
      id: 'atoms',
      data: scatterData,
      getPosition: d => d.position,
      getFillColor: d => d.color,
      getRadius: 10,
      radiusUnits: 'pixels',
      radiusMinPixels: 6,
      radiusMaxPixels: 18,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 100, 255],
      onClick: info => {
        if (!info.object || !map) return;
        const a = info.object;
        const loc = decodeAtomLocation(a.punkto);
        const coordStr = loc ? fmtCoords(loc.lat, loc.lon, loc.alt) : '';
        const timeStr = fmtTime(a.t);
        const html = [
          a.text ? `<div class="popup-text">${escHtml(a.text)}</div>` : '',
          `<div class="popup-meta">${escHtml(a.f || 'anon')} · ${timeStr}</div>`,
          `<div class="popup-canon">${escHtml(a.punkto)}</div>`,
          coordStr ? `<div class="popup-coords">${coordStr}</div>` : '',
        ].filter(Boolean).join('');
        new maplibregl.Popup({ closeButton: true, maxWidth: '280px', className: 'punkto-popup' })
          .setLngLat(info.coordinate.slice(0, 2))
          .setHTML(html)
          .addTo(map);
      },
    }),
    new TextLayer({
      id: 'atom-labels',
      data: scatterData.filter(d => d.label),
      getPosition: d => d.position,
      getText: d => d.label,
      getSize: 13,
      getColor: [0, 220, 255, 220],
      getBackgroundColor: [10, 10, 10, 180],
      background: true,
      backgroundPadding: [4, 2],
      getTextAnchor: 'start',
      getAlignmentBaseline: 'center',
      getPixelOffset: [14, 0],
      fontFamily: 'monospace',
      pickable: false,
    }),
  ];

  deckOverlay.setProps({ layers });
}

// ---------------------------------------------------------------------------
// Panel / atom list UI
// ---------------------------------------------------------------------------

async function refreshUI() {
  const total = await db.atoms.count();
  elCountNum.textContent = total;
  // Keep settings info (if menu is open) in sync
  if (elSettingsCount) elSettingsCount.textContent = String(total);

  // Render recent 50 in panel
  const recent = await db.atoms.orderBy('t').reverse().limit(50).toArray();

  if (recent.length === 0) {
    // Only show the empty placeholder AFTER the first sync has completed.
    // During cold boot (cache empty + sync in progress) we keep it hidden so
    // users see a clean list instead of a flash of "No atoms yet".
    if (initialSyncDone) {
      elAtomEmpty.textContent = 'No atoms yet.';
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
      const text = a.x ? escHtml(a.x) : '<span class="empty">no text</span>';
      const meta = [
        a.f ? escHtml(a.f) : null,
        escHtml(a.punkto || ''),
      ].filter(Boolean).join(' · ');
      el.innerHTML = `
        <div class="atom-dot"></div>
        <div class="atom-body">
          <div class="atom-text">${text}</div>
          <div class="atom-meta">${meta}</div>
        </div>
        <div class="atom-time">${fmtTime(a.t)}</div>
      `;
      elAtomList.appendChild(el);
    }
  }

  // Re-render deck.gl
  await renderAtoms();
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
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

function openModal() {
  elModalError.textContent = '';
  elModalText.value = '';
  // Keep author value between sessions (restore from localStorage)
  elModalAuthor.value = localStorage.getItem('punkto-author') || '';

  const punkto = encodeCurrentLocation(map);
  const loc = decodeAtomLocation(punkto);
  if (loc) {
    elModalLocation.textContent =
      `${punkto}  ·  ${fmtCoords(loc.lat, loc.lon, loc.alt)}`;
  } else {
    elModalLocation.textContent = punkto;
  }

  elModalOverlay.classList.add('open');
  setTimeout(() => elModalText.focus(), 80);
}

function closeModal() {
  elModalOverlay.classList.remove('open');
}

async function submitAtom() {
  const text   = elModalText.value.trim();
  const author = elModalAuthor.value.trim();
  const punkto = encodeCurrentLocation(map);
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
      await setStoredCursor(json.cursor);
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
    center: [10, 50],
    zoom: 3,
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

function updateSettingsInfo(count) {
  if (elSettingsNode) {
    try {
      elSettingsNode.textContent = new URL(NODE_URL).host;
    } catch {
      elSettingsNode.textContent = NODE_URL;
    }
  }
  if (elSettingsCount && typeof count === 'number') {
    elSettingsCount.textContent = String(count);
  }
}

async function openSettingsMenu() {
  settingsOpen = true;
  elSettingsMenu.classList.add('open');
  elSettingsMenu.setAttribute('aria-hidden', 'false');
  try {
    const count = await db.atoms.count();
    updateSettingsInfo(count);
  } catch {
    updateSettingsInfo(0);
  }
}

function closeSettingsMenu() {
  settingsOpen = false;
  elSettingsMenu.classList.remove('open');
  elSettingsMenu.setAttribute('aria-hidden', 'true');
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

  // Handle keyboard escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeModal();
      setPanelOpen(false);
      if (settingsOpen) closeSettingsMenu();
    }
  });
}
// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

async function boot() {
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
    const cachedCount = await db.atoms.count();
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
  initMap();
  setPanelOpen(true);
}

document.addEventListener('DOMContentLoaded', boot);
