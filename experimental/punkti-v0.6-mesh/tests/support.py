import hashlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from carrier import ALPHABET, SIGN_DOMAIN, b64, canonical, record


def atom(i=0, h='gggh00000000_0', x=None, **changes):
    key = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(f'mesh-key-{i % 3}'.encode()).digest())
    a = dict(v='punkti/0.6', t=i, h=h, x=f'opaque-{i}' if x is None else x,
             alg='ed25519', pk=b64(key.public_key().public_bytes(
                 serialization.Encoding.Raw, serialization.PublicFormat.Raw)),
             refs=[], ext='', sig=b64(bytes(64)))
    a.update(changes)
    a['sig'] = b64(key.sign(SIGN_DOMAIN + canonical(a)))
    return a


def fixture(i=0, **kwargs):
    return record(atom(i, **kwargs))


def geo(z):
    return '0000000000_' + str(z)
