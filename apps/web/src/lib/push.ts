/**
 * Ship push registration helpers.
 * On native (Capacitor), call after sign-in once PushNotifications permission is granted.
 * On web, the Ship page uses a dev stub token via registerPushToken.
 */

export const SHIP_DEEP_LINK_PATHS = {
  verify: "/auth/verify",
  home: "/ship",
  queue: "/ship/posts?tab=pending",
  review: (id: string) => `/ship/reviews/${id}`,
} as const;

export function parseNotificationDeepLink(data: Record<string, string> | undefined): string {
  if (!data) return SHIP_DEEP_LINK_PATHS.home;
  if (data.path) return data.path;
  if (data.post_id) return `${SHIP_DEEP_LINK_PATHS.queue}?post=${data.post_id}`;
  if (data.review_id) return SHIP_DEEP_LINK_PATHS.review(data.review_id);
  return SHIP_DEEP_LINK_PATHS.home;
}
