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
const MAP_STYLE = 'https://tiles.openfreemap.org/styles/dark';

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

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let map = null;
let deckOverlay = null;
let syncTimer = null;
let isSyncing = false;
let is3D = true;
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
 * Build LineLayer data connecting ALL atoms (full mesh), capped at 50.
 * Returns array of {sourcePosition, targetPosition} objects.
 */
function buildWireMesh(atoms) {
  const lines = [];
  const cap = Math.min(atoms.length, 50);
  for (let i = 0; i < cap; i++) {
    for (let j = i + 1; j < cap; j++) {
      lines.push({
        sourcePosition: [atoms[i].lon, atoms[i].lat, atoms[i].alt],
        targetPosition: [atoms[j].lon, atoms[j].lat, atoms[j].alt],
      });
    }
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

  // Only build wire mesh for nearby clusters (limit to avoid O(n²) explosion)

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
    pitch: 45,
    bearing: -10,
    antialias: true,
  });

  map.on('error', e => {
    console.warn('[map] error (ignored):', e.error && e.error.message);
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

    // Add terrain elevation (AWS Terrarium DEM — free, open)
    try {
      map.addSource('terrain-dem', {
        type: 'raster-dem',
        tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
        encoding: 'terrarium',
        tileSize: 256,
        maxzoom: 15,
      });
      map.setTerrain({ source: 'terrain-dem', exaggeration: 1.5 });
    } catch (e) {
      console.warn('[map] terrain failed:', e);
    }

    // Sky layer — atmosphere for 3D view
    try {
      map.addLayer({
        id: 'sky',
        type: 'sky',
        paint: {
          'sky-type': 'atmosphere',
          'sky-atmosphere-sun': [0.0, 90.0],
          'sky-atmosphere-sun-intensity': 5,
          'sky-atmosphere-color': 'rgba(5, 10, 25, 1)',
          'sky-atmosphere-halo-color': 'rgba(0, 60, 80, 0.8)',
        },
      });
    } catch (e) {
      console.warn('[map] sky layer failed:', e);
    }

    await refreshUI();
    // Start sync
    await syncFeed();
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
    try { map.setTerrain({ source: 'terrain-dem', exaggeration: 1.5 }); } catch(e) {}
    elToggle3D.textContent = '2D';
    elToggle3D.title = 'Switch to 2D view';
  } else {
    map.easeTo({ pitch: 0, bearing: 0, duration: 800 });
    try { map.setTerrain(null); } catch(e) {}
    elToggle3D.textContent = '3D';
    elToggle3D.title = 'Switch to 3D view';
  }
}

// ---------------------------------------------------------------------------
// Event wiring
// ---------------------------------------------------------------------------

function wireEvents() {
  // Panel toggle
  elFabPanel.addEventListener('click', () => setPanelOpen(!panelOpen));
  elPanelClose.addEventListener('click', () => setPanelOpen(false));

  // 3D toggle
  elToggle3D.addEventListener('click', toggle3D);
  const elReset = document.getElementById('btn-reset');
  if (elReset) elReset.addEventListener('click', resetCache);

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
  setPanelOpen(true);
}

document.addEventListener('DOMContentLoaded', boot);
