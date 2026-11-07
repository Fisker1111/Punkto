import json
from pathlib import Path
import random
import unittest
from discovery.geohash import encode, encode_independent, decode


class GeoHashTests(unittest.TestCase):
    def test_vectors_and_independent_path(self):
        vectors = json.loads((Path(__file__).resolve().parents[1] / 'vectors/geohash-vectors.json').read_text())
        for vector in vectors:
            lat, lon, expected = vector['lat'], vector['lon'], vector['hash']
            with self.subTest(expected=expected):
                self.assertEqual(encode(lat, lon, len(expected)), expected)
                self.assertEqual(encode_independent(lat, lon, len(expected)), expected)
                cell = decode(expected)
                self.assertLessEqual(cell['lat_min'], lat)
                self.assertGreaterEqual(cell['lat_max'], lat)
                self.assertLessEqual(cell['lon_min'], lon)
                self.assertGreaterEqual(cell['lon_max'], lon)

    def test_random_agreement_and_roundtrip(self):
        rng = random.Random(28)
        for _ in range(500):
            lat, lon, precision = rng.uniform(-90, 90), rng.uniform(-180, 180), rng.randint(1, 12)
            actual = encode(lat, lon, precision)
            self.assertEqual(actual, encode_independent(lat, lon, precision))
            center = decode(actual)
            self.assertEqual(encode(center['lat'], center['lon'], precision), actual)

    def test_invalid(self):
        for args in [(91, 0, 6), (0, 181, 6), (float('nan'), 0, 6), (0, 0, 0), (0, 0, True)]:
            with self.assertRaises(ValueError):
                encode(*args)
        for p in ['', '..', 'abc', 'a' * 13]:
            with self.assertRaises(ValueError):
                decode(p)
