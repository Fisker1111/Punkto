import { db } from './db.js';
import { decodeAtomLocation } from '../core/location.js';
import { normalizeAtomPayload } from '../protocol/atom-normalize.js';

export async function upsertAtom(atom) {
  const normalized = normalizeAtomPayload(atom);
  const loc = decodeAtomLocation(normalized.punkto);
  const record = {
    punkto: normalized.punkto,
    t: normalized.t,
    x: normalized.x || '',
    f: normalized.f || '',
    lat: loc ? loc.lat : 0,
    lon: loc ? loc.lon : 0,
    alt: loc ? loc.alt : 0,
  };

  const existing = await db.atoms
    .where('punkto').equals(normalized.punkto)
    .and(a => a.t === normalized.t)
    .first();

  if (!existing) {
    const newId = await db.atoms.add(record);
    return { inserted: true, id: newId };
  }
  return { inserted: false, id: existing.id };
}

export async function getAllAtomsNewestFirst() {
  return db.atoms.orderBy('t').reverse().toArray();
}

export async function getAllAtoms() {
  return db.atoms.toArray();
}
