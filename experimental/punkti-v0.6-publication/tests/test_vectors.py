import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from support import *


class Vectors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'vectors.json').read_text())

    def exercise(self, vector):
        for case in vector['cases']:
            for implementation in READERS:
                with self.subTest(vector=vector['id'], case=case['name'], implementation=implementation.__module__):
                    with tempfile.TemporaryDirectory() as tmp:
                        path = Path(tmp) / 'pub'
                        reader = implementation(packs=case.get('packs', False))
                        source = self.data['fixtures'][case['source']]
                        materialize(self.data['fixtures'].get(case.get('prime'), source), path)
                        with StaticSource(path) as server:
                            if 'prime' in case:
                                reader.read_publication(server.url)
                                shutil.rmtree(path)
                                materialize(source, path)
                            want = case['expected']
                            scope = o.Subscription(**case.get('scope', {}))
                            if want['error_class']:
                                before = copy.deepcopy(reader.checkpoints)
                                with self.assertRaises(ValueError) as error:
                                    reader.read_publication(server.url, scope)
                                self.assertEqual(error.exception.error_class, want['error_class'])
                                self.assertEqual(error.exception.reason, want['reason'])
                                self.assertEqual(reader.checkpoints, before)
                            else:
                                result = reader.read_publication(server.url, scope)
                                self.assertEqual(result['rejected'], want['rejected'])
                                self.assertEqual(result['valid'], want['valid_count'])
                                self.assertEqual(result['candidates'], want['candidate_count'])
                                self.assertEqual(result['admitted'], want['admitted'])
                                self.assertEqual(result['head'], want['head'])
                                self.assertEqual(result['seq'], want['seq'])
                                if case.get('retry'):
                                    self.assertEqual(reader.read_publication(server.url, scope)['admitted'], 0)
                            self.assertEqual({k: o.digest(v) for k, v in reader.store.valid.items()}, want['valid'])
                            self.assertEqual({k: v.hex() for k, v in reader.store.candidates.items()}, want['candidates'])
                            for sha in case.get('forbidden_records', []):
                                self.assertNotIn(o.object_path('records', sha), reader.paths)
                            for sha in case.get('required_records', []):
                                self.assertIn(o.object_path('records', sha), reader.paths)
        for item in vector.get('records', []):
            raw = bytes.fromhex(item['hex'])
            self.assertEqual(o.digest(raw), item['sha256'])
            atom, body, _ = o.carrier.decode(raw)
            self.assertEqual(o.carrier.record(atom), raw)
            self.assertEqual(o.MID_PREFIX + o.digest(o.carrier.MID_DOMAIN + body), item['mid'])
        for item in vector.get('variants', []):
            raw = bytes.fromhex(item['hex'])
            obs = o.carrier.validate(raw)
            self.assertEqual((o.digest(raw), obs.address, obs.state.value),
                             (item['sha256'], item['mid'], item['state']))


for i in range(1, 10):
    def test(self, i=i):
        self.exercise(next(v for v in self.data['vectors'] if v['id'] == f'V{i}'))
    setattr(Vectors, f'test_V{i}', test)
