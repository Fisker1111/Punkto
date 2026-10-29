#!/usr/bin/env python3
"""Independent, local-only GET demonstration; no admission or new cryptography."""
import argparse
import hashlib
import json
import urllib.request
import urllib.parse

ALPHABET = '0123456789bcdefghjkmnpqrstuvwxyz'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def spatial(h):
    if h == '':
        return '~'
    require(len(h) <= 32 and h.count('_') == 1, 'spatial address')
    xy, z = h.split('_')
    require(4 <= len(xy) <= 12 and all(c in ALPHABET for c in xy), 'XY')
    unsigned = z.removeprefix('-')
    parts = unsigned.split('.')
    require(1 <= len(parts) <= 2 and all(p and all(c in '0123456789' for c in p) for p in parts), 'Z decimal')
    require(len(z) <= 27 and (parts[0] == '0' or not parts[0].startswith('0'))
            and z != '-0' and (len(parts) == 1 or not parts[1].endswith('0')), 'canonical Z')
    return xy.ljust(12, '0')[:10]


class LengthReader:
    def __init__(self, raw):
        self.raw, self.pos = raw, 0

    def take(self, size):
        require(size <= len(self.raw) - self.pos, 'truncated LENGTH field')
        value = self.raw[self.pos:self.pos + size]
        self.pos += size
        return value

    def count(self):
        return int.from_bytes(self.take(4), 'big')

    def field(self):
        return self.take(self.count())

    def text(self):
        return self.field().decode('utf-8', errors='strict')

    def end(self):
        require(self.pos == len(self.raw), 'trailing bytes')


def decode(raw):
    require(len(raw) <= 2 * 1024 * 1024, 'record limit')
    outer = LengthReader(raw)
    body, sig = outer.field(), outer.field()
    outer.end()
    require(len(body) <= 1024 * 1024, 'body limit')
    r = LengthReader(body)
    v, timestamp, h, x, alg, pk = r.text(), r.text(), r.text(), r.text(), r.text(), r.field()
    require(v == 'punkti/0.6', 'version')
    require(timestamp and all(c in '0123456789' for c in timestamp)
            and str(int(timestamp)) == timestamp and int(timestamp) <= 9007199254740991, 'canonical timestamp')
    spatial(h)
    require(1 <= len(alg.encode()) <= 128 and alg.isascii() and pk and sig, 'algorithm/key/signature encoding')
    if alg == 'ed25519':
        require(len(pk) == 32 and len(sig) == 64, 'ed25519 lengths')
    count = r.count()
    require(count <= 256, 'reference limit')
    refs = []
    for _ in range(count):
        target, rel = r.text(), r.text()
        namespace, separator, digest = target.partition(':')
        require(separator and 1 <= len(namespace) <= 128
                and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789./_-' for c in namespace)
                and digest and len(digest) % 2 == 0 and all(c in '0123456789abcdef' for c in digest), 'reference address')
        require(namespace not in ('punkti/0.5.1', 'punkti/0.6') or len(digest) == 64, 'reference digest')
        require(len(rel.encode()) <= 1024, 'relation limit')
        refs.append(dict(target=target, rel=rel))
    ext = r.field()
    r.end()
    # Binary fields displayed as hex, not the JSON import envelope's base64.
    return dict(v=v, t=int(timestamp), h=h, x=x, alg=alg, pk_hex=pk.hex(),
                refs=refs, ext_hex=ext.hex(), sig_hex=sig.hex())


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('redirect refused: fixture-only client')


def sha_ok(value):
    require(isinstance(value, str) and len(value) == 64
            and all(c in '0123456789abcdef' for c in value), 'SHA-256 spelling')
    return value


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def parse(raw):
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
    def check(value):
        require(value is None or type(value) in (dict, list, str, int, bool), 'JSON type')
        for child in value.values() if isinstance(value, dict) else value if isinstance(value, list) else []:
            check(child)
    check(value)
    require(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode() == raw, 'canonical JSON')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--h', required=True, help='exact address; use an empty string for unanchored')
    parser.add_argument('--verify-with-frozen-carrier', action='store_true')
    args = parser.parse_args()
    base = args.base.rstrip('/')
    url = urllib.parse.urlsplit(base)
    require(url.scheme == 'http' and url.hostname == '127.0.0.1' and url.port
            and not url.username and not url.password and not url.query and not url.fragment, 'only explicit 127.0.0.1 HTTP fixture URLs allowed')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def get(path, expected=None, source='mutable pointer; no upstream digest'):
        if expected is not None:
            sha_ok(expected)
        address = base + '/' + path
        with opener.open(urllib.request.Request(address, method='GET'), timeout=10) as response:
            raw = response.read(64 * 1024 * 1024 + 1)
        require(len(raw) <= 64 * 1024 * 1024, 'object limit')
        digest = hashlib.sha256(raw).hexdigest()
        print(f'GET {address}\n  bytes={len(raw)} sha256={digest}\n  source={source}')
        require(expected is None or digest == expected, 'SHA-256 mismatch')
        print('  digest=MATCH' if expected else '  digest=OBSERVED ONLY (mutable root is not content-addressed)')
        return raw

    leaf = spatial(args.h)
    print(f'BASE={base} TARGET_H={json.dumps(args.h)} LEAF={leaf}')
    root = parse(get('root.json'))
    head = sha_ok(root['head'])
    print(f'HEAD={head}')
    manifest = parse(get(f'manifests/{head}.json', head, 'root.json.head'))
    require(manifest['seq'] == root['seq'], 'publication race')
    prefix = '~' if leaf == '~' else leaf[:2]
    sha = sha_ok(manifest['index'][prefix])
    source = f'manifests/{head}.json index[{prefix!r}]'
    while True:
        path = 'h/' + '/'.join(prefix) + '/' + sha + '.json'
        shard = parse(get(path, sha, source))
        require(shard['prefix'] == prefix, 'prefix chain')
        if prefix == leaf:
            require(not shard['children'] and shard['records'], 'leaf shape')
            break
        require(not shard['records'] and not shard['packs'], 'interior shape')
        for child, child_sha in shard['children'].items():
            require(len(child) == len(prefix) + 1 and child.startswith(prefix)
                    and all(c in ALPHABET for c in child), 'child prefix')
            sha_ok(child_sha)
        prefix = leaf[:len(prefix) + 1]
        sha = sha_ok(shard['children'][prefix])
        source = f'{path} children[{prefix!r}]'
    print(f'LEAF_PREFIX={prefix} LEAF_SHA={sha}')
    matched = 0
    for entry in shard['records']:
        require(set(entry) == {'h', 'mid', 'sha256'} and spatial(entry['h']) == leaf, 'entry shape/placement')
        sha_ok(entry['sha256'])
        if entry['h'] != args.h:
            print('EXCLUDED exact-h mismatch ' + json.dumps(entry, sort_keys=True))
            continue
        matched += 1
        print('MATCH ' + json.dumps(entry, sort_keys=True))
        record_sha = entry['sha256']
        raw = get(f'records/{record_sha[:2]}/{record_sha}', record_sha, f'{path} records[].sha256 (exact h)')
        atom = decode(raw)
        require(atom['h'] == args.h, 'decoded h mismatch')
        print('DECODED (binary fields hex; payload untrusted) ' + json.dumps(atom, sort_keys=True))
        if args.verify_with_frozen_carrier:
            # Optional separate reference check; never involved in fetching/decoding.
            import sys
            from pathlib import Path
            sys.dont_write_bytecode = True
            sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
            from punkti_node import carrier
            observation = carrier.validate(raw)
            require(observation.address == entry['mid'] and observation.h == entry['h'], 'frozen verifier metadata mismatch')
            print(f'FROZEN REFERENCE VERIFIER (not GET path): {observation.state.value}; MID and exact h match leaf')
    print(f'MATCHING_RECORDS={matched}')
    print('What raw GET can / cannot verify:')
    print('VERIFIED: transport digests (manifest, shards, records), structural/canonical decode, exact h comparison.')
    print('NOT VERIFIED by raw GET: signature validity, MID recomputation, author identity, global completeness/coverage.')
    print('Root digest is observed, not authenticated. Payload is untrusted data. No VALID claim from raw GET.')
    if args.verify_with_frozen_carrier:
        print('Optional frozen carrier adds signature verification and MID recomputation; no real-world identity or completeness claim.')


if __name__ == '__main__':
    main()
