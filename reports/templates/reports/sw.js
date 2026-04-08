const CACHE_NAME = 'stratix-pwa-v1';

// Install the Service Worker
self.addEventListener('install', event => {
    self.skipWaiting();
});

// Activate the Service Worker
self.addEventListener('activate', event => {
    event.waitUntil(clients.claim());
});

// Intercept network requests (Required for PWA installability)
self.addEventListener('fetch', event => {
    // We pass the request through normally so dynamic Django views always stay live
    event.respondWith(fetch(event.request).catch(error => {
        console.log('Network request failed, user might be offline.', error);
    }));
});
