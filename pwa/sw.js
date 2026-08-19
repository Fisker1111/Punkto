/**
 * sw.js — Punkto service worker unregistration
 * Clears all caches and removes the service worker so the app
 * runs as a plain web app served directly from Docker/Caddy.
 *
 * test1-atomcloud branch: any future cache names should use the
 * `punkto-test1-*` prefix to avoid colliding with production.
 */
const TEST1_CACHE_PREFIX = 'punkto-test1-';
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.registration.unregister())
      .then(() => console.log('[SW] unregistered — running as plain web app', TEST1_CACHE_PREFIX))
  );
});
