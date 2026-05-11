/**
 * sw.js — Punkto service worker
 * Cache-first for app shell, network-first for API endpoints.
 */

const CACHE_NAME = 'punkto-v30';

const APP_SHELL = [
  '/',
  '/index.html',
  '/app.js',
  '/geohash3d.js',
  '/manifest.json',
  '/logo-192.png',
  '/logo-512.png',
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
  return NETWORK_FIRST_PATTERNS.some(re => re.test(target));
}

// ---------------------------------------------------------------------------
// Install — pre-cache app shell
// ---------------------------------------------------------------------------
self.addEventListener('install', event => {
  console.log('[SW] install', CACHE_NAME);
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      // Cache each shell asset individually so one failure doesn't block all
      return Promise.allSettled(
        APP_SHELL.map(url =>
          cache.add(url).catch(err =>
            console.warn(`[SW] failed to cache ${url}:`, err)
          )
        )
      );
    }).then(() => self.skipWaiting())
  );
});

// ---------------------------------------------------------------------------
// Activate — purge old caches
// ---------------------------------------------------------------------------
self.addEventListener('activate', event => {
  console.log('[SW] activate', CACHE_NAME);
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== CACHE_NAME)
          .map(k => {
            console.log('[SW] deleting old cache', k);
            return caches.delete(k);
          })
      )
    ).then(() => self.clients.claim())
  );
});

// ---------------------------------------------------------------------------
// Fetch — routing strategy
// ---------------------------------------------------------------------------
self.addEventListener('fetch', event => {
  const { request } = event;

  // Only handle GET (POST /atom goes straight to network)
  if (request.method !== 'GET') {
    event.respondWith(fetch(request));
    return;
  }

  const url = request.url;

  // Network-first for API routes (feed, atom lookups)
  if (isNetworkFirst(url)) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Cache-first for app shell and static assets
  event.respondWith(cacheFirst(request));
});

// ---------------------------------------------------------------------------
// Strategies
// ---------------------------------------------------------------------------

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response && response.status === 200 && response.type !== 'opaque') {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    console.warn('[SW] cache-first network fail', request.url, err);
    // Return a minimal offline page for navigation requests
    if (request.mode === 'navigate') {
      const cached = await caches.match('/index.html');
      if (cached) return cached;
    }
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    console.warn('[SW] network-first fallback to cache', request.url);
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(
      JSON.stringify({ error: 'offline', message: 'No network and no cached response' }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
