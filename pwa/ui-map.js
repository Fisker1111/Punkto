/**
 * ui-map.js — Punkto PWA Map view wrapper
 *
 * Owns:
 *  - map page show/hide assumptions (lazy initMap)
 *  - map resize when shown
 *  - focus atom on map wrapper (delegates to app.js focusPunkto)
 *  - lazy init hook
 *
 * Map engine (MapLibre/deck.gl, layers, markers, overlays) stays in app.js.
 */

let _getMap   = null;
let _initMap  = null;

/**
 * @param {Object} opts
 * @param {() => any}  opts.getMap   returns current MapLibre map instance or falsy
 * @param {() => void} opts.initMap  initializes the map (called lazily once)
 */
export function initMapView({ getMap, initMap } = {}) {
  _getMap  = typeof getMap  === 'function' ? getMap  : null;
  _initMap = typeof initMap === 'function' ? initMap : null;
}

/**
 * Called when the Map page becomes visible. Initializes the map the first
 * time the view is shown, otherwise just resizes the existing instance so
 * MapLibre picks up the now-visible container dimensions.
 */
export function showMapView() {
  const map = _getMap ? _getMap() : null;
  if (!map) {
    if (_initMap) _initMap();
    return;
  }
  requestAnimationFrame(() => {
    const m = _getMap ? _getMap() : null;
    if (m && typeof m.resize === 'function') m.resize();
  });
}

/**
 * Focus a punkto on the map. Thin wrapper that ensures the map is initialized
 * before delegating to app.js's focus logic.
 *
 * @param {Object} opts
 * @param {string} opts.punktoId       id without 'p:' prefix
 * @param {(id:string)=>void} opts.focusPunktoCb  app.js focus implementation
 */
export function focusOnMap({ punktoId, focusPunktoCb } = {}) {
  if (!punktoId || typeof focusPunktoCb !== 'function') return;
  const map = _getMap ? _getMap() : null;
  if (!map && _initMap) _initMap();
  focusPunktoCb(punktoId);
}
