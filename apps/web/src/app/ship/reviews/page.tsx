"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { approveReviewReply, fetchMe, listReviews, ReviewItem } from "@/lib/api";
import { getAccessToken } from "@/lib/session";

export default function ShipReviewsPage() {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setError("Not signed in");
      return;
    }
    const me = await fetchMe(token);
    const cid = me.clients[0]?.client_id ?? me.user.client_ids[0];
    if (!cid) return;
    setReviews(await listReviews(token, cid));
  }, []);

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
  }, [load]);

  async function onApprove(reviewId: string) {
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await approveReviewReply(token, reviewId);
      setReviews((prev) => prev.map((r) => (r.review_id === reviewId ? updated : r)));
      setMessage("Reply approved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setBusy(false);
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

  return (
    <main className="mx-auto max-w-2xl space-y-6 px-6 py-12">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.16em] text-sky-800">The Ship</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
          Reputation Radar
        </h1>
        <p className="ahoy-muted mt-2">
          4–5★ drafts auto-sent in MVP stub; 1–3★ need your one-click approve.
        </p>
      </div>
      {message && <p className="text-sm text-emerald-800">{message}</p>}
      {error && error !== "Not signed in" && <p className="text-sm text-red-700">{error}</p>}
      <ul className="space-y-4">
        {reviews.map((r) => (
          <li key={r.review_id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-600">
              {r.provider} · {"★".repeat(r.rating)}
              {r.needs_captain ? " · needs you" : ""}
            </p>
            <p className="mt-2 font-medium text-slate-900">{r.reviewer_name || "Guest"}</p>
            <p className="ahoy-prose mt-2">{r.body || "(no text)"}</p>
            {r.ai_reply && (
              <div className="mt-3 rounded-md bg-slate-50 p-3">
                <p className="text-sm font-medium text-slate-600">Draft reply</p>
                <p className="ahoy-prose mt-1">{r.ai_reply}</p>
              </div>
            )}
            <p className="ahoy-muted mt-2 text-sm">Status: {r.reply_status || "—"}</p>
            {r.needs_captain && (
              <button
                type="button"
                disabled={busy}
                onClick={() => onApprove(r.review_id)}
                className="mt-3 rounded-md bg-sky-800 px-4 py-2.5 text-base font-medium text-white disabled:opacity-50"
              >
                Approve reply
              </button>
            )}
          </li>
        ))}
        {reviews.length === 0 && !error && (
          <li className="ahoy-muted rounded-xl border border-dashed border-slate-300 px-4 py-8 text-center">
            No reviews yet — apply migration 004.
          </li>
        )}
      </ul>
    </main>
  );
}
