import maplibregl, { type StyleSpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './style.css';
import { fixtureAdapter, FIXTURE_START, FIXTURE_END, type WorldAtom } from './atomsAdapter';
import { ThreeAtoms } from './threeAtoms';
import { createUI } from './ui';

// Keyless global CARTO dark raster context. Only the basemap uses the network.
const style: StyleSpecification = {
  version: 8,
  sources: { geography: { type: 'raster', tiles: ['https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'], tileSize: 256, maxzoom: 20,
    attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions" target="_blank" rel="noopener">CARTO</a>' } },
  layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#0a1017' } },
    { id: 'geography', type: 'raster', source: 'geography', paint: { 'raster-opacity': 0.85, 'raster-saturation': -0.75 } }],
};
const home = { center: [12.5683, 55.6761] as [number, number], zoom: 14.2, pitch: 58, bearing: -20 };
const overlay = new ThreeAtoms();
let map: maplibregl.Map;
let to = FIXTURE_END;
let selected: WorldAtom | null = null;
let generation = 0;
let ready = false;
let tileError = false;
const select = (atom: WorldAtom | null) => {
  selected = atom;
  overlay.select(atom?.id ?? null);
  ui.detail(atom);
};
const ui = createUI(value => { to = value; void refresh(); }, () => map?.easeTo({ ...home, duration: 1100 }), select, () => select(null));
async function refresh() {
  if (!ready) return;
  const request = ++generation;
  const bounds = map.getBounds();
  try {
    const atoms = await fixtureAdapter.getAtoms({ minLon: bounds.getWest(), maxLon: bounds.getEast(), minLat: bounds.getSouth(), maxLat: bounds.getNorth() }, { from: FIXTURE_START, to });
    if (request !== generation) return;
    overlay.setAtoms(atoms);
    ui.atoms(atoms);
    if (selected && !atoms.some(atom => atom.id === selected!.id)) select(null);
    ui.status(tileError ? 'Map tiles unavailable. Check your connection; fixture messages remain explorable.' : atoms.length ? 'Select a light to discover its story.' : 'No messages here at this time. Wander further or move time forward.');
  } catch {
    if (request === generation) ui.status('Messages could not be loaded. Move the map to try again.');
  }
}
try {
  map = new maplibregl.Map({ container: 'map', style, ...home, maxPitch: 75, minZoom: 3, maxZoom: 19, attributionControl: false, canvasContextAttributes: { antialias: true } });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');
  map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
  map.touchZoomRotate.enableRotation();
  map.touchPitch.enable();
  map.on('load', () => { map.addLayer(overlay); ready = true; void refresh(); });
  map.on('moveend', () => { void refresh(); });
  map.on('click', event => { if (ready) select(overlay.pick(event.point.x, event.point.y) ?? null); });
  map.on('mousemove', event => {
    if (ready) map.getCanvas().style.cursor = overlay.pick(event.point.x, event.point.y) ? 'pointer' : '';
  });
  map.on('error', () => { tileError = true; ui.status('Map tiles unavailable. Check your connection; fixture messages remain explorable.'); });
  map.on('sourcedata', event => { if (event.sourceId === 'geography' && event.isSourceLoaded && tileError) { tileError = false; void refresh(); } });
  map.getCanvas().addEventListener('webglcontextlost', () => ui.status('Graphics paused. Reload to reopen the world.'));
} catch {
  ui.status('This world needs WebGL. Please try a browser with hardware acceleration enabled.');
}
