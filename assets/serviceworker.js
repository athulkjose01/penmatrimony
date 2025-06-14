// static/serviceworker.js

// --- Constants for Cache ---
// Increment this version number every time you update any of the cached files.
const CACHE_NAME = 'pentecost-matrimony-cache-v4';
const urlsToCache = [
  '/', // The homepage (will be updated by the network-first strategy)
  '/static/images/hero.png',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
];

// --- Caching Strategy ---

// 1. Install Event: Cache the "app shell" (static assets)
self.addEventListener('install', event => {
  console.log('[SW] Event: install');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[SW] Caching app shell');
        return cache.addAll(urlsToCache);
      })
      .catch(error => {
        console.error('[SW] Failed to cache app shell:', error);
      })
  );
});

// 2. Activate Event: Clean up old caches
self.addEventListener('activate', event => {
  console.log('[SW] Event: activate');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          // If a cache's name is different from our current one, delete it.
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Clearing old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim()) // Take control of open pages immediately.
  );
});

// 3. Fetch Event: Implement smart caching strategies
self.addEventListener('fetch', event => {
  // We only handle GET requests. POST requests should always go to the network.
  if (event.request.method !== 'GET') {
    return;
  }

  // --- Strategy 1: Network First for HTML pages ---
  // This ensures the user always sees the latest version of a page (e.g., correct login state)
  // and fixes navigation issues.
  if (event.request.headers.get('accept').includes('text/html')) {
    event.respondWith(
      fetch(event.request)
        .then(networkResponse => {
          // If we get a valid response, we update the cache for offline use.
          if (networkResponse.ok) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, responseToCache);
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // If the network fails (user is offline), we serve the last good version from the cache.
          console.log('[SW] Network request for HTML failed, serving from cache.');
          return caches.match(event.request);
        })
    );
    return; // End here for HTML pages.
  }

  // --- Strategy 2: Cache First for all other static assets (CSS, JS, images) ---
  // This is super fast because it doesn't need to check the network unless the file is missing from the cache.
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // If it's in the cache, serve it immediately.
        if (response) {
          return response;
        }
        
        // If it's not in the cache, fetch it from the network and cache it for next time.
        return fetch(event.request).then(networkResponse => {
          if (networkResponse.ok) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, responseToCache);
            });
          }
          return networkResponse;
        });
      })
  );
});

// --- Push Notification Logic ---

self.addEventListener('push', event => {
  console.log('✅ [SW] Push Event Received!');
  if (!event.data) {
    console.error('❌ [SW] Push event had NO data.');
    event.waitUntil(self.registration.showNotification("Push Event Fired", { body: "But it had no data." }));
    return;
  }

  const rawData = event.data.text();
  console.log('📦 [SW] Raw payload from push service:', rawData);

  let payload;
  try {
    payload = JSON.parse(rawData);
  } catch (e) {
    console.error('❌ [SW] Failed to parse payload as JSON.', e);
    event.waitUntil(self.registration.showNotification("Push Payload Error", { body: `Could not parse push data: ${rawData}` }));
    return;
  }

  const title = payload.head || "New Notification";
  const options = {
    body: payload.body || "You have a new update.",
    icon: payload.icon || '/static/icons/icon-192x192.png',
    badge: '/static/icons/icon-96x96.png',
    data: { url: payload.url || '/' }
  };
  
  console.log('🔔 [SW] Displaying notification:', title);
  event.waitUntil(self.registration.showNotification(title, options));
});

// --- Notification Click Handler ---

self.addEventListener('notificationclick', event => {
  console.log('[SW] Event: notificationclick');
  event.notification.close();
  const urlToOpen = new URL(event.notification.data.url, self.location.origin).href;

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true })
      .then(clientList => {
        for (const client of clientList) {
          if (client.url === urlToOpen && 'focus' in client) {
            return client.focus();
          }
        }
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});