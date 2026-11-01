#!/usr/bin/env python3
"""Offline custody CLI checks with carrier-generated signed records."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'punkti_node'))
import carrier


class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root, self.mid = self.record('root', [])
        self.reply, _ = self.record('reply', [{'target': self.mid, 'rel': 'reply'}])

    def record(self, name, refs):
        key = Ed25519PrivateKey.generate()
        pk = key.public_key().public_bytes(serialization.Encoding.Raw,
                                          serialization.PublicFormat.Raw)
        atom = dict(v=carrier.VERSION, t=0, h='s00000000000_0', x=name,
                    alg='ed25519', pk=carrier.b64(pk), refs=refs, ext='',
                    sig=carrier.b64(bytes(64)))
        body = carrier.canonical(atom)
        atom['sig'] = carrier.b64(key.sign(carrier.SIGN_DOMAIN + body))
        raw = carrier.record(atom)
        self.assertEqual(carrier.validate(raw).state.value, 'VALID')
        path = Path(self.directory.name) / name
        path.write_bytes(raw)
        return path, carrier.VERSION + ':' + hashlib.sha256(carrier.MID_DOMAIN + body).hexdigest()

    def run_cli(self, *args):
        process = subprocess.run([sys.executable, str(ROOT / 'scripts/qa/custody_verify.py'),
                                  *map(str, args)], capture_output=True, text=True, cwd=ROOT)
        return process, [json.loads(line) for line in process.stdout.splitlines()]

    def test_root(self):
        process, rows = self.run_cli('--file', self.root, '--expect-mid', self.mid,
                                    '--expect-h', 's00000000000_0', '--expect-sha256',
                                    hashlib.sha256(self.root.read_bytes()).hexdigest())
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(rows[0]['ok'])
        self.assertEqual(rows[0]['state'], 'VALID')
        self.assertEqual(rows[0]['ed25519'], 'VALID')
        self.assertTrue(rows[0]['canonical_body'])

    def test_reply(self):
        process, rows = self.run_cli('--file', self.reply, '--expect-reply-of', self.mid)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(rows[0]['expectations']['reply_of'])

    def test_corruption(self):
        raw = bytearray(self.root.read_bytes())
        raw[-1] ^= 1
        self.root.write_bytes(raw)
        process, rows = self.run_cli('--file', self.root)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(rows[0]['ed25519'], 'INVALID')

    def test_mismatches(self):
        for option, value, path in [('--expect-sha256', '0' * 64, self.root),
                                    ('--expect-h', 's00000000000_1', self.root),
                                    ('--expect-mid', carrier.VERSION + ':' + '0' * 64, self.root),
                                    ('--expect-reply-of', carrier.VERSION + ':' + '0' * 64, self.reply)]:
            with self.subTest(option=option):
                process, rows = self.run_cli('--file', path, option, value)
                self.assertEqual(process.returncode, 1)
                self.assertFalse(rows[0]['ok'])

    def test_duplicate_reply(self):
        path, _ = self.record('duplicate', [{'target': self.mid, 'rel': 'reply'}] * 2)
        process, rows = self.run_cli('--file', path, '--expect-reply-of', self.mid)
        self.assertEqual(process.returncode, 1)
        self.assertFalse(rows[0]['expectations']['reply_of'])

    def test_continue_and_order(self):
        self.root.write_bytes(b'bad framing')
        process, rows = self.run_cli('--file', self.root, '--file', self.reply)
        self.assertEqual(process.returncode, 1)
        self.assertEqual([row['source'] for row in rows], [str(self.root), str(self.reply)])
        self.assertTrue(rows[1]['ok'])

    def test_missing_file(self):
        process, rows = self.run_cli('--file', Path(self.directory.name) / 'missing', self.root)
        self.assertEqual(process.returncode, 1)
        self.assertIn('error', rows[0])
        self.assertTrue(rows[1]['ok'])

    def test_usage(self):
        for args in [[], ['--file', self.root, self.reply, '--expect-sha256', '0' * 64]]:
            process, rows = self.run_cli(*args)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(rows, [])


if __name__ == '__main__':
    unittest.main()
