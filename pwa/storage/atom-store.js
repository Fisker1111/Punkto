import { db } from './db.js';
import { decodeAtomLocation } from '../core/location.js';
import { normalizeAtomPayload } from '../protocol/atom-normalize.js';
import { canonicalAtomId } from '../protocol/exact-link.js';
import { decode_xy, parse_h } from '../punkti/spatial.js';

function extractLayer4(rawX) {
  const source = typeof rawX === 'string' ? rawX : (rawX == null ? '' : String(rawX));
  let parsed = null;
  try {
    const candidate = JSON.parse(source);
    if (candidate && typeof candidate === 'object' && !Array.isArray(candidate)) {
      parsed = candidate;
    }
  } catch {}
  const text = parsed && typeof parsed.text === 'string' ? parsed.text : source;
  return {
    text,
    payload: source,
    meta: parsed && parsed.meta && typeof parsed.meta === 'object' ? parsed.meta : null,
  };
}

function spatialFromH(h) {
  if (typeof h !== 'string' || !h) return null;
  try {
    const parsed = parse_h(h);
    if (!parsed) return null;
    const xy = decode_xy(parsed.xy);
    const alt = Number(parsed.z);
    return {
      lat: xy.lat,
      lon: xy.lon,
      alt: Number.isFinite(alt) ? alt : null,
      xy: parsed.xy,
      z: parsed.z,
    };
  } catch {
    return null;
  }
}

export async function upsertAtom(atom) {
  const normalized = normalizeAtomPayload(atom);
  const layer4 = extractLayer4(normalized.x_payload ?? normalized.x);
  normalized.x = layer4.text;
  normalized.x_payload = layer4.payload;
  if (layer4.meta && !normalized.f && typeof layer4.meta.author === 'string') {
    normalized.f = layer4.meta.author;
  }
  if (layer4.meta && !normalized.category && typeof layer4.meta.category === 'string') {
    normalized.category = layer4.meta.category;
  }
  if (normalized.mid && !normalized.atom_id) {
    normalized.atom_id = normalized.mid;
  }
  let atomId = String(normalized.atom_id || '').trim();
  if (!atomId) {
    try {
      atomId = await canonicalAtomId(normalized);
      normalized.atom_id = atomId;
    } catch (err) {
      console.warn('[atom-store] atom_id unavailable:', err?.message || err);
    }
  }
  const hLoc = spatialFromH(normalized.h);
  const loc = hLoc || decodeAtomLocation(normalized.punkto);
  const explicitLocationFields = ['lat', 'lon', 'altitude_m', 'alt', 'z', 'floor', 'level']
    .filter((field) => normalized[field] != null);
  const record = {
    ...normalized,
    punkto: normalized.punkto,
    t: normalized.t,
    x: normalized.x || '',
    x_payload: normalized.x_payload || normalized.x || '',
    f: normalized.f || '',
    lat: normalized.lat ?? (loc ? loc.lat : 0),
    lon: normalized.lon ?? (loc ? loc.lon : 0),
    alt: normalized.alt ?? normalized.altitude_m ?? (loc ? loc.alt : 0),
    location_fields: explicitLocationFields,
    h: normalized.h,
    mid: normalized.mid ?? '',
    sha256: normalized.sha256 ?? '',
    verification_state: normalized.verification_state ?? '',
    publication_base_url: normalized.publication_base_url ?? '',
    publication_seq: normalized.publication_seq ?? null,
    publication_head: normalized.publication_head ?? '',
    ellipsoidal_z: normalized.ellipsoidal_z ?? (hLoc ? hLoc.z : null),
  };

  if (atomId) record.atom_id = atomId;

  const existingByAtomId = atomId
    ? await db.atoms.where('atom_id').equals(atomId).first()
    : null;
  if (existingByAtomId) {
    await db.atoms.update(existingByAtomId.id, record);
    return { inserted: false, id: existingByAtomId.id };
  }

  const existing = await db.atoms
    .where('punkto').equals(normalized.punkto)
    .and(a => a.t === normalized.t && String(a.atom_id || '') === String(record.atom_id || ''))
    .first();

  if (!existing) {
    const newId = await db.atoms.add(record);
    return { inserted: true, id: newId };
  }

  await db.atoms.update(existing.id, record);
  return { inserted: false, id: existing.id };
}

export async function getAllAtomsNewestFirst() {
  return db.atoms.orderBy('t').reverse().toArray();
}

export async function getAllAtoms() {
  return db.atoms.toArray();
}
