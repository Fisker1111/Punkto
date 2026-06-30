/**
 * ui-cloud.js — Punkto AtomCloud 3D view (Three.js)
 *
 * Context layer: faint map floor, grid, compass, scale, height ruler.
 * Atom layer: glowing points, stems, ground contact rings.
 * No message text/cards in the scene (height-only label on selection).
 */

import * as THREE from './lib/three.module.min.js';

const SCENE_BG = 0x060810;
const GRID_SIZE = 2000;
const GRID_DIVISIONS = 80;
const MIN_CAM_RADIUS = 20;
const MAX_CAM_RADIUS = 2500;
const ATOM_RADIUS = 2.6;
const RULER_MAX_M = 30;
const MAP_ZOOM = 16;
const MAP_FLOOR_OPACITY = 0.22;
const DEFAULT_ATOM_RGB = [138, 160, 190];

let _decodeLocation = null;
let _categoryColor = null;
let _getUserLocation = null;

let _container = null;
let _renderer = null;
let _scene = null;
let _camera = null;
let _grid = null;
let _mapFloor = null;
let _mapFloorKey = '';
let _mapFloorLoading = null;
let _atomRoot = null;
let _raycaster = null;
let _pointer = new THREE.Vector2();
let _projVec = new THREE.Vector3();

let _initialized = false;
let _animating = false;
let _rafId = 0;

let _origin = { lat: 0, lon: 0 };
let _originIsUser = false;
let _cachedOriginKeys = '';
let _lastAtoms = [];
let _userMarker = null;
let _atomsById = new Map();
let _groupsById = new Map();
let _selectedId = null;

let _camTarget = new THREE.Vector3(0, 40, 0);
let _camRadius = 320;
let _camTheta = 0.75;
let _camPhi = 1.05;

let _dragging = false;
let _lastX = 0;
let _lastY = 0;
let _pressX = 0;
let _pressY = 0;
let _pinchStartDist = 0;
let _pinchStartRadius = _camRadius;

function _getContainer() {
  if (!_container) _container = document.getElementById('page-cloud');
  return _container;
}

function _metersPerDegree(lat) {
  const latRad = (lat * Math.PI) / 180;
  return {
    lat: 110540,
    lon: 111320 * Math.cos(latRad),
  };
}

function _toLocalMeters(lat, lon, alt, origin = _origin) {
  const scale = _metersPerDegree(origin.lat);
  const x = (Number(lon) - origin.lon) * scale.lon;
  const z = (Number(lat) - origin.lat) * scale.lat;
  const y = Number.isFinite(Number(alt)) ? Number(alt) : 0;
  return { x, y, z };
}

function _atomKey(atom) {
  const id = String(atom?.punkto || atom?.id || '').replace(/^p:/, '').trim();
  return id || null;
}

function _resolveLocation(atom) {
  if (Number.isFinite(atom?.lat) && Number.isFinite(atom?.lon)) {
    return {
      lat: atom.lat,
      lon: atom.lon,
      alt: Number.isFinite(atom?.alt) ? atom.alt : 0,
    };
  }
  if (typeof _decodeLocation === 'function' && atom?.punkto) {
    const loc = _decodeLocation(atom.punkto);
    if (loc) return loc;
  }
  return null;
}

function _computeOrigin(atoms) {
  const locs = [];
  for (const atom of atoms) {
    const loc = _resolveLocation(atom);
    if (loc && Number.isFinite(loc.lat) && Number.isFinite(loc.lon)) {
      locs.push(loc);
    }
  }
  if (!locs.length) return { lat: 0, lon: 0 };
  const lat = locs.reduce((s, l) => s + l.lat, 0) / locs.length;
  const lon = locs.reduce((s, l) => s + l.lon, 0) / locs.length;
  return { lat, lon };
}

function _pickOrigin(atoms, userLoc) {
  if (userLoc && Number.isFinite(userLoc.lat) && Number.isFinite(userLoc.lon)) {
    return { lat: userLoc.lat, lon: userLoc.lon };
  }
  return _computeOrigin(atoms);
}

function _keysSignature(keys) {
  return [...keys].sort().join('|');
}

function _userGeoSignature(userLoc) {
  if (!userLoc || !Number.isFinite(userLoc.lat) || !Number.isFinite(userLoc.lon)) return 'none';
  return `${userLoc.lat.toFixed(4)},${userLoc.lon.toFixed(4)}`;
}

function _originSignature(userLoc, keys) {
  return `${_userGeoSignature(userLoc)}|${_keysSignature(keys)}`;
}

function _getAtomRgb(atom) {
  if (typeof _categoryColor === 'function') {
    const rgb = _categoryColor(atom);
    if (Array.isArray(rgb) && rgb.length >= 3) return rgb;
  }
  return DEFAULT_ATOM_RGB;
}

function _rgbToThreeColor(rgb) {
  const [r, g, b] = Array.isArray(rgb) && rgb.length >= 3 ? rgb : DEFAULT_ATOM_RGB;
  return new THREE.Color(r / 255, g / 255, b / 255);
}

function _metersPerPixel(lat, zoom) {
  const latRad = (lat * Math.PI) / 180;
  return (156543.03392 * Math.cos(latRad)) / Math.pow(2, zoom);
}

function _loadOsmTile(tx, ty, zoom) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`tile ${zoom}/${tx}/${ty}`));
    img.src = `https://tile.openstreetmap.org/${zoom}/${tx}/${ty}.png`;
  });
}

async function _buildMapTexture(lat, lon) {
  const zoom = MAP_ZOOM;
  const latRad = (lat * Math.PI) / 180;
  const mpp = _metersPerPixel(lat, zoom);
  const canvasSize = Math.min(2048, Math.max(512, Math.ceil(GRID_SIZE / mpp)));
  const halfM = GRID_SIZE / 2;
  const pxPerMeter = 1 / mpp;
  const n = 2 ** zoom;

  const originWorldX = ((lon + 180) / 360) * n * 256;
  const originWorldY = ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n * 256;

  const topLeftWorldX = originWorldX - halfM * pxPerMeter;
  const topLeftWorldY = originWorldY - halfM * pxPerMeter;

  const canvas = document.createElement('canvas');
  canvas.width = canvasSize;
  canvas.height = canvasSize;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#060810';
  ctx.fillRect(0, 0, canvasSize, canvasSize);

  const tileMinX = Math.floor(topLeftWorldX / 256);
  const tileMinY = Math.floor(topLeftWorldY / 256);
  const tileMaxX = Math.floor((topLeftWorldX + canvasSize) / 256);
  const tileMaxY = Math.floor((topLeftWorldY + canvasSize) / 256);

  const jobs = [];
  for (let ty = tileMinY; ty <= tileMaxY; ty += 1) {
    for (let tx = tileMinX; tx <= tileMaxX; tx += 1) {
      jobs.push(
        _loadOsmTile(tx, ty, zoom)
          .then((img) => {
            const dx = tx * 256 - topLeftWorldX;
            const dy = ty * 256 - topLeftWorldY;
            ctx.drawImage(img, dx, dy);
          })
          .catch(() => {}),
      );
    }
  }
  await Promise.all(jobs);

  ctx.fillStyle = 'rgba(6, 8, 16, 0.76)';
  ctx.fillRect(0, 0, canvasSize, canvasSize);

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

function _disposeMapFloor() {
  if (!_mapFloor) return;
  _scene?.remove(_mapFloor);
  _mapFloor.geometry?.dispose();
  _mapFloor.material?.map?.dispose();
  _mapFloor.material?.dispose();
  _mapFloor = null;
}

async function _loadMapFloor() {
  if (!_scene) return;
  const key = `${_origin.lat.toFixed(4)},${_origin.lon.toFixed(4)}`;
  if (key === _mapFloorKey && _mapFloor) return;
  if (_mapFloorLoading) return _mapFloorLoading;

  _mapFloorLoading = (async () => {
    try {
      if (!Number.isFinite(_origin.lat) || !Number.isFinite(_origin.lon)) return;
      if (_origin.lat === 0 && _origin.lon === 0) return;
      const tex = await _buildMapTexture(_origin.lat, _origin.lon);
      if (!_scene) return;
      _disposeMapFloor();
      const mat = new THREE.MeshBasicMaterial({
        map: tex,
        transparent: true,
        opacity: MAP_FLOOR_OPACITY,
        depthWrite: false,
      });
      _mapFloor = new THREE.Mesh(new THREE.PlaneGeometry(GRID_SIZE, GRID_SIZE), mat);
      _mapFloor.rotation.x = -Math.PI / 2;
      _mapFloor.position.y = -0.06;
      _scene.add(_mapFloor);
      if (_grid?.material) {
        _grid.material.opacity = 0.24;
        _grid.material.transparent = true;
      }
      _mapFloorKey = key;
    } catch (err) {
      console.warn('[cloud] map floor failed:', err);
    } finally {
      _mapFloorLoading = null;
    }
  })();
  return _mapFloorLoading;
}

function _updateCameraPosition() {
  if (!_camera) return;
  const sinPhi = Math.sin(_camPhi);
  _camera.position.set(
    _camTarget.x + _camRadius * sinPhi * Math.sin(_camTheta),
    _camTarget.y + _camRadius * Math.cos(_camPhi),
    _camTarget.z + _camRadius * sinPhi * Math.cos(_camTheta),
  );
  _camera.lookAt(_camTarget);
  _updateCloudHud();
}

function _makeAtomMaterial(selected = false, rgb = DEFAULT_ATOM_RGB) {
  const color = _rgbToThreeColor(rgb);
  return new THREE.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: selected ? 1.5 : 0.9,
    metalness: 0.12,
    roughness: 0.32,
  });
}

function _makeStemMaterial(selected = false, rgb = DEFAULT_ATOM_RGB) {
  const base = _rgbToThreeColor(rgb);
  return new THREE.LineDashedMaterial({
    color: selected ? base : new THREE.Color(0x4a6888),
    dashSize: 2.2,
    gapSize: 1.6,
    transparent: true,
    opacity: selected ? 0.95 : 0.68,
    linewidth: 1,
  });
}

function _rebuildStemLine(stem, height, material) {
  stem.geometry?.dispose();
  stem.geometry = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(0, Math.max(height, 0.01), 0),
  ]);
  stem.material = material;
  stem.computeLineDistances();
}

function _makeGroundContact(rgb, selected = false) {
  const color = _rgbToThreeColor(rgb);
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(2.8, 4.8, 32),
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: selected ? 0.72 : 0.42,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
  );
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = 0.1;
  const disc = new THREE.Mesh(
    new THREE.CircleGeometry(2.8, 24),
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: selected ? 0.22 : 0.12,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
  );
  disc.rotation.x = -Math.PI / 2;
  disc.position.y = 0.09;
  const group = new THREE.Group();
  group.add(disc);
  group.add(ring);
  return { group, ring, disc };
}

function _positionAtomEntry(entry, atom) {
  const loc = _resolveLocation(atom);
  if (!loc || !entry) return;
  const pos = _toLocalMeters(loc.lat, loc.lon, loc.alt);
  entry.group.position.set(pos.x, 0, pos.z);
  entry.sphere.position.y = pos.y;
  entry.localY = pos.y;
  const key = _atomKey(atom);
  _rebuildStemLine(entry.stem, pos.y, _makeStemMaterial(_selectedId === key, _getAtomRgb(atom)));
  entry.atom = atom;
}

function _buildAtomGroup(atom, key) {
  const loc = _resolveLocation(atom);
  if (!loc) return null;
  const pos = _toLocalMeters(loc.lat, loc.lon, loc.alt);
  const rgb = _getAtomRgb(atom);

  const group = new THREE.Group();
  group.position.set(pos.x, 0, pos.z);
  group.userData = { atomKey: key, atom, localY: pos.y };

  const ground = _makeGroundContact(rgb, false);
  group.add(ground.group);

  const stem = new THREE.Line(
    new THREE.BufferGeometry(),
    _makeStemMaterial(false, rgb),
  );
  _rebuildStemLine(stem, pos.y, stem.material);

  const sphere = new THREE.Mesh(
    new THREE.SphereGeometry(ATOM_RADIUS, 20, 20),
    _makeAtomMaterial(false, rgb),
  );
  sphere.position.y = pos.y;
  sphere.userData = { atomKey: key, pickTarget: true };

  group.add(stem);
  group.add(sphere);

  return { group, sphere, stem, ground, localY: pos.y, atom };
}

function _updateGroundContactVisual(entry, selected) {
  const color = _rgbToThreeColor(_getAtomRgb(entry.atom));
  entry.ground.ring.material.color.copy(color);
  entry.ground.ring.material.opacity = selected ? 0.72 : 0.42;
  entry.ground.disc.material.color.copy(color);
  entry.ground.disc.material.opacity = selected ? 0.22 : 0.12;
}

function _applySelectionVisual(key) {
  for (const [id, entry] of _groupsById) {
    const selected = id === key;
    const rgb = _getAtomRgb(entry.atom);
    entry.sphere.material = _makeAtomMaterial(selected, rgb);
    entry.sphere.scale.setScalar(selected ? 1.45 : 1);
    entry.stem.material.dispose();
    _rebuildStemLine(entry.stem, entry.localY, _makeStemMaterial(selected, rgb));
    _updateGroundContactVisual(entry, selected);
  }
  _updateCloudHud();
}

function _fitCameraToAtoms() {
  if (!_groupsById.size && !_originIsUser) {
    _camTarget.set(0, 40, 0);
    _camRadius = 320;
    _updateCameraPosition();
    return;
  }

  const box = new THREE.Box3();
  if (_originIsUser) box.expandByPoint(new THREE.Vector3(0, 0, 0));
  for (const entry of _groupsById.values()) {
    box.expandByObject(entry.group);
  }
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  _camTarget.copy(center);
  _camTarget.y = Math.max(center.y * 0.55, 20);
  const span = Math.max(size.x, size.z, size.y, 80);
  _camRadius = THREE.MathUtils.clamp(span * 1.35, MIN_CAM_RADIUS, MAX_CAM_RADIUS);
  _updateCameraPosition();
}

function _disposeMarker(marker) {
  if (!marker) return null;
  if (marker.parent) marker.parent.remove(marker);
  marker.traverse((obj) => {
    if (obj.geometry) obj.geometry.dispose();
    if (obj.material) {
      if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose());
      else obj.material.dispose();
    }
  });
  return null;
}

function _ensureUserMarker(show) {
  if (!_scene) return;
  if (!show) {
    _userMarker = _disposeMarker(_userMarker);
    return;
  }
  if (_userMarker) return;
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(2.5, 4.5, 32),
    new THREE.MeshBasicMaterial({
      color: 0x00d4ff,
      transparent: true,
      opacity: 0.85,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
  );
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = 0.12;
  const dot = new THREE.Mesh(
    new THREE.CircleGeometry(1.2, 24),
    new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.55, side: THREE.DoubleSide }),
  );
  dot.rotation.x = -Math.PI / 2;
  dot.position.y = 0.11;
  const group = new THREE.Group();
  group.add(ring);
  group.add(dot);
  _scene.add(group);
  _userMarker = group;
}

function _pickScaleMeters(visibleW) {
  const targets = [20, 50, 100, 200, 500, 1000];
  const goal = visibleW * 0.28;
  let best = targets[0];
  for (const t of targets) {
    if (Math.abs(t - goal) < Math.abs(best - goal)) best = t;
  }
  return best;
}

function _updateCloudHud() {
  const hud = document.getElementById('cloud-hud');
  if (!hud || !_container || _container.offsetParent === null) return;

  const rulerMarker = document.getElementById('cloud-ruler-marker');
  const scaleBar = document.getElementById('cloud-scale-bar');
  const compassDial = document.getElementById('cloud-compass-dial');
  const altLabel = document.getElementById('cloud-alt-label');

  if (rulerMarker) {
    const entry = _selectedId ? _groupsById.get(_selectedId) : null;
    if (entry) {
      const pct = THREE.MathUtils.clamp((entry.localY / RULER_MAX_M) * 100, 0, 100);
      rulerMarker.style.bottom = `${pct}%`;
      rulerMarker.classList.add('visible');
    } else {
      rulerMarker.classList.remove('visible');
    }
  }

  if (scaleBar && _camera) {
    const fovRad = (_camera.fov * Math.PI) / 180;
    const visibleW = 2 * _camRadius * Math.tan(fovRad / 2) * _camera.aspect * Math.sin(_camPhi);
    const scaleM = _pickScaleMeters(visibleW);
    const barPx = Math.round((_container.clientWidth || 320) * 0.18);
    scaleBar.textContent = `${scaleM} m`;
    scaleBar.style.setProperty('--cloud-scale-w', `${barPx}px`);
  }

  if (compassDial) {
    compassDial.style.transform = `rotate(${-_camTheta * (180 / Math.PI)}deg)`;
  }

  if (altLabel && _renderer && _camera) {
    const entry = _selectedId ? _groupsById.get(_selectedId) : null;
    if (!entry) {
      altLabel.hidden = true;
    } else {
      const bobY = entry.sphere.position.y;
      _projVec.set(entry.group.position.x, bobY, entry.group.position.z);
      _projVec.project(_camera);
      if (_projVec.z > 1) {
        altLabel.hidden = true;
      } else {
        const rect = _renderer.domElement.getBoundingClientRect();
        const sx = (_projVec.x * 0.5 + 0.5) * rect.width;
        const sy = (-_projVec.y * 0.5 + 0.5) * rect.height;
        altLabel.textContent = `+${Math.round(entry.localY)}m`;
        altLabel.style.left = `${sx}px`;
        altLabel.style.top = `${sy}px`;
        altLabel.hidden = false;
      }
    }
  }
}

function _bindHudControls() {
  const btn = document.getElementById('cloud-recenter-btn');
  if (!btn || btn.dataset.cloudHudBound === '1') return;
  btn.dataset.cloudHudBound = '1';
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    _fitCameraToAtoms();
  });
}

function _onPointerDown(ev) {
  if (ev.pointerType === 'touch' && ev.isPrimary === false) return;
  _dragging = true;
  _pressX = ev.clientX;
  _pressY = ev.clientY;
  _lastX = ev.clientX;
  _lastY = ev.clientY;
  if (_container) _container.setPointerCapture(ev.pointerId);
}

function _onPointerMove(ev) {
  if (!_dragging) return;
  const dx = ev.clientX - _lastX;
  const dy = ev.clientY - _lastY;
  _lastX = ev.clientX;
  _lastY = ev.clientY;
  _camTheta -= dx * 0.005;
  _camPhi = THREE.MathUtils.clamp(_camPhi + dy * 0.005, 0.15, Math.PI - 0.12);
  _updateCameraPosition();
}

function _onPointerUp(ev) {
  _dragging = false;
  if (_container && _container.hasPointerCapture(ev.pointerId)) {
    _container.releasePointerCapture(ev.pointerId);
  }
}

function _onWheel(ev) {
  ev.preventDefault();
  const delta = ev.deltaY > 0 ? 1.08 : 0.92;
  _camRadius = THREE.MathUtils.clamp(_camRadius * delta, MIN_CAM_RADIUS, MAX_CAM_RADIUS);
  _updateCameraPosition();
}

function _onTouchStart(ev) {
  if (ev.touches.length === 2) {
    const dx = ev.touches[0].clientX - ev.touches[1].clientX;
    const dy = ev.touches[0].clientY - ev.touches[1].clientY;
    _pinchStartDist = Math.hypot(dx, dy);
    _pinchStartRadius = _camRadius;
  }
}

function _onTouchMove(ev) {
  if (ev.touches.length !== 2 || !_pinchStartDist) return;
  ev.preventDefault();
  const dx = ev.touches[0].clientX - ev.touches[1].clientX;
  const dy = ev.touches[0].clientY - ev.touches[1].clientY;
  const dist = Math.hypot(dx, dy);
  const scale = _pinchStartDist / Math.max(dist, 1);
  _camRadius = THREE.MathUtils.clamp(_pinchStartRadius * scale, MIN_CAM_RADIUS, MAX_CAM_RADIUS);
  _updateCameraPosition();
}

function _pickAtom(clientX, clientY) {
  if (!_camera || !_renderer || !_raycaster) return null;
  const rect = _renderer.domElement.getBoundingClientRect();
  _pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
  _pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
  _raycaster.setFromCamera(_pointer, _camera);
  const meshes = [];
  for (const entry of _groupsById.values()) meshes.push(entry.sphere);
  const hits = _raycaster.intersectObjects(meshes, false);
  if (!hits.length) return null;
  return hits[0].object.userData.atomKey || null;
}

function _onClick(ev) {
  if (Math.hypot(ev.clientX - _pressX, ev.clientY - _pressY) > 6) return;
  const key = _pickAtom(ev.clientX, ev.clientY);
  if (!key) {
    _selectedId = null;
    _applySelectionVisual(null);
    return;
  }
  _selectedId = key;
  _applySelectionVisual(key);
}

function _bindControls() {
  const el = _getContainer();
  if (!el || el.dataset.cloudBound === '1') return;
  el.dataset.cloudBound = '1';
  el.addEventListener('pointerdown', _onPointerDown);
  el.addEventListener('pointermove', _onPointerMove);
  el.addEventListener('pointerup', _onPointerUp);
  el.addEventListener('pointercancel', _onPointerUp);
  el.addEventListener('wheel', _onWheel, { passive: false });
  el.addEventListener('touchstart', _onTouchStart, { passive: true });
  el.addEventListener('touchmove', _onTouchMove, { passive: false });
  el.addEventListener('click', _onClick);
  _bindHudControls();
}

function _bindWebGLContextHandlers() {
  if (!_renderer?.domElement || _renderer.domElement.dataset.contextBound === '1') return;
  _renderer.domElement.dataset.contextBound = '1';
  _renderer.domElement.addEventListener('webglcontextlost', (e) => {
    e.preventDefault();
    _stopAnimation();
  });
  _renderer.domElement.addEventListener('webglcontextrestored', () => {
    _teardownScene(false);
    _buildScene();
    _syncAtomMeshes(_lastAtoms);
    _startAnimation();
  });
}

function _teardownScene(resetControls = true) {
  _stopAnimation();
  _clearAtoms();
  _userMarker = _disposeMarker(_userMarker);
  _disposeMapFloor();
  _mapFloorKey = '';
  if (_renderer) {
    _renderer.dispose();
    _renderer.domElement?.remove();
  }
  _renderer = null;
  _scene = null;
  _camera = null;
  _grid = null;
  _atomRoot = null;
  _raycaster = null;
  _initialized = false;
  if (resetControls) {
    const el = _getContainer();
    if (el) delete el.dataset.cloudBound;
  }
}

function _buildScene() {
  const el = _getContainer();
  if (!el) return false;

  _scene = new THREE.Scene();
  _scene.background = new THREE.Color(SCENE_BG);
  _scene.fog = new THREE.FogExp2(SCENE_BG, 0.00035);

  _camera = new THREE.PerspectiveCamera(55, 1, 0.5, 12000);
  _updateCameraPosition();

  _renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  _renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  _renderer.setClearColor(SCENE_BG, 1);
  el.insertBefore(_renderer.domElement, el.firstChild);

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(GRID_SIZE, GRID_SIZE),
    new THREE.MeshBasicMaterial({ color: 0x04060c, transparent: true, opacity: 0.95 }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.1;
  _scene.add(floor);

  _grid = new THREE.GridHelper(GRID_SIZE, GRID_DIVISIONS, 0x1a3355, 0x0f1a28);
  _grid.material.opacity = 0.55;
  _grid.material.transparent = true;
  _grid.position.y = 0.02;
  _scene.add(_grid);

  _scene.add(new THREE.AmbientLight(0x334466, 0.55));
  const keyLight = new THREE.DirectionalLight(0xaaccff, 0.65);
  keyLight.position.set(120, 260, 80);
  _scene.add(keyLight);

  _atomRoot = new THREE.Group();
  _scene.add(_atomRoot);

  _raycaster = new THREE.Raycaster();

  _bindControls();
  _bindWebGLContextHandlers();
  _resize();
  if (!window.__punktoCloudResizeBound) {
    window.__punktoCloudResizeBound = true;
    window.addEventListener('resize', () => {
      _resize();
      _updateCloudHud();
    });
  }

  _initialized = true;
  _loadMapFloor().catch(() => {});
  return true;
}

function _resize() {
  if (!_renderer || !_camera || !_container) return;
  const w = _container.clientWidth || window.innerWidth;
  const h = _container.clientHeight || window.innerHeight;
  if (w < 1 || h < 1) return;
  _renderer.setSize(w, h, false);
  _camera.aspect = w / h;
  _camera.updateProjectionMatrix();
}

function _animate() {
  if (!_animating) return;
  _rafId = requestAnimationFrame(_animate);
  const t = performance.now() * 0.001;
  for (const entry of _groupsById.values()) {
    const bob = Math.sin(t * 1.6 + entry.localY * 0.08) * 0.35;
    entry.sphere.position.y = entry.localY + bob;
  }
  if (_renderer && _scene && _camera) _renderer.render(_scene, _camera);
  _updateCloudHud();
}

function _startAnimation() {
  if (_animating) return;
  _animating = true;
  _animate();
}

function _stopAnimation() {
  _animating = false;
  if (_rafId) cancelAnimationFrame(_rafId);
  _rafId = 0;
}

function _disposeAtomEntry(entry) {
  entry.sphere.geometry.dispose();
  entry.stem.geometry.dispose();
  entry.sphere.material.dispose();
  entry.stem.material.dispose();
  entry.ground.ring.geometry.dispose();
  entry.ground.disc.geometry.dispose();
  entry.ground.ring.material.dispose();
  entry.ground.disc.material.dispose();
}

function _clearAtoms() {
  if (!_atomRoot) return;
  for (const entry of _groupsById.values()) {
    _atomRoot.remove(entry.group);
    _disposeAtomEntry(entry);
  }
  _groupsById.clear();
  _atomsById.clear();
}

function _syncAtomMeshes(atoms) {
  if (!_atomRoot) return;
  const list = Array.isArray(atoms) ? atoms : [];
  _lastAtoms = list;

  const nextKeys = new Set();
  for (const atom of list) {
    const key = _atomKey(atom);
    if (!key) continue;
    const loc = _resolveLocation(atom);
    if (!loc) continue;
    nextKeys.add(key);
  }

  const keySig = _originSignature(
    typeof _getUserLocation === 'function' ? _getUserLocation() : null,
    nextKeys,
  );
  const originChanged = keySig !== _cachedOriginKeys;
  if (originChanged) {
    const userLoc = typeof _getUserLocation === 'function' ? _getUserLocation() : null;
    _origin = _pickOrigin(list, userLoc);
    _originIsUser = Boolean(userLoc && Number.isFinite(userLoc.lat) && Number.isFinite(userLoc.lon));
    _cachedOriginKeys = keySig;
    _loadMapFloor().catch(() => {});
  }
  _ensureUserMarker(_originIsUser);

  for (const atom of list) {
    const key = _atomKey(atom);
    if (!key || !nextKeys.has(key)) continue;

    const existing = _groupsById.get(key);
    if (existing) {
      _positionAtomEntry(existing, atom);
      _atomsById.set(key, atom);
      if (originChanged) continue;
      const rgb = _getAtomRgb(atom);
      const selected = _selectedId === key;
      existing.sphere.material = _makeAtomMaterial(selected, rgb);
      existing.stem.material.dispose();
      _rebuildStemLine(existing.stem, existing.localY, _makeStemMaterial(selected, rgb));
      _updateGroundContactVisual(existing, selected);
      continue;
    }

    const built = _buildAtomGroup(atom, key);
    if (!built) continue;
    _atomRoot.add(built.group);
    _groupsById.set(key, built);
    _atomsById.set(key, atom);
  }

  if (originChanged) {
    for (const entry of _groupsById.values()) {
      _positionAtomEntry(entry, entry.atom);
    }
  }

  for (const key of [..._groupsById.keys()]) {
    if (nextKeys.has(key)) continue;
    const entry = _groupsById.get(key);
    _atomRoot.remove(entry.group);
    _disposeAtomEntry(entry);
    _groupsById.delete(key);
    _atomsById.delete(key);
    if (_selectedId === key) _selectedId = null;
  }

  if (_selectedId && _groupsById.has(_selectedId)) _applySelectionVisual(_selectedId);
  else _updateCloudHud();
}

export function initCloudView({ decodeLocation, categoryColor, getUserLocation } = {}) {
  _decodeLocation = typeof decodeLocation === 'function' ? decodeLocation : null;
  _categoryColor = typeof categoryColor === 'function' ? categoryColor : null;
  _getUserLocation = typeof getUserLocation === 'function' ? getUserLocation : null;
}

export function showCloudView() {
  if (!_initialized) _buildScene();
  _resize();
  _startAnimation();
  _updateCloudHud();
}

export function hideCloudView() {
  _stopAnimation();
}

export function updateCloudAtoms(atoms, { fit = false } = {}) {
  if (!_initialized) _buildScene();
  if (!_initialized) return;
  const prevCount = _groupsById.size;
  _syncAtomMeshes(atoms);
  if (fit || prevCount === 0) _fitCameraToAtoms();
  if (_animating) _animate();
}

export function focusAtomInCloud(punktoId) {
  if (!_initialized) _buildScene();
  const key = String(punktoId || '').replace(/^p:/, '').trim();
  if (!key) return;
  const entry = _groupsById.get(key);
  if (!entry) return;
  _selectedId = key;
  _applySelectionVisual(key);
  const pos = entry.group.position;
  _camTarget.set(pos.x, Math.max(entry.localY * 0.6, 12), pos.z);
  _camRadius = THREE.MathUtils.clamp(Math.max(entry.localY + 80, 120), MIN_CAM_RADIUS, MAX_CAM_RADIUS);
  _updateCameraPosition();
}

export function isCloudInitialized() {
  return _initialized;
}
