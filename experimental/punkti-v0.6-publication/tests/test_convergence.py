import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from support import *


class Convergence(unittest.TestCase):
    def test_static_only_stopped_publishers_separate_readers(self):
        for packs in (False, True):
            with self.subTest(packs=packs), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                worker = ROOT / 'scripts/worker.py'
                seed_a = [fixture(200, ''), fixture(201, 'u4pruydqqv_-18')]
                seed_b = [fixture(202, 'ezs42_23.025'), fixture(203, '0000_0')]
                def run(operation, implementation, location, records=None):
                    args = [sys.executable, str(worker), operation, implementation, str(location)]
                    if packs:
                        args.append('--packs')
                    if records is not None:
                        input_path = tmp / 'input.json'
                        input_path.write_text(json.dumps([r.hex() for r in records]))
                        args.extend(['--input', str(input_path)])
                    process = subprocess.run(args, capture_output=True, text=True, timeout=30)
                    self.assertEqual(process.returncode, 0, process.stderr)
                    return json.loads(process.stdout)
                # subprocess.run has waited: both publisher processes are stopped.
                run('publish', 'reference', tmp / 'a', seed_a)
                run('publish', 'independent', tmp / 'b', seed_b)
                with StaticSource(tmp / 'a') as a, StaticSource(tmp / 'b') as b:
                    at_b = run('read', 'independent', a.url)
                    at_a = run('read', 'reference', b.url)
                    self.assertEqual(at_a['result']['valid'], 2)
                    self.assertEqual(at_b['result']['valid'], 2)
                    union_a = seed_a + [bytes.fromhex(r) for r in at_a['valid'].values()]
                    union_b = seed_b + [bytes.fromhex(r) for r in at_b['valid'].values()]
                    run('publish', 'reference', tmp / 'a', union_a)
                    run('publish', 'independent', tmp / 'b', union_b)
                    final_a = run('read', 'reference', b.url)
                    final_b = run('read', 'independent', a.url)
                    self.assertEqual(final_a['valid'], final_b['valid'])
                    self.assertEqual(len(final_a['valid']), 4)
                    expected = {o.carrier.validate(r).address: r.hex() for r in seed_a + seed_b}
                    self.assertEqual(final_a['valid'], expected)
                    for path in a.paths + b.paths:
                        self.assertTrue(path == '/root.json' or path.startswith(('/manifests/', '/h/', '/records/', '/segments/')))
                    print(f'STATIC CONVERGENCE packs={packs}: publishers exited; separate readers; 4 exact records; GETs={a.request_count + b.request_count}')
