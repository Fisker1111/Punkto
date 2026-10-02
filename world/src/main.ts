import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './style.css';
import { realAdapter, fixtureAdapter, FIXTURE_START, FIXTURE_END, type WorldAtom } from './atomsAdapter';
import { ThreeAtoms } from './threeAtoms';
import { createUI } from './ui';

// V0.4: OpenFreeMap dark vector basemap (loaded by URL so MapLibre resolves its
// vector source), re-tinted to the tonal-separation palette via paint overrides
// in the load handler below: charcoal land, mid-grey roads, darker navy water,
// near-black background — atoms untouched and stay dominant.
type Theme = 'dark' | 'light';
const styles = { dark: 'https://tiles.openfreemap.org/styles/dark', light: 'https://tiles.openfreemap.org/styles/bright' };
let theme: Theme = 'dark';
const home = { center: [12.5683, 55.6761] as [number, number], zoom: 14.2, pitch: 58, bearing: -20 };
const overlay = new ThreeAtoms();
let map: maplibregl.Map;
const useFixtures = import.meta.env.VITE_USE_FIXTURES === '1';
const adapter = useFixtures ? fixtureAdapter : realAdapter;
let to = useFixtures ? FIXTURE_END : Date.now();
let from = useFixtures ? FIXTURE_START : to - 86400000;
let rangeReady = useFixtures;
let discovery: Promise<WorldAtom[]> | undefined;
let selected: WorldAtom | null = null;
let generation = 0;
let ready = false;
let tileError = false;
const select = (atom: WorldAtom | null) => {
  selected = atom;
  overlay.select(atom?.id ?? null);
  ui.detail(atom);
};
const ui = createUI(value => { to = value; void refresh(); }, () => map?.easeTo({ ...home, duration: 1100 }), select, () => select(null), () => applyTheme(theme === 'dark' ? 'light' : 'dark'), { from, to }, useFixtures);
function applyTheme(next: Theme) {
  theme = next;
  document.documentElement.dataset.theme = theme;
  document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')!.content = theme === 'dark' ? '#0a1017' : '#f6f4ef';
  ui.theme(theme);
  if (!map) return;
  ready = false;
  ++generation; // Ignore atom requests started before the style swap.
  tileError = false;
  map.setStyle(styles[theme]);
}
async function refresh() {
  if (!ready) return;
  const request = ++generation;
  const bounds = map.getBounds();
  try {
    if (!rangeReady) {
      discovery ??= adapter.getAtoms({ minLon: -180, maxLon: 180, minLat: -90, maxLat: 90 }, { from: 0, to: Number.MAX_SAFE_INTEGER });
      let initial: WorldAtom[];
      try { initial = await discovery; } catch (error) { discovery = undefined; throw error; }
      if (request !== generation) return;
      if (initial.length) {
        from = Math.min(...initial.map(atom => atom.t));
        to = Math.max(...initial.map(atom => atom.t));
      }
      rangeReady = true;
      ui.timeWindow({ from, to });
    }
    const atoms = await adapter.getAtoms({ minLon: bounds.getWest(), maxLon: bounds.getEast(), minLat: bounds.getSouth(), maxLat: bounds.getNorth() }, { from, to });
    if (request !== generation) return;
    overlay.setAtoms(atoms);
    ui.atoms(atoms);
    if (selected && !atoms.some(atom => atom.id === selected!.id)) select(null);
    ui.status(tileError ? 'Map tiles unavailable. Check your connection; messages remain explorable.' : atoms.length ? 'Select a light to discover its story.' : 'No messages here at this time. Wander further or move time forward.');
  } catch {
    if (request === generation) ui.status('Messages could not be loaded. Move the map to try again.');
  }
}
try {
  map = new maplibregl.Map({ container: 'map', style: styles[theme], ...home, maxPitch: 75, minZoom: 3, maxZoom: 19, attributionControl: false, canvasContextAttributes: { antialias: true } });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');
  map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
  map.touchZoomRotate.enableRotation();
  map.touchPitch.enable();
  map.on('style.load', () => {
    // V0.4 tonal-separation palette: raise land to charcoal and roads to clear
    // mid-grey, keep water a darker navy than land, and anchor the background
    // near-black — while atoms keep their designed luminance and stay dominant.
    const T = (layer: string, prop: string, value: unknown) => { try { map.setPaintProperty(layer, prop, value); } catch { /* layer may be absent at some zooms */ } };
    if (theme === 'dark') {
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
    } else {
      // Bright uses hyphenated layer IDs, unlike the accepted dark style.
      for (const layer of map.getStyle().layers) {
        const id = layer.id;
        if (layer.type === 'background') T(id, 'background-color', '#f6f4ef');
        if (layer.type === 'fill') {
          let color: string | undefined;
          if (id.startsWith('landuse-')) color = '#e9e7e1';
          if (id.startsWith('landcover-')) color = '#e5e5db';
          if (/wood/.test(id)) color = '#d9e0d4';
          if (/park|grass|cemetery/.test(id)) color = '#dbe5d5';
          if (id.startsWith('water')) color = '#a9c2d4';
          if (id.startsWith('building')) {
            color = '#c9c9c6';
            T(id, 'fill-outline-color', '#b6b6b2');
          }
          if (/aeroway|highway-area|pier/.test(id)) color = '#d5d5cf';
          if (color) T(id, 'fill-color', color);
        }
        if (layer.type === 'line') {
          if (/waterway|ferry/.test(id)) T(id, 'line-color', '#a9c2d4');
          else if (/railway/.test(id)) T(id, 'line-color', '#6a6a68');
          else if (/^(highway|bridge|tunnel|aeroway|road_pier)/.test(id)) {
            T(id, 'line-color', /casing/.test(id) ? '#deddd6' : /motorway/.test(id) ? '#5f5f5d' : /primary|secondary|tertiary|trunk/.test(id) ? '#6f6f6c' : '#8a8a86');
          }
        }
        if (layer.type === 'symbol' && layer.layout?.['text-field']) {
          T(id, 'text-color', '#454b4e');
          T(id, 'text-halo-color', '#f6f4ef');
        }
      }
    }
    if (!map.getLayer(overlay.id)) map.addLayer(overlay);
    ready = true; void refresh();
  });
  map.on('moveend', () => { void refresh(); });
  map.on('click', event => { if (ready) select(overlay.pick(event.point.x, event.point.y) ?? null); });
  map.on('mousemove', event => {
    if (ready) map.getCanvas().style.cursor = overlay.pick(event.point.x, event.point.y) ? 'pointer' : '';
  });
  map.on('error', () => { tileError = true; ui.status('Map tiles unavailable. Check your connection; messages remain explorable.'); });
  map.on('sourcedata', event => { if (event.sourceId === 'geography' && event.isSourceLoaded && tileError) { tileError = false; void refresh(); } });
  map.getCanvas().addEventListener('webglcontextlost', () => ui.status('Graphics paused. Reload to reopen the world.'));
} catch {
  ui.status('This world needs WebGL. Please try a browser with hardware acceleration enabled.');
}
