"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchMe, MeResponse, registerPushToken } from "@/lib/api";
import { clearAccessToken, getAccessToken } from "@/lib/session";

export default function ShipPage() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pushStatus, setPushStatus] = useState<string | null>(null);

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

  if (error) {
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
    <main className="mx-auto max-w-2xl px-6 py-12">
      <p className="text-sm uppercase tracking-[0.2em] text-sky-700">The Ship</p>
      <h1 className="mt-2 text-3xl font-semibold">Welcome aboard, Captain {me.user.full_name}</h1>
      <p className="mt-2 text-slate-600">
        Role: {me.user.role}. Treasure Map and approval queue arrive in later milestones.
      </p>
      <ul className="mt-6 space-y-2 rounded-xl border border-slate-200 bg-white p-4">
        {me.clients.map((c) => (
          <li key={c.client_id} className="text-sm">
            <span className="font-medium">{c.business_name}</span> · {c.industry_vertical} · {c.tier}
          </li>
        ))}
      </ul>
      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={registerDevPush}
          className="rounded-md bg-sky-800 px-3 py-2 text-sm text-white"
        >
          Register push token (dev)
        </button>
        <button
          type="button"
          onClick={() => {
            clearAccessToken();
            window.location.href = "/auth/sign-in";
          }}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        >
          Sign out
        </button>
      </div>
      {pushStatus && <p className="mt-3 text-sm text-slate-600">{pushStatus}</p>}
    </main>
  );
}
