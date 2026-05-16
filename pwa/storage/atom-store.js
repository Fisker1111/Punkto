import { db } from './db.js';
import { decodeAtomLocation } from '../core/location.js';

export async function upsertAtom(atom) {
  const loc = decodeAtomLocation(atom.punkto);
  const record = {
    punkto: atom.punkto,
    t: atom.t,
    x: atom.x || '',
    f: atom.f || '',
    lat: loc ? loc.lat : 0,
    lon: loc ? loc.lon : 0,
    alt: loc ? loc.alt : 0,
  };

  const existing = await db.atoms
    .where('punkto').equals(atom.punkto)
    .and(a => a.t === atom.t)
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
