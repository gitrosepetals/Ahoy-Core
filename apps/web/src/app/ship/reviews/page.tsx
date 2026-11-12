"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { approveReviewReply, fetchMe, listReviews, ReviewItem, skipReviewReply } from "@/lib/api";
import { activeClientId, getAccessToken } from "@/lib/session";
import { IconSpyglass } from "@/components/pirate/Icons";
import { ShipHeader } from "@/components/pirate/ShipHeader";
import { AhoyReveal } from "@/components/AhoyReveal";

function statusLine(r: ReviewItem): string {
  if (r.reply_posted_at) {
    const when = new Date(r.reply_posted_at).toLocaleString();
    return r.reply_status === "skipped" ? `Captain replied on ${r.provider} (${when})` : `Reply posted ${when}`;
  }
  if (r.reply_status === "skipped") return "No reply will be posted";
  if (r.reply_status === "scheduled" && r.reply_due_at)
    return `Auto-reply posts ${new Date(r.reply_due_at).toLocaleString()} — skip or send now below`;
  if (r.needs_captain) return "Awaiting the Captain’s mark";
  if (!r.can_reply) return `${r.provider} doesn’t allow app replies — copy this and post it there`;
  if (r.reply_error) return `Couldn’t post yet: ${r.reply_error}`;
  return r.reply_status ?? "—";
}

export default function ShipReviewsPage() {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setError("Not signed in");
      return;
    }
    const me = await fetchMe(token);
    const cid = activeClientId(me);
    if (!cid) return;
    setReviews(await listReviews(token, cid));
  }, []);

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
  }, [load]);

  async function act(reviewId: string, kind: "approve" | "skip") {
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const updated =
        kind === "approve"
          ? await approveReviewReply(token, reviewId, drafts[reviewId])
          : await skipReviewReply(token, reviewId);
      setReviews((prev) => prev.map((r) => (r.review_id === reviewId ? updated : r)));
      setMessage(
        kind === "skip"
          ? "Skipped — nothing will be posted."
          : updated.reply_posted_at
            ? "Reply posted."
            : "Approved — we’ll post it shortly.",
      );
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
            Google, Facebook and Yelp in one place. Fair winds (4–5★) get an automatic reply
            after your delay; storms (1–3★) wait for the Captain’s mark with a drafted response.
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
              {r.needs_captain ? " · needs the Captain" : ""}
            </p>
            <p className="ahoy-title-sm mt-2">{r.reviewer_name || "Guest"}</p>
            <p className="ahoy-prose mt-2">{r.body || "(no text)"}</p>
            {r.ai_reply && (
              <div className="ahoy-inset mt-3">
                <p className="ahoy-kicker">{r.reply_posted_at ? "Reply" : "Draft reply"}</p>
                {r.needs_captain || (r.reply_status === "scheduled" && !r.reply_posted_at) ? (
                  <textarea
                    className="ahoy-input mt-2"
                    rows={4}
                    value={drafts[r.review_id] ?? r.ai_reply}
                    onChange={(e) => setDrafts({ ...drafts, [r.review_id]: e.target.value })}
                  />
                ) : (
                  <p className="ahoy-prose mt-2">{r.ai_reply}</p>
                )}
              </div>
            )}
            <p className="ahoy-muted mt-2">{statusLine(r)}</p>
            {!r.reply_posted_at && r.can_reply && (r.needs_captain || r.reply_status === "scheduled") && (
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => act(r.review_id, "approve")}
                  className="ahoy-btn"
                >
                  {r.needs_captain ? "Approve & post reply" : "Send now"}
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => act(r.review_id, "skip")}
                  className="ahoy-btn-ghost"
                >
                  Don’t reply
                </button>
              </div>
            )}
            {!r.can_reply && r.ai_reply && !r.reply_posted_at && (
              <button
                type="button"
                className="ahoy-btn-ghost mt-3"
                onClick={() => {
                  void navigator.clipboard?.writeText(r.ai_reply ?? "");
                  setMessage("Reply copied — paste it on " + r.provider + ".");
                }}
              >
                Copy reply
              </button>
            )}
          </AhoyReveal>
        ))}
        {reviews.length === 0 && !error && (
          <li className="ahoy-muted rounded-xl border border-dashed border-[var(--ahoy-panel-border)] px-4 py-8 text-center">
            No reviews yet — they appear here as soon as your Crew connects Google, Facebook or Yelp.
          </li>
        )}
      </ul>
    </main>
  );
}
