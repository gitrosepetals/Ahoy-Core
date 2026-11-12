/* A-hoy Ship service worker (0.12.0): installable PWA + push notifications via FCM.
 *
 * Firebase web config arrives base64-encoded in the registration URL (?fb=...) because a
 * service worker can't read build-time env vars. No offline caching: the Ship is a live
 * approval tool and stale data would be worse than a network error.
 */
const FIREBASE_VERSION = "11.10.0";
const config = new URL(self.location.href).searchParams.get("fb");

if (config) {
  importScripts(
    `https://www.gstatic.com/firebasejs/${FIREBASE_VERSION}/firebase-app-compat.js`,
    `https://www.gstatic.com/firebasejs/${FIREBASE_VERSION}/firebase-messaging-compat.js`,
  );
  firebase.initializeApp(JSON.parse(atob(config)));
  // Background messages that carry a `notification` block are displayed by the SDK.
  firebase.messaging();
}

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const data = event.notification.data || {};
  const fcm = data.FCM_MSG || {};
  const path = (fcm.data && fcm.data.path) || data.path || "/ship";
  const target = new URL(path, self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((wins) => {
      for (const w of wins) {
        if (w.url.startsWith(self.location.origin) && "focus" in w) {
          w.navigate(target);
          return w.focus();
        }
      }
      return self.clients.openWindow(target);
    }),
  );
});
