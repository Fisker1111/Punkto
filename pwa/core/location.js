/**
 * Pure location helpers shared by app/core UI logic.
 * No DOM, network, or storage dependencies.
 */

import { encode, decode } from '../geohash3d.js';

export const FLOOR_HEIGHT_M = 3;

export function decodeAtomLocation(punktoStr) {
  try {
    const spatial = String(punktoStr || '').replace(/^p:/, '').split('-')[0];
    if (spatial.length < 1) return null;
    return decode(spatial);
  } catch {
    return null;
  }
}

export function encodeLocation(lat, lon, altMeters = 0) {
  const alt = Number.isFinite(altMeters) ? altMeters : 0;
  const hash = encode(lat, lon, alt, 12);
  return `p:${hash}`;
}

export function encodeCurrentLocation(mapInst, altMeters = 0) {
  const center = mapInst.getCenter();
  return encodeLocation(center.lat, center.lng, altMeters);
}

export function haversineMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = d => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}
