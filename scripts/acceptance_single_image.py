"""Single-image acceptance proofs, run *inside* the combined Punkto container.

Modes
  all   : fresh-store proofs -> push a deliberate signed L4 atom through /api/push
          to node A, read it back byte-exactly, prove B receives it by mesh sync,
          write the evidence/state file for the restart phase.
  verify <state.json>
        : after the container is recreated from the same data volume, prove the
          atom, payload bytes and store epoch survived.

Both nodes must be configured with each other in network.peers. Uses only the
stdlib plus punkti_node.carrier (cryptography is in the image).
"""
import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

sys.path.insert(0, '/app')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from punkti_node import carrier  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

H = 'u07qskym6vu8'  # Valid 12-character 3D geohash (Copenhagen).
L4 = {
    'punkto': 'p:' + H,
    't': 1792676000000,
    'x': 'Acceptance atom: single image, clean 0.6 store. \u00e6\u00f8\u00e5',
    'f': 'acceptance',
    'nested': {'unknown': [1, 2, {'deep': True}], 'null': None, 'text': 'keep me'},
}


def get(base, path, timeout=10):
    with urlopen(base + path, timeout=timeout) as response:
        return response.status, json.loads(response.read())


def post(base, path, payload, timeout=10):
    from urllib.request import Request
    request = Request(base + path, data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=timeout) as response:
        return response.status, json.loads(response.read())


def pull(base, limit=32):
    records, cursor = [], None
    for _ in range(200):
        query = json.dumps({'scope': {}, 'limit': limit, 'cursor': cursor}, separators=(',', ':'))
        status, page = get(base, '/api/pull?q=' + quote(query))
        assert status == 200, status
        records.extend(page['records'])
        if page['end']:
            return records
        assert page['cursor'] and page['cursor'] != cursor, 'cursor did not advance'
        cursor = page['cursor']
    raise AssertionError('page limit exceeded')


def build_record(payload, key):
    x = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    atom = {'v': carrier.VERSION, 't': payload['t'], 'h': H, 'x': x, 'alg': 'ed25519',
            'pk': carrier.b64(key.public_key().public_bytes_raw()), 'refs': [], 'ext': '',
            'sig': carrier.b64(bytes(64))}
    body = carrier.canonical(atom)
    atom['sig'] = carrier.b64(key.sign(carrier.SIGN_DOMAIN + body))
    raw = carrier.record(atom)
    import hashlib
    address = carrier.VERSION + ':' + hashlib.sha256(carrier.MID_DOMAIN + body).hexdigest()
    return dict(address=address, sha256=hashlib.sha256(raw).hexdigest(),
                record=carrier.b64(raw)), x


def find(records, address):
    for item in records:
        if item['address'] == address:
            return item
    return None


def payload_of(item):
    raw = carrier.unb64(item['record'])
    atom, _, _ = carrier.decode(raw)
    assert carrier.validate(raw).state is carrier.State.VALID, 'record not VALID'
    return atom['x']


def wait_for(base, address, x, seconds=90):
    deadline = time.time() + seconds
    while time.time() < deadline:
        item = find(pull(base), address)
        if item and payload_of(item) == x:
            return True
        time.sleep(3)
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['all', 'verify'])
    parser.add_argument('state', nargs='?', default='/data/acceptance-state.json')
    parser.add_argument('--a', default='http://localhost:8000')
    parser.add_argument('--b', default='http://instance-b:8000')
    args = parser.parse_args()

    if args.mode == 'verify':
        state = json.loads(Path(args.state).read_text())
        status, info = get(args.a, '/api/node/info')
        assert status == 200 and info['epoch'] == state['epoch'], 'epoch changed across restart'
        item = find(pull(args.a), state['address'])
        assert item, 'atom missing after restart'
        assert payload_of(item) == state['x'], 'payload changed after restart'
        assert wait_for(args.b, state['address'], state['x'], 30), 'peer lost the atom'
        print(json.dumps({'restart': 'ok', 'epoch': info['epoch'],
                          'records': len(pull(args.a)), 'peer_copy': True}, sort_keys=True))
        return

    # 1. fresh store
    status, info = get(args.a, '/api/node/info')
    assert status == 200 and info['store']['valid'] == 0, 'store is not fresh'
    status, ready = get(args.a, '/api/ready')
    assert status == 200 and ready['status'] == 'ready', ready
    status, health = get(args.a, '/api/health')
    assert health['status'] == 'ok' and health['version'], health
    status_b, info_b = get(args.b, '/api/node/info')
    assert info_b['epoch'] != info['epoch'], 'instances must not share a store'
    assert info_b['peers'], 'peer not configured on instance B'

    # PWA is served from the same origin/container
    with urlopen(args.a + '/', timeout=10) as response:
        html = response.read().decode('utf-8', 'replace')
    assert response.status == 200 and 'Punkto' in html and '<script' in html, 'PWA not served'

    # deliberate signed atom through the public API path
    key = Ed25519PrivateKey.generate()
    item, x = build_record(L4, key)
    status, result = post(args.a, '/api/push', {'records': [item]})
    assert status == 200 and result['results'][0]['admitted'] is True, result

    # read back byte-exactly (unknown L4 keys preserved)
    stored = find(pull(args.a), item['address'])
    assert stored and stored['sha256'] == item['sha256'], 'record digest changed'
    assert payload_of(stored) == x, 'L4 payload not preserved byte-exactly'
    assert carrier.unb64(stored['record']) == carrier.unb64(item['record'])

    # duplicate admission is refused, not duplicated
    status, again = post(args.a, '/api/push', {'records': [item]})
    assert again['results'][0]['admitted'] is False and again['results'][0]['reason'] == 'duplicate'

    # mesh sync: B receives A's atom without any browser involvement
    assert wait_for(args.b, item['address'], x), 'peer sync failed'
    assert find(pull(args.b), item['address'])['sha256'] == item['sha256']

    # A works with no punkto.xyz reference and advertises its own URL
    assert 'punkto.xyz' not in json.dumps(info) and info['node']['public_url'] != '', info['node']

    Path(args.state).write_text(json.dumps(dict(epoch=info['epoch'], address=item['address'],
                                                sha256=item['sha256'], x=x), sort_keys=True))
    print(json.dumps({'fresh_store': True, 'pwa_same_origin': True, 'push': 'admitted',
                      'payload_preserved': True, 'duplicate_refused': True,
                      'peer_sync': True, 'api_aliases': True,
                      'version': health['version'], 'epoch': info['epoch'],
                      'address': item['address'], 'records': len(pull(args.a))}, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, URLError, OSError) as exc:
        print('ACCEPTANCE FAILED: %s: %s' % (type(exc).__name__, exc), file=sys.stderr)
        sys.exit(1)
