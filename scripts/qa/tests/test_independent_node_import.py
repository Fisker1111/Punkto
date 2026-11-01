"""Offline CLI transport tests; all HTTP is served on loopback."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'scripts/qa/independent_node_import.py'
RAW = b'\x00raw\xff\r\nrecord\x00'
SHA = hashlib.sha256(RAW).hexdigest()
MID = 'punkti/0.6:' + 'a' * 64


class ImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                cls.headers = dict(self.headers)
                cls.path = self.path
                self.send_response(cls.status)
                self.send_header('Content-Length', str(len(cls.body)))
                self.end_headers()
                self.wfile.write(cls.body)

            def do_POST(self):
                cls.headers = dict(self.headers)
                cls.path = self.path
                cls.sent = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                self.send_response(cls.status)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(cls.response)

        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.file = Path(self.directory.name) / 'record'
        type(self).body = RAW
        type(self).status = 200
        type(self).sent = None
        type(self).response = json.dumps(dict(results=[dict(admitted=True, sha256=SHA,
                                                             address=MID)])).encode()

    def cli(self, *args, isolated=False):
        env = {k: v for k, v in os.environ.items() if not k.lower().endswith('_proxy')}
        env['NO_PROXY'] = '*'
        return subprocess.run([sys.executable, *(['-S'] if isolated else []), str(SCRIPT),
                               *map(str, args)], capture_output=True, text=True, env=env,
                              timeout=10)

    def fetch(self, *extra):
        return self.cli('fetch', '--url', self.base + '/raw', '--out', self.file, *extra)

    def submit(self, *extra, isolated=False):
        self.file.write_bytes(RAW)
        return self.cli('submit', '--base', self.base, '--file', self.file,
                        *extra, isolated=isolated)

    def check(self, size=len(RAW)):
        return self.cli('check', '--base', self.base, '--sha256', SHA,
                        '--expect-bytes', size)

    def test_fetch_exact(self):
        result = self.fetch('--sha256', SHA)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.file.read_bytes(), RAW)
        self.assertEqual(json.loads(result.stdout)['sha256'], SHA)
        self.assertEqual(self.headers['Accept-Encoding'], 'identity')
        self.assertEqual(list(self.file.parent.iterdir()), [self.file])

    def test_fetch_digest_mismatch(self):
        self.assertNotEqual(self.fetch('--sha256', '0' * 64).returncode, 0)
        self.assertEqual(list(self.file.parent.iterdir()), [])

    def test_fetch_no_clobber(self):
        self.file.write_bytes(b'existing')
        self.assertNotEqual(self.fetch().returncode, 0)
        self.assertEqual(self.file.read_bytes(), b'existing')

    def test_fetch_force(self):
        self.file.write_bytes(b'existing')
        self.assertEqual(self.fetch('--force').returncode, 0)
        self.assertEqual(self.file.read_bytes(), RAW)

    def test_fetch_force_mismatch_preserves_existing(self):
        self.file.write_bytes(b'existing')
        self.assertNotEqual(self.fetch('--force', '--sha256', '0' * 64).returncode, 0)
        self.assertEqual(self.file.read_bytes(), b'existing')
        self.assertEqual(list(self.file.parent.iterdir()), [self.file])

    def test_fetch_404(self):
        type(self).status = 404
        self.assertNotEqual(self.fetch().returncode, 0)
        self.assertFalse(self.file.exists())

    def test_submit_exact_stdlib_only(self):
        result = self.submit('--address', MID, '--sha256', SHA, isolated=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.sent, dict(records=[dict(record=base64.b64encode(RAW).decode(),
                                                       sha256=SHA, address=MID)]))
        self.assertEqual(self.path, '/submit')
        self.assertEqual(self.headers['Content-Type'], 'application/json')
        self.assertIs(json.loads(result.stdout)['results'][0]['admitted'], True)

    def test_submit_rejected(self):
        type(self).response = b'{"results":[{"admitted":false}]}'
        self.assertNotEqual(self.submit('--address', MID).returncode, 0)

    def test_submit_http_rejected(self):
        type(self).status = 429
        self.assertNotEqual(self.submit('--address', MID).returncode, 0)

    def test_submit_duplicate_is_not_admission(self):
        type(self).response = b'{"results":[{"admitted":false,"duplicate":true}]}'
        self.assertNotEqual(self.submit('--address', MID).returncode, 0)

    def test_submit_unrelated_admission(self):
        type(self).response = json.dumps(dict(results=[dict(admitted=True, address=MID,
                                                            sha256='0' * 64)])).encode()
        self.assertNotEqual(self.submit('--address', MID).returncode, 0)

    def test_submit_malformed_response(self):
        type(self).response = b'not JSON'
        self.assertNotEqual(self.submit('--address', MID).returncode, 0)

    def test_submit_invalid_response_shape(self):
        type(self).response = b'[]'
        self.assertNotEqual(self.submit('--address', MID).returncode, 0)

    def test_submit_local_digest_mismatch(self):
        self.assertNotEqual(self.submit('--address', MID, '--sha256', '0' * 64).returncode, 0)
        self.assertIsNone(self.sent)

    def test_submit_requires_address_without_carrier_dependencies(self):
        result = self.submit(isolated=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--address', result.stderr)
        self.assertIsNone(self.sent)

    def test_check_exact(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)
        row = json.loads(result.stdout)
        self.assertEqual((row['status'], row['bytes'], row['sha256']), (200, len(RAW), SHA))
        self.assertEqual(self.path, '/publication/records/' + SHA[:2] + '/' + SHA)

    def test_check_wrong_length(self):
        self.assertNotEqual(self.check(len(RAW) + 1).returncode, 0)

    def test_check_wrong_digest(self):
        type(self).body = b'x' * len(RAW)
        self.assertNotEqual(self.check().returncode, 0)

    def test_check_404(self):
        type(self).status = 404
        self.assertNotEqual(self.check().returncode, 0)

    def test_invalid_digest_argument(self):
        result = self.fetch('--sha256', '../bad')
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.file.exists())

class SeedTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.file = self.directory / 'record'
        self.file.write_bytes(RAW)
        self.data = self.directory / 'data'
        self.target = self.data / 'atoms.jsonl'

    def seed(self, *extra, address=MID):
        args = [sys.executable, str(SCRIPT), 'seed', '--data-dir', str(self.data),
                '--file', str(self.file)]
        if address is not None:
            args += ['--address', address]
        return subprocess.run(args + list(extra), capture_output=True, text=True, timeout=10)

    def test_seed_exact_wrapper(self):
        result = self.seed('--sha256', SHA)
        self.assertEqual(result.returncode, 0, result.stderr)
        line = self.target.read_bytes()
        wrapper = dict(address=MID, sha256=SHA, record=base64.b64encode(RAW).decode())
        self.assertEqual(line, (json.dumps(wrapper, separators=(',', ':')) + '\n').encode())
        self.assertEqual(base64.b64decode(json.loads(line)['record']), RAW)
        self.assertEqual(json.loads(result.stdout), dict(file=str(self.target), appended=False,
                                                        bytes=len(RAW), sha256=SHA))
        self.assertEqual(list(self.data.iterdir()), [self.target])

    def test_seed_refuses_existing(self):
        self.data.mkdir()
        self.target.write_bytes(b'existing\n')
        self.assertNotEqual(self.seed().returncode, 0)
        self.assertEqual(self.target.read_bytes(), b'existing\n')

    def test_seed_append_preserves_existing(self):
        self.data.mkdir()
        existing = b'{ "untouched" : true }\r\n'
        self.target.write_bytes(existing)
        result = self.seed('--append')
        self.assertEqual(result.returncode, 0, result.stderr)
        added = self.target.read_bytes()[len(existing):]
        self.assertTrue(self.target.read_bytes().startswith(existing))
        self.assertEqual(added.count(b'\n'), 1)
        self.assertTrue(added.endswith(b'\n'))
        self.assertEqual(base64.b64decode(json.loads(added)['record']), RAW)
        self.assertIs(json.loads(result.stdout)['appended'], True)

    def test_seed_mismatch_writes_nothing(self):
        self.assertNotEqual(self.seed('--sha256', '0' * 64).returncode, 0)
        self.assertFalse(self.data.exists())

    def test_seed_append_mismatch_preserves_existing(self):
        self.data.mkdir()
        self.target.write_bytes(b'existing\n')
        self.assertNotEqual(self.seed('--append', '--sha256', '0' * 64).returncode, 0)
        self.assertEqual(self.target.read_bytes(), b'existing\n')

    def test_seed_derives_address(self):
        from punkti_node import carrier
        vectors = json.loads((ROOT / 'pwa/punkti/test-vectors/publication-vectors.json').read_text())
        raw = next(bytes.fromhex(case['hex']) for vector in vectors['vectors']
                   for case in vector.get('cases', []) if case.get('kind') == 'record'
                   and carrier.validate(bytes.fromhex(case['hex'])).state == carrier.State.VALID)
        self.file.write_bytes(raw)
        result = self.seed(address=None)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.target.read_bytes())['address'], carrier.validate(raw).address)

    def test_seed_append_creates(self):
        result = self.seed('--append')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.target.read_bytes().splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
