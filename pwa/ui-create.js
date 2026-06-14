import { FLOOR_HEIGHT_M } from './core/location.js';

const elModalOverlay = document.getElementById('modal-overlay');
const elModalText = document.getElementById('modal-text');
const elModalAuthor = document.getElementById('modal-author');
const elModalSubmit = document.getElementById('modal-submit');
const elModalCancel = document.getElementById('modal-cancel');
const elModalError = document.getElementById('modal-error');
const elAckBanner = document.getElementById('ack-banner');
const elAckBtn = document.getElementById('ack-btn');

const ACK_KEY = 'punkto-public-ack';

if (elAckBtn) {
  elAckBtn.addEventListener('click', () => {
    localStorage.setItem(ACK_KEY, '1');
    if (elAckBanner) elAckBanner.style.display = 'none';
    if (elModalSubmit) elModalSubmit.disabled = false;
    setTimeout(() => elModalText?.focus(), 40);
  });
}
const elModalAltitudeSlider = document.getElementById('modal-altitude-slider');
const elModalAltitudePrimary = document.getElementById('modal-altitude-primary');
const elModalAltitudeSecondary = document.getElementById('modal-altitude-secondary');
const elModalAltitudeHint = document.getElementById('modal-altitude-hint');
const elModalGroundBtn = document.getElementById('modal-ground-btn');
const elModalRoofBtn = document.getElementById('modal-roof-btn');
const elModalDeviceAltBtn = document.getElementById('modal-device-alt-btn');
const elModalFloorMinus = document.getElementById('modal-floor-minus');
const elModalFloorPlus = document.getElementById('modal-floor-plus');
const elModalFloorValue = document.getElementById('modal-floor-value');
const elModalManualAltitude = document.getElementById('modal-manual-altitude-value');
const elModalCategory = document.getElementById('modal-category');
const elModalEmergencyHint = document.getElementById('modal-emergency-hint');

let callbacks = null;
let modalAltitudeState = { mode: 'meter', building: null };
let draft = null;

function altitudeMeters() {
  const raw = Number(elModalAltitudeSlider?.value);
  if (!Number.isFinite(raw) || raw < 0) return 0;
  return modalAltitudeState.mode === 'floor' ? raw * FLOOR_HEIGHT_M : raw;
}

function emitPreview() {
  if (!draft) return;
  draft.altitude_m = altitudeMeters();
  draft.category = elModalCategory?.value || 'TEXT';
  draft.floor_hint = modalAltitudeState.mode === 'floor'
    ? Math.round(Number(elModalAltitudeSlider.value) || 0)
    : Math.round(draft.altitude_m / FLOOR_HEIGHT_M);
  callbacks?.onPreviewChanged?.({ ...draft });
}

function updateAltitudeLabels() {
  const val = Number(elModalAltitudeSlider?.value) || 0;
  if (modalAltitudeState.mode === 'floor') {
    const floor = Math.round(val);
    const meters = floor * FLOOR_HEIGHT_M;
    elModalAltitudePrimary.innerHTML = floor === 0 ? 'Ground <span class="alt-cyan">(Floor 0)</span>' : `Floor <span class="alt-cyan">${floor}</span>`;
    elModalAltitudeSecondary.textContent = `+${meters} m above ground`;
    const b = modalAltitudeState.building;
    const name = (b && b.name) ? b.name : 'Building';
    const maxFloor = (b && b.maxFloor) ? b.maxFloor : 1;
    elModalAltitudeHint.textContent = `Detected: ${name} · ${maxFloor} floor${maxFloor === 1 ? '' : 's'}`;
  } else {
    const meters = Math.round(val);
    const est = Math.round(meters / FLOOR_HEIGHT_M);
    elModalAltitudePrimary.innerHTML = meters === 0 ? 'Ground level' : `<span class="alt-cyan">+${meters} m</span> above ground`;
    elModalAltitudeSecondary.textContent = meters === 0 ? '~Floor 0' : `~Floor ${est}`;
    elModalAltitudeHint.textContent = meters === 0 ? '' : '(estimated, no building detected)';
  }
  emitPreview();
}

function setAltitudeMeters(meters, mode = 'manual') {
  const v = Math.max(0, Math.round(Number(meters) || 0));
  if (modalAltitudeState.mode === 'floor') {
    const floor = Math.round(v / FLOOR_HEIGHT_M);
    elModalAltitudeSlider.value = String(floor);
    if (elModalFloorValue) elModalFloorValue.value = String(floor);
  } else {
    elModalAltitudeSlider.value = String(v);
  }
  if (elModalManualAltitude) elModalManualAltitude.value = String(v);
  if (draft) draft.placement_mode = mode;
  updateAltitudeLabels();
}

function requestDeviceAltitude() {
  if (!navigator.geolocation || !elModalDeviceAltBtn) return;
  navigator.geolocation.getCurrentPosition((pos) => {
    const alt = pos?.coords?.altitude;
    if (alt == null || !Number.isFinite(alt)) {
      elModalDeviceAltBtn.style.display = 'none';
      return;
    }
    elModalDeviceAltBtn.style.display = '';
    elModalDeviceAltBtn.disabled = false;
    elModalDeviceAltBtn.dataset.altitude = String(Math.round(alt));
  }, () => {
    elModalDeviceAltBtn.style.display = 'none';
  }, { enableHighAccuracy: true, timeout: 5000 });
}

export function initCreateModal(opts) {
  callbacks = opts;
  elModalCancel?.addEventListener('click', closeCreateModal);
  elModalOverlay?.addEventListener('click', (e) => { if (e.target === elModalOverlay) closeCreateModal(); });
  elModalSubmit?.addEventListener('click', () => callbacks?.onSubmitCreate?.(readCreateFormState()));
  elModalText?.addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) callbacks?.onSubmitCreate?.(readCreateFormState()); });
  elModalAltitudeSlider?.addEventListener('input', updateAltitudeLabels);
  elModalAltitudeSlider?.addEventListener('change', updateAltitudeLabels);
  elModalGroundBtn?.addEventListener('click', () => setAltitudeMeters(0, 'ground'));
  elModalRoofBtn?.addEventListener('click', () => { const b = modalAltitudeState.building; if (b) setAltitudeMeters(b.height, 'roof'); });
  elModalFloorMinus?.addEventListener('click', () => setAltitudeMeters(((Number(elModalFloorValue?.value) || 0) - 1) * FLOOR_HEIGHT_M, 'manual'));
  elModalFloorPlus?.addEventListener('click', () => setAltitudeMeters(((Number(elModalFloorValue?.value) || 0) + 1) * FLOOR_HEIGHT_M, 'manual'));
  elModalFloorValue?.addEventListener('input', () => setAltitudeMeters((Math.max(0, Number(elModalFloorValue.value) || 0)) * FLOOR_HEIGHT_M, 'manual'));
  elModalManualAltitude?.addEventListener('input', () => setAltitudeMeters(Number(elModalManualAltitude.value) || 0, 'manual'));
  elModalDeviceAltBtn?.addEventListener('click', () => {
    const alt = Number(elModalDeviceAltBtn.dataset.altitude);
    if (Number.isFinite(alt)) setAltitudeMeters(alt, 'device');
  });
  elModalCategory?.addEventListener('change', () => {
    const isEmergency = elModalCategory.value === 'EMGC';
    if (elModalEmergencyHint) elModalEmergencyHint.style.display = isEmergency ? '' : 'none';
    emitPreview();
  });
}

export function openCreateModal() {
  const context = callbacks?.getInitialContext?.() || {};
  elModalError.textContent = '';
  elModalText.value = '';
  elModalAuthor.value = localStorage.getItem('punkto-name') || localStorage.getItem('punkto-author') || '';
  const building = context.building || null;
  modalAltitudeState = building ? { mode: 'floor', building } : { mode: 'meter', building: null };
  elModalAltitudeSlider.min = '0';
  elModalAltitudeSlider.max = building ? String(building.maxFloor) : '100';
  elModalAltitudeSlider.step = '1';
  elModalAltitudeSlider.value = '0';
  if (elModalRoofBtn) elModalRoofBtn.disabled = !building;
  if (elModalDeviceAltBtn) elModalDeviceAltBtn.disabled = true;
  if (elModalCategory) elModalCategory.value = 'TEXT';
  if (elModalEmergencyHint) elModalEmergencyHint.style.display = 'none';
  draft = { lat: context.center?.lat ?? 0, lon: context.center?.lng ?? 0, altitude_m: 0, floor_hint: 0, placement_mode: 'ground' };
  updateAltitudeLabels();
  requestDeviceAltitude();
  elModalOverlay.classList.add('open');
  // First-use public-data acknowledgement
  const acked = !!localStorage.getItem(ACK_KEY);
  if (elAckBanner) elAckBanner.style.display = acked ? 'none' : 'block';
  if (elModalSubmit) elModalSubmit.disabled = !acked;
  setTimeout(() => {
    if (!acked && elAckBtn) elAckBtn.focus();
    else elModalText?.focus();
  }, 80);
}

export function closeCreateModal() {
  elModalOverlay?.classList.remove('open');
  draft = null;
  callbacks?.onClosed?.();
}

export function readCreateFormState() {
  const author = elModalAuthor.value.trim();
  if (author) {
    localStorage.setItem('punkto-name', author);
    localStorage.setItem('punkto-author', author);
  }
  return { text: elModalText.value.trim(), author, category: elModalCategory?.value || 'TEXT', draft: draft ? { ...draft } : null };
}

export function setCreateError(message) { elModalError.textContent = message || ''; }
export function setCreateSubmitting(isSubmitting) { if (elModalSubmit) elModalSubmit.disabled = !!isSubmitting; }
export function updateCreateCenter(lat, lon) { if (!draft) return; draft.lat = lat; draft.lon = lon; emitPreview(); }
export function isCreateModalOpen() { return !!elModalOverlay?.classList.contains('open'); }
