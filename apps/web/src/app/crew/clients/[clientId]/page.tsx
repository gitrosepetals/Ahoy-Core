"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AuditEventItem,
  BillingInfo,
  BrandProfile,
  ClientSettings,
  createCheckout,
  getBilling,
  passThroughAdSpend,
  ContentQueueItem,
  crewEditCaption,
  generateCampaign,
  getBrandProfile,
  getClientSettings,
  Integration,
  listGoogleLocations,
  listAuditEvents,
  listIntegrations,
  listMedia,
  listNotifications,
  listQueue,
  markPublished,
  MediaAsset,
  NotificationItem,
  putAyrshareKey,
  putBrandProfile,
  putFacebookPage,
  putManualMetrics,
  releaseQueue,
  retryPublish,
  startGoogleConnect,
  syncReviews,
  updateClientSettings,
  uploadMedia,
} from "@/lib/api";
import { getAccessToken } from "@/lib/session";
import { AhoyBackLink } from "@/components/AhoyBackLink";

const CHANNELS = [
  { id: "instagram_post", label: "Instagram post" },
  { id: "instagram_reel", label: "Instagram Reel" },
  { id: "facebook", label: "Facebook" },
  { id: "tiktok", label: "TikTok" },
  { id: "gbp_update", label: "Google Business update" },
  { id: "email_blast", label: "Email newsletter" },
] as const;

type PostsTab = "drafts" | "needs_crew" | "expired" | "pending" | "approved";

function toLocalInput(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function needsCrew(p: ContentQueueItem) {
  return p.status === "changes_requested" && Boolean(p.generation_meta?.needs_crew);
}

function publishState(p: ContentQueueItem): { label: string; tone: "ok" | "warn" | "muted" } {
  const meta = p.generation_meta || {};
  if (p.status === "published")
    return { label: p.generation_meta?.published_manually_by ? "Sent manually" : "Published", tone: "ok" };
  if (meta.needs_manual_publish) return { label: "Send manually", tone: "warn" };
  if (meta.publish_failed) return { label: `Publish failed: ${String(meta.publish_error ?? "")}`, tone: "warn" };
  if (meta.publish_error) return { label: `Retrying: ${String(meta.publish_error)}`, tone: "warn" };
  return { label: "Scheduled", tone: "muted" };
}

function splitList(v: string) {
  return v
    .split(",")
    .map((z) => z.trim())
    .filter(Boolean);
}

export default function CrewClientPage() {
  const params = useParams();
  const clientId = String(params.clientId);

  const [brand, setBrand] = useState<BrandProfile | null>(null);
  const [voice, setVoice] = useState("");
  const [zips, setZips] = useState("");
  const [compliance, setCompliance] = useState("");
  const [servicesJson, setServicesJson] = useState("{}");
  const [pricing, setPricing] = useState("");
  const [offersJson, setOffersJson] = useState("[]");
  const [seoKeywords, setSeoKeywords] = useState("");
  const [media, setMedia] = useState<MediaAsset[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [queue, setQueue] = useState<ContentQueueItem[]>([]);
  const [count, setCount] = useState(4);
  const [days, setDays] = useState(7);
  const [channels, setChannels] = useState<Set<string>>(
    new Set(["instagram_post", "facebook", "tiktok", "gbp_update", "email_blast"]),
  );
  const [fanOut, setFanOut] = useState(true);
  const [editing, setEditing] = useState<{ postId: string; text: string; when?: string } | null>(
    null,
  );
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [clientSettings, setClientSettings] = useState<ClientSettings | null>(null);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [ayrshareKey, setAyrshareKey] = useState("");
  const [fbPage, setFbPage] = useState({ page_id: "", page_access_token: "" });
  const [billing, setBilling] = useState<BillingInfo | null>(null);
  const [audit, setAudit] = useState<AuditEventItem[]>([]);
  const [checkoutTier, setCheckoutTier] = useState<BillingInfo["tier"]>("cruiser");
  const [checkoutUrl, setCheckoutUrl] = useState<string | null>(null);
  const [adSpend, setAdSpend] = useState({ amount: "", description: "Ad spend (pass-through)" });
  const [gbpLocations, setGbpLocations] = useState<Array<{ name: string; title: string | null }>>(
    [],
  );
  const [manual, setManual] = useState({
    metric_date: new Date().toISOString().slice(0, 10),
    ad_spend_usd: "",
    impressions: "",
    clicks: "",
    gbp_direction_requests: "",
  });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [postsTab, setPostsTab] = useState<PostsTab>("drafts");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const token = typeof window !== "undefined" ? getAccessToken() : null;

  const refresh = useCallback(async () => {
    const access = getAccessToken();
    if (!access) {
      setError("Not signed in");
      return;
    }
    const [b, m, q, n, cs, ints] = await Promise.all([
      getBrandProfile(access, clientId),
      listMedia(access, clientId),
      listQueue(access, clientId),
      listNotifications(access, clientId).catch(() => [] as NotificationItem[]),
      getClientSettings(access, clientId).catch(() => null),
      listIntegrations(access, clientId).catch(() => [] as Integration[]),
    ]);
    setNotifications(n);
    setClientSettings(cs);
    setIntegrations(ints);
    listAuditEvents(access, clientId)
      .then(setAudit)
      .catch(() => setAudit([]));
    getBilling(access, clientId)
      .then((bi) => {
        setBilling(bi);
        setCheckoutTier(bi.tier);
      })
      .catch(() => setBilling(null));
    setBrand(b);
    setVoice(b.brand_voice_guidelines);
    setZips((b.target_zip_codes || []).join(", "));
    setCompliance(b.compliance_rules || "");
    setServicesJson(JSON.stringify(b.services_offered ?? {}, null, 2));
    setPricing(b.pricing_notes || "");
    setOffersJson(JSON.stringify(b.seasonal_offers ?? [], null, 2));
    setSeoKeywords((b.local_seo_keywords || []).join(", "));
    setMedia(m);
    setQueue(q);
    setSelected(new Set(m.map((a) => a.asset_id)));
  }, [clientId]);

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
  }, [refresh]);

  async function saveBrand() {
    const access = getAccessToken();
    if (!access) return;
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      let services: unknown = {};
      let offers: unknown = [];
      try {
        services = JSON.parse(servicesJson || "{}");
      } catch {
        throw new Error("services_offered must be valid JSON");
      }
      try {
        offers = JSON.parse(offersJson || "[]");
      } catch {
        throw new Error("Seasonal offers must be valid JSON");
      }
      const updated = await putBrandProfile(access, clientId, {
        brand_voice_guidelines: voice,
        target_zip_codes: splitList(zips),
        compliance_rules: compliance,
        services_offered: services,
        pricing_notes: pricing || null,
        seasonal_offers: offers,
        local_seo_keywords: splitList(seoKeywords),
      });
      setBrand(updated);
      setMessage(
        updated.has_embedding
          ? "Brand Brain saved (embedding updated)."
          : "Brand Brain saved.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(file: File | null) {
    const access = getAccessToken();
    if (!access || !file) return;
    setBusy(true);
    setError(null);
    try {
      await uploadMedia(access, clientId, file);
      await refresh();
      setMessage(`Uploaded ${file.name}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function onGenerate() {
    const access = getAccessToken();
    if (!access) return;
    setBusy(true);
    setError(null);
    try {
      const posts = await generateCampaign(access, clientId, {
        asset_ids: Array.from(selected),
        channels: CHANNELS.map((c) => c.id).filter((c) => channels.has(c)),
        days,
        count,
        fan_out: fanOut,
      });
      setMessage(`Generated ${posts.length} draft posts.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generate failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRelease() {
    const access = getAccessToken();
    if (!access) return;
    setBusy(true);
    setError(null);
    try {
      const drafts = queue.filter((p) => p.status === "draft_internal").map((p) => p.post_id);
      const released = await releaseQueue(access, clientId, drafts.length ? drafts : undefined);
      setMessage(`Released ${released.length} posts to Captain.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Release failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveCaption() {
    const access = getAccessToken();
    if (!access || !editing) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await crewEditCaption(
        access,
        editing.postId,
        editing.text,
        editing.when ? new Date(editing.when).toISOString() : undefined,
      );
      setEditing(null);
      setMessage(
        updated.status === "pending_client"
          ? "Caption fixed and sent back to the Captain."
          : "Caption saved.",
      );
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function run(action: () => Promise<unknown>, ok: string) {
    setBusy(true);
    setError(null);
    try {
      await action();
      setMessage(ok);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  function saveClientSettings() {
    const access = getAccessToken();
    if (!access || !clientSettings) return;
    const body = {
      twilio_tracking_number: clientSettings.twilio_tracking_number,
      gbp_location_id: clientSettings.gbp_location_id,
      pos_provider: clientSettings.pos_provider,
      average_ticket_value: clientSettings.average_ticket_value,
      conversion_rate_estimate: clientSettings.conversion_rate_estimate,
      billing_anchor_day: clientSettings.billing_anchor_day,
      forward_to_number: clientSettings.forward_to_number,
      record_calls: clientSettings.record_calls,
      timezone: clientSettings.timezone,
      auto_reply_delay_hours: clientSettings.auto_reply_delay_hours,
      yelp_business_id: clientSettings.yelp_business_id,
    };
    void run(() => updateClientSettings(access, clientId, body), "Client settings saved.");
  }

  function saveManualMetrics() {
    const access = getAccessToken();
    if (!access) return;
    const num = (v: string) => (v.trim() === "" ? undefined : Number(v));
    void run(
      () =>
        putManualMetrics(access, clientId, {
          metric_date: manual.metric_date,
          ad_spend_usd: num(manual.ad_spend_usd),
          impressions: num(manual.impressions),
          clicks: num(manual.clicks),
          gbp_direction_requests: num(manual.gbp_direction_requests),
        }),
      `Metrics saved for ${manual.metric_date}.`,
    );
  }

  function makeCheckoutLink() {
    const access = getAccessToken();
    if (!access) return;
    void run(async () => {
      const { url } = await createCheckout(access, clientId, checkoutTier);
      setCheckoutUrl(url);
      void navigator.clipboard?.writeText(url);
    }, "Checkout link created and copied — send it to the Captain.");
  }

  function addAdSpend() {
    const access = getAccessToken();
    const amount = Number(adSpend.amount);
    if (!access || !(amount > 0)) return;
    void run(async () => {
      await passThroughAdSpend(access, clientId, { amount_usd: amount, description: adSpend.description });
      setAdSpend({ ...adSpend, amount: "" });
    }, "Ad spend added to the next invoice.");
  }

  function connectGoogle() {
    const access = getAccessToken();
    if (!access) return;
    void run(async () => {
      const { auth_url } = await startGoogleConnect(access, clientId);
      window.location.href = auth_url;
    }, "Opening Google…");
  }

  function loadGbpLocations() {
    const access = getAccessToken();
    if (!access) return;
    void run(async () => setGbpLocations(await listGoogleLocations(access, clientId)), "Locations loaded.");
  }

  function saveFacebook() {
    const access = getAccessToken();
    if (!access) return;
    void run(async () => {
      await putFacebookPage(access, clientId, fbPage);
      setFbPage({ page_id: "", page_access_token: "" });
    }, "Facebook Page connected (token encrypted).");
  }

  function syncNow() {
    const access = getAccessToken();
    if (!access) return;
    void run(async () => {
      const res = await syncReviews(access, clientId);
      if (res.errors.length) throw new Error(res.errors.join("; "));
    }, "Reviews synced — new ones are drafted and scheduled.");
  }

  function saveAyrshare() {
    const access = getAccessToken();
    if (!access || !ayrshareKey.trim()) return;
    void run(async () => {
      await putAyrshareKey(access, clientId, ayrshareKey.trim());
      setAyrshareKey("");
    }, "Ayrshare profile key saved (encrypted).");
  }

  function toggleIn(setter: typeof setSelected, id: string) {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (!token && error === "Not signed in") {
    return (
      <main className="mx-auto max-w-lg px-6 py-16">
        <p className="ahoy-error">Not signed in</p>
        <Link href="/auth/sign-in" className="ahoy-btn mt-4">
          Sign in
        </Link>
      </main>
    );
  }

  if (!brand && !error) {
    return <main className="p-8 ahoy-muted">Loading client…</main>;
  }

  const drafts = queue.filter((p) => p.status === "draft_internal");
  const flagged = queue.filter(needsCrew);
  const pending = queue.filter(
    (p) => p.status === "pending_client" || (p.status === "changes_requested" && !needsCrew(p)),
  );
  const approved = queue.filter(
    (p) => p.status === "approved" || p.status === "published",
  );
  const expired = queue.filter((p) => p.status === "expired");
  const tabPosts = { drafts, needs_crew: flagged, expired, pending, approved }[postsTab];
  const emptyCopy = {
    drafts: "No drafts — Generate drafts above.",
    needs_crew: "No flagged revisions — the AI handled every edit request.",
    expired: "Nothing expired — the Captain approved everything in time.",
    pending: "Nothing awaiting the Captain — Release drafts when ready.",
    approved: "No approved posts yet.",
  }[postsTab];
  const editable = postsTab === "drafts" || postsTab === "needs_crew" || postsTab === "expired";

  return (
    <main className="mx-auto max-w-4xl space-y-10 px-6 py-12">
      <div>
        <AhoyBackLink href="/crew">Crew Deck</AhoyBackLink>
        <p className="mt-3 ahoy-kicker">Crew Deck</p>
        <h1 className="ahoy-title mt-2">Client berth</h1>
        <div className="ahoy-brass-rule" />
        <p className="mt-2 ahoy-muted">{clientId}</p>
      </div>

      {message && <p className="ahoy-success">{message}</p>}
      {error && <p className="ahoy-error">{error}</p>}

      <section className="space-y-3">
        <h2 className="ahoy-title-sm">Brand Brain</h2>
        <p className="ahoy-muted">
          Voice, zips, compliance, services, pricing, seasonal offers and SEO keywords — all of it
          goes into every caption, revision and review reply. Embedding recomputed on save when
          LLM is available (or in LLM_DEV_MODE).
          {brand?.has_embedding ? " Embedding present." : ""}
        </p>
        <label className="block text-base">
          <span className="ahoy-label">Brand voice</span>
          <textarea
            className="ahoy-input mt-1"
            rows={4}
            value={voice}
            onChange={(e) => setVoice(e.target.value)}
          />
        </label>
        <label className="block text-base">
          <span className="ahoy-label">Target ZIP codes (comma-separated)</span>
          <input
            className="ahoy-input mt-1"
            value={zips}
            onChange={(e) => setZips(e.target.value)}
          />
        </label>
        <label className="block text-base">
          <span className="ahoy-label">Compliance</span>
          <textarea
            className="ahoy-input mt-1"
            rows={3}
            value={compliance}
            onChange={(e) => setCompliance(e.target.value)}
          />
        </label>
        <label className="block text-base">
          <span className="ahoy-label">Services (JSON)</span>
          <textarea
            className="ahoy-input mt-1"
            rows={6}
            value={servicesJson}
            onChange={(e) => setServicesJson(e.target.value)}
          />
        </label>
        <label className="block text-base">
          <span className="ahoy-label">Pricing</span>
          <textarea
            className="ahoy-input mt-1"
            rows={2}
            value={pricing}
            onChange={(e) => setPricing(e.target.value)}
          />
        </label>
        <label className="block text-base">
          <span className="ahoy-label">Seasonal offers (JSON list)</span>
          <textarea
            className="ahoy-input mt-1"
            rows={4}
            value={offersJson}
            onChange={(e) => setOffersJson(e.target.value)}
          />
        </label>
        <label className="block text-base">
          <span className="ahoy-label">Local SEO keywords (comma-separated)</span>
          <input
            className="ahoy-input mt-1"
            value={seoKeywords}
            onChange={(e) => setSeoKeywords(e.target.value)}
          />
        </label>
        <button
          type="button"
          disabled={busy}
          onClick={saveBrand}
          className="ahoy-btn"
        >
          Save Brand Brain
        </button>
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="ahoy-title-sm">Media vault</h2>
          <p className="ahoy-muted mt-1">
            Uploads are auto-tagged (staff, exterior, product, testimonial…) for campaign pairing.
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="sr-only"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0] ?? null;
            void onUpload(file);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          disabled={busy}
          onClick={() => fileInputRef.current?.click()}
          className="ahoy-btn"
        >
          Upload photo
        </button>
        <ul className="space-y-3">
          {media.map((a) => {
            const thumb = a.thumbnail_url || a.storage_url;
            return (
              <li
                key={a.asset_id}
                className="flex items-start gap-3 ahoy-panel p-3"
              >
                <input
                  type="checkbox"
                  className="mt-2"
                  checked={selected.has(a.asset_id)}
                  onChange={() => toggleIn(setSelected, a.asset_id)}
                />
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={thumb}
                  alt={a.ai_tags?.join(", ") || a.asset_type}
                  className="h-20 w-20 shrink-0 rounded-md border border-[var(--ahoy-panel-border)] object-cover bg-[var(--ahoy-void)]"
                />
                <div className="min-w-0 flex-1">
                  <p className="ahoy-label">{a.asset_type}</p>
                  <p className="ahoy-muted mt-1">
                    {(a.ai_tags || []).join(", ") || "no tags"}
                    {a.is_used ? " · used" : ""}
                  </p>
                </div>
              </li>
            );
          })}
          {media.length === 0 && (
            <li className="rounded-md border border-dashed border-[var(--ahoy-panel-border)] px-4 py-8 text-center">
              <p className="ahoy-muted">No media yet.</p>
              <button
                type="button"
                disabled={busy}
                onClick={() => fileInputRef.current?.click()}
                className="mt-3 ahoy-btn"
              >
                Upload photo
              </button>
              <p className="ahoy-muted mt-2">
                Or apply seed migration 003 for Oak Lawn placeholders.
              </p>
            </li>
          )}
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="ahoy-title-sm">Generate campaign</h2>
        <div className="flex flex-wrap gap-4">
          <label className="ahoy-label">
            Post slots{" "}
            <input
              type="number"
              min={1}
              max={20}
              className="ahoy-input ml-1 !inline-block w-16"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
            />
          </label>
          <label className="ahoy-label">
            Days{" "}
            <input
              type="number"
              min={1}
              max={60}
              className="ahoy-input ml-1 !inline-block w-16"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            />
          </label>
        </div>
        <fieldset className="flex flex-wrap gap-x-5 gap-y-2">
          <legend className="ahoy-label mb-2">Channels</legend>
          {CHANNELS.map((c) => (
            <label key={c.id} className="flex items-center gap-2 text-base">
              <input
                type="checkbox"
                checked={channels.has(c.id)}
                onChange={() => toggleIn(setChannels, c.id)}
              />
              {c.label}
            </label>
          ))}
        </fieldset>
        <label className="flex items-center gap-2 text-base">
          <input type="checkbox" checked={fanOut} onChange={(e) => setFanOut(e.target.checked)} />
          One version per channel for every slot ({fanOut ? count * channels.size : count} drafts)
        </label>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled={busy || channels.size === 0}
            onClick={onGenerate}
            className="ahoy-btn"
          >
            Generate drafts
          </button>
          <button
            type="button"
            disabled={busy || drafts.length === 0}
            onClick={onRelease}
            className="ahoy-btn-ghost disabled:opacity-50"
          >
            Release to Captain ({drafts.length})
          </button>
        </div>
      </section>

      <section className="space-y-3">
        <div>
          <h2 className="ahoy-title-sm">Posts</h2>
          <p className="ahoy-muted mt-1">
            Split by stage — drafts stay internal until you release them to the Captain. “Needs
            crew” holds edit requests the AI could not rewrite; “Expired” holds posts the Captain
            didn’t approve before their publish time — reschedule to send them back.
          </p>
        </div>
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Post status">
          {(
            [
              { id: "drafts" as const, label: "Drafts", count: drafts.length },
              { id: "needs_crew" as const, label: "Needs crew", count: flagged.length },
              { id: "expired" as const, label: "Expired", count: expired.length },
              { id: "pending" as const, label: "Awaiting Captain", count: pending.length },
              { id: "approved" as const, label: "Approved", count: approved.length },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={postsTab === tab.id}
              onClick={() => setPostsTab(tab.id)}
              className={postsTab === tab.id ? "ahoy-tab ahoy-tab-active" : "ahoy-tab"}
            >
              {tab.label} ({tab.count})
            </button>
          ))}
        </div>
        <div className="overflow-x-auto ahoy-panel">
          <table className="w-full text-left text-base">
            <thead className="bg-[var(--ahoy-void)] text-[var(--ahoy-foam-dim)]">
              <tr>
                <th className="px-3 py-3 ahoy-label">Channel</th>
                <th className="px-3 py-3 ahoy-label">Caption</th>
                <th className="px-3 py-3 ahoy-label">When</th>
                {editable && <th className="px-3 py-3 ahoy-label" />}
              </tr>
            </thead>
            <tbody>
              {tabPosts.map((p) => (
                <tr key={p.post_id} className="border-t border-[var(--ahoy-panel-border)] align-top">
                  <td className="px-3 py-3 whitespace-nowrap text-[var(--ahoy-foam-dim)]">{p.channel}</td>
                  <td className="ahoy-prose max-w-md px-3 py-3">
                    {postsTab === "needs_crew" && p.client_feedback && (
                      <p className="ahoy-label mb-2">Captain asked: “{p.client_feedback}”</p>
                    )}
                    {postsTab === "needs_crew" && p.voice_feedback_url && (
                      <audio className="mb-2 w-full" controls src={p.voice_feedback_url} />
                    )}
                    {editing?.postId === p.post_id ? (
                      <div className="space-y-2">
                        <textarea
                          className="ahoy-input"
                          rows={5}
                          value={editing.text}
                          onChange={(e) => setEditing({ ...editing, text: e.target.value })}
                        />
                        {postsTab === "expired" && (
                          <label className="block">
                            <span className="ahoy-label">New publish time</span>
                            <input
                              type="datetime-local"
                              className="ahoy-input mt-1"
                              value={editing.when ?? ""}
                              onChange={(e) => setEditing({ ...editing, when: e.target.value })}
                            />
                          </label>
                        )}
                        <div className="flex gap-2">
                          <button
                            type="button"
                            disabled={
                              busy ||
                              !editing.text.trim() ||
                              (postsTab === "expired" && !editing.when)
                            }
                            onClick={saveCaption}
                            className="ahoy-btn"
                          >
                            {postsTab === "drafts" ? "Save" : "Save & send to Captain"}
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditing(null)}
                            className="ahoy-btn-ghost"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <span className="whitespace-pre-line">{p.caption_text}</span>
                    )}
                  </td>
                  <td className="ahoy-muted px-3 py-3 whitespace-nowrap">
                    {new Date(p.scheduled_publish_at).toLocaleString()}
                    {postsTab === "approved" && (() => {
                      const st = publishState(p);
                      const access = getAccessToken();
                      const meta = p.generation_meta || {};
                      return (
                        <div className="mt-2 space-y-2 whitespace-normal">
                          <p className={st.tone === "warn" ? "ahoy-error" : "ahoy-label"}>{st.label}</p>
                          {access && p.status === "approved" && Boolean(meta.publish_failed) && (
                            <button
                              type="button"
                              disabled={busy}
                              className="ahoy-btn-ghost"
                              onClick={() => void run(() => retryPublish(access, p.post_id), "Will retry on the next worker run.")}
                            >
                              Retry
                            </button>
                          )}
                          {access && p.status === "approved" && (Boolean(meta.needs_manual_publish) || Boolean(meta.publish_failed)) && (
                            <button
                              type="button"
                              disabled={busy}
                              className="ahoy-btn-ghost"
                              onClick={() => void run(() => markPublished(access, p.post_id), "Marked as sent.")}
                            >
                              Mark sent
                            </button>
                          )}
                        </div>
                      );
                    })()}
                  </td>
                  {editable && (
                    <td className="px-3 py-3">
                      {editing?.postId !== p.post_id && (
                        <button
                          type="button"
                          onClick={() =>
                            setEditing({
                              postId: p.post_id,
                              text: p.caption_text,
                              when:
                                postsTab === "expired"
                                  ? toLocalInput(new Date(Date.now() + 2 * 86400000))
                                  : undefined,
                            })
                          }
                          className="ahoy-btn-ghost"
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
              {tabPosts.length === 0 && (
                <tr>
                  <td colSpan={editable ? 4 : 3} className="ahoy-muted px-3 py-4">
                    {emptyCopy}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {clientSettings && (
        <section className="space-y-3">
          <h2 className="ahoy-title-sm">Client settings &amp; integrations</h2>
          <p className="ahoy-muted">
            Tracking number routes Twilio calls to this client; GBP location id is used for reviews
            and posts; POS provider switches the Treasure Map from estimate to POS revenue.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {(
              [
                ["twilio_tracking_number", "Twilio tracking number", "text"],
                ["gbp_location_id", "Google Business location id", "text"],
                ["pos_provider", "POS provider (blank = estimate)", "text"],
                ["average_ticket_value", "Average ticket ($)", "number"],
                ["conversion_rate_estimate", "Lead conversion rate (0-1)", "number"],
                ["billing_anchor_day", "Billing day of month (1-28)", "number"],
                ["forward_to_number", "Forward tracked calls to", "text"],
                ["timezone", "Timezone (e.g. America/Chicago)", "text"],
                ["auto_reply_delay_hours", "Auto-reply delay for 4-5★ (hours, 0-72)", "number"],
                ["yelp_business_id", "Yelp business id (read-only reviews)", "text"],
              ] as const
            ).map(([key, label, type]) => (
              <label key={key} className="block text-base">
                <span className="ahoy-label">{label}</span>
                <input
                  className="ahoy-input mt-1"
                  type={type}
                  step={key === "conversion_rate_estimate" ? "0.01" : undefined}
                  value={clientSettings[key] ?? ""}
                  onChange={(e) =>
                    setClientSettings({
                      ...clientSettings,
                      [key]: type === "number" ? Number(e.target.value) : e.target.value,
                    })
                  }
                />
              </label>
            ))}
          </div>
          <label className="flex items-center gap-2 text-base">
            <input
              type="checkbox"
              checked={clientSettings.record_calls}
              onChange={(e) =>
                setClientSettings({ ...clientSettings, record_calls: e.target.checked })
              }
            />
            Record tracked calls (callers hear a recording notice first)
          </label>
          <button type="button" disabled={busy} onClick={saveClientSettings} className="ahoy-btn">
            Save client settings
          </button>
          <div className="ahoy-panel space-y-1 p-3">
            <p className="ahoy-label">Wiring</p>
            <p className="ahoy-muted break-all">
              Twilio number → Voice webhook (POST): {clientSettings.twilio_voice_webhook_url}
            </p>
            <p className="ahoy-muted break-all">
              Website form action (POST, fields name/email/phone/message, optional _redirect):{" "}
              {clientSettings.lead_form_url ?? "—"}
            </p>
          </div>
          <div className="ahoy-panel space-y-2 p-3">
            <p className="ahoy-label">
              Manual metrics (ad spend, impressions/clicks, directions — until those APIs are
              connected)
            </p>
            <div className="grid gap-2 sm:grid-cols-5">
              <input
                type="date"
                className="ahoy-input"
                value={manual.metric_date}
                onChange={(e) => setManual({ ...manual, metric_date: e.target.value })}
              />
              {(
                [
                  ["ad_spend_usd", "Ad $"],
                  ["impressions", "Impressions"],
                  ["clicks", "Clicks"],
                  ["gbp_direction_requests", "Directions"],
                ] as const
              ).map(([key, label]) => (
                <input
                  key={key}
                  type="number"
                  min={0}
                  placeholder={label}
                  aria-label={label}
                  className="ahoy-input"
                  value={manual[key]}
                  onChange={(e) => setManual({ ...manual, [key]: e.target.value })}
                />
              ))}
            </div>
            <button type="button" disabled={busy} onClick={saveManualMetrics} className="ahoy-btn-ghost">
              Save metrics
            </button>
          </div>
          <div className="ahoy-panel space-y-2 p-3">
            <p className="ahoy-label">
              Google Business Profile (reviews, replies, impressions){" "}
              {integrations.some((i) => i.provider === "google") ? "· connected" : "· not connected"}
            </p>
            <div className="flex flex-wrap gap-2">
              <button type="button" disabled={busy} onClick={connectGoogle} className="ahoy-btn-ghost">
                Connect Google (Captain signs in)
              </button>
              {integrations.some((i) => i.provider === "google") && (
                <button type="button" disabled={busy} onClick={loadGbpLocations} className="ahoy-btn-ghost">
                  Choose location
                </button>
              )}
            </div>
            {gbpLocations.length > 0 && (
              <select
                className="ahoy-input"
                value={clientSettings.gbp_location_id ?? ""}
                onChange={(e) =>
                  setClientSettings({ ...clientSettings, gbp_location_id: e.target.value })
                }
              >
                <option value="">Select a location, then Save client settings</option>
                {gbpLocations.map((l) => (
                  <option key={l.name} value={l.name}>
                    {l.title ?? l.name}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div className="ahoy-panel space-y-2 p-3">
            <p className="ahoy-label">
              Facebook Page (ratings + replies){" "}
              {integrations.some((i) => i.provider === "facebook") ? "· connected" : "· not connected"}
            </p>
            <div className="grid gap-2 sm:grid-cols-3">
              <input
                className="ahoy-input"
                placeholder="Page id"
                value={fbPage.page_id}
                onChange={(e) => setFbPage({ ...fbPage, page_id: e.target.value })}
              />
              <input
                className="ahoy-input sm:col-span-2"
                type="password"
                placeholder="Long-lived Page access token"
                value={fbPage.page_access_token}
                onChange={(e) => setFbPage({ ...fbPage, page_access_token: e.target.value })}
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busy || !fbPage.page_id || fbPage.page_access_token.length < 20}
                onClick={saveFacebook}
                className="ahoy-btn-ghost"
              >
                Save Facebook
              </button>
              <button type="button" disabled={busy} onClick={syncNow} className="ahoy-btn-ghost">
                Sync reviews now
              </button>
            </div>
          </div>
          <div className="ahoy-panel space-y-2 p-3">
            <p className="ahoy-label">
              Ayrshare (publishing){" "}
              {integrations.some((i) => i.provider === "ayrshare") ? "· connected" : "· not connected"}
            </p>
            <div className="flex flex-wrap gap-2">
              <input
                className="ahoy-input !w-auto flex-1"
                type="password"
                placeholder="Ayrshare profile key"
                value={ayrshareKey}
                onChange={(e) => setAyrshareKey(e.target.value)}
              />
              <button
                type="button"
                disabled={busy || ayrshareKey.trim().length < 8}
                onClick={saveAyrshare}
                className="ahoy-btn-ghost"
              >
                Save key
              </button>
            </div>
          </div>
        </section>
      )}

      {billing && (
        <section className="space-y-3">
          <h2 className="ahoy-title-sm">Billing</h2>
          <p className="ahoy-muted">
            Plan <strong className="capitalize">{billing.tier}</strong> · status{" "}
            {billing.subscription_status}
            {billing.current_period_end
              ? ` · renews ${new Date(billing.current_period_end).toLocaleDateString()}`
              : ""}
            {billing.billing_enabled ? "" : " · Stripe not configured (STRIPE_SECRET_KEY)"}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <select
              className="ahoy-input !w-auto"
              value={checkoutTier}
              onChange={(e) => setCheckoutTier(e.target.value as BillingInfo["tier"])}
            >
              <option value="harbor">Harbor</option>
              <option value="cruiser">Cruiser</option>
              <option value="flagship">Flagship</option>
            </select>
            <button
              type="button"
              disabled={busy || !billing.billing_enabled}
              onClick={makeCheckoutLink}
              className="ahoy-btn-ghost"
            >
              Create checkout link
            </button>
          </div>
          {checkoutUrl && <p className="ahoy-muted break-all">{checkoutUrl}</p>}
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="number"
              min={0}
              step="0.01"
              placeholder="Ad spend $"
              className="ahoy-input !w-32"
              value={adSpend.amount}
              onChange={(e) => setAdSpend({ ...adSpend, amount: e.target.value })}
            />
            <input
              className="ahoy-input !w-auto flex-1"
              value={adSpend.description}
              onChange={(e) => setAdSpend({ ...adSpend, description: e.target.value })}
            />
            <button
              type="button"
              disabled={busy || !billing.billing_enabled || !(Number(adSpend.amount) > 0)}
              onClick={addAdSpend}
              className="ahoy-btn-ghost"
            >
              Bill ad spend
            </button>
          </div>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="ahoy-title-sm">Captain notifications</h2>
        <p className="ahoy-muted">
          Push first, SMS with a 48-hour sign-in link as fallback. “log” means dev mode
          (nothing was sent).
        </p>
        <ul className="space-y-2">
          {notifications.slice(0, 10).map((n) => (
            <li key={n.notification_id} className="ahoy-panel p-3">
              <p className="ahoy-label">
                {n.kind} · {n.channel} · {n.status}
                {n.created_at ? ` · ${new Date(n.created_at).toLocaleString()}` : ""}
              </p>
              {n.body && <p className="ahoy-muted mt-1 break-words">{n.body}</p>}
              {n.error && <p className="ahoy-error mt-1">{n.error}</p>}
            </li>
          ))}
          {notifications.length === 0 && <li className="ahoy-muted">No notifications yet.</li>}
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="ahoy-title-sm">Ship’s log (audit)</h2>
        <p className="ahoy-muted">Every post, review, integration and billing change — and who made it.</p>
        <ul className="space-y-1">
          {audit.slice(0, 25).map((e) => (
            <li key={e.audit_id} className="ahoy-muted border-t border-[var(--ahoy-panel-border)] pt-1">
              {e.created_at ? new Date(e.created_at).toLocaleString() : ""} · {e.actor_role} ·{" "}
              {e.entity_type} {e.action}
              {e.from_status || e.to_status ? ` (${e.from_status ?? "—"} → ${e.to_status ?? "—"})` : ""}
            </li>
          ))}
          {audit.length === 0 && <li className="ahoy-muted">Nothing logged yet.</li>}
        </ul>
      </section>
    </main>
  );
}
