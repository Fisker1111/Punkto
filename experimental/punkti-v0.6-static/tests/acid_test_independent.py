"""Independent acid-test check, not part of the repo suite.

Uses a plain `python3 -m http.server` as the origin (NOT the repo's own
StaticSource) and a separate reader process to prove the static-first claim:
stop the publisher entirely, serve only the generated directory, and replicate
from a different process.
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

PROTO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROTO / 'src'))
sys.path.insert(0, str(PROTO / 'tests'))

from staticpub.harness import Node  # noqa: E402
from staticpub.carrier_io import make_record  # noqa: E402
from test_static_publication import make_h  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix='acid-'))
node_a = Node(tmp / 'a', mode='B', leaf_depth=2)
records = [make_record(i + 1, make_h(i + 1, prefix='u4')) for i in range(12)]
for raw in records:
    node_a.store.admit(raw)
node_a.publish()
node_a.stop()  # there is no daemon to keep alive

pub = node_a.path / 'public'
print('published dir:', pub)
print('root.json present:', (pub / 'punkti' / 'root.json').is_file())

# Origin = a completely dumb stdlib static server on the generated directory.
port = 8931
proc = subprocess.Popen(
    [sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1'],
    cwd=str(pub), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    base = f'http://127.0.0.1:{port}/punkti'
    for _ in range(50):
        try:
            with urlopen(base + '/root.json', timeout=2) as r:
                if r.status == 200:
                    break
        except Exception:
            time.sleep(0.1)
    else:
        raise SystemExit('static origin never came up')

    # A separate node in this process replicates purely over static GETs.
    node_b = Node(tmp / 'b', mode='B', leaf_depth=2)
    results = node_b.replicate(base)
    print('replicate results:', results)
    print('B valid count:', len(node_b.store.valid))
    print('A valid count:', len(node_a.store.valid))
    assert len(node_b.store.valid) == len(records), 'replication incomplete'

    # B republishes into its own publication and A reads B back -> union.
    node_b.publish()
    base_b = None
    proc2 = subprocess.Popen(
        [sys.executable, '-m', 'http.server', str(port + 1), '--bind', '127.0.0.1'],
        cwd=str(node_b.path / 'public'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(0.6)
        base_b = f'http://127.0.0.1:{port + 1}/punkti'
        node_a.replicate(base_b)
        print('after mutual replicate, A:', len(node_a.store.valid), 'B:', len(node_b.store.valid))
        assert set(node_a.store.valid) == set(node_b.store.valid), 'no convergence'

        # Clean-room independent parser over the same static origin.
        from staticpub import cleanroom
        accepted = cleanroom.read(base, packs=True, leaf_depth=2)
        print('clean-room accepted:', len(accepted))
        assert len(accepted) == len(records), 'clean-room mismatch'
    finally:
        proc2.terminate()
        proc2.wait(timeout=10)
finally:
    proc.terminate()
    proc.wait(timeout=10)

print('ACID TEST OK: static-only origin, daemon-free publisher, independent reader')
