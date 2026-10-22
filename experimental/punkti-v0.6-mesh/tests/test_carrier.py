import hashlib
import json
import unittest
from support import atom, fixture, geo
from carrier import (SIGN_DOMAIN, ResourceLimit, State, b64, canonical,
                     decode, import_json, lp, record, validate)
from spatial import Subscription, altitude


class CarrierTests(unittest.TestCase):
    def test_framing_domains_and_determinism(self):
        a = atom(x='\x00未知e\u0301', refs=[{'target': 'future/v9:abcd', 'rel': '?!'}], ext=b64(b'\xff'))
        body = canonical(a)
        # Independent framing construction pins field order and domain literals.
        import base64
        fields = [a['v'].encode(), b'0', a['h'].encode(), a['x'].encode(), b'ed25519', base64.b64decode(a['pk'])]
        frame = lambda b: len(b).to_bytes(4, 'big') + b
        expected = b''.join(map(frame, fields)) + (1).to_bytes(4, 'big')
        expected += frame(b'future/v9:abcd') + frame(b'?!') + frame(b'\xff')
        self.assertEqual(body, expected)
        raw = record(a)
        self.assertEqual(raw, frame(expected) + frame(base64.b64decode(a['sig'])))
        self.assertEqual(decode(raw)[0], a)
        self.assertEqual(validate(raw).address, 'punkti/0.6:' + hashlib.sha256(b'PUNKTI-L3-MID\0' + expected).hexdigest())
        self.assertEqual(fixture(5), fixture(5))
        self.assertEqual(SIGN_DOMAIN, b'PUNKTI-L3-SIGN\0')

    def test_every_signed_field_bound(self):
        original = atom(refs=[dict(target='future:aa', rel='one'), dict(target='future:bb', rel='two')])
        changes = dict(t=1, h='gggj00000000', x='changed', pk=atom(1)['pk'],
                       refs=list(reversed(original['refs'])), ext=b64(b'changed'))
        for field, value in changes.items():
            with self.subTest(field=field):
                altered = dict(original, **{field: value})
                self.assertEqual(validate(record(altered)).state, State.PROVENANCE)
                self.assertNotEqual(validate(record(altered)).address, validate(record(original)).address)
        altered = dict(original, alg='ED25519')
        self.assertEqual(validate(record(altered)).state, State.ALGORITHM)
        self.assertNotEqual(validate(record(altered)).address, validate(record(original)).address)

    def test_json_strictness(self):
        good = json.dumps(atom()).encode()
        self.assertEqual(import_json(good), fixture())
        for raw in [good.replace(b'"t": 0', b'"t": 0.0'), good.replace(b'"t": 0', b'"t": 0e0'),
                    good.replace(b'"t": 0', b'"t": true'), good.replace(b'"t": 0', b'"t": -1'),
                    good.replace(b'"t": 0', b'"t": 9007199254740992'),
                    good.replace(b'"t": 0', b'"t": 0, "t": 0'),
                    good[:-1] + b', "extra": 0}', good.replace(b'opaque-0', b'\\ud800')]:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    import_json(raw)
        for change in [dict(pk='AB=='), dict(sig=''), dict(pk=b64(b'x')), dict(h='i'*12),
                       dict(refs=[dict(target='punkti/0.6:aa', rel='')]), dict(alg='é')]:
            with self.assertRaises(ValueError):
                record(dict(atom(), **change))

    def test_record_negative_vectors(self):
        raw = fixture()
        for bad in [b'', raw[:-1], raw + b'x', b'\xff'*4 + raw[4:]]:
            self.assertEqual(validate(bad).state, State.STRUCTURAL)
        body, sig = decode(raw)[1:]
        bad_body = body.replace(lp(b'0'), lp(b'00'), 1)
        self.assertEqual(validate(lp(bad_body) + lp(sig)).state, State.STRUCTURAL)
        self.assertEqual(validate(raw[:-1] + bytes([raw[-1] ^ 1])).state, State.PROVENANCE)
        with self.assertRaises(ResourceLimit):
            record(dict(atom(), x='a' * 1048576))

    def test_spatial_boundaries(self):
        scope = Subscription('gggh', 'gggj')
        self.assertTrue(scope.matches('gggh00000000'))
        self.assertFalse(scope.matches('gggj00000000'))
        self.assertFalse(scope.matches(''))
        self.assertTrue(Subscription().matches(''))
        h = geo(100)
        z = altitude(h)
        self.assertAlmostEqual(z, 100, delta=0.005)
        self.assertTrue(Subscription(z_min=z, z_max=z+1).matches(h))
        self.assertFalse(Subscription(z_max=z).matches(h))
        for args in [dict(h_lo='i'), dict(h_lo='z', h_hi='a'), dict(z_min=float('nan'))]:
            with self.assertRaises(ValueError):
                Subscription(**args)
