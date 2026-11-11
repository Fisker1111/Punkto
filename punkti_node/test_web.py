"""Real HTTP coverage of optional UI hosting and deployment route aliases."""
import gzip
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
        self.publication = self.root / 'data' / 'publication'
        self.publication.mkdir(parents=True, exist_ok=True)
        (self.publication / 'root.json').write_text('{"head":"0"}')
        self.node.web = StaticWeb(self.web, True, {'/publication': self.publication})
        self.addCleanup(self.node.durable.close)
        self.addCleanup(self.node.stop)

    def get(self, path, method='GET', body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.node.server.server_port)
        conn.request(method, path, body=json.dumps(body) if body else None, headers=headers or {})
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
        self.assertEqual(self.get('/publication/root.json')[0], 200)
        self.assertEqual(self.get('/p/exact-link')[2], b'index.html')
        # SPA fallback must not turn unknown API-like paths into HTML 200s.
        for path in ['/atom', '/feed', '/latest', '/atoms/v1/info', '/missing']:
            self.assertEqual(self.get(path)[0], 404, path)
        self.node.web.spa_fallback = False
        self.assertEqual(self.get('/missing')[0], 404)

    def test_lib_cache_and_gzip(self):
        (self.web / 'lib').mkdir()
        big = ('const vendored = 1;\n' * 400).encode()
        (self.web / 'lib' / 'vendor.js').write_bytes(big)
        (self.web / 'lib' / 'vendor.css').write_bytes(b'a{}' * 600)
        (self.web / 'big.js').write_bytes(big)
        # Vendored /lib/* is cacheable; root app JS stays no-store.
        status, headers, raw = self.get('/lib/vendor.js')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'public, max-age=86400, immutable')
        self.assertEqual(raw, big)
        self.assertNotIn('Content-Encoding', headers)
        self.assertEqual(self.get('/lib/vendor.css')[1]['Cache-Control'], 'public, max-age=86400, immutable')
        self.assertIn('no-store', self.get('/big.js')[1]['Cache-Control'])
        # Publication mount keeps its existing policy even under a lib-like name.
        self.assertIn('no-store', self.get('/publication/root.json')[1]['Cache-Control'])
        # gzip only when accepted, above the size floor, and byte-exact on decode.
        status, headers, raw = self.get('/lib/vendor.js', headers={'Accept-Encoding': 'br, gzip;q=0.8'})
        self.assertEqual(headers['Content-Encoding'], 'gzip')
        self.assertEqual(headers['Vary'], 'Accept-Encoding')
        self.assertEqual(int(headers['Content-Length']), len(raw))
        self.assertLess(len(raw), len(big))
        self.assertEqual(gzip.decompress(raw), big)
        status, headers, raw = self.get('/big.js', 'HEAD', headers={'Accept-Encoding': 'gzip'})
        self.assertEqual(raw, b'')
        self.assertEqual(headers['Content-Encoding'], 'gzip')
        self.assertNotIn('Content-Encoding', self.get('/big.js', headers={'Accept-Encoding': 'gzip;q=0'})[1])
        self.assertNotIn('Content-Encoding', self.get('/app.js', headers={'Accept-Encoding': 'gzip'})[1])
        self.assertNotIn('Content-Encoding', self.get('/icon.png', headers={'Accept-Encoding': 'gzip'})[1])
        # Cache refreshes when the file changes.
        (self.web / 'lib' / 'vendor.js').write_bytes(big + b'//v2\n' * 300)
        raw = self.get('/lib/vendor.js', headers={'Accept-Encoding': 'gzip'})[2]
        self.assertTrue(gzip.decompress(raw).endswith(b'//v2\n'))

    def test_confinement(self):
        for path in ['/../secret', '/%2e%2e/secret', '/%252e%252e/secret', '/escape', '/%2fetc/passwd', '/dir/../../secret', '/missing.js', '/%00']:
            self.assertIn(self.get(path)[0], (400, 404), path)
        for path in ['/api/missing', '/api/missing.js', '/api']:
            self.assertEqual(self.get(path)[0], 400)

    def test_page_alias(self):
        (self.web / 'ai.html').write_text('<h1>machine entrance</h1>')
        self.node.web = StaticWeb(self.web, True, pages=self.config['web']['pages'])
        status, headers, raw = self.get('/ai')
        self.assertEqual(status, 200)
        self.assertEqual(raw, b'<h1>machine entrance</h1>')
        self.assertEqual(headers['Content-Type'], 'text/html; charset=utf-8')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(headers['Cache-Control'], 'no-cache, no-store, must-revalidate')
        self.assertEqual(self.get('/ai', 'HEAD')[2], b'')
        self.assertEqual(self.get('/ai.html')[0], 200)
        for route in ['/ai/', '/ai/child', '/aix', '/%61i']:
            self.assertEqual(self.get(route)[0], 404)
        self.node.web.pages['/leak'] = 'escape'
        self.assertEqual(self.get('/leak')[0], 404)
        self.node.web.pages['/leak'] = '../secret'
        self.assertEqual(self.get('/leak')[0], 404)

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
        self.node.web = StaticWeb(None, False, {'/publication': self.publication})
        self.assertEqual(self.get('/')[0], 400)
        self.assertEqual(self.get('/publication/root.json')[0], 200)
        for value in ['0', 'false', 'no', 'off']:
            self.assertFalse(load_config(environ={'PUNKTO_WEB_ENABLED': value})['web']['enabled'])
        for root in ['relative', str(self.root / 'missing')]:
            with self.assertRaisesRegex(ValueError, 'web.root'):
                load_config(environ={'PUNKTO_WEB_ROOT': root})


if __name__ == '__main__':
    unittest.main()
