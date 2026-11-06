"""Explicit online capture utility; never invoked by the offline test suite."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

ORIGIN = 'https://punkto.xyz'
EXPECTED = {
    '2446a3b353e451b99c8868fbed544e9d7b3378e63dc0837a54171f88244e2f2d': 'punkti/0.6:fc1887028aedd99fc39fbb07848e375f2be6289966a2f19468db56313689b2ed',
    '0c7259dac68a6f3bab62f0f57691d586aec4955d173cb7103bd37f85a8e0169b': 'punkti/0.6:70e0da2fc002e38374947be6ec9af4c7fd4914fbb4cc41bb58513538551d6854',
}
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError('Redirect refused')
opener = urllib.request.build_opener(NoRedirect)
objects = {}
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def get(path, digest=None):
    assert path.startswith('/publication/') and '..' not in path
    with opener.open(urllib.request.Request(ORIGIN + path, method='GET'), timeout=15) as response:
        raw = response.read(1048577)
    assert len(raw) <= 1048576
    assert digest is None or sha(raw) == digest, path
    objects[path] = raw
    return raw

def encode(obj):
    return json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode()
root_raw = get('/publication/root.json')
root = json.loads(root_raw)
manifest_path = '/publication/manifests/' + root['head'] + '.json'
manifest = json.loads(get(manifest_path, root['head']))
chain = []
digest = manifest['index']['s0']
for depth in range(2, 11):
    prefix = 's000000000'[:depth]
    path = '/publication/h/' + '/'.join(prefix) + '/' + digest + '.json'
    shard = json.loads(get(path, digest))
    assert shard['prefix'] == prefix
    chain.append((path, shard))
    if depth < 10:
        digest = shard['children']['s000000000'[:depth+1]]
selected = [r for r in shard['records'] if r['sha256'] in EXPECTED]
assert len(selected) == 2
for record in selected:
    assert record['h'] == 's00000000000_0'
    assert record['mid'] == EXPECTED[record['sha256']]
    digest = record['sha256']
    get('/publication/records/' + digest[:2] + '/' + digest, digest)
captured = {path: sha(raw) for path, raw in objects.items()}
removed_count = len(shard['records']) - len(selected)
trimmed = selected != shard['records']
if trimmed:
    # Preserve raw records; rehash only changed JSON objects up to the mutable root.
    child = None
    for path, obj in reversed(chain):
        if child is None:
            obj['records'] = selected
        else:
            obj['children'][child_prefix] = child
        raw = encode(obj)
        child = sha(raw)
        child_prefix = obj['prefix']
        del objects[path]
        objects[path.rsplit('/', 1)[0] + '/' + child + '.json'] = raw
    manifest['index']['s0'] = child
    manifest['record_count'] -= removed_count
    raw = encode(manifest)
    del objects[manifest_path]
    root['head'] = sha(raw)
    objects['/publication/manifests/' + root['head'] + '.json'] = raw
    objects['/publication/root.json'] = encode(root)
base = Path(__file__).resolve().parents[1] / 'test/fixtures'
shutil.rmtree(base / 'publication')
for path, raw in objects.items():
    target = base / path.lstrip('/')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
provenance = {'captured_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'origin': ORIGIN, 'live_root': json.loads(root_raw), 'trimmed': trimmed,
              'captured_objects_sha256': captured,
              'note': 'GET only; digest integrity checked; no signature validation performed.'}
(base / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
print(json.dumps(provenance, indent=2))
