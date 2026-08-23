import { FLOOR_HEIGHT_M } from './core/location.js';

const elModalOverlay = document.getElementById('modal-overlay');
const elModalText = document.getElementById('modal-text');
const elModalAuthor = document.getElementById('modal-author');
const elModalSubmit = document.getElementById('modal-submit');
const elModalCancel = document.getElementById('modal-cancel');
const elModalError = document.getElementById('modal-error');
const elModalBox = document.getElementById('modal');
const elAckBanner = document.getElementById('ack-banner');
const elAckBtn = document.getElementById('ack-btn');
const elModalOptions = document.getElementById('modal-options');
const elModalOptionsLabel = document.querySelector('#modal-options .modal-adjust-label');
const elModalOptionsHint = document.querySelector('#modal-options .modal-adjust-hint');

const ACK_KEY = 'punkto-public-ack';
const MAX_DRAFT_HEIGHT_M = 200;

if (elAckBtn) {
  elAckBtn.addEventListener('click', () => {
    localStorage.setItem(ACK_KEY, '1');
    if (elAckBanner) elAckBanner.style.display = 'none';
    updateSubmitState();
    notifyViewportChangedSoon();
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
let isSubmitting = false;
let viewportNotifyRaf = null;
let modalResizeObserver = null;

function isAcked() {
  return !!localStorage.getItem(ACK_KEY);
}

function hasPublishableText() {
  return !!elModalText?.value.trim();
}

function canPublish() {
  return isAcked() && hasPublishableText() && !isSubmitting;
}

function updateSubmitState() {
  if (!elModalSubmit) return;
  elModalSubmit.disabled = !canPublish();
}

function submitIfEligible() {
  updateSubmitState();
  if (!canPublish()) return;
  callbacks?.onSubmitCreate?.(readCreateFormState());
}

function readComposerRect() {
  if (!elModalBox || !isCreateModalOpen()) return null;
  const rect = elModalBox.getBoundingClientRect();
  return {
    top: rect.top,
    right: rect.right,
    bottom: rect.bottom,
    left: rect.left,
    width: rect.width,
    height: rect.height,
  };
}

function notifyViewportChangedSoon() {
  if (!isCreateModalOpen()) return;
  if (viewportNotifyRaf) cancelAnimationFrame(viewportNotifyRaf);
  viewportNotifyRaf = requestAnimationFrame(() => {
    viewportNotifyRaf = null;
    callbacks?.onViewportChanged?.(true, readComposerRect());
  });
}

function startViewportObservation() {
  stopViewportObservation();
  if (window.ResizeObserver && elModalBox) {
    modalResizeObserver = new ResizeObserver(() => notifyViewportChangedSoon());
    modalResizeObserver.observe(elModalBox);
  }
  window.addEventListener('resize', notifyViewportChangedSoon);
  window.addEventListener('orientationchange', notifyViewportChangedSoon);
}

function stopViewportObservation() {
  if (viewportNotifyRaf) {
    cancelAnimationFrame(viewportNotifyRaf);
    viewportNotifyRaf = null;
  }
  if (modalResizeObserver) {
    modalResizeObserver.disconnect();
    modalResizeObserver = null;
  }
  window.removeEventListener('resize', notifyViewportChangedSoon);
  window.removeEventListener('orientationchange', notifyViewportChangedSoon);
}

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
  const v = Math.min(MAX_DRAFT_HEIGHT_M, Math.max(0, Math.round(Number(meters) || 0)));
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
  elModalDeviceAltBtn.disabled = true;
  elModalDeviceAltBtn.textContent = 'Finding altitude...';
  navigator.geolocation.getCurrentPosition((pos) => {
    const alt = pos?.coords?.altitude;
    if (alt == null || !Number.isFinite(alt)) {
      elModalDeviceAltBtn.textContent = 'Altitude unavailable';
      return;
    }
    setAltitudeMeters(Math.round(alt), 'device');
    elModalDeviceAltBtn.textContent = 'Use my altitude';
    elModalDeviceAltBtn.disabled = false;
  }, () => {
    elModalDeviceAltBtn.textContent = 'Altitude unavailable';
  }, { enableHighAccuracy: true, timeout: 5000 });
}

export function initCreateModal(opts) {
  callbacks = opts;
  if (elModalOptionsLabel) elModalOptionsLabel.textContent = 'Location & options';
  if (elModalOptionsHint) elModalOptionsHint.textContent = 'ground by default';
  elModalCancel?.addEventListener('click', closeCreateModal);
  elModalOverlay?.addEventListener('click', (e) => { if (e.target === elModalOverlay) closeCreateModal(); });
  elModalSubmit?.addEventListener('click', submitIfEligible);
  elModalText?.addEventListener('input', updateSubmitState);
  elModalText?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      submitIfEligible();
    }
  });
  elModalAltitudeSlider?.addEventListener('input', updateAltitudeLabels);
  elModalAltitudeSlider?.addEventListener('change', updateAltitudeLabels);
  elModalOptions?.addEventListener('toggle', notifyViewportChangedSoon);
  elModalGroundBtn?.addEventListener('click', () => setAltitudeMeters(0, 'ground'));
  elModalRoofBtn?.addEventListener('click', () => { const b = modalAltitudeState.building; if (b) setAltitudeMeters(b.height, 'roof'); });
  elModalFloorMinus?.addEventListener('click', () => setAltitudeMeters(((Number(elModalFloorValue?.value) || 0) - 1) * FLOOR_HEIGHT_M, 'manual'));
  elModalFloorPlus?.addEventListener('click', () => setAltitudeMeters(((Number(elModalFloorValue?.value) || 0) + 1) * FLOOR_HEIGHT_M, 'manual'));
  elModalFloorValue?.addEventListener('input', () => setAltitudeMeters((Math.max(0, Number(elModalFloorValue.value) || 0)) * FLOOR_HEIGHT_M, 'manual'));
  elModalManualAltitude?.addEventListener('input', () => setAltitudeMeters(Number(elModalManualAltitude.value) || 0, 'manual'));
  elModalDeviceAltBtn?.addEventListener('click', requestDeviceAltitude);
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
  if (elModalOptions) elModalOptions.open = false;
  const building = context.building || null;
  modalAltitudeState = building ? { mode: 'floor', building } : { mode: 'meter', building: null };
  elModalAltitudeSlider.min = '0';
  elModalAltitudeSlider.max = building ? String(Math.min(building.maxFloor, Math.floor(MAX_DRAFT_HEIGHT_M / FLOOR_HEIGHT_M))) : String(MAX_DRAFT_HEIGHT_M);
  elModalAltitudeSlider.step = '1';
  elModalAltitudeSlider.value = '0';
  if (elModalRoofBtn) elModalRoofBtn.disabled = !building;
  if (elModalDeviceAltBtn) {
    elModalDeviceAltBtn.disabled = !navigator.geolocation;
    elModalDeviceAltBtn.textContent = navigator.geolocation ? 'Use my altitude' : 'Altitude unavailable';
  }
  if (elModalCategory) elModalCategory.value = 'TEXT';
  if (elModalEmergencyHint) elModalEmergencyHint.style.display = 'none';
  draft = { lat: context.center?.lat ?? 0, lon: context.center?.lng ?? 0, altitude_m: 0, floor_hint: 0, placement_mode: 'ground' };
  updateAltitudeLabels();
  elModalOverlay.classList.add('open');
  startViewportObservation();
  // First-use public-data acknowledgement
  const acked = isAcked();
  if (elAckBanner) elAckBanner.style.display = acked ? 'none' : 'block';
  notifyViewportChangedSoon();
  setTimeout(notifyViewportChangedSoon, 260);
  updateSubmitState();
  setTimeout(() => {
    if (!acked && elAckBtn) elAckBtn.focus();
    else elModalText?.focus();
  }, 80);
}

export function closeCreateModal() {
  stopViewportObservation();
  callbacks?.onViewportChanged?.(false, null);
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
export function setCreateSubmitting(submitting) { isSubmitting = !!submitting; updateSubmitState(); }
export function updateCreateCenter(lat, lon) { if (!draft) return; draft.lat = lat; draft.lon = lon; emitPreview(); }
export function updateCreateAltitude(meters, mode = 'spatial-drag') { if (!draft) return; setAltitudeMeters(meters, mode); }
export function isCreateModalOpen() { return !!elModalOverlay?.classList.contains('open'); }
