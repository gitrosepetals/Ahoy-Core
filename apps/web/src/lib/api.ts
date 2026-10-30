const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type AuthUser = {
  user_id: string;
  email: string;
  full_name: string;
  phone_number: string | null;
  role: "captain" | "crew" | "deckhand" | "admin";
  client_ids: string[];
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: AuthUser;
  redirect_path: string;
};

export type MeResponse = {
  user: AuthUser;
  clients: Array<{
    client_id: string;
    business_name: string;
    industry_vertical: string;
    tier: string;
  }>;
};

function authHeaders(token?: string | null): HeadersInit {
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export async function requestMagicLink(input: {
  phone_number?: string;
  email?: string;
  redirect_path?: string;
}) {
  const res = await fetch(`${API_BASE}/auth/magic-link`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{
    message: string;
    dev_magic_link?: string | null;
    expires_in_minutes: number;
  }>;
}

export async function verifyMagicLink(token: string) {
  const res = await fetch(`${API_BASE}/auth/verify?token=${encodeURIComponent(token)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<TokenResponse>;
}

export async function fetchMe(accessToken: string) {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: authHeaders(accessToken),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<MeResponse>;
}

export async function registerPushToken(
  accessToken: string,
  body: { token: string; platform: "ios" | "android" | "web" },
) {
  const res = await fetch(`${API_BASE}/devices/push-token`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
