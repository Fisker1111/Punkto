// Isolated L3-backed cache: legacy relay atoms are never loaded.
// Identity recovery remains in localStorage and is imported by app.js.
const db = new Dexie('punkto-v06');

db.version(1).stores({
  atoms: '++id, atom_id, punkto, t, lat, lon, alt',
  meta: 'key',
});

db.version(2).stores({
  atoms: '++id, atom_id, mid, h, punkto, t, lat, lon, alt',
  meta: 'key',
});

export { db };
