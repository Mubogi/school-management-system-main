const CACHE_NAME = 'jordan-school-hub-v2';
const SHELL = [
  '/',
  '/accounts/login/',
  '/manifest.json',
  '/sw.js',
  '/static/core/css/tailwind.min.css',
  '/static/core/css/offline.css',
  '/static/core/css/icons.css',
  '/static/core/js/offline-sync.js',
  '/static/core/favicon.ico',
  '/static/core/icon-192.png',
  '/static/core/icon-512.png',
  '/static/core/img/login-bg.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const network = fetch(event.request).then((response) => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((c) => c.put(event.request, clone));
        }
        return response;
      });
      return cached || network.catch(() => caches.match('/accounts/login/'));
    })
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'DRAIN_OFFLINE_QUEUE') {
    event.waitUntil(self.clients.matchAll().then((clients) => {
      clients.forEach((c) => c.postMessage({ type: 'SYNC_NOW' }));
    }));
  }
});
