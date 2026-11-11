"""Protocol-neutral, confined static serving for an optional bundled UI."""
import gzip
from pathlib import Path
from urllib.parse import unquote

# Vendored third-party libraries under the web root's /lib/ change only with a
# deploy. Matches the Caddy node policy and docs/cache-cloudflare.md.
LIB_CACHE_CONTROL = 'public, max-age=86400, immutable'
NO_STORE = 'no-cache, no-store, must-revalidate'
GZIP_SUFFIXES = ('.html', '.js', '.mjs', '.css', '.json', '.svg', '.txt', '.map', '.webmanifest')
GZIP_MIN_BYTES = 1024


class StaticWeb:
    SPA_PREFIXES = ('/p/',)
    MIME = {'.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
            '.css': 'text/css', '.json': 'application/json', '.png': 'image/png',
            '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json',
            '.map': 'application/json', '.txt': 'text/plain', '.wasm': 'application/wasm',
            '.woff': 'font/woff', '.woff2': 'font/woff2', '.jpg': 'image/jpeg'}

    def __init__(self, root=None, spa_fallback=False, mounts=None, pages=None):
        self.root = Path(root).resolve() if root else None
        self.spa_fallback = spa_fallback
        self.pages = dict(pages or {})
        self.mounts = []
        for prefix, directory in (mounts or {}).items():
            if not isinstance(prefix, str) or not prefix.startswith('/') or (prefix != '/' and prefix.endswith('/')):
                raise ValueError('mount prefix')
            self.mounts.append((prefix, Path(directory).resolve()))
        self.mounts.sort(key=lambda item: len(item[0]), reverse=True)
        self._gzip_cache = {}

    def _gzipped(self, target, raw):
        """Return gzip bytes for ``target``, cached per (path, mtime, size)."""
        stat = target.stat()
        key = str(target)
        stamp = (stat.st_mtime_ns, stat.st_size)
        cached = self._gzip_cache.get(key)
        if cached and cached[0] == stamp:
            return cached[1]
        body = gzip.compress(raw, compresslevel=6, mtime=0)
        self._gzip_cache[key] = (stamp, body)
        return body

    @staticmethod
    def _accepts_gzip(handler):
        headers = getattr(handler, 'headers', None)
        value = headers.get('Accept-Encoding', '') if headers is not None else ''
        for part in value.split(','):
            token, _, params = part.strip().partition(';')
            if token.strip().lower() in ('gzip', '*'):
                q = params.strip().lower()
                return not (q.startswith('q=') and q[2:].strip() in ('0', '0.0', '0.00', '0.000'))
        return False

    def _resolve(self, root, decoded):
        if not decoded.startswith('/') or decoded.startswith('//') or '\\' in decoded or '\x00' in decoded or '..' in decoded.split('/') or '%' in decoded:
            return None
        target = (root / decoded.lstrip('/')).resolve()
        if not target.is_relative_to(root):
            return None
        return target

    def _serve_path(self, handler, root, decoded, spa_fallback=False, page_alias=False, cacheable_lib=False):
        target = self._resolve(root, decoded)
        if target is None:
            handler.send_error(404)
            return True
        if decoded.endswith('/'):
            target = (target / 'index.html').resolve()
        if not target.is_file() and spa_fallback and decoded.startswith(self.SPA_PREFIXES):
            target = (root / 'index.html').resolve()
        if not target.is_relative_to(root) or not target.is_file():
            handler.send_error(404)
            return True
        raw = target.read_bytes()
        compressible = page_alias or target.suffix in GZIP_SUFFIXES
        encoded = compressible and len(raw) >= GZIP_MIN_BYTES and self._accepts_gzip(handler)
        body = self._gzipped(target, raw) if encoded else raw
        if page_alias or (target.suffix in ('.html', '.js', '.mjs', '.json') and not cacheable_lib):
            cache_control = NO_STORE
        elif cacheable_lib:
            cache_control = LIB_CACHE_CONTROL
        else:
            cache_control = 'public, max-age=3600'
        handler.send_response(200)
        handler.send_header('Content-Type', 'text/html; charset=utf-8' if page_alias else self.MIME.get(target.suffix, 'application/octet-stream'))
        handler.send_header('Content-Length', str(len(body)))
        if encoded:
            handler.send_header('Content-Encoding', 'gzip')
        if compressible:
            handler.send_header('Vary', 'Accept-Encoding')
        handler.send_header('X-Content-Type-Options', 'nosniff')
        handler.send_header('Cache-Control', cache_control)
        handler.end_headers()
        if handler.command != 'HEAD':
            handler.wfile.write(body)
        return True

    def serve(self, handler, path):
        if handler.command not in ('GET', 'HEAD'):
            return False
        decoded = unquote(path)
        if decoded == '/api' or decoded.startswith('/api/'):
            return False
        for prefix, root in self.mounts:
            if decoded == prefix or decoded.startswith(prefix + '/'):
                relative = decoded[len(prefix):] or '/'
                if not relative.startswith('/'):
                    relative = '/' + relative
                return self._serve_path(handler, root, relative, spa_fallback=False)
        if self.root is None:
            return False
        if path in self.pages:
            return self._serve_path(handler, self.root, '/' + self.pages[path], page_alias=True)
        return self._serve_path(handler, self.root, decoded, spa_fallback=self.spa_fallback,
                                cacheable_lib=decoded.startswith('/lib/'))
