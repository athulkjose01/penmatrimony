// --- Constants for Caching ---
// Increment this version number every time you want to force an update of the cached files.
const CACHE_NAME = 'pentecost-matrimony-cache-v4';

// These are the core files for your "app shell".
// They will be cached when the service worker is first installed.
const urlsToCache = [
  '/', // The homepage will be cached for offline access.
  '/static/images/hero.png',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  // You can add other critical static assets here, like your main CSS file.
];


// --- Service Worker Lifecycle Events ---

// 1. Install Event: Fired when the service worker is first registered.
self.addEventListener('install', event => {
  console.log('[Service Worker] Event: install');
  // We wait until the cache is opened and our app shell files are all cached.
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Caching app shell');
        return cache.addAll(urlsToCache);
      })
      .catch(error => {
        console.error('[Service Worker] Failed to cache app shell:', error);
      })
  );
});

// 2. Activate Event: Fired when the service worker becomes active.
// This is the perfect place to clean up old, outdated caches.
self.addEventListener('activate', event => {
  console.log('[Service Worker] Event: activate');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          // If a cache's name is different from our current CACHE_NAME, it's an old cache.
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Clearing old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      // Take control of any open pages immediately without needing a reload.
      return self.clients.claim();
    })
  );
});

// 3. Fetch Event: Fired every time the browser tries to fetch a resource (HTML, CSS, image, etc.).
// This is where we implement our caching strategy.
self.addEventListener('fetch', event => {
  // We only want to cache GET requests.
  if (event.request.method !== 'GET') {
    return;
  }

  // Strategy for HTML pages: Network First, then Cache
  // This ensures users always get the latest page content if they are online.
  if (event.request.headers.get('accept').includes('text/html')) {
    event.respondWith(
      fetch(event.request)
        .then(networkResponse => {
          // If the network request is successful, cache the response for offline use.
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
          return networkResponse;
        })
        .catch(() => {
          // If the network fails (user is offline), serve the page from the cache.
          console.log('[Service Worker] Network request for HTML failed, serving from cache.');
          return caches.match(event.request);
        })
    );
    return;
  }

  // Strategy for all other assets (CSS, JS, images): Cache First, then Network
  // This is very fast as it serves from the cache immediately if available.
  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        // If the response is in the cache, return it.
        if (cachedResponse) {
          return cachedResponse;
        }
        // If not, fetch it from the network, cache it, and then return it.
        return fetch(event.request).then(networkResponse => {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
          return networkResponse;
        });
      })
  );
});