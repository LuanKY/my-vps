// ==============================================================================
// MyVPS - Service Worker
// Provides PWA capabilities, app shell offline caching, and ensures real-time
// WebSocket telemetry and dynamic API data are NEVER cached.
// ==============================================================================

const CACHE_NAME = "myvps-cache-v1";

const APP_SHELL_ASSETS = [
  "./",
  "./index.html",
  "./script.js",
  "./manifest.webmanifest",
  "./icons/favicon.svg",
  "./icons/icon-192x192.png",
  "./icons/icon-512x512.png",
  "./icons/maskable-icon-192x192.png",
  "./icons/maskable-icon-512x512.png",
  "./icons/apple-touch-icon.png",
  "./icons/favicon-32x32.png",
  "./icons/favicon-16x16.png",
  "./icons/favicon.ico"
];

// Install: Cache essential app shell assets and activate immediately
self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(APP_SHELL_ASSETS).catch((err) => {
        console.warn("Some non-critical assets failed to cache during install:", err);
      });
    })
  );
});

// Activate: Clean up any old caches and claim connected clients
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: Strategy for requests
self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // 1. Never intercept non-GET requests
  if (request.method !== "GET") {
    return;
  }

  // 2. CRITICAL: Never intercept or cache WebSocket handshakes, dynamic telemetry metrics or health checks
  if (
    url.pathname.includes("/ws/") ||
    url.pathname.endsWith("/data") ||
    url.pathname.endsWith("/health") ||
    url.pathname.startsWith("/api/")
  ) {
    return; // Pass through directly to network
  }

  // 3. Stale-While-Revalidate for app shell and static resources
  event.respondWith(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.match(request).then((cachedResponse) => {
        const fetchPromise = fetch(request)
          .then((networkResponse) => {
            // Only cache valid standard responses
            if (networkResponse && networkResponse.status === 200 && networkResponse.type === "basic") {
              cache.put(request, networkResponse.clone());
            }
            return networkResponse;
          })
          .catch((fetchError) => {
            // If network fails and we have a cached response, that's already handled
            return cachedResponse;
          });

        return cachedResponse || fetchPromise;
      });
    })
  );
});
