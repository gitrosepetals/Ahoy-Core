const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

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
  pricing_notes: string | null;
  seasonal_offers: unknown;
  local_seo_keywords: string[] | null;
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
  voice_feedback_url?: string | null;
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
    pricing_notes?: string | null;
    seasonal_offers?: unknown;
    local_seo_keywords?: string[] | null;
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
    fan_out?: boolean;
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

export async function crewEditCaption(
  accessToken: string,
  postId: string,
  caption: string,
  scheduledPublishAt?: string,
) {
  const res = await fetch(`${API_BASE}/queue/${postId}/caption`, {
    method: "PUT",
    headers: authHeaders(accessToken),
    body: JSON.stringify({
      caption_text: caption,
      ...(scheduledPublishAt ? { scheduled_publish_at: scheduledPublishAt } : {}),
    }),
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
  period: "billing" | "rolling";
  period_start: string;
  period_end: string;
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
  qualified_call_min_seconds: number;
  detail: {
    impressions: number;
    clicks: number;
    ctr: number | null;
    gbp_direction_requests: number;
    cost_per_lead_usd: number | null;
  };
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
  impressions: number;
  clicks: number;
};

/** Omit ``days`` for the current billing period (PRD Story 2.1). */
export async function fetchRoi(accessToken: string, clientId: string, days?: number) {
  const q = days ? `?days=${days}` : "";
  const res = await fetch(`${API_BASE}/clients/${clientId}/roi${q}`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<RoiSummary>;
}

export async function fetchRoiBreakdown(accessToken: string, clientId: string, days?: number) {
  const q = days ? `?days=${days}` : "";
  const res = await fetch(`${API_BASE}/clients/${clientId}/roi/breakdown${q}`, {
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
  reply_due_at: string | null;
  reply_posted_at: string | null;
  reply_error: string | null;
  can_reply: boolean;
};

export async function listReviews(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/reviews`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ReviewItem[]>;
}

export async function approveReviewReply(accessToken: string, reviewId: string, replyText?: string) {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/approve-reply`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: replyText ? JSON.stringify({ reply_text: replyText }) : undefined,
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

export type NotificationItem = {
  notification_id: string;
  kind: string;
  channel: "push" | "sms" | "log";
  status: "sent" | "failed" | "logged";
  deep_link: string | null;
  body: string | null;
  error: string | null;
  created_at: string | null;
};

export async function listNotifications(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/notifications`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<NotificationItem[]>;
}

export type ClientSettings = {
  client_id: string;
  business_name: string;
  twilio_tracking_number: string | null;
  gbp_location_id: string | null;
  pos_provider: string | null;
  average_ticket_value: number;
  conversion_rate_estimate: number;
  billing_anchor_day: number;
  forward_to_number: string | null;
  record_calls: boolean;
  timezone: string;
  auto_reply_delay_hours: number;
  facebook_page_id: string | null;
  yelp_business_id: string | null;
  lead_form_key: string | null;
  lead_form_url: string | null;
  twilio_voice_webhook_url: string;
};

export type Integration = { provider: string; connected: boolean; updated_at: string | null };

export async function getClientSettings(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/settings`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ClientSettings>;
}

export async function updateClientSettings(
  accessToken: string,
  clientId: string,
  body: Partial<
    Omit<
      ClientSettings,
      "client_id" | "business_name" | "lead_form_key" | "lead_form_url" | "twilio_voice_webhook_url"
    >
  >,
) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/settings`, {
    method: "PATCH",
    headers: authHeaders(accessToken, clientId),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ClientSettings>;
}

export async function listIntegrations(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/integrations`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Integration[]>;
}

export async function putAyrshareKey(accessToken: string, clientId: string, profileKey: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/integrations/ayrshare`, {
    method: "PUT",
    headers: authHeaders(accessToken, clientId),
    body: JSON.stringify({ profile_key: profileKey }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Integration>;
}

export async function retryPublish(accessToken: string, postId: string) {
  const res = await fetch(`${API_BASE}/queue/${postId}/publish-retry`, {
    method: "POST",
    headers: authHeaders(accessToken),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ContentQueueItem>;
}

export async function markPublished(accessToken: string, postId: string) {
  const res = await fetch(`${API_BASE}/queue/${postId}/mark-published`, {
    method: "POST",
    headers: authHeaders(accessToken),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ContentQueueItem>;
}

export type LeadEventItem = {
  event_id: string;
  event_type: "tracked_call" | "form_lead" | "gbp_direction";
  occurred_at: string;
  duration_seconds: number | null;
  qualified: boolean;
  caller: string | null;
  call_status: string | null;
  has_recording: boolean;
  name: string | null;
  email: string | null;
  phone: string | null;
  message: string | null;
};

export async function fetchRoiLeads(accessToken: string, clientId: string, days?: number) {
  const q = days ? `?days=${days}` : "";
  const res = await fetch(`${API_BASE}/clients/${clientId}/roi/leads${q}`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<LeadEventItem[]>;
}

/** Recording is proxied through the API (bearer auth), so fetch it as a blob URL for <audio>. */
export async function fetchRecordingUrl(accessToken: string, clientId: string, eventId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/leads/${eventId}/recording`, {
    headers: { Authorization: `Bearer ${accessToken}`, "X-Client-Id": clientId },
  });
  if (!res.ok) throw new Error(await parseError(res));
  return URL.createObjectURL(await res.blob());
}

export async function putManualMetrics(
  accessToken: string,
  clientId: string,
  body: {
    metric_date: string;
    ad_spend_usd?: number;
    impressions?: number;
    clicks?: number;
    gbp_direction_requests?: number;
    pos_attributed_revenue_usd?: number;
  },
) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/roi/manual`, {
    method: "PUT",
    headers: authHeaders(accessToken, clientId),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<RoiDayRow>;
}

export async function skipReviewReply(accessToken: string, reviewId: string) {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/skip-reply`, {
    method: "POST",
    headers: authHeaders(accessToken),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ReviewItem>;
}

export async function syncReviews(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/reviews/sync`, {
    method: "POST",
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<{ new: number; errors: string[] }>;
}

export async function startGoogleConnect(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/integrations/google/start`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<{ auth_url: string }>;
}

export async function listGoogleLocations(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/integrations/google/locations`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Array<{ name: string; title: string | null }>>;
}

export async function putFacebookPage(
  accessToken: string,
  clientId: string,
  body: { page_id: string; page_access_token: string },
) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/integrations/facebook`, {
    method: "PUT",
    headers: authHeaders(accessToken, clientId),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Integration>;
}

export async function requestEditVoice(accessToken: string, postId: string, audio: Blob) {
  const form = new FormData();
  const ext = audio.type.includes("mp4") ? "m4a" : audio.type.includes("ogg") ? "ogg" : "webm";
  form.append("audio", audio, `voice-note.${ext}`);
  const res = await fetch(`${API_BASE}/queue/${postId}/request-edit-voice`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ContentQueueItem>;
}

export type BillingInfo = {
  tier: "harbor" | "cruiser" | "flagship";
  subscription_status: string;
  current_period_end: string | null;
  has_customer: boolean;
  billing_enabled: boolean;
};

export async function getBilling(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/billing`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<BillingInfo>;
}

export async function createCheckout(accessToken: string, clientId: string, tier: BillingInfo["tier"]) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/billing/checkout`, {
    method: "POST",
    headers: authHeaders(accessToken, clientId),
    body: JSON.stringify({ tier }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<{ url: string }>;
}

export async function createBillingPortal(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/billing/portal`, {
    method: "POST",
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<{ url: string }>;
}

export async function passThroughAdSpend(
  accessToken: string,
  clientId: string,
  body: { amount_usd: number; description?: string },
) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/billing/ad-spend`, {
    method: "POST",
    headers: authHeaders(accessToken, clientId),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<{ invoice_item_id: string }>;
}

export type AuditEventItem = {
  audit_id: string;
  actor_role: string;
  actor_user_id: string | null;
  entity_type: string;
  entity_id: string | null;
  action: string;
  from_status: string | null;
  to_status: string | null;
  created_at: string | null;
};

export async function listAuditEvents(accessToken: string, clientId: string) {
  const res = await fetch(`${API_BASE}/clients/${clientId}/audit`, {
    headers: authHeaders(accessToken, clientId),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<AuditEventItem[]>;
}

export type ClientKpis = {
  client_id: string;
  business_name: string;
  approvals_30d: number;
  avg_time_to_approve_hours: number | null;
  approved_within_48h_pct: number | null;
  captain_active_30d: boolean;
  captain_last_seen: string | null;
  notifications_30d: Record<string, number>;
  subscription_status: string;
};

export type KpiReport = {
  clients: ClientKpis[];
  summary: {
    client_count: number;
    avg_time_to_approve_hours: number | null;
    captain_active_30d_pct: number | null;
    logo_churn_pct: number | null;
    targets: Record<string, string>;
  };
};

export async function fetchKpis(accessToken: string) {
  const res = await fetch(`${API_BASE}/kpis`, { headers: authHeaders(accessToken) });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<KpiReport>;
}
