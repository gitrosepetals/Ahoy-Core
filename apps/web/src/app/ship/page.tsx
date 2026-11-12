"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  BillingInfo,
  createBillingPortal,
  fetchMe,
  getBilling,
  fetchRecordingUrl,
  fetchRoi,
  fetchRoiBreakdown,
  fetchRoiLeads,
  LeadEventItem,
  MeResponse,
  RoiDayRow,
  RoiSummary,
} from "@/lib/api";
import { activeClientId, clearAccessToken, getAccessToken, pickActiveClient } from "@/lib/session";
import { enableNotifications } from "@/lib/push";
import { IconCoins, IconCompass } from "@/components/pirate/Icons";
import { ShipHeader } from "@/components/pirate/ShipHeader";
import { AhoyReveal } from "@/components/AhoyReveal";

const DETAIL_KEY = "ahoy_detailed_view";

function money(n: number) {
  return n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function periodLabel(roi: RoiSummary) {
  if (roi.period === "rolling") return `Last ${roi.days} days`;
  const start = new Date(`${roi.period_start}T00:00:00`);
  return `Since ${start.toLocaleDateString(undefined, { month: "short", day: "numeric" })} (this billing period)`;
}

function duration(s: number | null) {
  if (s == null) return "—";
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

function LeadRow({
  lead,
  token,
  clientId,
}: {
  lead: LeadEventItem;
  token: string;
  clientId: string;
}) {
  const [audio, setAudio] = useState<string | null>(null);
  const [audioError, setAudioError] = useState<string | null>(null);
  const when = new Date(lead.occurred_at).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

  if (lead.event_type === "form_lead") {
    return (
      <li className="border-t border-[var(--ahoy-panel-border)] py-2">
        <p className="ahoy-label">
          📝 Web form · {when}
        </p>
        <p className="ahoy-muted mt-1">
          {[lead.name, lead.email, lead.phone].filter(Boolean).join(" · ")}
        </p>
        {lead.message && <p className="ahoy-muted mt-1 italic">“{lead.message}”</p>}
      </li>
    );
  }

  return (
    <li className="border-t border-[var(--ahoy-panel-border)] py-2">
      <p className="ahoy-label">
        📞 Call · {when} · {duration(lead.duration_seconds)}{" "}
        {lead.qualified ? "· counted" : "· under 60s, not counted"}
      </p>
      <p className="ahoy-muted mt-1">
        {lead.caller ?? "Unknown caller"}
        {lead.call_status && lead.call_status !== "completed" ? ` · ${lead.call_status}` : ""}
      </p>
      {lead.has_recording && !audio && (
        <button
          type="button"
          className="ahoy-btn-ghost mt-2"
          onClick={() =>
            fetchRecordingUrl(token, clientId, lead.event_id)
              .then(setAudio)
              .catch((e) => setAudioError(e instanceof Error ? e.message : "Unavailable"))
          }
        >
          ▶ Play recording
        </button>
      )}
      {audio && <audio className="mt-2 w-full" controls autoPlay src={audio} />}
      {audioError && <p className="ahoy-error mt-1">{audioError}</p>}
    </li>
  );
}

export default function ShipPage() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [roi, setRoi] = useState<RoiSummary | null>(null);
  const [breakdown, setBreakdown] = useState<RoiDayRow[] | null>(null);
  const [leads, setLeads] = useState<LeadEventItem[]>([]);
  const [showBreakdown, setShowBreakdown] = useState(false);
  const [detailed, setDetailed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pushStatus, setPushStatus] = useState<string | null>(null);
  const [billing, setBilling] = useState<BillingInfo | null>(null);

  const clientId = me ? activeClientId(me) : undefined;

  useEffect(() => {
    try {
      setDetailed(window.localStorage.getItem(DETAIL_KEY) === "1");
    } catch {
      /* storage unavailable */
    }
    const token = getAccessToken();
    if (!token) {
      setError("Not signed in");
      return;
    }
    // Me first (paint shell), then ROI summary only — breakdown loads on demand.
    fetchMe(token)
      .then(async (profile) => {
        setMe(profile);
        const cid = activeClientId(profile);
        if (!cid) return;
        setRoi(await fetchRoi(token, cid));
        getBilling(token, cid)
          .then(setBilling)
          .catch(() => setBilling(null));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, []);

  useEffect(() => {
    if (!showBreakdown || breakdown !== null || !clientId) return;
    const token = getAccessToken();
    if (!token) return;
    Promise.all([fetchRoiBreakdown(token, clientId), fetchRoiLeads(token, clientId)])
      .then(([days, items]) => {
        setBreakdown(days);
        setLeads(items);
      })
      .catch(() => setBreakdown([]));
  }, [showBreakdown, breakdown, clientId]);

  function toggleDetailed() {
    setDetailed((v) => {
      try {
        window.localStorage.setItem(DETAIL_KEY, v ? "0" : "1");
      } catch {
        /* storage unavailable */
      }
      return !v;
    });
  }

  async function manageBilling() {
    const token = getAccessToken();
    if (!token || !clientId) return;
    try {
      const { url } = await createBillingPortal(token, clientId);
      window.location.href = url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Billing unavailable");
    }
  }

  async function turnOnNotifications() {
    const token = getAccessToken();
    if (!token) return;
    try {
      const result = await enableNotifications(token);
      setPushStatus(
        {
          enabled: "Notifications on — we’ll ping this device when the Manifest or Radar needs the Captain.",
          "dev-stub": "Dev mode: registered a stub token (set NEXT_PUBLIC_FIREBASE_* for real push).",
          denied: "Notifications are blocked — we’ll text you instead.",
          unsupported: "This browser can’t do push — we’ll text you instead.",
        }[result],
      );
    } catch (err) {
      setPushStatus(err instanceof Error ? err.message : "Couldn’t turn on notifications");
    }
  }

  if (error === "Not signed in") {
    return (
      <main className="mx-auto max-w-lg px-6 py-16">
        <p className="ahoy-error">{error}</p>
        <Link href="/auth/sign-in" className="ahoy-btn mt-4">
          Sign in
        </Link>
      </main>
    );
  }

  if (!me) {
    return <main className="p-8 ahoy-muted">Loading the Ship…</main>;
  }

  const token = getAccessToken();

  return (
    <main className="mx-auto max-w-2xl space-y-6 px-6 py-12">
      <AhoyReveal variant="sail">
        <ShipHeader icon={<IconCompass />} title="Treasure Map">
          <p className="ahoy-muted mt-3">
            Ahoy, Captain {me.user.full_name}
            {pickActiveClient(me) ? ` · ${pickActiveClient(me)?.business_name}` : ""}.
          </p>
        </ShipHeader>
      </AhoyReveal>

      {error && error !== "Not signed in" && (
        <p className="ahoy-error">{error}</p>
      )}

      {roi ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <AhoyReveal variant="heave" delay={40}>
            <button
              type="button"
              onClick={() => setShowBreakdown((v) => !v)}
              className="ahoy-panel p-4 text-left w-full"
            >
              <p className="flex items-center gap-2 ahoy-label">
                <IconCoins className="ahoy-mark text-[var(--ahoy-brass)]" />
                {roi.using_pos ? "POS revenue" : "Estimated revenue"}
              </p>
              <p className="ahoy-stat mt-2">{money(roi.estimated_revenue_usd)}</p>
              <p className="ahoy-muted mt-2">
                {periodLabel(roi)} · tap to see every call &amp; form
              </p>
            </button>
          </AhoyReveal>
          <AhoyReveal variant="sail" delay={90}>
            <div className="ahoy-panel p-4">
              <p className="ahoy-label">Total leads</p>
              <p className="ahoy-stat mt-2">{roi.total_leads}</p>
              <p className="ahoy-muted mt-2">
                {roi.total_calls} calls · {roi.total_form_leads} forms
              </p>
            </div>
          </AhoyReveal>
          <AhoyReveal variant="heave" delay={140}>
            <div className="ahoy-panel p-4">
              <p className="ahoy-label">New reviews</p>
              <p className="ahoy-stat mt-2">{roi.total_reviews}</p>
            </div>
          </AhoyReveal>
          <AhoyReveal variant="sail" delay={190}>
            <div className="ahoy-panel p-4">
              <p className="ahoy-label">Ad spend</p>
              <p className="ahoy-stat mt-2">{money(roi.total_ad_spend_usd)}</p>
            </div>
          </AhoyReveal>
        </div>
      ) : (
        <p className="ahoy-muted">Unfurling the Treasure Map…</p>
      )}

      {roi && (
        <div>
          <button type="button" onClick={toggleDetailed} className="ahoy-btn-ghost" aria-pressed={detailed}>
            {detailed ? "Hide detailed view" : "Detailed view"}
          </button>
          {detailed && (
            <AhoyReveal variant="drop">
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                <div className="ahoy-panel p-3">
                  <p className="ahoy-label">Impressions</p>
                  <p className="ahoy-stat mt-1">{roi.detail.impressions.toLocaleString()}</p>
                </div>
                <div className="ahoy-panel p-3">
                  <p className="ahoy-label">Clicks · CTR</p>
                  <p className="ahoy-stat mt-1">
                    {roi.detail.clicks.toLocaleString()}
                    <span className="ahoy-muted text-base">
                      {" "}
                      · {roi.detail.ctr == null ? "—" : `${(roi.detail.ctr * 100).toFixed(1)}%`}
                    </span>
                  </p>
                </div>
                <div className="ahoy-panel p-3">
                  <p className="ahoy-label">Direction requests</p>
                  <p className="ahoy-stat mt-1">{roi.detail.gbp_direction_requests}</p>
                </div>
                <div className="ahoy-panel p-3 sm:col-span-3">
                  <p className="ahoy-label">Cost per lead</p>
                  <p className="ahoy-stat mt-1">
                    {roi.detail.cost_per_lead_usd == null ? "—" : money(roi.detail.cost_per_lead_usd)}
                  </p>
                </div>
              </div>
            </AhoyReveal>
          )}
        </div>
      )}

      {showBreakdown && (
        <AhoyReveal variant="drop">
          <section className="ahoy-panel p-4">
            <h2 className="ahoy-title-sm">How we got this number</h2>
            <p className="ahoy-muted mt-1">
              {roi?.using_pos
                ? "Revenue attributed by your point-of-sale system."
                : `Est. = (calls over ${roi?.qualified_call_min_seconds ?? 60}s + forms) × ${((roi?.conversion_rate_estimate ?? 0.25) * 100).toFixed(0)}% × ${money(roi?.average_ticket_value ?? 150)}`}
            </p>
            {breakdown === null ? (
              <p className="ahoy-muted mt-3">Loading…</p>
            ) : (
              <>
                <h3 className="ahoy-label mt-4">Every lead</h3>
                <ul className="mt-1">
                  {token &&
                    clientId &&
                    leads.map((l) => (
                      <LeadRow key={l.event_id} lead={l} token={token} clientId={clientId} />
                    ))}
                  {leads.length === 0 && (
                    <li className="ahoy-muted py-2">
                      No tracked calls or form leads yet this period.
                    </li>
                  )}
                </ul>
                <h3 className="ahoy-label mt-4">By day</h3>
                <ul className="mt-1 space-y-2">
                  {breakdown.map((d) => (
                    <li
                      key={d.metric_date}
                      className="flex flex-wrap justify-between gap-2 border-t border-[var(--ahoy-panel-border)] py-2"
                    >
                      <span className="ahoy-label">{d.metric_date}</span>
                      <span className="ahoy-muted">
                        {d.tracked_calls_count} calls · {d.form_leads_count} forms ·{" "}
                        {money(d.estimated_revenue_usd)}
                      </span>
                    </li>
                  ))}
                  {breakdown.length === 0 && (
                    <li className="ahoy-muted py-2">No daily metrics in this window.</li>
                  )}
                </ul>
              </>
            )}
          </section>
        </AhoyReveal>
      )}

      {billing && billing.billing_enabled && (
        <section className="ahoy-panel flex flex-wrap items-center justify-between gap-3 p-4">
          <div>
            <p className="ahoy-label">Your Ship’s plan</p>
            <p className="ahoy-title-sm mt-1 capitalize">
              {billing.tier}
              {billing.subscription_status !== "active" && billing.subscription_status !== "none"
                ? ` · ${billing.subscription_status.replace("_", " ")}`
                : ""}
            </p>
            {billing.current_period_end && (
              <p className="ahoy-muted mt-1">
                Renews {new Date(billing.current_period_end).toLocaleDateString()}
              </p>
            )}
          </div>
          {billing.has_customer && (
            <button type="button" onClick={manageBilling} className="ahoy-btn-ghost">
              Manage billing
            </button>
          )}
        </section>
      )}

      <AhoyReveal variant="heave" delay={80}>
        <div className="flex flex-wrap gap-3">
          <Link href="/ship/posts?tab=pending" className="ahoy-btn">
            Open the Manifest
          </Link>
          <button type="button" onClick={turnOnNotifications} className="ahoy-btn-ghost">
            Turn on Ship alerts
          </button>
          <button
            type="button"
            onClick={() => {
              clearAccessToken();
              window.location.href = "/auth/sign-in";
            }}
            className="ahoy-btn-ghost"
          >
            Sign out
          </button>
        </div>
      </AhoyReveal>
      {pushStatus && <p className="ahoy-muted">{pushStatus}</p>}
    </main>
  );
}
