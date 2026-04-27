#!/usr/bin/env python3
"""Patch script: add Reset Cache button to index.html and app.js, bump sw to v5."""
import re, json

# ── index.html ────────────────────────────────────────────────────────────────
with open('/var/www/punkto/index.html') as f:
    html = f.read()

# Add CSS for reset button
reset_css = """
    /* ── Reset cache button ──────────────────────────────── */
    #btn-reset {
      position: absolute;
      top: 86px;
      right: 10px;
      z-index: 10;
      background: var(--surface);
      color: #ff6666;
      border: 1px solid #442222;
      border-radius: 4px;
      padding: 4px 10px;
      font-family: inherit;
      font-size: 11px;
      cursor: pointer;
      letter-spacing: 0.05em;
    }
    #btn-reset:hover { background: #1a0808; }"""

html = html.replace(
    '    #toggle-3d:hover { background: var(--border); }',
    '    #toggle-3d:hover { background: var(--border); }' + reset_css
)

# Add reset button HTML after the 3D toggle button
html = html.replace(
    '  <!-- Map container -->',
    '  <button id="btn-reset" title="Clear local cache and resync">&#8635; reset</button>\n\n  <!-- Map container -->'
)

with open('/var/www/punkto/index.html', 'w') as f:
    f.write(html)
print('index.html patched')

# ── app.js ────────────────────────────────────────────────────────────────────
with open('/var/www/punkto/app.js') as f:
    js = f.read()

# Add resetCache function — insert before wireEvents section
reset_fn = '''
// ---------------------------------------------------------------------------
// Reset cache — wipe local DB, clear SW caches, reload clean
// ---------------------------------------------------------------------------
async function resetCache() {
  if (!confirm('Clear local cache and resync from server?')) return;
  try { await db.delete(); } catch (e) { /* ignore */ }
  try { localStorage.removeItem('punkto-cursor'); } catch (e) { /* ignore */ }
  if ('serviceWorker' in navigator) {
    const regs = await navigator.serviceWorker.getRegistrations();
    for (const r of regs) await r.unregister();
  }
  if ('caches' in window) {
    const keys = await caches.keys();
    for (const k of keys) await caches.delete(k);
  }
  location.reload(true);
}

'''

# Insert before wireEvents
js = js.replace(
    '// ---------------------------------------------------------------------------\n// Events',
    reset_fn + '// ---------------------------------------------------------------------------\n// Events'
)

# Wire the button — after elToggle3D.addEventListener line
js = js.replace(
    "elToggle3D.addEventListener('click', toggle3D);",
    "elToggle3D.addEventListener('click', toggle3D);\n  const elReset = document.getElementById('btn-reset');\n  if (elReset) elReset.addEventListener('click', resetCache);"
)

with open('/var/www/punkto/app.js', 'w') as f:
    f.write(js)
print('app.js patched')

# ── sw.js — bump to v5 ────────────────────────────────────────────────────────
with open('/var/www/punkto/sw.js') as f:
    sw = f.read()
sw = re.sub(r'punkto-v\d+', 'punkto-v5', sw)
with open('/var/www/punkto/sw.js', 'w') as f:
    f.write(sw)
print('sw.js bumped to v5')

# ── Fix Agent Zero atom timestamp ─────────────────────────────────────────────
atoms = []
with open('/var/www/punkto/data/atoms.ndjson') as f:
    for line in f:
        line = line.strip()
        if line:
            a = json.loads(line)
            if a.get('f') == 'agent0':
                a['t'] = 1777165200000  # 2026-04-25 ~23:00 UTC
            atoms.append(a)
with open('/var/www/punkto/data/atoms.ndjson', 'w') as f:
    for a in atoms:
        f.write(json.dumps(a) + '\n')
print('Agent Zero atom timestamp fixed')
print('All done.')
