/**
 * sw.js — Punkto service worker
 * Network-first for JS/HTML (dev-friendly), cache-first for assets.
 */

const CACHE_NAME = 'punkto-v46';

const APP_SHELL = [
  '/',
  '/index.html',
  '/app.js',
  '/geohash3d.js',
  '/manifest.json',
  '/logo-192.png',
  '/logo-512.png',
  '/lib/maplibre-gl.css',
  '/lib/maplibre-gl.js',
  '/lib/dist.min.js',
  '/lib/dexie.min.js',
  '/nacl.min.js',
  '/key-management.js',
];

// Routes that should always go network-first
const NETWORK_FIRST_PATTERNS = [
  /\/feed(\?|$)/,
  /\/atom$/,
  /\/punkto\//,
  /\/health$/,
  /\/info$/,
];

function isNetworkFirst(url) {
  const { pathname, search } = new URL(url);
  const target = pathname + search;
  // Always network-first for JS and HTML (ensures fresh code during development)
  if (pathname.endsWith('.js') || pathname.endsWith('.html') || pathname === '/') {
    return true;
  }
  return NETWORK_FIRST_PATTERNS.some(re => re.test(target));
}

// Install: cache app shell
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

// Activate: clear old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) return caches.delete(key);
        })
      )
    ).then(() => self.clients.claim())
  );
});

// Fetch: network-first for JS/HTML/API, cache-first for static assets
self.addEventListener('fetch', event => {
  const url = event.request.url;
  if (isNetworkFirst(url)) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          if (response.ok) {
            const cloned = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, cloned));
          }
          return response;
        })
        .catch(() => caches.match(event.request).then(
          cached => cached || new Response(JSON.stringify({ error: 'peer_unreachable' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }
          })
        ))
    );
    return;
  }
  // Cache-first for images, fonts, other static assets
  event.respondWith(
    caches.match(event.request)
      .then(cached => cached || fetch(event.request))
  );
});
