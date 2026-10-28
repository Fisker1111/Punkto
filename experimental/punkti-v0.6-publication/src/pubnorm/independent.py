"""Independent revision 3 implementation, with a queue-based traversal.

Imports only stdlib and approved carrier/spatial codecs. No reference publication
helpers, publisher, reader, store, or staticpub imports. Own JSON/framing, object
checks, pack grouping, publication construction and admission state. The accepted
staticpub clean-room experiment motivates this boundary, not shared parser code.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.request import urlopen
from urllib.error import URLError

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'punkti-v0.6-mesh/src'))
import carrier
from spatial import Subscription, parse_h


class ReadError(ValueError):
    error_class = 'retryable'

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    """Small recursive encoder, independent of reference json.dumps encoding."""
    if value is None:
        return b'null'
    if type(value) is bool:
        return b'true' if value else b'false'
    if type(value) is int:
        return str(value).encode('ascii')
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False).encode('utf-8')
    if isinstance(value, list):
        return b'[' + b','.join(map(encode, value)) + b']'
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return b'{' + b','.join(encode(k) + b':' + encode(value[k]) for k in sorted(value)) + b'}'
    raise ValueError('JSON value')


def decode(data):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError('duplicate member')
            out[k] = v
        return out
    def noninteger(_):
        raise ValueError('number')
    value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                       parse_float=noninteger, parse_constant=noninteger)
    if encode(value) != data:
        raise ValueError('canonical encoding')
    return value


def digest_string(s):
    if not isinstance(s, str) or re.fullmatch(r'[0-9a-f]{64}', s) is None:
        raise ValueError('digest')


def fields(obj, names):
    if type(obj) is not dict or set(obj) != set(names.split()) or obj['v'] != 'punkti/pub/0.6':
        raise ValueError('members/version')


def number(n, low):
    if type(n) is not int or n < low:
        raise ValueError('integer')


def prefix(p, size):
    if not isinstance(p, str) or len(p) != size or re.fullmatch('[0123456789bcdefghjkmnpqrstuvwxyz]+', p) is None:
        raise ValueError('prefix')


def placement(h):
    xy_z = parse_h(h)
    return (xy_z[0] + '000000000000')[:10] if xy_z else '~'


def selected(p, scope):
    if p == '~':
        return all(x is None for x in scope.wire().values())
    bottom = p + '0' * (12 - len(p))
    top = p + 'z' * (12 - len(p))
    return ((scope.xy_lo is None or top >= scope.xy_lo.ljust(12, '0')) and
            (scope.xy_hi is None or bottom < scope.xy_hi.ljust(12, '0')))


def bundle(blobs):
    if not 1 <= len(blobs) <= 256 or any(len(b) == 0 for b in blobs):
        raise ValueError('pack count/size')
    return b'PUNKTIPACK1' + len(blobs).to_bytes(4, 'big') + b''.join(len(b).to_bytes(4, 'big') + b for b in blobs)


def unbundle(data):
    if not data.startswith(b'PUNKTIPACK1') or len(data) < 15:
        raise ValueError('pack header')
    count = int.from_bytes(data[11:15], 'big')
    if count < 1 or count > 256:
        raise ValueError('pack count')
    cursor, blobs = 15, []
    for _ in range(count):
        if cursor + 4 > len(data):
            raise ValueError('pack framing')
        size = int.from_bytes(data[cursor:cursor + 4], 'big')
        cursor += 4
        if size == 0 or cursor + size > len(data):
            raise ValueError('pack size')
        blobs.append(data[cursor:cursor + size])
        cursor += size
    if cursor != len(data):
        raise ValueError('pack trailing data')
    return blobs


class Reader:
    def __init__(self, packs=False, retries=2):
        self.packs, self.retries = packs, retries
        self.valid, self.candidates, self.heads, self.checkpoints = {}, {}, {}, {}
        self.paths = []

    @property
    def store(self):
        return self

    def fetch(self, url, path, expected=None):
        self.paths.append(path)
        try:
            with urlopen(url + '/' + path, timeout=10) as stream:
                data = stream.read(67108865)
        except (URLError, OSError) as exc:
            if hasattr(exc, 'close'):
                exc.close()
            raise ReadError('missing object') from exc
        if len(data) > 67108864:
            raise ReadError('resource limit')
        if expected is not None and hash_bytes(data) != expected:
            raise ReadError('corrupt object')
        return data

    def read_publication(self, base, scope=None):
        url, scope = base.rstrip('/'), scope or Subscription()
        for n in range(self.retries + 1):
            try:
                return self.scan(url, scope)
            except ReadError as exc:
                if exc.reason == 'publication race' and n < self.retries:
                    continue
                raise
            except carrier.ResourceLimit as exc:
                raise ReadError('resource limit') from exc
            except (ValueError, TypeError, KeyError, RecursionError, OverflowError) as exc:
                raise ReadError('invalid object') from exc

    def scan(self, url, scope):
        pointer = decode(self.fetch(url, 'root.json'))
        fields(pointer, 'v seq head')
        number(pointer['seq'], 1)
        digest_string(pointer['head'])
        current = (pointer['seq'], pointer['head'])
        if url in self.heads:
            prior = self.heads[url]
            if current[0] < prior[0]:
                raise ReadError('stale root')
            if current[0] == prior[0] and current[1] != prior[1]:
                raise ReadError('equivocal root')
        m = decode(self.fetch(url, 'manifests/' + current[1] + '.json', current[1]))
        fields(m, 'index pack_count prev record_count seq v')
        number(m['seq'], 1)
        number(m['record_count'], 0)
        number(m['pack_count'], 0)
        if m['prev'] is not None:
            digest_string(m['prev'])
        if (m['seq'] == 1) != (m['prev'] is None):
            raise ValueError('previous manifest')
        if type(m['index']) is not dict or len(m['index']) > 1025:
            raise ValueError('index')
        if current[0] != m['seq']:
            raise ReadError('publication race')
        queue = []
        for p, s in m['index'].items():
            if p != '~':
                prefix(p, 2)
            digest_string(s)
            queue.append((p, s))
        valid, candidates, rejected, totals = {}, {}, 0, [0, 0]
        for p, s in queue:
            if not selected(p, scope):
                continue
            node = decode(self.fetch(url, 'h/' + '/'.join(p) + '/' + s + '.json', s))
            fields(node, 'children packs prefix records v')
            if node['prefix'] != p or type(node['children']) is not dict or type(node['records']) is not list or type(node['packs']) is not list:
                raise ValueError('shard')
            leaf = p == '~' or len(p) == 10
            if leaf:
                if node['children'] or not node['records']:
                    raise ValueError('leaf')
            elif not node['children'] or node['records'] or node['packs']:
                raise ValueError('interior')
            for child, address in node['children'].items():
                prefix(child, len(p) + 1)
                if len(child) > 10 or child[:-1] != p:
                    raise ValueError('chain')
                digest_string(address)
                queue.append((child, address))
            by_hash = {}
            for entry in node['records']:
                if type(entry) is not dict or set(entry) != {'h', 'mid', 'sha256'}:
                    raise ValueError('entry')
                digest_string(entry['sha256'])
                if not isinstance(entry['mid'], str) or re.fullmatch(r'punkti/0\.6:[0-9a-f]{64}', entry['mid']) is None:
                    raise ValueError('MID')
                if placement(entry['h']) != p or entry['sha256'] in by_hash:
                    raise ValueError('placement/duplicate')
                by_hash[entry['sha256']] = entry
            hashes = list(by_hash)
            if hashes != sorted(hashes):
                raise ValueError('entry order')
            for address in node['packs']:
                digest_string(address)
            if node['packs'] != sorted(set(node['packs'])):
                raise ValueError('pack order')
            if node['packs'] and len(node['packs']) != (len(hashes) + 255) // 256:
                raise ValueError('pack count')
            totals[0] += len(hashes)
            totals[1] += len(node['packs'])
            blobs = {}
            if self.packs and node['packs']:
                expected_groups = {tuple(hashes[i:i + 256]) for i in range(0, len(hashes), 256)}
                for address in node['packs']:
                    items = unbundle(self.fetch(url, 'segments/' + address[:2] + '/' + address, address))
                    group = tuple(hash_bytes(b) for b in items)
                    if group not in expected_groups:
                        raise ReadError('pack membership')
                    expected_groups.remove(group)
                    blobs.update(zip(group, items))
                if expected_groups:
                    raise ReadError('pack membership')
            else:
                for address in hashes:
                    blobs[address] = self.fetch(url, 'records/' + address[:2] + '/' + address, address)
            for address, data in blobs.items():
                obs = carrier.validate(data)
                entry = by_hash[address]
                if obs.address is not None and (obs.address != entry['mid'] or obs.h != entry['h']):
                    raise ReadError('record metadata')
                if obs.state in (carrier.State.STRUCTURAL, carrier.State.PROVENANCE):
                    rejected += 1
                    continue
                if scope.matches(obs.h):
                    if obs.state == carrier.State.VALID:
                        valid.setdefault(obs.address, data)
                    elif obs.state in (carrier.State.ALGORITHM, carrier.State.KEY):
                        candidates[address] = data
        if scope == Subscription() and totals != [m['record_count'], m['pack_count']]:
            raise ReadError('manifest counts')
        before = len(self.valid)
        for mid, data in valid.items():
            self.valid.setdefault(mid, data)
        self.candidates.update(candidates)
        self.heads[url] = current
        self.checkpoints[(url, tuple(scope.wire().items()))] = current[1]
        return dict(head=current[1], seq=current[0], admitted=len(self.valid) - before,
                    valid=len(self.valid), candidates=len(self.candidates), rejected=rejected)


def publication(records, packs=False, previous=None):
    """Pure independent publication builder: ordered (path, bytes) writes."""
    records = {hash_bytes(b): b for b in records}
    writes, nodes = [], {}
    for address in sorted(records):
        data = records[address]
        obs = carrier.validate(data)
        if obs.state not in (carrier.State.VALID, carrier.State.ALGORITHM, carrier.State.KEY):
            raise ValueError('unadmitted record')
        p = placement(obs.h)
        nodes.setdefault(p, {'children': {}, 'packs': [], 'prefix': p, 'records': [], 'v': 'punkti/pub/0.6'})['records'].append({'h': obs.h, 'mid': obs.address, 'sha256': address})
        writes.append(('records/' + address[:2] + '/' + address, data))
    pack_total = 0
    for p in sorted(nodes):
        node = nodes[p]
        if packs:
            for i in range(0, len(node['records']), 256):
                blob = bundle([records[e['sha256']] for e in node['records'][i:i + 256]])
                address = hash_bytes(blob)
                writes.append(('segments/' + address[:2] + '/' + address, blob))
                node['packs'].append(address)
                pack_total += 1
            node['packs'].sort()
    # Construct all ancestor nodes before serializing them deepest-first.
    for p in list(nodes):
        if p == '~':
            continue
        for depth in range(2, 10):
            ancestor = p[:depth]
            nodes.setdefault(ancestor, dict(children={}, packs=[], prefix=ancestor, records=[], v='punkti/pub/0.6'))
    index = {}
    for p in sorted(nodes, key=lambda k: (-len(k), k)):
        data = encode(nodes[p])
        address = hash_bytes(data)
        writes.append(('h/' + '/'.join(p) + '/' + address + '.json', data))
        if p == '~' or len(p) == 2:
            index[p] = address
        else:
            nodes[p[:-1]]['children'][p] = address
    state = dict(index=index, record_count=len(records), pack_count=pack_total)
    if previous and all(previous[k] == v for k, v in state.items()):
        return writes, dict(v='punkti/pub/0.6', seq=previous['seq'], head=hash_bytes(encode(previous))), False
    m = dict(state, v='punkti/pub/0.6', seq=previous['seq'] + 1 if previous else 1,
             prev=hash_bytes(encode(previous)) if previous else None)
    data = encode(m)
    address = hash_bytes(data)
    writes.append(('manifests/' + address + '.json', data))
    return writes, dict(v='punkti/pub/0.6', seq=m['seq'], head=address), True


def publish(directory, records, packs=False):
    """Independent single-writer durable adapter, root replaced last."""
    directory = Path(directory)
    def write(path, data):
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        for ancestor in (target.parent, *target.parent.parents):
            fd = os.open(ancestor, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        temporary = target.with_name('.' + target.name + '.tmp')
        try:
            with temporary.open('wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        finally:
            temporary.unlink(missing_ok=True)
    previous = None
    if (directory / 'root.json').exists():
        r = decode((directory / 'root.json').read_bytes())
        fields(r, 'v seq head')
        number(r['seq'], 1)
        digest_string(r['head'])
        data = (directory / 'manifests' / (r['head'] + '.json')).read_bytes()
        if hash_bytes(data) != r['head']:
            raise ValueError('previous digest')
        previous = decode(data)
        if previous['seq'] != r['seq']:
            raise ValueError('previous sequence')
    writes, root, changed = publication(records, packs, previous)
    for path, data in writes:
        target = directory / path
        if not target.exists() or target.read_bytes() != data:
            write(path, data)
    if changed:
        write('root.json', encode(root))
    return root
