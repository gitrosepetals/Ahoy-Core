"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { approveReviewReply, fetchMe, listReviews, ReviewItem } from "@/lib/api";
import { getAccessToken } from "@/lib/session";
import { IconSpyglass } from "@/components/pirate/Icons";
import { ShipHeader } from "@/components/pirate/ShipHeader";
import { AhoyReveal } from "@/components/AhoyReveal";

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
        <p className="ahoy-error">{error}</p>
        <Link href="/auth/sign-in" className="ahoy-btn mt-4">
          Sign in
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl space-y-6 px-6 py-12">
      <AhoyReveal variant="sail">
        <ShipHeader icon={<IconSpyglass />} title="Reputation Radar">
          <p className="ahoy-muted mt-3">
            Fair winds (4–5★) auto-reply in the MVP stub; storms (1–3★) wait for your mark.
          </p>
        </ShipHeader>
      </AhoyReveal>
      {message && <p className="ahoy-success">{message}</p>}
      {error && error !== "Not signed in" && <p className="ahoy-error">{error}</p>}
      <ul className="space-y-4">
        {reviews.map((r, i) => (
          <AhoyReveal
            key={r.review_id}
            as="li"
            variant={i % 2 === 0 ? "heave" : "drop"}
            delay={Math.min(i * 45, 220)}
            className="ahoy-panel p-5"
          >
            <p className="ahoy-label">
              {r.provider} ·{" "}
              <span className="text-[var(--ahoy-lantern)]">{"★".repeat(r.rating)}</span>
              {r.needs_captain ? " · needs you" : ""}
            </p>
            <p className="ahoy-title-sm mt-2">{r.reviewer_name || "Guest"}</p>
            <p className="ahoy-prose mt-2">{r.body || "(no text)"}</p>
            {r.ai_reply && (
              <div className="ahoy-inset mt-3">
                <p className="ahoy-kicker">Draft reply</p>
                <p className="ahoy-prose mt-2">{r.ai_reply}</p>
              </div>
            )}
            <p className="ahoy-muted mt-2">Status: {r.reply_status || "—"}</p>
            {r.needs_captain && (
              <button
                type="button"
                disabled={busy}
                onClick={() => onApprove(r.review_id)}
                className="ahoy-btn mt-3"
              >
                Approve reply
              </button>
            )}
          </AhoyReveal>
        ))}
        {reviews.length === 0 && !error && (
          <li className="ahoy-muted rounded-xl border border-dashed border-[var(--ahoy-panel-border)] px-4 py-8 text-center">
            No reviews yet — apply migration 004.
          </li>
        )}
      </ul>
    </main>
  );
}
