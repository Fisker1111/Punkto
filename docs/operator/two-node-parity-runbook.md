# Two-node parity operator runbook

This procedure changes only temporary local test data. Requirements: Python 3.12+
and installed `cryptography` and `PyYAML`. Run from the repository root.

## Hermetic proof

```bash
python3 -m unittest punkti_node.test_two_node_parity -v
```

A green run lists ten named tests, then `Ran 10 tests in ...` and `OK`.
The harness denies non-loopback connections/DNS and disables proxies. It uses
independent temporary stores and the existing deterministic signing fixtures.
It exercises the runtime worker with controlled wakeups, including a stopped
source daemon, retries, publication races and stale roots. XY/Z lower bounds
are inclusive and upper bounds exclusive. Equal peer head/sequence values are
not required: compare the admitted verified `(MID, sha256)` union.

## Two isolated nodes and independent static origins

Run this single copy-pasteable Python session from the repository root. It chooses
all ports dynamically on loopback. Each data root and test signing key is
separate; these keys are fixtures, never production identities. There is no
systemd unit, production port, DNS or external connection. The node itself
validates signed records; it does not sign on behalf of users.

```bash
python3 - <<'PY'
import hashlib, json, os, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.request import ProxyHandler, build_opener
sys.path.insert(0, 'experimental/punkti-v0.6-mesh/tests')
from support import fixture
from punkti_node.config import load_config
from punkti_node.mesh import wire
from punkti_node.store import PersistentNode
from punkti_node.test_publication import _StaticSource

http = build_opener(ProxyHandler({}))
processes = []
sources = []
with tempfile.TemporaryDirectory(prefix='punkti-parity-') as tmp:
    base = Path(tmp)
    try:
        for i in (1, 2):
            directory = base / str(i)
            directory.mkdir()
            # Fixture i uses this separate deterministic Ed25519 seed.
            key = directory / 'test-key.seed'
            key.write_bytes(hashlib.sha256(f'mesh-key-{i}'.encode()).digest())
            key.chmod(0o600)
            path = base / f'{i}.json'
            path.write_text(json.dumps({
                'web': {'enabled': False},
                'storage': {'data_path': str(directory)},
                'network': {'listen_host': '127.0.0.1', 'listen_port': 0,
                            'sync_interval_seconds': 1}}))
            node = PersistentNode(load_config(path, {}))
            node.submit_records([wire(fixture(i))])
            node.after_sync()
            node.durable.close()
            source = _StaticSource(directory / 'publication').__enter__()
            sources.append(source)
        for i in (1, 2):
            path = base / f'{i}.json'
            config = json.loads(path.read_text())
            config['replication'] = {'static_peers': [sources[2-i].url]}
            path.write_text(json.dumps(config))
            log = open(base / f'{i}.log', 'w')
            # Avoid inherited overrides or proxies affecting this isolated run.
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith('PUNKTO_') and 'proxy' not in k.lower()}
            process = subprocess.Popen([sys.executable, '-u', '-m', 'punkti_node',
                                        '--config', str(path)], env=env,
                                       stdout=log, stderr=subprocess.STDOUT)
            log.close()
            processes.append(process)
        # Stop source daemon 1 before the initial runtime sync (2-second delay).
        processes[0].terminate()
        processes[0].wait(timeout=15)
        print('Node 1 daemon stopped; static origin remains:', sources[0].url)
        deadline = time.monotonic() + 20
        while True:
            with http.open(sources[1].url + '/root.json') as r:
                root = json.load(r)
            with http.open(sources[1].url + '/manifests/' + root['head'] + '.json') as r:
                manifest = json.load(r)
            if manifest['record_count'] == 2:
                break
            if time.monotonic() > deadline:
                raise RuntimeError('convergence timeout; inspect temporary logs')
            time.sleep(.2)
        print('Node 2 republished both signed records:', root)
        print('Temporary roots:', base)
        input('Press Enter to stop node 2, static origins, and remove test data: ')
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)
        for source in sources:
            source.__exit__(None, None, None)
PY
```

`_StaticSource` is a plain stdlib `http.server.ThreadingHTTPServer` bound to
`127.0.0.1:0`, serving only the publication directory. In an isolated config,
`replication.static_peers` lists the other directory's HTTP base (containing
`root.json`), without a trailing slash. `PUNKTO_STATIC_PEERS` is the equivalent
comma-separated environment override. The default empty list changes no existing
runtime behavior. Failed peers are logged and retried on the next sync interval;
live Mesh synchronization remains independent. The harness additionally proves
bidirectional union convergence; the session above isolates the stopped-daemon case.

## Read-only inspection of real nodes (operator-run only)

Set these to the two approved node origins and their actual publication roots.
No command below submits records or changes either host. This implementation run
does not execute these external reads.

```bash
export NODE1='https://punkto.xyz'
export NODE2='https://test2.punkto.xyz'
export PUB1="$NODE1/publication"
export PUB2="$NODE2/publication"
python3 - <<'PY'
import json, os
from urllib.request import urlopen
from punkti_node.publication import Reader, root, manifest, digest
from punkti_node.carrier import validate, State

def get(url):
    with urlopen(url, timeout=10) as response:
        return response.read()

sets = []
for number in (1, 2):
    origin, publication = os.environ[f'NODE{number}'], os.environ[f'PUB{number}']
    hello = json.loads(get(origin + '/hello'))
    print(origin, 'hello (inspect peers, epoch, scopes):', hello)
    published = root(get(publication + '/root.json'))
    raw = get(publication + '/manifests/' + published['head'] + '.json')
    assert digest(raw) == published['head']
    metadata = manifest(raw)
    assert metadata['seq'] == published['seq']
    print('root:', published, 'manifest:', metadata)
    reader = Reader()
    reader.read_publication(publication)  # GET only; verifies shards and carriers
    records = set()
    for raw in reader.store.valid.values():
        observation = validate(raw)
        assert observation.state == State.VALID
        records.add((observation.address, digest(raw)))
    print('verified records:', sorted(records))
    sets.append(records)
print('only node 1:', sorted(sets[0] - sets[1]))
print('only node 2:', sorted(sets[1] - sets[0]))
print('verified sets equal:', sets[0] == sets[1])
PY
```

A moving publication may require another read. Compare verified records within
compatible subscriptions, not advertised counts or equal sequence/head values.
These observations establish only the records visible at inspection time.

## Legacy StarNode cron and limits

`/opt/punkti/sync.sh` is **obsolete**: it implements the April 2026 `log.ndjson`
design with unanchored rows, not the v0.6 signed store. The task's reported current
failures are `www.punkti.net` → TLS failure → HTTP 000 on node2, and
`www.sunebech.com` → HTTP 302 on node1. It does **not** feed the v0.6 store and
must not be mistaken for replication. Its removal/disablement requires founder
approval; this runbook does not instruct changing that cron.

Not covered: DNS/HA changes, apex cutover, production writes, or a new production
replication job. This work does not deploy anything or authorize production
configuration changes.
