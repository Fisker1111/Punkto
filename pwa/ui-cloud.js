/**
 * ui-cloud.js — Punkto AtomCloud 3D view (Three.js)
 *
 * Standalone immersive spatial view: glowing atoms at real-world height,
 * vertical stems, dark grid floor. No text/cards/popups in the scene.
 */

import * as THREE from './lib/three.module.min.js';

const SCENE_BG = 0x060810;
const GRID_SIZE = 2000;
const GRID_DIVISIONS = 80;
const MIN_CAM_RADIUS = 20;
const MAX_CAM_RADIUS = 2500;
const ATOM_RADIUS = 2.4;
const STEM_RADIUS = 0.35;
const DEFAULT_ATOM_RGB = [138, 160, 190];

let _decodeLocation = null;
let _categoryColor = null;

let _container = null;
let _renderer = null;
let _scene = null;
let _camera = null;
let _grid = null;
let _atomRoot = null;
let _raycaster = null;
let _pointer = new THREE.Vector2();

let _initialized = false;
let _animating = false;
let _rafId = 0;

let _origin = { lat: 0, lon: 0 };
let _cachedOriginKeys = '';
let _lastAtoms = [];
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

function _keysSignature(keys) {
  return [...keys].sort().join('|');
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

function _updateCameraPosition() {
  if (!_camera) return;
  const sinPhi = Math.sin(_camPhi);
  _camera.position.set(
    _camTarget.x + _camRadius * sinPhi * Math.sin(_camTheta),
    _camTarget.y + _camRadius * Math.cos(_camPhi),
    _camTarget.z + _camRadius * sinPhi * Math.cos(_camTheta),
  );
  _camera.lookAt(_camTarget);
}

function _makeAtomMaterial(selected = false, rgb = DEFAULT_ATOM_RGB) {
  const color = _rgbToThreeColor(rgb);
  return new THREE.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: selected ? 1.4 : 0.85,
    metalness: 0.15,
    roughness: 0.35,
  });
}

function _makeStemMaterial(selected = false, rgb = DEFAULT_ATOM_RGB) {
  const base = _rgbToThreeColor(rgb);
  if (selected) {
    return new THREE.MeshBasicMaterial({
      color: base,
      transparent: true,
      opacity: 0.95,
    });
  }
  return new THREE.MeshBasicMaterial({
    color: 0x2a4a66,
    transparent: true,
    opacity: 0.55,
  });
}

function _positionAtomEntry(entry, atom) {
  const loc = _resolveLocation(atom);
  if (!loc || !entry) return;
  const pos = _toLocalMeters(loc.lat, loc.lon, loc.alt);
  entry.group.position.set(pos.x, 0, pos.z);
  entry.sphere.position.y = pos.y;
  entry.localY = pos.y;
  entry.stem.scale.y = Math.max(pos.y, 0.01) / Math.max(entry.stem.geometry.parameters.height, 0.01);
  entry.stem.position.y = pos.y / 2;
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

  const sphere = new THREE.Mesh(
    new THREE.SphereGeometry(ATOM_RADIUS, 20, 20),
    _makeAtomMaterial(false, rgb),
  );
  sphere.position.y = pos.y;
  sphere.userData = { atomKey: key, pickTarget: true };

  const stemHeight = Math.max(pos.y, 0.01);
  const stem = new THREE.Mesh(
    new THREE.CylinderGeometry(STEM_RADIUS, STEM_RADIUS, stemHeight, 8),
    _makeStemMaterial(false, rgb),
  );
  stem.position.y = stemHeight / 2;

  group.add(stem);
  group.add(sphere);

  return { group, sphere, stem, localY: pos.y, atom };
}

function _applySelectionVisual(key) {
  for (const [id, entry] of _groupsById) {
    const selected = id === key;
    const rgb = _getAtomRgb(entry.atom);
    entry.sphere.material = _makeAtomMaterial(selected, rgb);
    entry.sphere.scale.setScalar(selected ? 1.45 : 1);
    entry.stem.material = _makeStemMaterial(selected, rgb);
  }
}

function _fitCameraToAtoms() {
  if (!_groupsById.size) {
    _camTarget.set(0, 40, 0);
    _camRadius = 320;
    _updateCameraPosition();
    return;
  }

  const box = new THREE.Box3();
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
  _scene.fog = new THREE.FogExp2(SCENE_BG, 0.00045);

  _camera = new THREE.PerspectiveCamera(55, 1, 0.5, 12000);
  _updateCameraPosition();

  _renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  _renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  _renderer.setClearColor(SCENE_BG, 1);
  el.appendChild(_renderer.domElement);

  _grid = new THREE.GridHelper(GRID_SIZE, GRID_DIVISIONS, 0x1a3355, 0x0f1a28);
  _grid.material.opacity = 0.55;
  _grid.material.transparent = true;
  _grid.position.y = 0;
  _scene.add(_grid);

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(GRID_SIZE, GRID_SIZE),
    new THREE.MeshBasicMaterial({ color: 0x04060c, transparent: true, opacity: 0.92 }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.05;
  _scene.add(floor);

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
    window.addEventListener('resize', _resize);
  }

  _initialized = true;
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

function _clearAtoms() {
  if (!_atomRoot) return;
  for (const entry of _groupsById.values()) {
    _atomRoot.remove(entry.group);
    entry.sphere.geometry.dispose();
    entry.stem.geometry.dispose();
    entry.sphere.material.dispose();
    entry.stem.material.dispose();
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

  const keySig = _keysSignature(nextKeys);
  const originChanged = keySig !== _cachedOriginKeys;
  if (originChanged) {
    _origin = _computeOrigin(list);
    _cachedOriginKeys = keySig;
  }

  for (const atom of list) {
    const key = _atomKey(atom);
    if (!key || !nextKeys.has(key)) continue;

    const existing = _groupsById.get(key);
    if (existing) {
      _positionAtomEntry(existing, atom);
      _atomsById.set(key, atom);
      if (originChanged) continue;
      const rgb = _getAtomRgb(atom);
      existing.sphere.material = _makeAtomMaterial(_selectedId === key, rgb);
      existing.stem.material = _makeStemMaterial(_selectedId === key, rgb);
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
    entry.sphere.geometry.dispose();
    entry.stem.geometry.dispose();
    entry.sphere.material.dispose();
    entry.stem.material.dispose();
    _groupsById.delete(key);
    _atomsById.delete(key);
    if (_selectedId === key) _selectedId = null;
  }

  if (_selectedId && _groupsById.has(_selectedId)) _applySelectionVisual(_selectedId);
}

/**
 * @param {Object} opts
 * @param {(punkto:string)=>object|null} opts.decodeLocation
 * @param {(atom:object)=>number[]|null} opts.categoryColor
 */
export function initCloudView({ decodeLocation, categoryColor } = {}) {
  _decodeLocation = typeof decodeLocation === 'function' ? decodeLocation : null;
  _categoryColor = typeof categoryColor === 'function' ? categoryColor : null;
}

/**
 * Show the cloud view: lazy-init scene, resize, start render loop.
 */
export function showCloudView() {
  if (!_initialized) _buildScene();
  _resize();
  _startAnimation();
}

/**
 * Hide cloud view and pause rendering (optional power save).
 */
export function hideCloudView() {
  _stopAnimation();
}

/**
 * Replace atoms in the scene from the current feed/cache list.
 * @param {Array<object>} atoms
 * @param {{ fit?: boolean }} opts
 */
export function updateCloudAtoms(atoms, { fit = false } = {}) {
  if (!_initialized) _buildScene();
  if (!_initialized) return;
  const prevCount = _groupsById.size;
  _syncAtomMeshes(atoms);
  if (fit || prevCount === 0) _fitCameraToAtoms();
  if (_animating) _animate();
}

/**
 * Focus camera on a specific atom by punkto id (without 'p:' prefix).
 * @param {string} punktoId
 */
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
