"""Run as python -m punkto_atoms.make_atom lat lon alt t message fp.

A fresh Ed25519 key is generated per invocation; no private key is persisted.
"""
import argparse
import base64
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core.geohash3d import encode
from .atoms_core import compute_mid, signing_input, validate_atom


def make_atom(lat, lon, alt, t, message, fp, private_key=None):
    key = private_key or Ed25519PrivateKey.generate()
    atom = dict(t=t, h=encode(lat, lon, alt), x=message, fp=fp)
    atom['sig'] = base64.b64encode(key.sign(signing_input(atom))).decode('ascii')
    atom['mid'] = compute_mid(atom)
    validate_atom(atom)
    return atom


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('lat', 'lon', 'alt'):
        parser.add_argument(name, type=float)
    parser.add_argument('t', type=int)
    parser.add_argument('message')
    parser.add_argument('fp')
    args = parser.parse_args()
    print(json.dumps(make_atom(**vars(args)), ensure_ascii=False))


if __name__ == '__main__':
    main()
