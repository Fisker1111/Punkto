/**
 * sw.js — Punkto service worker unregistration
 * Clears all caches and removes the service worker so the app
 * runs as a plain web app served directly from Docker/Caddy.
 */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.registration.unregister())
      .then(() => console.log('[SW] unregistered — running as plain web app'))
  );
});
