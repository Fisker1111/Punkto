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

    def __init__(self, root, spa_fallback=False):
        self.root = Path(root).resolve()
        self.spa_fallback = spa_fallback

    def serve(self, handler, path):
        if handler.command not in ('GET', 'HEAD'):
            return False
        decoded = unquote(path)
        if decoded == '/api' or decoded.startswith('/api/'):
            return False
        if not decoded.startswith('/') or decoded.startswith('//') or '\\' in decoded or '\x00' in decoded or '..' in decoded.split('/') or '%' in decoded:
            handler.send_error(404)
            return True
        target = (self.root / decoded.lstrip('/')).resolve()
        if not target.is_relative_to(self.root):
            handler.send_error(404)
            return True
        if decoded.endswith('/'):
            target = (target / 'index.html').resolve()
        # SPA fallback is limited to client-side routes (exact links) so that
        # unknown operational/API-looking paths still 404 instead of returning
        # HTML with a 200.
        if not target.is_file() and self.spa_fallback and decoded.startswith(self.SPA_PREFIXES):
            target = (self.root / 'index.html').resolve()
        if not target.is_relative_to(self.root) or not target.is_file():
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
