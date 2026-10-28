"""Protocol-neutral, confined static serving for an optional bundled UI."""
from pathlib import Path
from urllib.parse import unquote


class StaticWeb:
    SPA_PREFIXES = ('/p/',)
    MIME = {'.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
            '.css': 'text/css', '.json': 'application/json', '.png': 'image/png',
            '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json',
            '.map': 'application/json', '.txt': 'text/plain', '.wasm': 'application/wasm',
            '.woff': 'font/woff', '.woff2': 'font/woff2', '.jpg': 'image/jpeg'}

    def __init__(self, root=None, spa_fallback=False, mounts=None):
        self.root = Path(root).resolve() if root else None
        self.spa_fallback = spa_fallback
        self.mounts = []
        for prefix, directory in (mounts or {}).items():
            if not isinstance(prefix, str) or not prefix.startswith('/') or (prefix != '/' and prefix.endswith('/')):
                raise ValueError('mount prefix')
            self.mounts.append((prefix, Path(directory).resolve()))
        self.mounts.sort(key=lambda item: len(item[0]), reverse=True)

    def _resolve(self, root, decoded):
        if not decoded.startswith('/') or decoded.startswith('//') or '\\' in decoded or '\x00' in decoded or '..' in decoded.split('/') or '%' in decoded:
            return None
        target = (root / decoded.lstrip('/')).resolve()
        if not target.is_relative_to(root):
            return None
        return target

    def _serve_path(self, handler, root, decoded, spa_fallback=False):
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
        handler.send_response(200)
        handler.send_header('Content-Type', self.MIME.get(target.suffix, 'application/octet-stream'))
        handler.send_header('Content-Length', str(len(raw)))
        handler.send_header('X-Content-Type-Options', 'nosniff')
        handler.send_header('Cache-Control', 'no-cache, no-store, must-revalidate' if target.suffix in ('.html', '.js', '.mjs', '.json') else 'public, max-age=3600')
        handler.end_headers()
        if handler.command != 'HEAD':
            handler.wfile.write(raw)
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
        return self._serve_path(handler, self.root, decoded, spa_fallback=self.spa_fallback)
