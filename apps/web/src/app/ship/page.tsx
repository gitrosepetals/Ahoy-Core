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
    fetchMe(token)
      .then(async (profile) => {
        setMe(profile);
        const clientId = profile.clients[0]?.client_id ?? profile.user.client_ids[0];
        if (!clientId) return;
        const [summary, days] = await Promise.all([
          fetchRoi(token, clientId, 30),
          fetchRoiBreakdown(token, clientId, 30),
        ]);
        setRoi(summary);
        setBreakdown(days);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, []);

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
        <p className="text-sm text-red-700">{error}</p>
        <Link href="/auth/sign-in" className="mt-4 inline-block text-sky-800 underline">
          Sign in
        </Link>
      </main>
    );
  }

  if (!me) {
    return <main className="p-8 text-sm text-slate-600">Loading Ship…</main>;
  }

  return (
    <main className="mx-auto max-w-2xl space-y-6 px-6 py-12">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.16em] text-sky-800">The Ship</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
          Treasure Map
        </h1>
        <p className="ahoy-muted mt-2">
          Ahoy, Captain {me.user.full_name}
          {me.clients[0] ? ` · ${me.clients[0].business_name}` : ""}.
        </p>
      </div>

      {error && error !== "Not signed in" && <p className="text-sm text-red-700">{error}</p>}

      {roi ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => setShowBreakdown((v) => !v)}
            className="rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm"
          >
            <p className="text-sm font-medium text-slate-600">
              {roi.using_pos ? "POS revenue" : "Estimated revenue"}
            </p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">
              {money(roi.estimated_revenue_usd)}
            </p>
            <p className="ahoy-muted mt-2 text-sm">
              Last {roi.days} days · tap for breakdown
            </p>
          </button>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm font-medium text-slate-600">Total leads</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{roi.total_leads}</p>
            <p className="ahoy-muted mt-2 text-sm">
              {roi.total_calls} calls · {roi.total_form_leads} forms
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm font-medium text-slate-600">New reviews</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{roi.total_reviews}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm font-medium text-slate-600">Ad spend</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">
              {money(roi.total_ad_spend_usd)}
            </p>
          </div>
        </div>
      ) : (
        <p className="ahoy-muted">Loading Treasure Map…</p>
      )}

      {showBreakdown && (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-lg font-semibold text-slate-900">Daily breakdown</h2>
          <p className="ahoy-muted mt-1 text-sm">
            Est. = (calls + forms) × {((roi?.conversion_rate_estimate ?? 0.25) * 100).toFixed(0)}% ×{" "}
            {money(roi?.average_ticket_value ?? 150)}
          </p>
          <ul className="mt-3 space-y-2">
            {breakdown.map((d) => (
              <li
                key={d.metric_date}
                className="flex flex-wrap justify-between gap-2 border-t border-slate-100 py-2 text-sm"
              >
                <span className="font-medium text-slate-800">{d.metric_date}</span>
                <span className="text-slate-600">
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
      )}

      <div className="flex flex-wrap gap-3">
        <Link
          href="/ship/posts?tab=pending"
          className="rounded-md bg-sky-800 px-4 py-2.5 text-base font-medium text-white"
        >
          Open posts
        </Link>
        <button
          type="button"
          onClick={registerDevPush}
          className="rounded-md border border-slate-300 px-4 py-2.5 text-base font-medium text-slate-800"
        >
          Register push token (dev)
        </button>
        <button
          type="button"
          onClick={() => {
            clearAccessToken();
            window.location.href = "/auth/sign-in";
          }}
          className="rounded-md border border-slate-300 px-4 py-2.5 text-base font-medium text-slate-800"
        >
          Sign out
        </button>
      </div>
      {pushStatus && <p className="ahoy-muted">{pushStatus}</p>}
    </main>
  );
}
