"""Deterministic candidate vectors; run python3 tests/vectors.py from the checkout."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import hashlib
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from nairobidot.carrier import b64, from_atom

SEED = hashlib.sha256(b'nairobidot-clean-room-vectors').digest()
KEY = Ed25519PrivateKey.from_private_bytes(SEED)


def atom(index: int = 0, h: str = 'u3bu_23', **changes) -> dict:
    value = dict(v='punkti/0.6', t=index, h=h, x=f'opaque {index}', alg='ed25519',
                 pk=b64(KEY.public_key().public_bytes_raw()), refs=[], ext='', sig=b64(bytes(64)))
    value.update(changes)
    value['sig'] = b64(KEY.sign(from_atom(value).S))
    return value


def vectors() -> list[dict]:
    result = []
    for index, h in enumerate(('u3bu_23', 's00000000000_23', 's00000000001_23.025')):
        a = atom(index, h, refs=[{'target': 'future:00', 'rel': ''}], ext=b64(b'\x00\xff'))
        r = from_atom(a)
        result.append({'name': ('anchored', 'xy-scope', 'xyz-scope')[index],
                       'atom': a, 'C': r.C.hex(), 'S': r.S.hex(), 'MID': r.mid,
                       'address': r.address, 'R': b64(r.R), 'signature': a['sig']})
    return result


if __name__ == '__main__':
    print(json.dumps({'seed_hex': SEED.hex(), 'vectors': vectors()}, indent=2))
