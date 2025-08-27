// HomeGrubHub Service Worker - PWA Offline Support
const CACHE_NAME = 'homegrubhub-v1.0.0';
const OFFLINE_PAGE = '/offline';

// Assets to cache immediately
const CORE_ASSETS = [
  '/',
  '/offline',
  '/static/style.css',
  '/static/HomeGrubHub.png',
  '/static/manifest.json',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// Install event - cache core assets
self.addEventListener('install', event => {
  console.log('HomeGrubHub Service Worker: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('HomeGrubHub Service Worker: Caching core assets');
        return cache.addAll(CORE_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('HomeGrubHub Service Worker: Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('HomeGrubHub Service Worker: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('HomeGrubHub Service Worker: Activated');
      return self.clients.claim();
    })
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', event => {
  // Skip cross-origin requests
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // Handle navigation requests
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          return caches.match(OFFLINE_PAGE);
        })
    );
    return;
  }

  // Handle other requests with cache-first strategy
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }

        return fetch(event.request).then(response => {
          // Don't cache non-successful responses
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone the response for caching
          const responseToCache = response.clone();
          
          // Cache recipes and static assets
          if (event.request.url.includes('/recipes/') || 
              event.request.url.includes('/static/') ||
              event.request.url.includes('/dashboard')) {
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
          }

          return response;
        });
      })
      .catch(() => {
        // Return offline page for navigation requests
        if (event.request.mode === 'navigate') {
          return caches.match(OFFLINE_PAGE);
        }
      })
  );
});

// Background sync for offline actions
self.addEventListener('sync', event => {
  if (event.tag === 'background-sync') {
    console.log('HomeGrubHub Service Worker: Background sync triggered');
    event.waitUntil(
      // Handle any pending offline actions
      handleBackgroundSync()
    );
  }
});

// Push notification handling
self.addEventListener('push', event => {
  console.log('HomeGrubHub Service Worker: Push notification received');
  
  const options = {
    body: event.data ? event.data.text() : 'New notification from HomeGrubHub',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/icon-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'view',
        title: 'View',
        icon: '/static/icons/icon-72x72.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/static/icons/icon-72x72.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('HomeGrubHub', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
  console.log('HomeGrubHub Service Worker: Notification clicked');
  event.notification.close();

  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Helper function for background sync
async function handleBackgroundSync() {
  try {
    // Get any pending offline data from IndexedDB
    // This would handle offline recipe saves, shopping list updates, etc.
    console.log('HomeGrubHub Service Worker: Handling background sync');
    
    // Example: sync offline saved recipes
    const pendingRecipes = await getPendingRecipes();
    for (const recipe of pendingRecipes) {
      await syncRecipe(recipe);
    }
    
    return Promise.resolve();
  } catch (error) {
    console.error('HomeGrubHub Service Worker: Background sync failed:', error);
    return Promise.reject(error);
  }
}

// Placeholder functions for offline data handling
async function getPendingRecipes() {
  // Would integrate with IndexedDB to get offline-saved recipes
  return [];
}

async function syncRecipe(recipe) {
  // Would sync recipe data when back online
  return Promise.resolve();
}

// Allow service worker to control the root scope
// This comment is for reference: you must set the HTTP header 'Service-Worker-Allowed: /' in your server config for this file.