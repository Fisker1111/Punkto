"""Reset envelope/framing/provenance and deterministic vector checks."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import unittest

from vectors import atom, vectors
from nairobidot.carrier import (MAX_C, MAX_R, ResourceError, State, StructuralError,
                               b64, decode_record, dumps, from_atom, import_json,
                               lp, unb64, validate)


class CarrierTests(unittest.TestCase):
    def test_roundtrip_and_frozen_vectors(self):
        expected = json.loads((Path(__file__).parent / 'vectors.json').read_text())
        self.assertEqual(vectors(), expected['vectors'])
        for vector in vectors():
            rec = from_atom(vector['atom'])
            self.assertEqual(rec, decode_record(rec.R))
            self.assertEqual(validate(rec).state, State.VALID)
            self.assertEqual(rec.C.hex(), vector['C'])
            self.assertEqual(rec.S, b'PUNKTI-L3-SIGN\x00' + rec.C)
            self.assertEqual(rec.mid, hashlib.sha256(b'PUNKTI-L3-MID\x00' + rec.C).hexdigest())
            original = json.dumps(vector['atom'], indent=3).encode()
            imported = import_json(original)
            self.assertEqual(imported.original_json, original)
            self.assertEqual(imported.R, rec.R)

    def test_json_negative_vectors(self):
        a = atom()
        raw = json.dumps(a)
        cases = []
        cases.extend([raw[:-1] + ', "x":"duplicate"}', raw[:-1] + ', "extra":0}'])
        for spelling in ('0.0', '0e0', '-0', '-1', '9007199254740992', 'true', '"0"', 'NaN', '01'):
            cases.append(raw.replace('"t": 0', '"t": ' + spelling))
        for data in cases:
            with self.subTest(data=data):
                self.assertEqual(validate(data).state, State.STRUCTURAL)

    def test_field_and_unicode_checks(self):
        for field, value in [('v', 'punkti/0.7'), ('x', '\ud800'), ('h', 'a' * 12),
                             ('h', '0'), ('pk', ''), ('sig', ''), ('alg', ''),
                             ('alg', 'é'), ('alg', 'a' * 129), ('refs', {}),
                             ('refs', [{'target': 'future:0', 'rel': ''}]),
                             ('refs', [{'target': 'punkti/0.6:00', 'rel': ''}]),
                             ('refs', [{'target': 'future:00', 'rel': '', 'a': 1}]),
                             ('pk', b64(bytes(31))), ('sig', b64(bytes(63)))]:
            with self.subTest(field=field, value=value):
                a = atom()
                a[field] = value
                self.assertEqual(validate(a).state, State.STRUCTURAL)
        a = atom(x='e\u0301\x00雪', refs=[{'target': 'future:ab', 'rel': 'unknown\x00'}])
        self.assertEqual(validate(a).state, State.VALID)
        b = copy.deepcopy(a)
        b['x'] = 'é\x00雪'
        self.assertNotEqual(from_atom(a).mid, from_atom(b).mid)

    def test_base64(self):
        for value in ('Zg', 'Zg=', 'Zg===', 'Zh==', 'Zg==\n', 'Zg== ', '-w==', 'é', '===='):
            with self.subTest(value=value), self.assertRaises(StructuralError):
                unb64(value)
        self.assertEqual(unb64('Zg=='), b'f')
        self.assertEqual(unb64(''), b'')

    def test_framing_negative_vectors(self):
        r = from_atom(atom())
        for raw in (r.R[:-1], r.R + b'\0', b'', b'\xff' * 4, lp(r.C + b'\0') + lp(bytes(64))):
            with self.subTest(raw=raw[:8]), self.assertRaises(StructuralError):
                decode_record(raw)
        body = r.C.replace(lp(b'0'), lp(b'00'), 1)
        with self.assertRaises(StructuralError):
            decode_record(lp(body) + lp(bytes(64)))
        body = r.C.replace(lp(b'0'), lp(b'0e0'), 1)
        with self.assertRaises(StructuralError):
            decode_record(lp(body) + lp(bytes(64)))
        # Overflowing declared C length must fail without allocation.
        with self.assertRaises(StructuralError):
            decode_record(struct.pack('>I', 2**32 - 1) + r.R[4:])

    def test_limits(self):
        a = atom()
        a['refs'] = [{'target': 'future:00', 'rel': ''}] * 257
        with self.assertRaises(ResourceError):
            from_atom(a)
        a['refs'] = [{'target': 'future:00', 'rel': 'é' * 513}]
        with self.assertRaises(ResourceError):
            from_atom(a)
        a = atom()
        overhead = len(from_atom(a).C) - len(a['x'])
        a['x'] = 'x' * (MAX_C - overhead)
        self.assertEqual(len(from_atom(a).C), MAX_C)
        a['x'] += 'x'
        with self.assertRaises(ResourceError):
            from_atom(a)
        with self.assertRaises(ResourceError):
            decode_record(b'0' * (MAX_R + 1))
        a = atom(refs=[{'target': 'future:00', 'rel': 'é' * 512}] * 256)
        self.assertEqual(validate(a).state, State.VALID)

    def test_mutation_key_substitution_and_algorithm_dispatch(self):
        original = atom(refs=[{'target': 'future:00', 'rel': 'opaque'},
                             {'target': 'future:01', 'rel': ''}], ext=b64(b'abc'))
        for field, value in [('t', 1), ('h', '000000000000'), ('x', 'changed'),
                             ('pk', b64(bytes(range(32)))), ('ext', b64(b'abd')),
                             ('refs', list(reversed(original['refs'])))]:
            a = copy.deepcopy(original)
            a[field] = value
            with self.subTest(field=field):
                self.assertEqual(validate(a).state, State.PROVENANCE)
                self.assertNotEqual(from_atom(a).address, from_atom(original).address)
        a = copy.deepcopy(original)
        a['sig'] = b64(bytes(64))
        self.assertEqual(from_atom(a).address, from_atom(original).address)
        self.assertEqual(validate(a).state, State.PROVENANCE)
        a['alg'], a['pk'], a['sig'] = 'Ed25519', b64(b'k'), b64(b's')
        self.assertEqual(validate(a).state, State.ALGORITHM)
        a['sig'] = ''
        self.assertEqual(validate(a).state, State.STRUCTURAL)
