"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchMe, MeResponse } from "@/lib/api";
import { clearAccessToken, getAccessToken } from "@/lib/session";
import { IconAnchor } from "@/components/pirate/Icons";
import { AhoyReveal } from "@/components/AhoyReveal";

export default function CrewDeckPage() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setError("Not signed in");
      return;
    }
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
