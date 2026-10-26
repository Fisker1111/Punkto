"""Run every published vector independently on each subprocess implementation."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from vector_suite import HOME, Runner

DOCUMENT = json.loads((HOME / 'vectors.json').read_text())
# Explicit inventory prevents silently generating tests for unintended/missing IDs.
IDS = tuple('V' + str(i) for i in range(1, 14))
EXERCISED = set()


class Vectors(unittest.TestCase):
    def test_zz_inventory_exercised(self):
        ids = [v['id'] for v in DOCUMENT['vectors']]
        self.assertGreaterEqual(len(ids), 8)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(IDS))
        self.assertEqual(EXERCISED, {(kind, id) for kind in ('ref', 'nb') for id in ids})


def test_for(id):
    def test(self):
        v = next(v for v in DOCUMENT['vectors'] if v['id'] == id)
        outputs = {}
        for kind in ('ref', 'nb'):
            with self.subTest(implementation=kind, vector=id):
                outputs[kind] = Runner(kind, DOCUMENT).run(v)
                EXERCISED.add((kind, id))
        self.assertEqual(set(outputs), {'ref', 'nb'})
        self.assertEqual(outputs['ref'], outputs['nb'], id + ': normative equality')
    return test


for id in IDS:
    setattr(Vectors, 'test_' + id.zfill(3), test_for(id))

if __name__ == '__main__':
    unittest.main()
