/**
 * app.js — Punkto PWA main application
 * Depends on: MapLibre GL JS, deck.gl 8.9.x UMD (window.deck), Dexie.js
 */

import { encode, decode } from './geohash3d.js';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const NODE_URL = 'https://punkto.xyz';
const SYNC_INTERVAL_MS = 30_000;
const WIRE_PROXIMITY_DEG = 0.5; // connect atoms within this many degrees
const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const MAP_FALLBACK_STYLE = 'https://demotiles.maplibre.org/style.json';

// ---------------------------------------------------------------------------
// Dexie (IndexedDB)
// ---------------------------------------------------------------------------

const db = new Dexie('punkto');
db.version(1).stores({
  atoms: '++id, punkto, t, lat, lon, alt',
  meta:  'key',
});

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let map = null;
let deckOverlay = null;
let syncTimer = null;
let isSyncing = false;

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

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

function setSyncStatus(state) {
  elSyncDot.className = '';
  if (state) elSyncDot.classList.add(state);
}

function fmtTime(ms) {
  const d = new Date(ms);
  const now = Date.now();
  const diff = now - ms;
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

async function getStoredCursor() {
  const row = await db.meta.get('cursor');
  return row ? row.value : 0;
}

async function setStoredCursor(cursor) {
  await db.meta.put({ key: 'cursor', value: cursor });
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

  try {
    const cursor = await getStoredCursor();
    const url = `${NODE_URL}/feed${cursor > 0 ? `?since=${cursor}` : ''}`;
    const res = await fetch(url, { signal: AbortSignal.timeout(15_000) });

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
      await setStoredCursor(data.cursor);
    }

    setSyncStatus('ok');
    await refreshUI();
  } catch (err) {
    console.warn('[sync] feed error:', err);
    setSyncStatus('error');
  } finally {
    isSyncing = false;
  }
}

// ---------------------------------------------------------------------------
// deck.gl rendering
// ---------------------------------------------------------------------------

/**
 * Build LineLayer data for atoms within WIRE_PROXIMITY_DEG of each other.
 * Returns array of {sourcePosition, targetPosition} objects.
 */
function buildWireMesh(atoms) {
  const lines = [];
  for (let i = 0; i < atoms.length; i++) {
    for (let j = i + 1; j < atoms.length; j++) {
      const a = atoms[i];
      const b = atoms[j];
      const dLat = Math.abs(a.lat - b.lat);
      const dLon = Math.abs(a.lon - b.lon);
      if (dLat < WIRE_PROXIMITY_DEG && dLon < WIRE_PROXIMITY_DEG) {
        lines.push({
          sourcePosition: [a.lon, a.lat, a.alt],
          targetPosition: [b.lon, b.lat, b.alt],
        });
      }
    }
  }
  return lines;
}

/**
 * Map altitude to RGBA color. Higher = brighter cyan.
 * alt range: -500 to 8500 → intensity 0.2 to 1.0
 */
function altToColor(alt) {
  const t = Math.max(0, Math.min(1, (alt + 500) / 9000));
  const intensity = Math.round(40 + t * 215); // 40–255
  return [0, intensity, Math.round(200 + t * 55), 220]; // RGBA cyan-ish
}

async function renderAtoms() {
  if (!deckOverlay) return;

  const atoms = await db.atoms.orderBy('t').reverse().toArray();

  const scatterData = atoms.map(a => ({
    position: [a.lon, a.lat, a.alt],
    color: altToColor(a.alt),
    punkto: a.punkto,
    text: a.x,
  }));

  // Only build wire mesh for nearby clusters (limit to avoid O(n²) explosion)
  const wireAtoms = atoms.slice(0, 500); // cap at 500 for performance
  const wireData = buildWireMesh(wireAtoms);

  const { ScatterplotLayer, LineLayer, MapboxOverlay } = window.deck;

  const layers = [
    new LineLayer({
      id: 'wire-mesh',
      data: wireData,
      getSourcePosition: d => d.sourcePosition,
      getTargetPosition: d => d.targetPosition,
      getColor: [60, 120, 130, 100],
      getWidth: 1,
      widthUnits: 'pixels',
      pickable: false,
    }),
    new ScatterplotLayer({
      id: 'atoms',
      data: scatterData,
      getPosition: d => d.position,
      getFillColor: d => d.color,
      getRadius: 6,
      radiusUnits: 'pixels',
      radiusMinPixels: 3,
      radiusMaxPixels: 14,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 100, 255],
      onClick: info => {
        if (info.object) {
          const a = info.object;
          const msg = [
            a.text || '(no text)',
            a.punkto,
          ].join('\n');
          // Brief tooltip via console; in production would show popover
          console.log('[click]', msg);
        }
      },
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

  // Render recent 50 in panel
  const recent = await db.atoms.orderBy('t').reverse().limit(50).toArray();

  if (recent.length === 0) {
    elAtomEmpty.style.display = 'block';
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
        fmtCoords(a.lat, a.lon, a.alt),
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

    // Post to node
    const res = await fetch(`${NODE_URL}/atom`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(atom),
      signal: AbortSignal.timeout(10_000),
    });

    const json = await res.json();

    if (!res.ok) {
      throw new Error(json.message || `HTTP ${res.status}`);
    }

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
    pitch: 0,
    bearing: 0,
    antialias: true,
  });

  map.on('error', e => {
    // If the dark CartoDB style fails, fall back to demotiles
    console.warn('[map] style error, trying fallback', e);
    map.setStyle(MAP_FALLBACK_STYLE);
  });

  // Add navigation controls
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');

  // Try to geolocate
  map.addControl(
    new maplibregl.GeolocateControl({
      positionOptions: { enableHighAccuracy: true },
      trackUserLocation: false,
      showAccuracyCircle: false,
    }),
    'top-right'
  );

  // deck.gl overlay
  deckOverlay = new MapboxOverlay({
    interleaved: false,
    layers: [],
  });
  map.addControl(deckOverlay);

  map.on('load', async () => {
    console.log('[map] loaded');
    await refreshUI();
    // Start sync
    await syncFeed();
    syncTimer = setInterval(syncFeed, SYNC_INTERVAL_MS);
  });
}

// ---------------------------------------------------------------------------
// Event wiring
// ---------------------------------------------------------------------------

function wireEvents() {
  // Panel toggle
  elFabPanel.addEventListener('click', () => setPanelOpen(!panelOpen));
  elPanelClose.addEventListener('click', () => setPanelOpen(false));

  // Add atom
  elFabAdd.addEventListener('click', () => openModal());
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

  wireEvents();
  initMap();
}

document.addEventListener('DOMContentLoaded', boot);
