import json
from pathlib import Path
import unittest
from discovery.metrics import measure


class MetricsTests(unittest.TestCase):
    def test_real_http_and_file_counts(self):
        result = measure(sizes=(10, 100))
        evidence = json.loads((Path(__file__).resolve().parents[1] / 'evidence/metrics.json').read_text())
        self.assertEqual(result['fixture'], evidence['fixture'])
        self.assertEqual(result['http'], evidence['http'])
        self.assertEqual(result['synthetic'], evidence['synthetic'][:2])
        self.assertEqual(result['fixture']['discovery']['files'], 11)
        self.assertEqual(result['http']['unknown_discovery']['records'], 7)
        self.assertEqual(result['http']['known_discovery']['records'], 3)
        for scenario in ('unknown', 'known'):
            derived, frozen = (result['http'][scenario + '_' + method] for method in ('discovery', 'frozen'))
            self.assertLess(derived['requests'], frozen['requests'])
            self.assertGreater(derived['bytes'], 0)
            self.assertEqual(derived['records'], frozen['records'])
        self.assertGreater(result['synthetic'][1]['files'], result['synthetic'][0]['files'])
        self.assertGreater(result['synthetic'][1]['bytes'], result['synthetic'][0]['bytes'])

    def test_committed_evidence(self):
        path = Path(__file__).resolve().parents[1] / 'evidence/metrics.json'
        evidence = json.loads(path.read_text())
        self.assertEqual([row['atoms'] for row in evidence['synthetic']], [10, 100, 1000, 10000])
        for row in evidence['synthetic']:
            self.assertGreater(row['files'], row['atoms'])
            self.assertGreater(row['bytes'], row['files'])
