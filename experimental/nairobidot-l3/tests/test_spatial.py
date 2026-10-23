"""Mesh provisional altitude and exact endpoint semantics."""
import unittest
from nairobidot.carrier import ALPHABET, StructuralError
from nairobidot.spatial import altitude, matches, normalize, subscribed


def encode_z(z: int) -> str:
    bits = ''.join('00' + bit for bit in f'{z:020b}')
    return ''.join(ALPHABET[int(bits[i:i+5], 2)] for i in range(0, 60, 5))


class SpatialTests(unittest.TestCase):
    def test_altitude_bit_order_and_centers(self):
        for z in (0, 1, 2, 2**19, 2**20 - 1):
            self.assertEqual(altitude(encode_z(z)), -500 + (z + .5) * 9000 / 2**20)
        self.assertEqual(altitude('s00000000000'), altitude('000000000000'))
        self.assertEqual(altitude('s00000000001'), altitude(encode_z(1)))

    def test_scopes(self):
        h = 'gggh00000000'
        self.assertTrue(matches(h, {'h_lo': 'gggh', 'h_hi': 'gggj'}))
        self.assertFalse(matches('gggj00000000', {'h_hi': 'gggj'}))
        self.assertFalse(matches('ggggzzzzzzzz', {'h_lo': 'gggh'}))
        self.assertTrue(matches('', {}))
        self.assertTrue(matches(None, normalize({})))
        for scope in ({'h_lo': '0'}, {'h_hi': 'z'}, {'z_min': -1000}, {'z_max': 9000}):
            self.assertFalse(matches('', scope))
            self.assertFalse(matches(None, scope))
        z = altitude(h)
        self.assertTrue(matches(h, {'z_min': z, 'z_max': z + 1}))
        self.assertFalse(matches(h, {'z_max': z}))
        self.assertFalse(subscribed(h, []))
        self.assertTrue(subscribed(h, [{'h_hi': '0'}, {'h_lo': 'g'}]))
        with self.assertRaises(StructuralError):
            matches(h, {'h_lo': 'z', 'h_hi': '0'})

    def test_bad_scopes(self):
        for s in ({'h_lo': 'g', 'h_hi': 'g'}, {'h_lo': 'z', 'h_hi': '0'},
                  {'z_min': 1, 'z_max': 1}, {'z_min': 1, 'z_max': -1}, {'h_lo': ''}, {'h_hi': 'i'}, {'z_min': True}, {'z_max': float('inf')},
                  {'z_min': float('nan')}, {'z_min': 10**1000}, {'x': ''}, []):
            with self.subTest(scope=s), self.assertRaises(StructuralError):
                normalize(s)
