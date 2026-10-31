"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchMe, listMedia, MediaAsset } from "@/lib/api";
import { getAccessToken } from "@/lib/session";

export default function ShipMediaPage() {
  const [media, setMedia] = useState<MediaAsset[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setError("Not signed in");
      return;
    }
    fetchMe(token)
      .then(async (me) => {
        const cid = me.clients[0]?.client_id ?? me.user.client_ids[0];
        if (!cid) return;
        setMedia(await listMedia(token, cid));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
  }, []);

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

  return (
    <main className="mx-auto max-w-2xl space-y-6 px-6 py-12">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.16em] text-sky-800">The Ship</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Media vault</h1>
        <p className="ahoy-muted mt-2">Read-only view of your Crew-managed assets.</p>
      </div>
      {error && <p className="text-sm text-red-700">{error}</p>}
      <ul className="space-y-3">
        {media.map((a) => (
          <li
            key={a.asset_id}
            className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={a.thumbnail_url || a.storage_url}
              alt=""
              className="h-16 w-16 rounded-md object-cover"
            />
            <div>
              <p className="font-medium text-slate-900">{a.asset_type}</p>
              <p className="ahoy-muted text-sm">{(a.ai_tags || []).join(", ") || "no tags"}</p>
            </div>
          </li>
        ))}
        {media.length === 0 && !error && (
          <li className="ahoy-muted rounded-xl border border-dashed border-slate-300 px-4 py-8 text-center">
            No media yet.
          </li>
        )}
      </ul>
    </main>
  );
}
