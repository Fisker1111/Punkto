"""Strict derived-object validation. Fixed record links allow one parent hop only."""
import re
from punkti_node import publication as pub
from .geohash import ALPHABET

VERSION = 'punkti/discovery/0.1'
canonical = pub.canonical
digest = pub.digest


def sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('sha256')
    return value


def prefix(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-z]{1,12}', value) or any(c not in ALPHABET for c in value):
        raise ValueError('prefix')
    return value


def href(value, checksum, record=False):
    sha(checksum)
    expected = ('../' + pub.object_path('records', checksum)) if record else f'd/{checksum}.json'
    if value != expected:
        raise ValueError('href')
    return value


def integer(value):
    if type(value) is not int or value < 0:
        raise ValueError('count')


def descriptor(value):
    if not isinstance(value, dict) or set(value) != {'atoms', 'addresses', 'sha256', 'href'}:
        raise ValueError('descriptor')
    integer(value['atoms'])
    integer(value['addresses'])
    if not 0 < value['addresses'] <= value['atoms']:
        raise ValueError('occupied descriptor')
    href(value['href'], value['sha256'])


def validate(raw, source=None, expected_prefix=None):
    obj = pub.parse(raw)
    common = {'v', 'source', 'prefix', 'atoms', 'addresses'}
    if not isinstance(obj, dict) or obj.get('v') != VERSION:
        raise ValueError('version')
    terminal = 'entries' in obj
    allowed = common | ({'entries'} if terminal else {'children'})
    if not terminal and obj.get('prefix') == '' and 'unanchored' in obj:
        allowed.add('unanchored')
    if set(obj) != allowed:
        raise ValueError('shape')
    binding = obj['source']
    if not isinstance(binding, dict) or set(binding) != {'head', 'seq'}:
        raise ValueError('source')
    sha(binding['head'])
    integer(binding['seq'])
    if binding['seq'] < 1 or (source is not None and binding != source):
        raise ValueError('snapshot')
    p = obj['prefix']
    if p != '':
        prefix(p)
    if expected_prefix is not None and p != expected_prefix:
        raise ValueError('prefix chain')
    integer(obj['atoms'])
    integer(obj['addresses'])
    if terminal:
        if len(p) not in (0, 10) or not isinstance(obj['entries'], list) or not obj['entries']:
            raise ValueError('terminal')
        hs, ids = [], []
        for entry in obj['entries']:
            if not isinstance(entry, dict) or set(entry) != {'h', 'atoms'}:
                raise ValueError('entry')
            h = entry['h']
            if pub.leaf_key(h) != (p or pub.UNANCHORED):
                raise ValueError('placement')
            hs.append(h)
            if not isinstance(entry['atoms'], list) or not entry['atoms']:
                raise ValueError('atoms')
            ordering = []
            for atom in entry['atoms']:
                if not isinstance(atom, dict) or set(atom) != {'mid', 'sha256', 'href'}:
                    raise ValueError('atom')
                if not isinstance(atom['mid'], str) or not atom['mid'].startswith(pub.MID_PREFIX):
                    raise ValueError('mid')
                sha(atom['mid'][len(pub.MID_PREFIX):])
                href(atom['href'], atom['sha256'], True)
                ids.append(atom['sha256'])
                ordering.append((atom['mid'], atom['sha256']))
            if ordering != sorted(set(ordering)):
                raise ValueError('atom order')
        if hs != sorted(set(hs)) or len(ids) != len(set(ids)):
            raise ValueError('entry order/duplicates')
        counts = len(ids), len(hs)
    else:
        if len(p) not in (0, 2, 6) or not isinstance(obj['children'], dict):
            raise ValueError('branch')
        depth = {0: 2, 2: 6, 6: 10}[len(p)]
        descriptors = list(obj['children'].values())
        for child, desc in obj['children'].items():
            prefix(child)
            if len(child) != depth or not child.startswith(p):
                raise ValueError('child prefix')
            descriptor(desc)
        if 'unanchored' in obj:
            descriptor(obj['unanchored'])
            descriptors.append(obj['unanchored'])
        counts = tuple(sum(d[key] for d in descriptors) for key in ('atoms', 'addresses'))
        if p and not descriptors:
            raise ValueError('empty branch')
    if counts != (obj['atoms'], obj['addresses']):
        raise ValueError('counts')
    return obj
