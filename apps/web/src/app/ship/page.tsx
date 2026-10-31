"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchMe,
  fetchRoi,
  fetchRoiBreakdown,
  MeResponse,
  registerPushToken,
  RoiDayRow,
  RoiSummary,
} from "@/lib/api";
import { clearAccessToken, getAccessToken } from "@/lib/session";
import { IconCoins, IconCompass } from "@/components/pirate/Icons";
import { ShipHeader } from "@/components/pirate/ShipHeader";
import { AhoyReveal } from "@/components/AhoyReveal";

function money(n: number) {
  return n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export default function ShipPage() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [roi, setRoi] = useState<RoiSummary | null>(null);
  const [breakdown, setBreakdown] = useState<RoiDayRow[]>([]);
  const [showBreakdown, setShowBreakdown] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pushStatus, setPushStatus] = useState<string | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setError("Not signed in");
      return;
    }
    // Me first (paint shell), then ROI summary only — breakdown loads on demand.
    fetchMe(token)
      .then(async (profile) => {
        setMe(profile);
        const clientId = profile.clients[0]?.client_id ?? profile.user.client_ids[0];
        if (!clientId) return;
        setRoi(await fetchRoi(token, clientId, 30));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, []);

  useEffect(() => {
    if (!showBreakdown || breakdown.length > 0 || !me) return;
    const token = getAccessToken();
    if (!token) return;
    const clientId = me.clients[0]?.client_id ?? me.user.client_ids[0];
    if (!clientId) return;
    fetchRoiBreakdown(token, clientId, 30)
      .then(setBreakdown)
      .catch(() => setBreakdown([]));
  }, [showBreakdown, breakdown.length, me]);

  async function registerDevPush() {
    const token = getAccessToken();
    if (!token) return;
    try {
      await registerPushToken(token, {
        token: `web-dev-token-${Date.now()}`,
        platform: "web",
      });
      setPushStatus("Push token registered (dev stub).");
    } catch (err) {
      setPushStatus(err instanceof Error ? err.message : "Push register failed");
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

  return (
    <main className="mx-auto max-w-2xl space-y-6 px-6 py-12">
      <AhoyReveal variant="sail">
        <ShipHeader icon={<IconCompass />} title="Treasure Map">
          <p className="ahoy-muted mt-3">
            Ahoy, Captain {me.user.full_name}
            {me.clients[0] ? ` · ${me.clients[0].business_name}` : ""}.
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
              <p className="ahoy-muted mt-2">Last {roi.days} days · tap for breakdown</p>
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

      {showBreakdown && (
        <AhoyReveal variant="drop">
          <section className="ahoy-panel p-4">
            <h2 className="ahoy-title-sm">Daily breakdown</h2>
            <p className="ahoy-muted mt-1">
              Est. = (calls + forms) × {((roi?.conversion_rate_estimate ?? 0.25) * 100).toFixed(0)}% ×{" "}
              {money(roi?.average_ticket_value ?? 150)}
            </p>
            <ul className="mt-3 space-y-2">
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
          </section>
        </AhoyReveal>
      )}

      <AhoyReveal variant="heave" delay={80}>
        <div className="flex flex-wrap gap-3">
          <Link href="/ship/posts?tab=pending" className="ahoy-btn">
            Open the Manifest
          </Link>
          <button type="button" onClick={registerDevPush} className="ahoy-btn-ghost">
            Register push token (dev)
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
