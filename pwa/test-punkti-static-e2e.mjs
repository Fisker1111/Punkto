import assert from 'node:assert/strict';
import http from 'node:http';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync, cpSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const PWA_DIR = path.resolve(ROOT, 'pwa');
const VECTORS = JSON.parse(readFileSync(path.resolve(ROOT, 'experimental/punkti-v0.6-publication/vectors.json'), 'utf8'));

async function importPlaywright() {
  const explicitPath = process.env.PLAYWRIGHT_MODULE;
  if (explicitPath) {
    try {
      return await import(explicitPath);
    } catch (error) {
      throw new Error(`playwright unavailable via PLAYWRIGHT_MODULE: ${error?.message || error}`);
    }
  }
  try {
    return await import('playwright');
  } catch (error) {
    throw new Error(`playwright unavailable: ${error?.message || error}`);
  }
}

async function launchChromium(playwright, options = {}) {
  try {
    return await playwright.chromium.launch({ headless: true, ...options });
  } catch (error) {
    throw new Error(`chromium unavailable for playwright; install browser with \"npx playwright install --with-deps chromium\": ${error?.message || error}`);
  }
}

function materializeFixture(fixture, directory) {
  mkdirSync(directory, { recursive: true });
  writeFileSync(path.join(directory, 'root.json'), Buffer.from(fixture.root, 'hex'));
  for (const [sha, object] of Object.entries(fixture.objects)) {
    const raw = Buffer.from(object.hex, 'hex');
    let relative;
    if (object.kind === 'manifest') {
      relative = `manifests/${sha}.json`;
    } else if (object.kind === 'shard') {
      const body = JSON.parse(raw.toString('utf8'));
      relative = `h/${body.prefix.split('').join('/')}/${sha}.json`;
    } else if (object.kind === 'record') {
      relative = `records/${sha.slice(0, 2)}/${sha}`;
    } else {
      relative = `segments/${sha.slice(0, 2)}/${sha}`;
    }
    const target = path.join(directory, relative);
    mkdirSync(path.dirname(target), { recursive: true });
    writeFileSync(target, raw);
  }
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.wasm': 'application/wasm',
};

function serveStatic(root, { defaultFile = 'index.html' } = {}) {
  const requests = [];
  const server = http.createServer((req, res) => {
    const pathname = decodeURIComponent(new URL(req.url || '/', 'http://localhost').pathname);
    requests.push(pathname);
    const filePath = path.join(root, pathname === '/' ? defaultFile : pathname.slice(1));
    try {
      const raw = readFileSync(filePath);
      res.statusCode = 200;
      // Browsers enforce strict MIME checking for ES module imports; a dumb
      // static server must still declare text/javascript for .js files.
      res.setHeader('Content-Type', MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream');
      res.end(raw);
    } catch {
      res.statusCode = 404;
      res.end();
    }
  });
  return { requests, server };
}

function listen(server) {
  return new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      resolve(`http://127.0.0.1:${address.port}`);
    });
  });
}

function close(server) {
  return new Promise((resolve) => server.close(resolve));
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = http.createServer();
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      server.close((error) => {
        if (error) reject(error);
        else resolve(address.port);
      });
    });
  });
}

async function loadNacl(page, origin) {
  await page.addScriptTag({ url: `${origin}/nacl.min.js` });
  const ready = await page.evaluate(() => Boolean(globalThis.nacl));
  assert.equal(ready, true, 'nacl available in browser context');
}

async function staticReadAcidTest(playwright) {
  const tempRoot = mkdtempSync(path.join(tmpdir(), 'punkti-static-acid-'));
  try {
    const publication = path.join(tempRoot, 'publication');
    materializeFixture(VECTORS.fixtures.index, publication);
    mkdirSync(path.join(tempRoot, 'punkti'), { recursive: true });
    cpSync(path.join(PWA_DIR, 'punkti'), path.join(tempRoot, 'punkti'), { recursive: true });
    cpSync(path.join(PWA_DIR, 'nacl.min.js'), path.join(tempRoot, 'nacl.min.js'));
    writeFileSync(path.join(tempRoot, 'acid.html'), '<!doctype html><html><body>acid</body></html>');

    const { server, requests } = serveStatic(tempRoot, { defaultFile: 'acid.html' });
    const origin = await listen(server);

    const browser = await launchChromium(playwright);
    const page = await browser.newPage();
    const seen = [];
    page.on('request', (req) => seen.push(new URL(req.url()).pathname));

    await page.goto(`${origin}/acid.html`, { waitUntil: 'networkidle' });
    await loadNacl(page, origin);

    const result = await page.evaluate(async (base) => {
      const mod = await import(`${base}/punkti/reader.js`);
      const reader = mod.createReader({ resolver: mod.hexShardedResolver(), maxRetries: 0 });
      const read = await reader.readPublication(`${base}/publication`, {});
      return {
        valid: read.valid_count,
        seq: read.seq,
        head: read.head,
      };
    }, origin);

    assert.ok(result.valid > 0, 'static reader returns valid records');
    assert.ok(result.seq >= 1, 'publication seq available');
    assert.ok(/^[0-9a-f]{64}$/.test(result.head), 'publication head digest');
    assert.equal(seen.some((pathname) => pathname.includes('/pull') || pathname.includes('/sync') || pathname.includes('/push')), false, 'no legacy dynamic-read routes');
    assert.equal(requests.some((pathname) => pathname.includes('/pull') || pathname.includes('/sync') || pathname.includes('/push')), false, 'server saw no legacy dynamic routes');

    await browser.close();
    await close(server);
  } finally {
    rmSync(tempRoot, { recursive: true, force: true });
  }
}

function toRequestPath(url) {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

function hasLegacySyncPath(pathname) {
  const route = String(pathname || '');
  return route === '/pull' || route === '/sync' || route === '/push';
}

function parseVisibleCount(raw) {
  const value = Number.parseInt(String(raw || '').trim(), 10);
  return Number.isFinite(value) ? value : 0;
}

function isToleratedConsoleError(text) {
  const lower = String(text || '').toLowerCase();
  if (lower.includes('/node/info')) return true;
  if (lower.includes('failed to load resource')) {
    if (lower.includes('404 (not found)')) return true;
    if (lower.includes('tile') || lower.includes('glyph') || lower.includes('sprite') || lower.includes('maptiler')) {
      return true;
    }
    if (lower.includes('favicon.ico')) return true;
  }
  if (lower.includes('err_name_not_resolved') || lower.includes('err_internet_disconnected')) return true;
  return false;
}

async function realPwaStaticReadTest(playwright) {
  const tempRoot = mkdtempSync(path.join(tmpdir(), 'punkti-real-pwa-static-'));
  try {
    cpSync(PWA_DIR, tempRoot, { recursive: true });
    const publication = path.join(tempRoot, 'publication');
    materializeFixture(VECTORS.fixtures.index, publication);

    const { server, requests } = serveStatic(tempRoot, { defaultFile: 'index.html' });
    const origin = await listen(server);

    const browser = await launchChromium(playwright, {
      args: ['--use-angle=swiftshader', '--use-gl=swiftshader'],
    });
    const page = await browser.newPage();
    const seenRequests = [];
    const consoleErrors = [];
    const pageErrors = [];

    page.on('request', (req) => {
      const pathName = toRequestPath(req.url());
      seenRequests.push(pathName);
    });
    page.on('console', (message) => {
      if (message.type() === 'error') {
        consoleErrors.push(message.text());
      }
    });
    page.on('pageerror', (error) => {
      pageErrors.push(String(error?.stack || error));
    });

    try {
      await page.goto(`${origin}/index.html`, { waitUntil: 'domcontentloaded' });
      const textNavSelector = '#nav-text:visible, #nav-rail-text:visible';
      await page.waitForSelector(textNavSelector, { timeout: 15000 });
      await page.click(textNavSelector);

      await page.waitForSelector('#world-apply', { timeout: 15000 });
      await page.click('#world-apply');

      await page.waitForFunction(() => {
        const cards = document.querySelectorAll('#main-feed-list .main-card').length;
        const count = Number.parseInt(document.getElementById('count-num')?.textContent || '0', 10);
        return cards > 0 || count > 0;
      }, { timeout: 30000 });

      const baseline = await page.evaluate(() => ({
        visibleCount: Number.parseInt(document.getElementById('count-num')?.textContent || '0', 10),
        cardCount: document.querySelectorAll('#main-feed-list .main-card').length,
      }));
      const baselineVisible = Math.max(parseVisibleCount(baseline.visibleCount), baseline.cardCount);

      const exactIdentity = await page.evaluate(async (base) => {
        const [{ getAllAtomsNewestFirst }, { canonicalAtomPath, canonicalAtomUrl, parsePublicPPath }, { qrPayloadForAtom }] = await Promise.all([
          import(`${base}/storage/atom-store.js`),
          import(`${base}/protocol/exact-link.js`),
          import(`${base}/print-pdf.js`),
        ]);
        const atoms = await getAllAtomsNewestFirst();
        const atom = atoms.find((candidate) => String(candidate?.mid || '').startsWith('punkti/0.6:')) || atoms[0] || null;
        if (!atom) {
          return { ok: false, reason: 'no atoms in local cache' };
        }
        const identity = String(atom.mid || atom.atom_id || '').trim();
        const path = canonicalAtomPath(identity);
        const url = await canonicalAtomUrl(atom, base);
        const parsed = parsePublicPPath(path);
        const qr = await qrPayloadForAtom(atom, base);
        return {
          ok: true,
          identity,
          path,
          url,
          qr,
          parsed,
        };
      }, origin);

      await page.fill('#world-xy-prefix', 'zzzz');
      await page.click('#world-apply');
      await page.waitForFunction(() => {
        const cards = document.querySelectorAll('#main-feed-list .main-card').length;
        const count = Number.parseInt(document.getElementById('count-num')?.textContent || '0', 10);
        return Math.max(Number.isFinite(count) ? count : 0, cards) === 0;
      }, { timeout: 15000 });

      const zeroScoped = await page.evaluate(() => ({
        visibleCount: Number.parseInt(document.getElementById('count-num')?.textContent || '0', 10),
        cardCount: document.querySelectorAll('#main-feed-list .main-card').length,
      }));

      await page.fill('#world-xy-prefix', '');
      await page.click('#world-apply');
      await page.waitForFunction(() => {
        const cards = document.querySelectorAll('#main-feed-list .main-card').length;
        const count = Number.parseInt(document.getElementById('count-num')?.textContent || '0', 10);
        return Math.max(Number.isFinite(count) ? count : 0, cards) > 0;
      }, { timeout: 30000 });

      const restored = await page.evaluate(() => ({
        visibleCount: Number.parseInt(document.getElementById('count-num')?.textContent || '0', 10),
        cardCount: document.querySelectorAll('#main-feed-list .main-card').length,
      }));
      const restoredVisible = Math.max(parseVisibleCount(restored.visibleCount), restored.cardCount);
      const zeroScopedVisible = Math.max(parseVisibleCount(zeroScoped.visibleCount), zeroScoped.cardCount);

      const allRequests = [...requests, ...seenRequests];
      const hasLegacyPath = allRequests.some(hasLegacySyncPath);

      const fatalConsoleErrors = consoleErrors.filter((text) => !isToleratedConsoleError(text));
      const publicationRequestSeen = allRequests.some((pathname) => pathname.startsWith('/publication/'));

      assert.equal(pageErrors.length, 0, `no uncaught page errors in real PWA static-read path; got: ${JSON.stringify(pageErrors, null, 2)}`);
      assert.equal(publicationRequestSeen, true, 'real PWA requested static publication objects from /publication');
      assert.equal(hasLegacyPath, false, `no /pull,/sync,/push requests in real PWA static-read path; got: ${JSON.stringify(allRequests, null, 2)}`);
      assert.ok(baselineVisible > 0, 'real PWA displays atoms from static publication (feed cards and/or visible count)');
      assert.equal(exactIdentity.ok, true, `real PWA cached at least one static atom; got: ${JSON.stringify(exactIdentity)}`);
      assert.ok(exactIdentity.path.startsWith('/p/'), `MID deep-link path generated for static atom: ${JSON.stringify(exactIdentity)}`);
      assert.ok(exactIdentity.url.startsWith(`${origin}/p/`), `MID deep-link URL generated for static atom: ${JSON.stringify(exactIdentity)}`);
      assert.notEqual(exactIdentity.qr, '', `QR/PDF payload URL is non-empty for static atom: ${JSON.stringify(exactIdentity)}`);
      assert.deepEqual(exactIdentity.parsed, { kind: 'atom', id: exactIdentity.identity }, `MID deep-link path parses back to exact identity: ${JSON.stringify(exactIdentity)}`);
      assert.equal(zeroScopedVisible, 0, 'non-matching XY prefix produces zero visible atoms/cards');
      assert.ok(restoredVisible > 0, 'clearing XY prefix restores visible atoms/cards');
      assert.equal(fatalConsoleErrors.length, 0, `no fatal console errors in real PWA static-read path; got: ${JSON.stringify(fatalConsoleErrors, null, 2)}`);

      console.log('[real-pwa-static] baseline', baseline);
      console.log('[real-pwa-static] exact-identity', exactIdentity);
      console.log('[real-pwa-static] zero-scoped', zeroScoped);
      console.log('[real-pwa-static] restored', restored);
      console.log('[real-pwa-static] requests', JSON.stringify(allRequests));
      if (consoleErrors.length) {
        console.log('[real-pwa-static] tolerated-console-errors', JSON.stringify(consoleErrors));
      }
    } finally {
      await browser.close();
      await close(server);
    }
  } finally {
    rmSync(tempRoot, { recursive: true, force: true });
  }
}

async function writeRoundTripTest(playwright) {
  const tempRoot = mkdtempSync(path.join(tmpdir(), 'punkti-write-roundtrip-'));
  const webRoot = path.join(tempRoot, 'web');
  const dataRoot = path.join(tempRoot, 'data');
  const publicationRoot = path.join(dataRoot, 'publication');
  mkdirSync(webRoot, { recursive: true });
  mkdirSync(dataRoot, { recursive: true });
  mkdirSync(publicationRoot, { recursive: true });
  cpSync(path.join(PWA_DIR, 'punkti'), path.join(webRoot, 'punkti'), { recursive: true });
  cpSync(path.join(PWA_DIR, 'nacl.min.js'), path.join(webRoot, 'nacl.min.js'));
  writeFileSync(path.join(webRoot, 'acid.html'), '<!doctype html><html><body>roundtrip</body></html>');

  const port = await freePort();
  const configPath = path.join(tempRoot, 'config.yml');
  writeFileSync(configPath, [
    'node:',
    '  name: e2e-node',
    `  public_url: http://127.0.0.1:${port}`,
    'network:',
    '  listen_host: 127.0.0.1',
    `  listen_port: ${port}`,
    '  peers: []',
    '  sync_interval_seconds: 3600',
    'web:',
    '  enabled: true',
    `  root: ${webRoot}`,
    '  spa_fallback: false',
    'publication:',
    '  enabled: true',
    `  path: ${publicationRoot}`,
    '  serve_prefix: /publication',
    '  packs: false',
    'storage:',
    `  data_path: ${dataRoot}`,
  ].join('\n'));

  const node = spawn('python3', ['-m', 'punkti_node', '--config', configPath], {
    cwd: ROOT,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  const nodeErrors = [];
  node.stderr.on('data', (chunk) => nodeErrors.push(chunk.toString('utf8')));
  const waitReady = async () => {
    const deadline = Date.now() + 15000;
    while (Date.now() < deadline) {
      try {
        const response = await fetch(`http://127.0.0.1:${port}/health`);
        if (response.ok) return;
      } catch {}
      await new Promise((resolve) => setTimeout(resolve, 200));
    }
    throw new Error(`node failed to become ready: ${nodeErrors.join('')}`);
  };

  const browser = await launchChromium(playwright);
  try {
    await waitReady();
    const origin = `http://127.0.0.1:${port}`;
    const page = await browser.newPage();
    const seen = [];
    page.on('request', (req) => seen.push(new URL(req.url()).pathname));
    await page.goto(`${origin}/acid.html`, { waitUntil: 'networkidle' });
    await loadNacl(page, origin);

    const result = await page.evaluate(async (base) => {
      const spatial = await import(`${base}/punkti/spatial.js`);
      const submitMod = await import(`${base}/punkti/submit.js`);
      const readerMod = await import(`${base}/punkti/reader.js`);
      const keyPair = globalThis.nacl.sign.keyPair();
      const submitClient = submitMod.createSubmitClient({
        baseUrl: base,
        identity: { secretKey: keyPair.secretKey },
      });
      const now = Date.now();
      const h = spatial.encode_h(55.6761, 12.5683, '23.4', 12);
      const atom = {
        v: 'punkti/0.6',
        t: now,
        h,
        x: JSON.stringify({ text: 'browser e2e roundtrip', meta: { category: 'TEXT' } }),
      };
      const first = await submitClient.submit(atom);
      const second = await submitClient.submit(atom);
      const reader = readerMod.createReader({ resolver: readerMod.hexShardedResolver(), maxRetries: 2 });
      const read = await reader.readPublication(`${base}/publication`, {});
      return {
        first,
        second,
        validCount: read.valid_count,
        found: read.valid_records.some((record) => record.mid === first.mid),
      };
    }, origin);

    assert.equal(result.first.ok, true, 'first submit succeeds');
    assert.equal(result.second.ok, true, 'duplicate submit succeeds');
    assert.equal(result.second.duplicate, true, 'duplicate submit is idempotent');
    assert.ok(result.validCount >= 1, 'publication has records');
    assert.equal(result.found, true, 'submitted record visible via static read path');
    assert.equal(seen.some((pathname) => pathname.includes('/pull') || pathname.includes('/sync') || pathname.includes('/push')), false, 'no legacy pull/sync/push calls');
    assert.equal(seen.some((pathname) => pathname === '/submit'), true, 'submit endpoint used');
  } finally {
    browser.close();
    node.kill('SIGTERM');
    await new Promise((resolve) => node.once('exit', resolve));
    rmSync(tempRoot, { recursive: true, force: true });
  }
}

async function main() {
  const playwright = await importPlaywright();
  await staticReadAcidTest(playwright);
  await realPwaStaticReadTest(playwright);
  await writeRoundTripTest(playwright);
  console.log('punkti static e2e: PASS');
}

main().catch((error) => {
  console.error(String(error?.stack || error));
  process.exit(1);
});
