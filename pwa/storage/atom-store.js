import { db } from './db.js';
import { decodeAtomLocation } from '../core/location.js';
import { normalizeAtomPayload } from '../protocol/atom-normalize.js';
import { computeAtomId } from '../protocol/atom-id.js';

export async function upsertAtom(atom) {
  const normalized = normalizeAtomPayload(atom);
  const loc = decodeAtomLocation(normalized.punkto);
  const explicitLocationFields = ['lat', 'lon', 'altitude_m', 'alt', 'z', 'floor', 'level']
    .filter((field) => normalized[field] != null);
  const record = {
    ...normalized,
    punkto: normalized.punkto,
    t: normalized.t,
    x: normalized.x || '',
    f: normalized.f || '',
    lat: normalized.lat ?? (loc ? loc.lat : 0),
    lon: normalized.lon ?? (loc ? loc.lon : 0),
    alt: normalized.alt ?? normalized.altitude_m ?? (loc ? loc.alt : 0),
    location_fields: explicitLocationFields,
  };

  if (!record.atom_id) {
    try {
      record.atom_id = await computeAtomId(normalized);
    } catch (err) {
      console.warn('[atom-store] atom_id unavailable:', err?.message || err);
    }
  }

  const existing = await db.atoms
    .where('punkto').equals(normalized.punkto)
    .and(a => a.t === normalized.t)
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
