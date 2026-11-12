/**
 * Ship push + PWA helpers.
 *
 * Web: service worker `/sw.js` + Firebase Cloud Messaging token (the API pushes via FCM v1).
 * Configure NEXT_PUBLIC_FIREBASE_CONFIG (web app config JSON) and NEXT_PUBLIC_FIREBASE_VAPID_KEY.
 * Without them, `enableNotifications` registers a dev stub token so the local flow still works.
 * Native (Capacitor): register the FCM token from the PushNotifications plugin the same way.
 */
import { registerPushToken } from "@/lib/api";

export const SHIP_DEEP_LINK_PATHS = {
  verify: "/auth/verify",
  home: "/ship",
  queue: "/ship/posts?tab=pending",
  reviews: "/ship/reviews",
} as const;

export function parseNotificationDeepLink(data: Record<string, string> | undefined): string {
  if (!data) return SHIP_DEEP_LINK_PATHS.home;
  if (data.path) return data.path;
  if (data.post_id) return SHIP_DEEP_LINK_PATHS.queue;
  if (data.review_id) return SHIP_DEEP_LINK_PATHS.reviews;
  return SHIP_DEEP_LINK_PATHS.home;
}

function firebaseConfig(): Record<string, string> | null {
  const raw = process.env.NEXT_PUBLIC_FIREBASE_CONFIG;
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function swUrl(): string {
  const cfg = firebaseConfig();
  return cfg ? `/sw.js?fb=${encodeURIComponent(btoa(JSON.stringify(cfg)))}` : "/sw.js";
}

export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return null;
  try {
    return await navigator.serviceWorker.register(swUrl(), { scope: "/" });
  } catch {
    return null;
  }
}

export type PushResult = "enabled" | "dev-stub" | "denied" | "unsupported";

/** Ask permission, get an FCM token, and register it for the signed-in Captain. */
export async function enableNotifications(accessToken: string): Promise<PushResult> {
  const cfg = firebaseConfig();
  const vapidKey = process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY;
  if (!cfg || !vapidKey) {
    await registerPushToken(accessToken, { token: `web-dev-token-${Date.now()}`, platform: "web" });
    return "dev-stub";
  }
  if (typeof window === "undefined" || !("Notification" in window)) return "unsupported";
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return "denied";

  const registration = await registerServiceWorker();
  if (!registration) return "unsupported";
  const [{ initializeApp, getApps }, messaging] = await Promise.all([
    import("firebase/app"),
    import("firebase/messaging"),
  ]);
  if (!(await messaging.isSupported())) return "unsupported";
  const app = getApps()[0] ?? initializeApp(cfg);
  const token = await messaging.getToken(messaging.getMessaging(app), {
    vapidKey,
    serviceWorkerRegistration: registration,
  });
  if (!token) return "denied";
  await registerPushToken(accessToken, { token, platform: "web" });
  return "enabled";
}
