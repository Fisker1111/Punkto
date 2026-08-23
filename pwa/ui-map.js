/**
 * ui-map.js - Punkto PWA Map UI
 *
 * Owns MapLibre/deck.gl presentation, map lifecycle, beacon layer rendering,
 * selected-beacon visual state, map-only focus/camera behavior, and map-local
 * controls. App-level data, storage, sync, create submission, and board actions
 * are supplied through explicit callbacks.
 */

import { decodeAtomLocation, FLOOR_HEIGHT_M } from './core/location.js';
import { fmtCoords, fmtRelativeTime, fmtTime, escHtml, renderAtomText } from './core/display.js';
import { stripPunktoPrefix, ensurePunktoPrefix } from './protocol/punkto-id.js';
import { getAtomStableId } from './ui-text.js';

const CATEGORY_META = {
  TEXT: { code: 'TEXT', label: 'Talk', cls: 'cat-talk', color: [138, 160, 190] },
  INFO: { code: 'INFO', label: 'Info', cls: 'cat-info', color: [11, 157, 255] },
  WARN: { code: 'WARN', label: 'Warning', cls: 'cat-warn', color: [255, 179, 0] },
  EMGC: { code: 'EMGC', label: 'Emergency', cls: 'cat-emgc', color: [255, 85, 102] },
  EVNT: { code: 'EVNT', label: 'Event', cls: 'cat-evnt', color: [0, 210, 118] },
  LOST: { code: 'LOST', label: 'Lost/Found', cls: 'cat-lost', color: [255, 132, 64] },
};
const IMPORTED_SOURCE_COLOR = [255, 193, 7];
const DRAFT_COLOR = [255, 220, 80];

let _mapStyle = 'https://tiles.openfreemap.org/styles/liberty';
let _getAllAtomsNewestFirst = async () => [];
let _isHiddenAtom = () => false;
let _getAtomSelectionId = null;
let _getSelectedAtomId = () => null;
let _getPlacementDraft = () => null;
let _setPlacementDraftPosition = null;
let _setPlacementDraftHeight = null;
let _isCreateModalOpen = () => false;
let _onOpenMapBoardForAtom = null;
let _onOpenTextBoardForAtom = null;
let _onClearSelection = null;
let _onRefreshUI = null;
let _onQueueRefreshUI = null;
let _onFocusDeepLinkIfReady = null;
let _onShowOnboarding = null;
let _hasDeepLink = () => false;
let _getCurrentPage = () => 'map';

let map = null;
let mapInitStarted = false;
let mapLoadComplete = false;
let deckOverlay = null;
let is3D = true;
let atomMarkers = new Map();
let _lastRenderedAtoms = [];
let focusedPunktoId = null;
let hasBootFit = false;
let svgLeaderOverlay = null;
let mapBoardBasePadding = null;
let draftHeightDrag = null;
let draftHeightDragRaf = null;
let draftHeightDragPending = null;

const SPATIAL_LOD = {
  groundRelationZoom: 14,
  stemZoom: 16,
};
const MAX_DRAFT_HEIGHT_M = 200;

export function initMapView({
  mapStyle,
  getAllAtomsNewestFirst,
  isHiddenAtom,
  getAtomSelectionId,
  getSelectedAtomId,
  getPlacementDraft,
  setPlacementDraftPosition,
  setPlacementDraftHeight,
  isCreateModalOpen,
  onOpenMapBoardForAtom,
  onOpenTextBoardForAtom,
  onClearSelection,
  onRefreshUI,
  onQueueRefreshUI,
  onFocusDeepLinkIfReady,
  onShowOnboarding,
  hasDeepLink,
  getCurrentPage,
} = {}) {
  if (mapStyle) _mapStyle = mapStyle;
  _getAllAtomsNewestFirst = typeof getAllAtomsNewestFirst === 'function' ? getAllAtomsNewestFirst : _getAllAtomsNewestFirst;
  _isHiddenAtom = typeof isHiddenAtom === 'function' ? isHiddenAtom : _isHiddenAtom;
  _getAtomSelectionId = typeof getAtomSelectionId === 'function' ? getAtomSelectionId : null;
  _getSelectedAtomId = typeof getSelectedAtomId === 'function' ? getSelectedAtomId : _getSelectedAtomId;
  _getPlacementDraft = typeof getPlacementDraft === 'function' ? getPlacementDraft : _getPlacementDraft;
  _setPlacementDraftPosition = typeof setPlacementDraftPosition === 'function' ? setPlacementDraftPosition : null;
  _setPlacementDraftHeight = typeof setPlacementDraftHeight === 'function' ? setPlacementDraftHeight : null;
  _isCreateModalOpen = typeof isCreateModalOpen === 'function' ? isCreateModalOpen : _isCreateModalOpen;
  _onOpenMapBoardForAtom = typeof onOpenMapBoardForAtom === 'function' ? onOpenMapBoardForAtom : null;
  _onOpenTextBoardForAtom = typeof onOpenTextBoardForAtom === 'function' ? onOpenTextBoardForAtom : null;
  _onClearSelection = typeof onClearSelection === 'function' ? onClearSelection : null;
  _onRefreshUI = typeof onRefreshUI === 'function' ? onRefreshUI : null;
  _onQueueRefreshUI = typeof onQueueRefreshUI === 'function' ? onQueueRefreshUI : null;
  _onFocusDeepLinkIfReady = typeof onFocusDeepLinkIfReady === 'function' ? onFocusDeepLinkIfReady : null;
  _onShowOnboarding = typeof onShowOnboarding === 'function' ? onShowOnboarding : null;
  _hasDeepLink = typeof hasDeepLink === 'function' ? hasDeepLink : _hasDeepLink;
  _getCurrentPage = typeof getCurrentPage === 'function' ? getCurrentPage : _getCurrentPage;
}

export function getMapInstance() {
  return map;
}

export function isMapLoaded() {
  return mapLoadComplete;
}

export function setMapBoardViewport(open, boardRect = null) {
  if (!map || typeof map.easeTo !== 'function') return;
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
  const isDesktop = viewportWidth >= 900;
  const currentPadding = typeof map.getPadding === 'function'
    ? map.getPadding()
    : { top: 0, right: 0, bottom: 0, left: 0 };

  if (open && !mapBoardBasePadding) {
    mapBoardBasePadding = { ...currentPadding };
  }

  const base = mapBoardBasePadding || currentPadding;
  let padding = { ...base };
  if (open) {
    if (isDesktop) {
      const sidecarWidth = boardRect?.width || 424;
      padding.right = Math.max(base.right || 0, Math.ceil(sidecarWidth + 44));
    } else {
      const sheetHeight = boardRect?.height || Math.round(viewportHeight * 0.58);
      padding.bottom = Math.max(base.bottom || 0, Math.min(Math.ceil(sheetHeight + 22), Math.round(viewportHeight * 0.66)));
    }
  }

  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  try {
    map.easeTo({
      padding,
      duration: reduceMotion ? 0 : 180,
      pitch: map.getPitch(),
      bearing: map.getBearing(),
      zoom: map.getZoom(),
    });
    if (!open) mapBoardBasePadding = null;
  } catch (err) {
    console.warn('[map-board] viewport padding failed:', err);
    if (!open) mapBoardBasePadding = null;
  }
}

export function missingMapLibraries() {
  const missing = [];
  if (!window.maplibregl) missing.push('MapLibre');
  if (!window.deck || !window.deck.MapboxOverlay) missing.push('deck.gl');
  return missing;
}

export function showMapView() {
  if (!map) {
    ensureMapInitialized();
    return;
  }
  requestAnimationFrame(() => {
    if (map && typeof map.resize === 'function') map.resize();
  });
}

export function ensureMapInitialized() {
  console.log('[map] ensure init');
  const missing = missingMapLibraries();
  if (missing.length) return null;
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

export async function focusPunktoOnMap(id) {
  if (!id) return;
  ensureMapInitialized();
  const punkto = ensurePunktoPrefix(id);
  const loc = decodeAtomLocation(punkto);
  if (!loc || !map) return;

  map.flyTo({ center: [loc.lon, loc.lat], zoom: 16, duration: 1200 });
  document.title = `Punkto · ${punkto}`;

  if (focusedPunktoId && focusedPunktoId !== id) {
    const prev = atomMarkers.get(`p:${focusedPunktoId}`);
    if (prev) prev.getElement().classList.remove('atom-bubble--focus');
  }
  focusedPunktoId = id;

  const focusAtoms = (await _getAllAtomsNewestFirst()).filter(a => !_isHiddenAtom(a));
  const focusedAtom = focusAtoms.find((atom) => {
    const pid = String(atom?.punkto || '').trim();
    const stable = getAtomStableId(atom);
    return pid === punkto || stripPunktoPrefix(pid) === id || stable === id;
  }) || null;
  if (focusedAtom && _onOpenMapBoardForAtom) {
    await _onOpenMapBoardForAtom(focusedAtom, focusAtoms);
  } else if (_onClearSelection) {
    _onClearSelection();
  }
  const cur = atomMarkers.get(punkto);
  if (cur) cur.getElement().classList.add('atom-bubble--focus');
}

export async function renderAtoms(newAtomIds = null) {
  if (!deckOverlay) return;

  const atoms = (await _getAllAtomsNewestFirst()).filter(a => !_isHiddenAtom(a));
  _lastRenderedAtoms = atoms;
  const zoom = map && typeof map.getZoom === 'function' ? map.getZoom() : 0;

  const atomsByPunkto = new Map();
  for (const a of atoms) {
    if (!a.punkto) continue;
    const arr = atomsByPunkto.get(a.punkto);
    if (arr) arr.push(a);
    else atomsByPunkto.set(a.punkto, [a]);
  }

  const selectionIds = await buildSelectionIds(atoms);
  const selectedAtomId = _getSelectedAtomId();
  const scatterData = atoms.map(a => {
    const selectionId = selectionIds.get(a) || getAtomStableId(a) || stripPunktoPrefix(a.punkto || '');
    const isSel = selectedAtomId && selectionId === selectedAtomId;
    const altitude = physicalAltitude(a);
    return {
      atom: a,
      selectionId,
      altitude,
      position: [a.lon, a.lat, altitude],
      ground: [a.lon, a.lat, 0],
      source: [a.lon, a.lat, 0],
      target: [a.lon, a.lat, altitude],
      color: mapColorForAtom(a, isSel ? 255 : 245),
      haloColor: mapColorForAtom(a, isSel ? 120 : 70),
      strokeColor: isSel ? [255, 255, 100, 255] : [8, 12, 20, 220],
      ringColor: mapColorForAtom(a, isSel ? 200 : 90),
      stemColor: mapColorForAtom(a, isSel ? 220 : 153),
      width: isSel ? 2.5 : 1.5,
      selected: isSel,
      hasHeight: altitude > 0,
      punkto: a.punkto,
      text: a.x,
      f: a.f,
      t: a.t,
      label: (a.x || a.f || '').slice(0, 40),
      spatialLabel: formatSpatialHeightLabel(altitude),
    };
  });

  const placementDraft = _getPlacementDraft();
  if (placementDraft) {
    const draftAlt = placementDraft.altitude_m || 0;
    scatterData.push({
      position: [placementDraft.lon, placementDraft.lat, draftAlt],
      ground: [placementDraft.lon, placementDraft.lat, 0],
      source: [placementDraft.lon, placementDraft.lat, 0],
      target: [placementDraft.lon, placementDraft.lat, draftAlt],
      color: rgba(DRAFT_COLOR, 255),
      haloColor: rgba(DRAFT_COLOR, 95),
      strokeColor: [8, 12, 20, 230],
      ringColor: rgba(DRAFT_COLOR, 120),
      stemColor: rgba(DRAFT_COLOR, 180),
      width: 2,
      selected: false,
      hasHeight: draftAlt > 0,
      selectionId: 'draft',
      punkto: 'draft',
      text: 'Placement preview',
      f: 'draft',
      t: Date.now(),
      label: 'draft',
      spatialLabel: draftAlt > 0 ? formatSpatialHeightLabel(draftAlt) : 'Ground',
    });
  }

  const groundRingData = scatterData.filter(d =>
    d.selected || d.selectionId === 'draft' || zoom >= SPATIAL_LOD.groundRelationZoom
  );
  const stemData = scatterData.filter(d =>
    d.hasHeight && (d.selected || d.selectionId === 'draft' || zoom >= SPATIAL_LOD.stemZoom)
  );
  const selectedLabelData = scatterData.filter(d => d.selected || d.selectionId === 'draft');

  const { ScatterplotLayer, TextLayer } = window.deck;
  const layers = [
    new ScatterplotLayer({
      id: 'atom-ground-rings',
      data: groundRingData,
      getPosition: d => d.ground,
      getFillColor: d => d.ringColor,
      stroked: true,
      getLineColor: d => d.ringColor,
      getLineWidth: d => d.selected ? 2 : 1,
      lineWidthUnits: 'pixels',
      getRadius: d => d.selected ? 18 : (d.hasHeight ? 11 : 9),
      radiusUnits: 'pixels',
      radiusMinPixels: 8,
      radiusMaxPixels: 28,
      pickable: false,
    }),
    new ScatterplotLayer({
      id: 'atom-category-halos',
      data: scatterData,
      getPosition: d => d.position,
      getFillColor: d => d.haloColor,
      getRadius: d => d.selected ? 26 : 18,
      radiusUnits: 'pixels',
      radiusMinPixels: 13,
      radiusMaxPixels: 36,
      pickable: false,
    }),
    new ScatterplotLayer({
      id: 'atoms',
      data: scatterData,
      getPosition: d => d.position,
      getFillColor: d => d.color,
      stroked: true,
      getLineColor: d => d.strokeColor,
      getLineWidth: d => d.selected ? 3 : 2,
      lineWidthUnits: 'pixels',
      getRadius: d => d.selectionId === 'draft' ? 15 : (d.selected ? 17 : 12),
      radiusUnits: 'pixels',
      radiusMinPixels: 8,
      radiusMaxPixels: 26,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 100, 255],
      onClick: info => {
        if (info.object?.selectionId === 'draft') return;
        if (!info.object || !map || !_onOpenMapBoardForAtom) return;
        _onOpenMapBoardForAtom(info.object.atom || info.object, atoms).catch((err) => console.warn('[map-board] open failed:', err));
      },
    }),
  ];

  const { LineLayer } = window.deck;
  if (LineLayer) {
    layers.push(
      new LineLayer({
        id: 'atom-lollipops',
        data: stemData,
        getSourcePosition: d => d.source,
        getTargetPosition: d => d.target,
        getColor: d => d.stemColor,
        getWidth: d => d.width,
        widthUnits: 'pixels',
        pickable: false,
      })
    );
  }

  if (TextLayer && selectedLabelData.length) {
    layers.push(
      new TextLayer({
        id: 'selected-atom-spatial-label',
        data: selectedLabelData,
        getPosition: d => d.position,
        getText: d => d.spatialLabel,
        getColor: d => d.selectionId === 'draft' ? [255, 246, 190, 255] : [244, 249, 255, 245],
        getBackgroundColor: d => d.selectionId === 'draft' ? [31, 25, 9, 220] : [8, 13, 22, 210],
        background: true,
        backgroundPadding: [7, 4],
        getSize: 13,
        sizeUnits: 'pixels',
        getPixelOffset: d => d.selectionId === 'draft' ? [0, -42] : [0, -34],
        getTextAnchor: 'middle',
        getAlignmentBaseline: 'bottom',
        billboard: true,
        pickable: false,
      })
    );
  }

  deckOverlay.setProps({ layers });

  const PILOT1_SLICE2_BUBBLES_ENABLED = false;
  if (map && PILOT1_SLICE2_BUBBLES_ENABLED) {
    const seen = new Set();
    for (const [pid, group] of atomsByPunkto) {
      const a = group[0];
      seen.add(pid);
      const count = group.length;
      let marker = atomMarkers.get(pid);
      let el;
      if (!marker) {
        el = buildBubbleElement(a, count, group);
        marker = new maplibregl.Marker({ element: el, anchor: 'bottom', offset: [0, -16] })
          .setLngLat([a.lon, a.lat])
          .addTo(map);
        atomMarkers.set(pid, marker);
      } else {
        el = marker.getElement();
        updateBubbleElement(el, a, count, group);
      }
      if (newAtomIds && newAtomIds.size > 0 && group.some(x => newAtomIds.has(x.id))) {
        el.classList.remove('atom-bubble--new');
        void el.offsetWidth;
        el.classList.add('atom-bubble--new');
        setTimeout(() => el.classList.remove('atom-bubble--new'), 700);
      }
    }
    for (const [pid, marker] of atomMarkers) {
      if (!seen.has(pid)) {
        marker.remove();
        atomMarkers.delete(pid);
      }
    }
  } else if (atomMarkers.size > 0) {
    for (const [, marker] of atomMarkers) marker.remove();
    atomMarkers.clear();
  }
  updateBubbleVisibility();
  if (svgLeaderOverlay) svgLeaderOverlay.innerHTML = '';

  if (!hasBootFit) hasBootFit = true;
}

export function cancelPlacementDraftHeightDrag() {
  endDraftHeightDrag();
}

export function updateCrosshairReadout() {
  const elCrosshairReadout = document.getElementById('crosshair-readout');
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

export function detectBuildingAtCenter() {
  if (!map) return { building: null };
  try {
    const center = map.getCenter();
    const screenPt = map.project(center);
    const layers = (map.getStyle().layers || []).filter(l => l.type === 'fill-extrusion' || (l.id && l.id.toLowerCase().includes('building'))).map(l => l.id);
    if (layers.length === 0) return { building: null };
    const R = 30;
    const box = [[screenPt.x - R, screenPt.y - R], [screenPt.x + R, screenPt.y + R]];
    const features = map.queryRenderedFeatures(box, { layers });
    if (!features || features.length === 0) return { building: null };
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

export function toggle3D() {
  if (!map) return;
  const elToggle3D = document.getElementById('toggle-3d');
  is3D = !is3D;
  if (is3D) {
    map.easeTo({ pitch: 45, bearing: -10, duration: 800 });
    if (elToggle3D) {
      elToggle3D.textContent = '2D';
      elToggle3D.title = 'Switch to 2D view';
    }
  } else {
    map.easeTo({ pitch: 0, bearing: 0, duration: 800 });
    if (elToggle3D) {
      elToggle3D.textContent = '3D';
      elToggle3D.title = 'Switch to 3D view';
    }
  }
}

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
  const rect = container.getBoundingClientRect();
  if (rect) console.log('[map] container size before init', Math.round(rect.width), Math.round(rect.height));
  const { MapboxOverlay } = window.deck;

  try {
    map = new maplibregl.Map({
      container: 'map',
      style: _mapStyle,
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

  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
  map.addControl(
    new maplibregl.GeolocateControl({
      positionOptions: { enableHighAccuracy: true },
      trackUserLocation: false,
      showUserLocation: true,
      showAccuracyCircle: false,
    }),
    'bottom-right'
  );

  deckOverlay = new MapboxOverlay({
    interleaved: false,
    layers: [],
  });
  map.addControl(deckOverlay);
  installDraftHeightDragHandlers();

  map.on('load', async () => {
    console.log('[map] loaded');
    mapLoadComplete = true;

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

    ensureLeaderOverlay();
    map.on('render', drawLeaderLines);
    map.on('click', (e) => {
      const placementDraft = _getPlacementDraft();
      if (_isCreateModalOpen() && placementDraft && _setPlacementDraftPosition) {
        _setPlacementDraftPosition(e.lngLat.lat, e.lngLat.lng);
      }
    });

    if (!_hasDeepLink() && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          try {
            map.jumpTo({
              center: [pos.coords.longitude, pos.coords.latitude],
              zoom: 14,
              pitch: 45,
              bearing: -10,
            });
            updateBubbleVisibility();
            drawLeaderLines();
            queueRefreshUI();
          } catch (e) {
            console.warn('[punkto] nearby-center jumpTo failed:', e);
          }
        },
        (err) => {
          console.log('[punkto] nearby geolocation unavailable:', err?.message || err);
        },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
      );
    }

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

    if (_onRefreshUI) await _onRefreshUI();
    requestAnimationFrame(() => { if (map) map.resize(); });
    if (_onFocusDeepLinkIfReady) await _onFocusDeepLinkIfReady();
    if (_onShowOnboarding) _onShowOnboarding();
  });
  return map;
}

function installDraftHeightDragHandlers() {
  if (!map) return;
  const container = map.getContainer();
  if (!container || container._punktoDraftHeightDragInstalled) return;
  container._punktoDraftHeightDragInstalled = true;
  container.addEventListener('pointerdown', onDraftPointerDown, { capture: true });
}

function onDraftPointerDown(ev) {
  if (!map || !deckOverlay || !_isCreateModalOpen() || !_setPlacementDraftHeight) return;
  if (ev.button != null && ev.button !== 0) return;
  const draft = _getPlacementDraft();
  if (!draft) return;
  const point = eventPointInMap(ev);
  if (!point) return;
  const picked = deckOverlay.pickObject?.({
    x: point.x,
    y: point.y,
    radius: 18,
    layerIds: ['atoms'],
  });
  if (picked?.object?.selectionId !== 'draft') return;

  ev.preventDefault();
  ev.stopPropagation();
  if (typeof ev.stopImmediatePropagation === 'function') ev.stopImmediatePropagation();
  beginDraftHeightDrag(ev, draft);
}

function beginDraftHeightDrag(ev, draft) {
  endDraftHeightDrag();
  draftHeightDrag = {
    pointerId: ev.pointerId,
    startY: ev.clientY,
    startHeight: clampDraftHeight(draft.altitude_m || 0),
    lat: draft.lat,
    lon: draft.lon,
    gestures: disableMapGestures(),
  };
  const container = map?.getContainer();
  if (container) {
    container.classList.add('draft-height-dragging');
    try { container.setPointerCapture?.(ev.pointerId); } catch {}
  }
  window.addEventListener('pointermove', onDraftPointerMove, { capture: true });
  window.addEventListener('pointerup', onDraftPointerUp, { capture: true });
  window.addEventListener('pointercancel', onDraftPointerCancel, { capture: true });
}

function onDraftPointerMove(ev) {
  if (!draftHeightDrag || ev.pointerId !== draftHeightDrag.pointerId) return;
  ev.preventDefault();
  ev.stopPropagation();
  const nextHeight = heightFromPointerDelta(draftHeightDrag.startHeight, draftHeightDrag.startY - ev.clientY);
  draftHeightDragPending = nextHeight;
  if (draftHeightDragRaf) return;
  draftHeightDragRaf = requestAnimationFrame(() => {
    draftHeightDragRaf = null;
    const pending = draftHeightDragPending;
    draftHeightDragPending = null;
    if (pending == null) return;
    _setPlacementDraftHeight?.(pending, 'spatial-drag');
  });
}

function onDraftPointerUp(ev) {
  if (!draftHeightDrag || ev.pointerId !== draftHeightDrag.pointerId) return;
  ev.preventDefault();
  ev.stopPropagation();
  endDraftHeightDrag();
}

function onDraftPointerCancel(ev) {
  if (!draftHeightDrag || ev.pointerId !== draftHeightDrag.pointerId) return;
  endDraftHeightDrag();
}

function endDraftHeightDrag() {
  if (!draftHeightDrag) return;
  const drag = draftHeightDrag;
  draftHeightDrag = null;
  if (draftHeightDragRaf) {
    cancelAnimationFrame(draftHeightDragRaf);
    draftHeightDragRaf = null;
  }
  if (draftHeightDragPending != null) {
    _setPlacementDraftHeight?.(draftHeightDragPending, 'spatial-drag');
    draftHeightDragPending = null;
  }
  restoreMapGestures(drag.gestures);
  const container = map?.getContainer();
  if (container) {
    container.classList.remove('draft-height-dragging');
    try { container.releasePointerCapture?.(drag.pointerId); } catch {}
  }
  window.removeEventListener('pointermove', onDraftPointerMove, { capture: true });
  window.removeEventListener('pointerup', onDraftPointerUp, { capture: true });
  window.removeEventListener('pointercancel', onDraftPointerCancel, { capture: true });
}

function eventPointInMap(ev) {
  const rect = map?.getContainer()?.getBoundingClientRect();
  if (!rect) return null;
  return { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
}

function heightFromPointerDelta(startHeight, upwardPixels) {
  const start = clampDraftHeight(startHeight);
  const pixels = Number(upwardPixels) || 0;
  if (pixels <= 0) {
    return clampDraftHeight(start + pixels * (start > 30 ? 0.22 : 0.14));
  }
  if (start >= 30) return clampDraftHeight(start + pixels * 0.22);
  const pixelsToThirtyMeters = (30 - start) / 0.14;
  if (pixels <= pixelsToThirtyMeters) return clampDraftHeight(start + pixels * 0.14);
  return clampDraftHeight(30 + ((pixels - pixelsToThirtyMeters) * 0.22));
}

function clampDraftHeight(height) {
  const n = Number(height);
  if (!Number.isFinite(n)) return 0;
  return Math.min(MAX_DRAFT_HEIGHT_M, Math.max(0, n));
}

function disableMapGestures() {
  if (!map) return [];
  const names = ['dragPan', 'scrollZoom', 'boxZoom', 'dragRotate', 'keyboard', 'doubleClickZoom', 'touchZoomRotate'];
  const disabled = [];
  for (const name of names) {
    const gesture = map[name];
    if (!gesture || typeof gesture.disable !== 'function') continue;
    let wasEnabled = true;
    try {
      wasEnabled = typeof gesture.isEnabled === 'function' ? gesture.isEnabled() : true;
      if (wasEnabled) gesture.disable();
    } catch (err) {
      console.warn(`[map] could not disable ${name}:`, err);
      continue;
    }
    disabled.push({ gesture, wasEnabled, name });
  }
  return disabled;
}

function restoreMapGestures(gestures) {
  for (const item of Array.isArray(gestures) ? gestures : []) {
    if (!item.wasEnabled || !item.gesture || typeof item.gesture.enable !== 'function') continue;
    try {
      item.gesture.enable();
    } catch (err) {
      console.warn(`[map] could not restore ${item.name}:`, err);
    }
  }
}

async function buildSelectionIds(atoms) {
  if (!_getAtomSelectionId) return new Map();
  const pairs = await Promise.all((Array.isArray(atoms) ? atoms : []).map(async (atom) => [atom, await _getAtomSelectionId(atom)]));
  return new Map(pairs);
}

function queueRefreshUI() {
  if (_onQueueRefreshUI) _onQueueRefreshUI();
}

function getCategoryMeta(atom) {
  const key = String(atom?.category || atom?.kind || '').trim().toUpperCase();
  if (key === 'TALK') return CATEGORY_META.TEXT;
  return CATEGORY_META[key] || CATEGORY_META.TEXT;
}

function rgba(color, alpha = 245) {
  return [color[0], color[1], color[2], alpha];
}

function physicalAltitude(atom) {
  const alt = Number(atom?.alt);
  return Number.isFinite(alt) && alt > 0 ? alt : 0;
}

function formatSpatialHeightLabel(alt) {
  const height = Number(alt);
  if (!Number.isFinite(height) || height < 1) return 'Ground';
  const meters = Math.round(height);
  const floor = Math.max(1, Math.round(height / FLOOR_HEIGHT_M));
  return `+${meters} m · ~Floor ${floor}`;
}

function mapColorForAtom(atom, alpha = 245) {
  if (isImportedSourceAtom(atom)) return rgba(IMPORTED_SOURCE_COLOR, alpha);
  return rgba(getCategoryMeta(atom).color, alpha);
}

function isImportedSourceAtom(atom) {
  return atom?.imported === true || Boolean(String(atom?.import_source || '').trim());
}

function importedSourceLine(atom) {
  if (!isImportedSourceAtom(atom)) return '';
  const sourceName = String(atom?.source_name || atom?.source || '').trim();
  const station = String(atom?.source_station_name || '').trim();
  const stationId = String(atom?.source_station_id || '').trim();
  const details = [sourceName || 'Source data', [station, stationId].filter(Boolean).join(' ')].filter(Boolean);
  return `Imported source · ${details.join(' · ')}`;
}

function renderPopupText(atom, rawText) {
  const text = String(rawText || '').trim();
  if (!text) return '';
  if (!isImportedSourceAtom(atom)) return `<div class="popup-text">${escHtml(text)}</div>`;

  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (!lines.length) return '';
  const title = lines.shift();
  const rows = [];
  const notes = [];
  for (const line of lines.slice(0, 5)) {
    const match = line.match(/^([^:]{2,32}):\s*(.+)$/);
    if (match) rows.push({ key: match[1], value: match[2] });
    else notes.push(line);
  }

  return [
    '<div class="popup-imported-card">',
    `<div class="popup-imported-title">${escHtml(title)}</div>`,
    rows.length ? '<dl class="popup-imported-facts">' + rows.map((row) =>
      `<div><dt>${escHtml(row.key)}</dt><dd>${escHtml(row.value)}</dd></div>`
    ).join('') + '</dl>' : '',
    notes.length ? `<div class="popup-imported-note">${escHtml(notes.join(' · '))}</div>` : '',
    '</div>',
  ].filter(Boolean).join('');
}

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
    const sourceLine = importedSourceLine(a);
    html = [
      isImportedSourceAtom(a) ? '<div class="popup-source-badge">Imported source</div>' : '',
      renderPopupText(a, text),
      sourceLine ? `<div class="popup-source-line">${escHtml(sourceLine)} · not user-created content</div>` : '',
      `<div class="popup-meta">${escHtml(a.f || 'anon')} · ${timeStr}</div>`,
      coordStr ? `<div class="popup-coords">${coordStr}</div>` : '',
    ].filter(Boolean).join('');
  } else {
    const sorted = atoms.slice().sort((a, b) => (b.t || 0) - (a.t || 0));
    const head = `<div class="popup-meta" style="font-weight:600;">${sorted.length} Punkti at this place</div>`;
    const items = sorted.map(a => {
      const text = a.text || a.x || '';
      const timeStr = fmtTime(a.t);
      const sourceLine = importedSourceLine(a);
      return [
        '<div class="popup-atom" style="margin-top:8px;padding-top:6px;border-top:1px solid #333;">',
        isImportedSourceAtom(a) ? '<div class="popup-source-badge">Imported source</div>' : '',
        renderPopupText(a, text),
        sourceLine ? `<div class="popup-source-line">${escHtml(sourceLine)}</div>` : '',
        `<div class="popup-meta">${escHtml(a.f || 'anon')} · ${timeStr}</div>`,
        '</div>',
      ].filter(Boolean).join('');
    }).join('');
    const loc = decodeAtomLocation(sorted[0].punkto);
    const coordStr = loc ? fmtCoords(loc.lat, loc.lon, loc.alt) : '';
    html = head + items +
      (coordStr ? `<div class="popup-coords">${coordStr}</div>` : '');
  }

  const hasImportedSource = atoms.some(isImportedSourceAtom);
  new maplibregl.Popup({
    closeButton: true,
    maxWidth: hasImportedSource ? '340px' : '280px',
    className: hasImportedSource ? 'punkto-popup punkto-popup--imported' : 'punkto-popup',
  })
    .setLngLat(lngLat)
    .setHTML(html)
    .addTo(map);
}

function buildBubbleElement(atom, count = 1, group = null) {
  const el = document.createElement('div');
  el.className = 'atom-bubble';
  el.dataset.punkto = atom.punkto || '';
  if (focusedPunktoId && atom.punkto === `p:${focusedPunktoId}`) {
    el.classList.add('atom-bubble--focus');
  }
  updateBubbleElement(el, atom, count, group);

  el.addEventListener('click', (ev) => {
    ev.stopPropagation();
    if (ev.target.closest('a')) return;
    if (ev.target.closest('.atom-bubble-count')) return;
    const currentGroup = el._punktoGroup || [atom];
    const selectedAtom = currentGroup[0] || atom;
    if (_onOpenTextBoardForAtom) _onOpenTextBoardForAtom(selectedAtom, currentGroup);
  });

  return el;
}

function updateBubbleElement(el, atom, count = 1, group = null) {
  const textHtml = renderAtomText(atom.x || '');
  const author = escHtml(atom.f || 'anon');
  const timeStr = escHtml(fmtRelativeTime(atom.t));
  const cat = getCategoryMeta(atom);
  const isImportedSource = isImportedSourceAtom(atom);

  el._punktoGroup = group || [atom];

  const badgeHtml = count > 1
    ? `<span class="atom-bubble-count" title="${count} Punkti at this place">+${count - 1}</span>`
    : '';

  let altBadgeHtml = '';
  const _loc = atom.punkto ? decodeAtomLocation(atom.punkto) : null;
  if (_loc && _loc.alt > 0) {
    const altRounded = Math.round(_loc.alt);
    altBadgeHtml = `<span class="atom-bubble-alt" title="altitude: ${altRounded} m">+${altRounded}m</span>`;
  }

  el.innerHTML = `
    <div class="atom-bubble-body${isImportedSource ? ' atom-bubble-body--imported-source' : ''}">
      ${isImportedSource ? '<div class="atom-bubble-source">Imported source</div>' : ''}
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

  const body = el.querySelector('.atom-bubble-body');
  if (body) {
    const hue = hashAuthorHue(atom.f);
    if (!isImportedSource && hue != null) body.style.setProperty('--author-hue', String(hue));
    else body.style.removeProperty('--author-hue');
  }

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

function updateBubbleVisibility() {
  if (!map) return;
  const z = map.getZoom();
  let anyAtomInViewport = false;
  const bounds = (typeof map.getBounds === 'function') ? map.getBounds() : null;
  for (const [, marker] of atomMarkers) {
    const el = marker.getElement();
    if (z < 10) {
      el.style.display = 'none';
    } else {
      el.style.display = '';
      el.classList.toggle('atom-bubble--compact', z < 14);
    }
  }
  if (bounds) {
    for (const a of _lastRenderedAtoms) {
      if (bounds.contains([a.lon, a.lat])) {
        anyAtomInViewport = true;
        break;
      }
    }
  }
  const elMapEmptyHint = document.getElementById('map-empty-hint');
  if (elMapEmptyHint) {
    const showEmpty = _getCurrentPage() === 'map' && !anyAtomInViewport;
    elMapEmptyHint.classList.toggle('open', showEmpty);
    elMapEmptyHint.setAttribute('aria-hidden', showEmpty ? 'false' : 'true');
  }
}

function ensureLeaderOverlay() {
  if (!map) return null;
  if (svgLeaderOverlay && svgLeaderOverlay.isConnected) return svgLeaderOverlay;
  const container = map.getContainer();
  let svg = container.querySelector('#leader-lines');
  if (!svg) {
    svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('id', 'leader-lines');
    svg.setAttribute('aria-hidden', 'true');
    container.appendChild(svg);
  }
  svgLeaderOverlay = svg;
  return svg;
}

function drawLeaderLines() {
  if (!map || atomMarkers.size === 0) {
    if (svgLeaderOverlay) svgLeaderOverlay.innerHTML = '';
    return;
  }
  const svg = ensureLeaderOverlay();
  if (!svg) return;

  const containerRect = map.getContainer().getBoundingClientRect();
  const parts = [];

  for (const [, marker] of atomMarkers) {
    const el = marker.getElement();
    if (!el || el.style.display === 'none') continue;

    const lngLat = marker.getLngLat();
    const dotPt = map.project([lngLat.lng, lngLat.lat]);
    if (!dotPt || !isFinite(dotPt.x) || !isFinite(dotPt.y)) continue;

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

    const group = el._punktoGroup;
    const atom = group && group.length ? group[0] : null;
    const lineColor = atom ? mapColorForAtom(atom, 255) : rgba(CATEGORY_META.TEXT.color, 255);

    parts.push(
      `<line x1="${dotPt.x.toFixed(1)}" y1="${dotPt.y.toFixed(1)}"` +
      ` x2="${bubbleX.toFixed(1)}" y2="${bubbleY.toFixed(1)}"` +
      ` stroke="rgb(${lineColor[0]} ${lineColor[1]} ${lineColor[2]})" stroke-width="1.5"` +
      ` stroke-opacity="0.65" stroke-linecap="round" />`
    );
  }

  svg.innerHTML = parts.join('');
}
