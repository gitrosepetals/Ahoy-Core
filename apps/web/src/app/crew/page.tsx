"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchMe, MeResponse } from "@/lib/api";
import { clearAccessToken, getAccessToken } from "@/lib/session";

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
        <p className="text-sm text-red-700">{error}</p>
        <Link href="/auth/sign-in" className="mt-4 inline-block text-sky-800 underline">
          Sign in
        </Link>
      </main>
    );
  }

  if (!me) {
    return <main className="p-8 text-sm text-slate-600">Loading Crew Deck…</main>;
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <p className="text-sm uppercase tracking-[0.2em] text-slate-500">Crew Deck</p>
      <h1 className="mt-2 text-3xl font-semibold">Ahoy, {me.user.full_name}</h1>
      <p className="mt-2 text-slate-600">
        Role: {me.user.role}. Brand Brain is inside each client workspace — click the button below.
      </p>
      {me.user.role !== "crew" && me.user.role !== "admin" && (
        <p className="mt-2 text-sm text-amber-800">
          You are signed in as {me.user.role}. Brand Brain needs Crew — sign in with{" "}
          <code>+15551234002</code>.
        </p>
      )}
      <div className="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Client</th>
              <th className="px-4 py-2 font-medium">Vertical</th>
              <th className="px-4 py-2 font-medium">Tier</th>
              <th className="px-4 py-2 font-medium" />
            </tr>
          </thead>
          <tbody>
            {me.clients.map((c) => (
              <tr key={c.client_id} className="border-t border-slate-100">
                <td className="px-4 py-2 font-medium">{c.business_name}</td>
                <td className="px-4 py-2">{c.industry_vertical}</td>
                <td className="px-4 py-2">{c.tier}</td>
                <td className="px-4 py-2 text-right">
                  <Link
                    href={`/crew/clients/${c.client_id}`}
                    className="inline-block rounded-md bg-sky-800 px-3 py-1.5 font-medium text-white"
                  >
                    Brand Brain &amp; campaigns
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {me.clients.length === 0 && (
        <p className="mt-4 text-sm text-red-700">
          No clients assigned. Sign in as Crew (+15551234002), not Captain.
        </p>
      )}
      <button
        type="button"
        className="mt-6 rounded-md border border-slate-300 px-3 py-2 text-sm"
        onClick={() => {
          clearAccessToken();
          window.location.href = "/auth/sign-in";
        }}
      >
        Sign out
      </button>
    </main>
  );
}
