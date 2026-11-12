import type { MeResponse } from "@/lib/api";

const TOKEN_KEY = "ahoy_access_token";
const ACTIVE_CLIENT_KEY = "ahoy_active_client";

export function saveAccessToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function clearAccessToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(ACTIVE_CLIENT_KEY);
}

export function setActiveClientId(clientId: string) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(ACTIVE_CLIENT_KEY, clientId);
  } catch {
    /* storage unavailable */
  }
}

/** The business the Captain is looking at: their saved choice if still theirs, else the first. */
export function pickActiveClient(me: MeResponse): MeResponse["clients"][number] | undefined {
  let saved: string | null = null;
  try {
    saved = typeof window === "undefined" ? null : window.localStorage.getItem(ACTIVE_CLIENT_KEY);
  } catch {
    saved = null;
  }
  return me.clients.find((c) => c.client_id === saved) ?? me.clients[0];
}

export function activeClientId(me: MeResponse): string | undefined {
  return pickActiveClient(me)?.client_id ?? me.user.client_ids[0];
}
