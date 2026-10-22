"""Real HTTP coverage of optional UI hosting and deployment route aliases."""
import http.client
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import quote
from .config import load_config
from .store import PersistentNode
from .web import StaticWeb


class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.web = self.root / 'web'
        self.web.mkdir()
        for name in ['index.html', 'app.js', 'module.mjs', 'manifest.json', 'icon.png', 'style.css', 'font.woff2']:
            (self.web / name).write_text(name)
        (self.root / 'secret').write_text('secret')
        (self.web / 'escape').symlink_to(self.root / 'secret')
        (self.web / 'dir').mkdir()
        (self.web / 'dir/index.html').write_text('directory')
        self.config = load_config(environ={'PUNKTO_WEB_ROOT': str(self.web), 'PUNKTO_DATA_DIR': str(self.root / 'data')})
        self.node = PersistentNode(self.config).start(0, '127.0.0.1')
        self.node.web = StaticWeb(self.web, True)
        self.addCleanup(self.node.durable.close)
        self.addCleanup(self.node.stop)

    def get(self, path, method='GET', body=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.node.server.server_port)
        conn.request(method, path, body=json.dumps(body) if body else None)
        response = conn.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        conn.close()
        return result

    def test_static_and_headers(self):
        for path, mime in [('/', 'text/html'), ('/app.js', 'text/javascript'), ('/module.mjs', 'text/javascript'), ('/manifest.json', 'application/json'), ('/icon.png', 'image/png'), ('/style.css', 'text/css'), ('/font.woff2', 'font/woff2')]:
            status, headers, raw = self.get(path)
            self.assertEqual(status, 200)
            self.assertEqual(headers['Content-Type'], mime)
            self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
            self.assertIn('max-age=3600' if path.endswith(('.png', '.css', '.woff2')) else 'no-store', headers['Cache-Control'])
            self.assertTrue(raw)
        status, headers, raw = self.get('/app.js', 'HEAD')
        self.assertEqual(status, 200)
        self.assertEqual(raw, b'')
        self.assertEqual(headers['Content-Length'], '6')
        self.assertEqual(self.get('/dir/')[2], b'directory')
        self.assertEqual(self.get('/p/exact-link')[2], b'index.html')
        # SPA fallback must not turn unknown API-like paths into HTML 200s.
        for path in ['/atom', '/feed', '/latest', '/atoms/v1/info', '/missing']:
            self.assertEqual(self.get(path)[0], 404, path)
        self.node.web.spa_fallback = False
        self.assertEqual(self.get('/missing')[0], 404)

    def test_confinement(self):
        for path in ['/../secret', '/%2e%2e/secret', '/%252e%252e/secret', '/escape', '/%2fetc/passwd', '/dir/../../secret', '/missing.js', '/%00']:
            self.assertIn(self.get(path)[0], (400, 404), path)
        for path in ['/api/missing', '/api/missing.js', '/api']:
            self.assertEqual(self.get(path)[0], 400)

    def test_aliases(self):
        for path in ['/hello', '/health', '/ready', '/node/info', '/pull?q=' + quote('{"limit":1}')]:
            native = self.get(path)
            alias = self.get('/api' + path)
            self.assertEqual(native[0], alias[0])
            a, b = json.loads(native[2]), json.loads(alias[2])
            a.pop('metrics', None); b.pop('metrics', None)
            self.assertEqual(a, b)
        for path, body in [('/push', {'records': []}), ('/sync', {'peer': 'http://unconfigured.example', 'phase': 'push'})]:
            native = self.get(path, 'POST', body)
            alias = self.get('/api' + path, 'POST', body)
            self.assertEqual((native[0], native[2]), (alias[0], alias[2]))

    def test_disabled_and_config(self):
        self.node.web = None
        self.assertEqual(self.get('/')[0], 400)
        for value in ['0', 'false', 'no', 'off']:
            self.assertFalse(load_config(environ={'PUNKTO_WEB_ENABLED': value})['web']['enabled'])
        for root in ['relative', str(self.root / 'missing')]:
            with self.assertRaisesRegex(ValueError, 'web.root'):
                load_config(environ={'PUNKTO_WEB_ROOT': root})


if __name__ == '__main__':
    unittest.main()
