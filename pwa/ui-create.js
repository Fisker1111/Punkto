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
const elModalPlacementSummary = document.getElementById('modal-placement-summary');
const elHeightStage = document.getElementById('height-placement');
const elHeightReadout = document.getElementById('height-placement-readout');
const elHeightLever = document.getElementById('height-lever');
const elHeightHandle = document.getElementById('height-lever-handle');
const elHeightMeter = document.getElementById('height-lever-meter');
const elHeightDone = document.getElementById('height-placement-done');
const elHeightCancel = document.getElementById('height-placement-cancel');
const elHeightGround = document.getElementById('height-placement-ground');

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
let createStage = 'closed';
let leverDrag = null;
let leverRaf = null;
let leverPositionRaf = null;
let placementScreenPoint = null;

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

function formatHeightLabel(meters) {
  const height = Math.round(Math.max(0, Number(meters) || 0));
  if (height < 1) return 'Ground';
  const floor = Math.max(1, Math.round(height / FLOOR_HEIGHT_M));
  return `+${height} m · ~Floor ${floor}`;
}

function setCreateStage(stage) {
  createStage = stage;
  const isHeight = stage === 'height';
  const isWrite = stage === 'write';
  elModalOverlay?.classList.toggle('open', isHeight || isWrite);
  elModalOverlay?.classList.toggle('height-placement-open', isHeight);
  elModalOverlay?.classList.toggle('write-stage-open', isWrite);
  document.body?.classList.toggle('create-height-placement-open', isHeight);
  if (elModalBox) elModalBox.hidden = !isWrite;
  if (elHeightStage) {
    elHeightStage.hidden = !isHeight;
    elHeightStage.setAttribute('aria-hidden', isHeight ? 'false' : 'true');
  }
  if (isHeight) positionHeightLeverSoon();
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
  updatePlacementReadouts();
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
    const b = modalAltitudeState.building;
    if (b && b.name) elModalAltitudeHint.textContent = `Detected: ${b.name} · approximate floors`;
    else if (b) elModalAltitudeHint.textContent = 'Detected building · approximate floors';
    else elModalAltitudeHint.textContent = meters === 0 ? '' : '(estimated, no building detected)';
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

function updatePlacementReadouts() {
  if (!draft) return;
  const label = formatHeightLabel(draft.altitude_m || 0);
  if (elHeightReadout) elHeightReadout.textContent = label;
  if (elModalPlacementSummary) elModalPlacementSummary.textContent = label;
  updateLeverVisual(draft.altitude_m || 0);
  positionHeightLeverSoon();
}

function updateLeverVisual(meters) {
  if (!elHeightHandle || !elHeightMeter) return;
  const height = Math.min(MAX_DRAFT_HEIGHT_M, Math.max(0, Number(meters) || 0));
  const pct = heightToLeverPct(height);
  elHeightHandle.style.bottom = `${pct}%`;
  elHeightMeter.style.height = `${pct}%`;
  elHeightHandle.setAttribute('aria-valuenow', String(Math.round(height)));
  elHeightHandle.setAttribute('aria-valuetext', formatHeightLabel(height));
}

function heightToLeverPct(height) {
  const h = Math.min(MAX_DRAFT_HEIGHT_M, Math.max(0, Number(height) || 0));
  if (h <= 30) return (h / 30) * 58;
  return 58 + ((h - 30) / (MAX_DRAFT_HEIGHT_M - 30)) * 42;
}

function leverPctToHeight(pct) {
  const p = Math.min(100, Math.max(0, Number(pct) || 0));
  if (p <= 58) return (p / 58) * 30;
  return 30 + ((p - 58) / 42) * (MAX_DRAFT_HEIGHT_M - 30);
}

function heightFromLeverEvent(ev) {
  const rect = elHeightLever?.getBoundingClientRect?.();
  if (!rect || rect.height <= 0) return draft?.altitude_m || 0;
  const y = Math.min(rect.bottom, Math.max(rect.top, ev.clientY));
  const pct = ((rect.bottom - y) / rect.height) * 100;
  return Math.round(leverPctToHeight(pct));
}

function beginLeverDrag(ev) {
  if (!draft || createStage !== 'height') return;
  ev.preventDefault();
  ev.stopPropagation();
  if (typeof ev.stopImmediatePropagation === 'function') ev.stopImmediatePropagation();
  leverDrag = { pointerId: ev.pointerId };
  elHeightLever?.setPointerCapture?.(ev.pointerId);
  updateLeverFromEvent(ev);
  window.addEventListener('pointermove', onLeverPointerMove, { capture: true });
  window.addEventListener('pointerup', endLeverDrag, { capture: true });
  window.addEventListener('pointercancel', endLeverDrag, { capture: true });
}

function updateLeverFromEvent(ev) {
  if (!draft) return;
  const nextHeight = heightFromLeverEvent(ev);
  if (leverRaf) cancelAnimationFrame(leverRaf);
  leverRaf = requestAnimationFrame(() => {
    leverRaf = null;
    setAltitudeMeters(nextHeight, nextHeight === 0 ? 'ground' : 'height-lever');
  });
}

function onLeverPointerMove(ev) {
  if (!leverDrag || ev.pointerId !== leverDrag.pointerId) return;
  ev.preventDefault();
  ev.stopPropagation();
  updateLeverFromEvent(ev);
}

function endLeverDrag(ev) {
  if (!leverDrag || ev.pointerId !== leverDrag.pointerId) return;
  ev.preventDefault();
  ev.stopPropagation();
  try { elHeightLever?.releasePointerCapture?.(leverDrag.pointerId); } catch {}
  leverDrag = null;
  window.removeEventListener('pointermove', onLeverPointerMove, { capture: true });
  window.removeEventListener('pointerup', endLeverDrag, { capture: true });
  window.removeEventListener('pointercancel', endLeverDrag, { capture: true });
}

function positionHeightLeverSoon() {
  if (createStage !== 'height' || !elHeightLever) return;
  if (leverPositionRaf) cancelAnimationFrame(leverPositionRaf);
  leverPositionRaf = requestAnimationFrame(() => {
    leverPositionRaf = null;
    positionHeightLever();
  });
}

function positionHeightLever() {
  if (createStage !== 'height' || !elHeightLever) return;
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
  if (!viewportWidth || !viewportHeight) return;

  const rect = elHeightLever.getBoundingClientRect();
  const leverWidth = rect.width || 104;
  const leverHeight = rect.height || 300;
  const margin = 18;
  const localGap = Math.min(140, Math.max(80, Math.round(viewportWidth * 0.12)));
  const fallbackGap = Math.min(localGap, 58);
  const anchorX = Number.isFinite(placementScreenPoint?.x) ? placementScreenPoint.x : viewportWidth / 2;
  const anchorY = Number.isFinite(placementScreenPoint?.y) ? placementScreenPoint.y : viewportHeight / 2;
  const relation = placementRelationBounds();

  const readoutRect = elHeightReadout?.closest('.height-placement-readout')?.getBoundingClientRect?.();
  const actionsRect = document.querySelector('.height-placement-actions')?.getBoundingClientRect?.();
  const topLimit = Math.max(margin, Math.ceil((readoutRect?.bottom || 0) + 18));
  const bottomLimit = Math.min(
    viewportHeight - margin,
    Math.floor((actionsRect?.top || viewportHeight) - 18)
  );
  const minTop = topLimit;
  const maxTop = Math.max(minTop, bottomLimit - leverHeight);
  const top = clamp(anchorY - (leverHeight / 2), minTop, maxTop);

  const minLeft = margin;
  const maxLeft = Math.max(minLeft, viewportWidth - margin - leverWidth);
  const rightLeft = anchorX + localGap;
  const leftLeft = anchorX - localGap - leverWidth;
  const rightFits = rightLeft <= maxLeft && !leverOverlapsRelation(rightLeft, top, leverWidth, leverHeight, relation);
  const leftFits = leftLeft >= minLeft && !leverOverlapsRelation(leftLeft, top, leverWidth, leverHeight, relation);
  const narrowPortrait = viewportWidth < 460 && viewportHeight > viewportWidth;
  const rightSpace = viewportWidth - anchorX - margin;
  const leftSpace = anchorX - margin;
  let side = 'right';

  if (narrowPortrait) {
    side = rightSpace >= leftSpace ? 'right' : 'left';
  }
  if (side === 'right' && !rightFits && leftFits) side = 'left';
  if (side === 'left' && !leftFits && rightFits) side = 'right';

  let left;
  if (side === 'right' && rightFits) {
    left = rightLeft;
  } else if (side === 'left' && leftFits) {
    left = leftLeft;
  } else {
    side = rightSpace >= leftSpace ? 'right' : 'left';
    const fallbackLeft = side === 'right'
      ? anchorX + fallbackGap
      : anchorX - fallbackGap - leverWidth;
    left = clamp(fallbackLeft, minLeft, maxLeft);
  }

  const connectorY = clamp(anchorY - top, 38, leverHeight - 38);
  const leverEdgeX = side === 'right' ? left : left + leverWidth;
  const connectorWidth = Math.min(66, Math.max(18, Math.abs(leverEdgeX - anchorX) - 17));
  elHeightLever.style.left = `${Math.round(left)}px`;
  elHeightLever.style.top = `${Math.round(top)}px`;
  elHeightLever.style.setProperty('--height-lever-guide-y', `${Math.round(connectorY)}px`);
  elHeightLever.style.setProperty('--height-lever-guide-w', `${Math.round(connectorWidth)}px`);
  elHeightLever.classList.toggle('height-lever--left', side === 'left');
  elHeightLever.classList.toggle('height-lever--right', side !== 'left');
}

function placementRelationBounds() {
  const ground = readScreenPoint('ground');
  const top = readScreenPoint('top');
  const points = [ground, top].filter(Boolean);
  if (!points.length) return null;
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  return {
    left: Math.min(...xs) - 28,
    right: Math.max(...xs) + 28,
    top: Math.min(...ys) - 28,
    bottom: Math.max(...ys) + 28,
  };
}

function readScreenPoint(kind) {
  const xKey = kind === 'top' ? 'topX' : 'groundX';
  const yKey = kind === 'top' ? 'topY' : 'groundY';
  const x = Number(placementScreenPoint?.[xKey]);
  const y = Number(placementScreenPoint?.[yKey]);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  return { x, y };
}

function leverOverlapsRelation(left, top, width, height, relation) {
  if (!relation) return false;
  return left < relation.right
    && left + width > relation.left
    && top < relation.bottom
    && top + height > relation.top;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, Number(value) || 0));
}

function onLeverKeyDown(ev) {
  if (!draft || createStage !== 'height') return;
  const current = Number(draft.altitude_m || 0);
  let next = current;
  if (ev.key === 'ArrowUp') next = current + (current < 30 ? 1 : 5);
  else if (ev.key === 'ArrowDown') next = current - (current <= 30 ? 1 : 5);
  else if (ev.key === 'PageUp') next = current + 10;
  else if (ev.key === 'PageDown') next = current - 10;
  else if (ev.key === 'Home') next = 0;
  else if (ev.key === 'End') next = MAX_DRAFT_HEIGHT_M;
  else return;
  ev.preventDefault();
  setAltitudeMeters(next, next <= 0 ? 'ground' : 'height-lever');
}

function onHeightStageKeyDown(ev) {
  if (createStage !== 'height') return;
  if (ev.key === 'Escape') {
    ev.preventDefault();
    closeCreateModal();
  }
  if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey)) {
    ev.preventDefault();
    openWriteStage();
  }
}

function openWriteStage() {
  if (!draft) return;
  callbacks?.onHeightPlacementChanged?.(false, { ...draft });
  setCreateStage('write');
  startViewportObservation();
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
  elHeightLever?.addEventListener('pointerdown', beginLeverDrag, { capture: true });
  elHeightHandle?.addEventListener('keydown', onLeverKeyDown);
  document.addEventListener('keydown', onHeightStageKeyDown);
  elHeightDone?.addEventListener('click', openWriteStage);
  elHeightCancel?.addEventListener('click', closeCreateModal);
  elHeightGround?.addEventListener('click', () => setAltitudeMeters(0, 'ground'));
}

export function openCreateModal() {
  const context = callbacks?.getInitialContext?.() || {};
  elModalError.textContent = '';
  elModalText.value = '';
  elModalAuthor.value = localStorage.getItem('punkto-name') || localStorage.getItem('punkto-author') || '';
  if (elModalOptions) elModalOptions.open = false;
  const building = context.building || null;
  modalAltitudeState = { mode: 'meter', building };
  elModalAltitudeSlider.min = '0';
  elModalAltitudeSlider.max = String(MAX_DRAFT_HEIGHT_M);
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
  setCreateStage('height');
  stopViewportObservation();
  callbacks?.onViewportChanged?.(false, null);
  callbacks?.onHeightPlacementChanged?.(true, { ...draft });
  positionHeightLeverSoon();
  updateSubmitState();
  setTimeout(() => elHeightDone?.focus(), 80);
}

export function closeCreateModal() {
  if (leverDrag) {
    const pointerId = leverDrag.pointerId;
    try { elHeightLever?.releasePointerCapture?.(pointerId); } catch {}
    leverDrag = null;
    window.removeEventListener('pointermove', onLeverPointerMove, { capture: true });
    window.removeEventListener('pointerup', endLeverDrag, { capture: true });
    window.removeEventListener('pointercancel', endLeverDrag, { capture: true });
  }
  if (leverRaf) {
    cancelAnimationFrame(leverRaf);
    leverRaf = null;
  }
  if (leverPositionRaf) {
    cancelAnimationFrame(leverPositionRaf);
    leverPositionRaf = null;
  }
  placementScreenPoint = null;
  if (elHeightLever) {
    elHeightLever.style.left = '';
    elHeightLever.style.top = '';
    elHeightLever.classList.remove('height-lever--left', 'height-lever--right');
  }
  stopViewportObservation();
  callbacks?.onViewportChanged?.(false, null);
  callbacks?.onHeightPlacementChanged?.(false, draft ? { ...draft } : null);
  setCreateStage('closed');
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
export function updateCreatePlacementScreenPoint(point) {
  placementScreenPoint = point && Number.isFinite(Number(point.x)) && Number.isFinite(Number(point.y))
    ? { ...point, x: Number(point.x), y: Number(point.y) }
    : null;
  positionHeightLeverSoon();
}
export function isCreateModalOpen() { return !!elModalOverlay?.classList.contains('open'); }
export function isCreateHeightPlacementOpen() { return createStage === 'height'; }
