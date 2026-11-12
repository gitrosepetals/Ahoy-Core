"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchKpis, fetchMe, KpiReport, MeResponse } from "@/lib/api";
import { clearAccessToken, getAccessToken } from "@/lib/session";
import { IconAnchor } from "@/components/pirate/Icons";
import { AhoyReveal } from "@/components/AhoyReveal";

export default function CrewDeckPage() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [kpis, setKpis] = useState<KpiReport | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setError("Not signed in");
      return;
    }
    fetchKpis(token)
      .then(setKpis)
      .catch(() => setKpis(null));
    fetchMe(token)
      .then(setMe)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, []);

  if (error) {
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
    return <main className="p-8 ahoy-muted">Loading Crew Deck…</main>;
  }

  return (
    <main className="mx-auto max-w-3xl space-y-6 px-6 py-12">
        <AhoyReveal variant="sail">
          <div>
            <p className="ahoy-kicker">Crew Deck</p>
            <h1 className="ahoy-title mt-2 flex items-center gap-3">
              <span className="text-[var(--ahoy-brass)]" aria-hidden>
                <IconAnchor />
              </span>
              Ahoy, {me.user.full_name}
            </h1>
            <div className="ahoy-brass-rule" />
            <p className="ahoy-muted mt-3">
              Role: {me.user.role}. Open a client berth for Brand Brain and campaigns.
            </p>
            {me.user.role !== "crew" && me.user.role !== "admin" && (
              <p className="ahoy-muted mt-2">
                You are signed in as {me.user.role}. Brand Brain needs Crew — sign in with{" "}
                <code>+15551234002</code>.
              </p>
            )}
          </div>
        </AhoyReveal>
        <AhoyReveal variant="heave" delay={80}>
          <div className="ahoy-panel overflow-hidden">
            <table className="w-full text-left">
              <thead>
                <tr>
                  <th className="px-4 py-2">Client</th>
                  <th className="px-4 py-2">Vertical</th>
                  <th className="px-4 py-2">Tier</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {me.clients.map((c) => (
                  <tr key={c.client_id} className="border-t border-[var(--ahoy-panel-border)]">
                    <td className="ahoy-strong px-4 py-2">{c.business_name}</td>
                    <td className="px-4 py-2">{c.industry_vertical}</td>
                    <td className="px-4 py-2">{c.tier}</td>
                    <td className="px-4 py-2 text-right">
                      <Link href={`/crew/clients/${c.client_id}`} className="ahoy-btn inline-block">
                        Brand Brain &amp; campaigns
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </AhoyReveal>
        {kpis && kpis.clients.length > 0 && (
          <section className="ahoy-panel space-y-3 p-4">
            <h2 className="ahoy-title-sm">Pilot KPIs (last 30 days)</h2>
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <p className="ahoy-label">Avg time to approve</p>
                <p className="ahoy-stat">
                  {kpis.summary.avg_time_to_approve_hours ?? "—"}
                  {kpis.summary.avg_time_to_approve_hours != null ? "h" : ""}
                </p>
                <p className="ahoy-muted">target {kpis.summary.targets.avg_time_to_approve_hours}h</p>
              </div>
              <div>
                <p className="ahoy-label">Captains active</p>
                <p className="ahoy-stat">{kpis.summary.captain_active_30d_pct ?? "—"}%</p>
                <p className="ahoy-muted">target {kpis.summary.targets.captain_active_30d_pct}%</p>
              </div>
              <div>
                <p className="ahoy-label">Logo churn</p>
                <p className="ahoy-stat">
                  {kpis.summary.logo_churn_pct == null ? "—" : `${kpis.summary.logo_churn_pct}%`}
                </p>
                <p className="ahoy-muted">target {kpis.summary.targets.logo_churn_pct}%</p>
              </div>
            </div>
            <table className="w-full text-left">
              <thead>
                <tr>
                  <th className="py-1">Client</th>
                  <th className="py-1">Approve (avg h)</th>
                  <th className="py-1">&lt;48h</th>
                  <th className="py-1">Captain active</th>
                  <th className="py-1">Billing</th>
                </tr>
              </thead>
              <tbody>
                {kpis.clients.map((k) => (
                  <tr key={k.client_id} className="border-t border-[var(--ahoy-panel-border)]">
                    <td className="py-1">{k.business_name}</td>
                    <td className="py-1">{k.avg_time_to_approve_hours ?? "—"}</td>
                    <td className="py-1">
                      {k.approved_within_48h_pct == null ? "—" : `${k.approved_within_48h_pct}%`}
                    </td>
                    <td className="py-1">{k.captain_active_30d ? "yes" : "no"}</td>
                    <td className="py-1">{k.subscription_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
        {me.clients.length === 0 && (
          <p className="ahoy-error">
            No clients assigned. Sign in as Crew (+15551234002), not Captain.
          </p>
        )}
        <AhoyReveal delay={120}>
          <button
            type="button"
            className="ahoy-btn-ghost"
            onClick={() => {
              clearAccessToken();
              window.location.href = "/auth/sign-in";
            }}
          >
            Sign out
          </button>
        </AhoyReveal>
      </main>
  );
}
