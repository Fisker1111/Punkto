"""Exercise the World adapter against a temporary, signed local atom store.
Run from the repository root: python3 world/tests/atoms-smoke.py
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from punkto_atoms.make_atom import make_atom
from punkto_atoms.server import AtomService, Config, make_server
from punkto_atoms.store import AtomStore

with tempfile.TemporaryDirectory() as directory:
    store = AtomStore(Path(directory) / 'atoms.db')
    now = int(time.time() * 1000)
    for lat, lon, alt, t, message, identity in [
        (55.6761, 12.5683, 32, now - 3600000, 'World smoke: City Hall', 'smoke-signe'),
        (55.6798, 12.5908, 18, now, 'World smoke: Nyhavn', 'smoke-freja'),
    ]:
        store.insert(make_atom(lat, lon, alt, t, message, identity))
    server = make_server(AtomService(store, Config()), host='127.0.0.1', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        script = r'''
import assert from 'node:assert/strict';
import { build } from 'esbuild';
const built = await build({ entryPoints: ['src/atomsAdapter.ts'], bundle: true,
  write: false, format: 'esm', define: { 'import.meta.env.VITE_ATOM_URL': JSON.stringify(BASE) } });
const { realAdapter, fixtureAdapter, FIXTURE_START, FIXTURE_END } =
  await import('data:text/javascript;base64,' + Buffer.from(built.outputFiles[0].text).toString('base64'));
const bounds = { minLon: 12.55, maxLon: 12.65, minLat: 55.66, maxLat: 55.70 };
const time = { from: 0, to: Number.MAX_SAFE_INTEGER };
const atoms = await realAdapter.getAtoms(bounds, time);
const source = await (await fetch(BASE + '/atoms/v1/feed')).json();
assert.equal(atoms.length, 2);
for (const atom of atoms) {
  const raw = source.find(item => item.mid === atom.id);
  assert.deepEqual({ ...atom, color: undefined }, { id: raw.mid, x: raw.lon, y: raw.lat,
    altitudeM: raw.alt, t: raw.t, message: raw.x, identity: raw.fp, color: undefined });
  assert.ok(['#f6bb78', '#8bd6cb', '#b8a4ef'].includes(atom.color));
}
assert.deepEqual(await realAdapter.getAtoms(bounds, time), atoms);
assert.equal((await realAdapter.getAtoms(bounds, { from: 0, to: Math.min(...atoms.map(a => a.t)) })).length, 1);
assert.deepEqual(await realAdapter.getAtoms({ minLon: 0, maxLon: 1, minLat: 0, maxLat: 1 }, time), []);
assert.ok((await fixtureAdapter.getAtoms(bounds, { from: FIXTURE_START, to: FIXTURE_END })).length > 0);
const originalFetch = globalThis.fetch;
for (const response of [new Response('oops', { status: 500 }), new Response('invalid json'), new Response('{}'), new Response('[{}]')]) {
  globalThis.fetch = async () => response;
  await assert.rejects(() => realAdapter.getAtoms(bounds, time));
}
globalThis.fetch = async () => { throw new Error('offline'); };
await assert.rejects(() => realAdapter.getAtoms(bounds, time));
globalThis.fetch = originalFetch;
console.log(JSON.stringify(atoms, null, 2));
console.log('PASS: real mapping, stable colors, time/bounds filtering, empty result, fixture query, HTTP/JSON/schema/network errors');
'''
        subprocess.run(['node', '--input-type=module', '-e', 'const BASE = ' + json.dumps(base) + ';\n' + script], cwd=ROOT / 'world', check=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        store.close()
