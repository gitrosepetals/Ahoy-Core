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

export type BrandProfile = {
  profile_id: string;
  client_id: string;
  brand_voice_guidelines: string;
  target_zip_codes: string[] | null;
  compliance_rules: string | null;
  services_offered: unknown;
  has_embedding: boolean;
  updated_at: string | null;
};

export type MediaAsset = {
  asset_id: string;
  client_id: string;
  storage_url: string;
  thumbnail_url: string | null;
  asset_type: string;
  ai_tags: string[] | null;
  is_used: boolean;
  created_at: string | null;
};

export type ContentQueueItem = {
  post_id: string;
  client_id: string;
  asset_id: string | null;
  channel: string;
  caption_text: string;
  scheduled_publish_at: string;
  status: string;
  client_feedback: string | null;
  generation_meta: Record<string, unknown> | null;
  created_at: string | null;
};

function authHeaders(token?: string | null, clientId?: string | null): HeadersInit {
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (clientId) headers["X-Client-Id"] = clientId;
  return headers;
}

async function parseError(res: Response): Promise<string> {
  const text = await res.text();
  try {
    const j = JSON.parse(text);
    if (typeof j.detail === "string") return j.detail;
    return text;
  } catch {
    return text;
  }
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
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<{
    message: string;
    dev_magic_link?: string | null;
    expires_in_minutes: number;
  }>;
}

export async function verifyMagicLink(token: string) {
  const res = await fetch(`${API_BASE}/auth/verify?token=${encodeURIComponent(token)}`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<TokenResponse>;
}

export async function fetchMe(accessToken: string) {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: authHeaders(accessToken),
  });
  if (!res.ok) throw new Error(await parseError(res));
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
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function getBrandProfile(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/brand-profile`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<BrandProfile>;
}

export async function putBrandProfile(
  accessToken: string,
  clientId: string,
  body: {
    brand_voice_guidelines: string;
    target_zip_codes?: string[] | null;
    compliance_rules?: string | null;
    services_offered?: unknown;
  },
) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/brand-profile`, {
    method: "PUT",
    headers: authHeaders(accessToken, clientId),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<BrandProfile>;
}

export async function listMedia(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/media`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<MediaAsset[]>;
}

export async function registerMedia(
  accessToken: string,
  clientId: string,
  body: {
    storage_url: string;
    thumbnail_url?: string | null;
    asset_type?: string;
    ai_tags?: string[] | null;
  },
) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/media`, {
    method: "POST",
    headers: authHeaders(accessToken, clientId),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<MediaAsset>;
}

export async function uploadMedia(accessToken: string, clientId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  form.append("asset_type", "raw_photo");
  const res = await fetch(`${API_BASE}/clients/${clientId}/media/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "X-Client-Id": clientId,
    },
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<MediaAsset>;
}

export async function generateCampaign(
  accessToken: string,
  clientId: string,
  body: {
    asset_ids?: string[];
    channels?: string[];
    days?: number;
    count?: number;
  },
) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/campaigns/generate`, {
    method: "POST",
    headers: authHeaders(accessToken, clientId),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ContentQueueItem[]>;
}

export async function listQueue(accessToken: string, clientId: string, status?: string) {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  const res = await fetch(`${API_BASE}/clients/${clientId}/queue${q}`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ContentQueueItem[]>;
}

export async function releaseQueue(accessToken: string, clientId: string, postIds?: string[]) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/queue/release`, {
    method: "POST",
    headers: authHeaders(accessToken, clientId),
    body: JSON.stringify(postIds ? { post_ids: postIds } : {}),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ContentQueueItem[]>;
}

export async function approvePost(accessToken: string, postId: string) {
  const res = await fetch(`${API_BASE}/queue/${postId}/approve`, {
    method: "POST",
    headers: authHeaders(accessToken),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ContentQueueItem>;
}

export async function requestEdit(accessToken: string, postId: string, feedback: string) {
  const res = await fetch(`${API_BASE}/queue/${postId}/request-edit`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify({ feedback }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ContentQueueItem>;
}

export async function swapAsset(accessToken: string, postId: string, assetId: string) {
  const res = await fetch(`${API_BASE}/queue/${postId}/swap-asset`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify({ asset_id: assetId }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ContentQueueItem>;
}

export async function approveAllQueue(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/queue/approve-all`, {
    method: "POST",
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ContentQueueItem[]>;
}

export type RoiSummary = {
  client_id: string;
  days: number;
  total_calls: number;
  total_form_leads: number;
  total_leads: number;
  total_reviews: number;
  total_ad_spend_usd: number;
  total_pos_revenue_usd: number;
  estimated_revenue_usd: number;
  using_pos: boolean;
  average_ticket_value: number;
  conversion_rate_estimate: number;
};

export type RoiDayRow = {
  metric_date: string;
  tracked_calls_count: number;
  form_leads_count: number;
  gbp_direction_requests: number;
  new_reviews_count: number;
  ad_spend_usd: number;
  pos_attributed_revenue_usd: number;
  estimated_revenue_usd: number;
};

export async function fetchRoi(accessToken: string, clientId: string, days = 30) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/roi?days=${days}`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<RoiSummary>;
}

export async function fetchRoiBreakdown(accessToken: string, clientId: string, days = 30) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/roi/breakdown?days=${days}`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<RoiDayRow[]>;
}

export type ReviewItem = {
  review_id: string;
  client_id: string;
  provider: string;
  external_id: string;
  rating: number;
  body: string | null;
  reviewer_name: string | null;
  ai_reply: string | null;
  reply_status: string | null;
  reviewed_at: string | null;
  created_at: string | null;
  needs_captain: boolean;
};

export async function listReviews(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/reviews`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ReviewItem[]>;
}

export async function approveReviewReply(accessToken: string, reviewId: string) {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/approve-reply`, {
    method: "POST",
    headers: authHeaders(accessToken),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ReviewItem>;
}

export async function submitMarketingLead(input: {
  email: string;
  business_name?: string;
  source?: string;
}) {
  const res = await fetch(`${API_BASE}/marketing/leads`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      email: input.email,
      business_name: input.business_name || null,
      source: input.source || "welcome",
    }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<{ ok: boolean; email: string }>;
}
