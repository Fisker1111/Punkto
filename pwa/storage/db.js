const db = new Dexie('punkto');

db.version(1).stores({
  atoms: '++id, punkto, t, lat, lon, alt',
  meta:  'key',
});
// v2: clear stale atoms from old feed (forces re-sync from server)
db.version(2).stores({
  atoms: '++id, punkto, t, lat, lon, alt',
  meta:  'key',
}).upgrade(tx => tx.table('atoms').clear());
db.version(3).stores({
  atoms: '++id, punkto, t, lat, lon, alt',
  meta:  'key',
}).upgrade(tx => tx.table('atoms').clear());
// v4: add nodes table for per-node sync cursors and peer discovery
db.version(4).stores({
  atoms: '++id, punkto, t, lat, lon, alt',
  meta:  'key',
  nodes: 'url',
});

export { db };
