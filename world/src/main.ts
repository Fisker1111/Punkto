import maplibregl, { type StyleSpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './style.css';
import { fixtureAdapter, FIXTURE_START, FIXTURE_END, type WorldAtom } from './atomsAdapter';
import { ThreeAtoms } from './threeAtoms';
import { createUI } from './ui';

// V0.4: OpenFreeMap dark vector basemap (loaded by URL so MapLibre resolves its
// vector source), re-tinted to the tonal-separation palette via paint overrides
// in the load handler below: charcoal land, mid-grey roads, darker navy water,
// near-black background — atoms untouched and stay dominant.
const style = 'https://tiles.openfreemap.org/styles/dark';
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
  map.on('load', () => {
    // V0.4 tonal-separation palette: raise land to charcoal and roads to clear
    // mid-grey, keep water a darker navy than land, and anchor the background
    // near-black — while atoms keep their designed luminance and stay dominant.
    const T = (layer: string, prop: string, value: unknown) => { try { map.setPaintProperty(layer, prop, value); } catch { /* layer may be absent at some zooms */ } };
    T('background', 'background-color', '#05070b');
    T('water', 'fill-color', '#111927');
    T('waterway', 'line-color', '#2e3948');
    T('landuse_residential', 'fill-color', '#3a3f47'); T('landuse_residential', 'fill-opacity', 1);
    T('landcover_wood', 'fill-color', '#32373f');
    T('landcover_glacier', 'fill-color', '#32373f');
    T('landuse_park', 'fill-color', '#343940');
    T('building', 'fill-color', '#4a515a'); T('building', 'fill-outline-color', '#5d656f');
    T('highway_minor', 'line-color', '#585f67');
    T('highway_major_casing', 'line-color', '#5c636b');
    T('highway_major_inner', 'line-color', '#687079');
    T('highway_major_subtle', 'line-color', '#585f67');
    T('highway_motorway_casing', 'line-color', '#626a71');
    T('highway_motorway_inner', 'line-color', '#767e87');
    T('highway_motorway_subtle', 'line-color', '#585f67');
    T('road_oneway', 'line-color', '#687079');
    T('road_oneway_opposite', 'line-color', '#687079');
    T('railway', 'line-color', '#464c53');
    map.addLayer(overlay); ready = true; void refresh();
  });
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
