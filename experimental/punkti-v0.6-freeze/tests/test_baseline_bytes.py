"""Pin hardening aea705e bytes independently of regenerated freeze vectors."""
import base64
import hashlib
import json
import unittest
import subprocess
import sys

from vector_suite import HOME, spec, b64

GOLDEN = json.loads((HOME / 'golden_base.json').read_text())


# The captured baseline signs even the future-algorithm fixture. The vector RPC
# intentionally uses a zero signature for unknown algorithms, so mint in an
# isolated process with each carrier directly, retaining that baseline convention.
MINT = r"""
import sys, json, hashlib, base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
sys.path.insert(0, sys.argv[1])
if sys.argv[2] == 'ref':
    import carrier as c
else:
    from nairobidot import carrier as c
s = json.load(sys.stdin)
b64 = lambda b: base64.b64encode(b).decode('ascii')
k = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(s.pop('seed').encode()).digest())
a = dict(s, v='punkti/0.6', pk=b64(k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)), sig=b64(bytes(64)))
C = c.canonical(a) if sys.argv[2] == 'ref' else c.canonical_body(a)
a['sig'] = b64(k.sign(b'PUNKTI-L3-SIGN\0' + C))
R = c.record(a) if sys.argv[2] == 'ref' else c.from_atom(a).R
v = c.validate(R)
address = v.address if sys.argv[2] == 'ref' else v.record.address
decoded = c.decode(R)[0] if sys.argv[2] == 'ref' else c.decode_record(R).atom
print(json.dumps(dict(C=C.hex(), R=b64(R), sig=a['sig'], state=v.state.value,
                     address=address, MID=address.split(':')[1],
                     sha256=hashlib.sha256(R).hexdigest(), atom=decoded)))
"""


class BaselineBytes(unittest.TestCase):
    def check_fixture(self, name, inputs):
        expected = GOLDEN[name]
        for kind in ('ref', 'nb'):
            with self.subTest(implementation=kind):
                folder = 'punkti-v0.6-mesh' if kind == 'ref' else 'nairobidot-l3'
                result = subprocess.run([sys.executable, '-c', MINT, str(HOME.parent / folder / 'src'), kind],
                                        input=json.dumps(inputs), text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                actual = json.loads(result.stdout)
                for field in ('C', 'R', 'sig', 'state', 'address'):
                    self.assertEqual(actual[field], expected[field], field)
                self.assertEqual(actual['MID'], expected['address'].split(':')[1])
                raw = base64.b64decode(actual['R'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected['sha256_R'])
                self.assertEqual(actual['sha256'], expected['sha256_R'])
                length = int.from_bytes(raw[:4], 'big')
                self.assertEqual(raw[4:4+length], bytes.fromhex(expected['C']))
                sig_start = 4 + length
                sig_length = int.from_bytes(raw[sig_start:sig_start+4], 'big')
                self.assertEqual(len(raw), sig_start + 4 + sig_length)
                self.assertEqual(raw[sig_start+4:], base64.b64decode(expected['sig']))
                decoded = actual
                self.assertEqual(decoded['atom']['x'].encode('utf-8'), expected['x'].encode('utf-8'))
                self.assertEqual(base64.b64decode(decoded['atom']['ext']), base64.b64decode(expected['ext']))

    def test_canonical(self):
        self.check_fixture('canonical', spec())

    def test_zero(self):
        self.check_fixture('zero', spec(t=0))

    def test_opaque_l4(self):
        self.check_fixture('opaque_l4', spec(alg='future-signature', x='opaque\0 🌍 e\u0301',
                                             ext=b64(b'\xff\0opaque')))
