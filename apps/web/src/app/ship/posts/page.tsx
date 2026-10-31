"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  approveAllQueue,
  approvePost,
  ContentQueueItem,
  fetchMe,
  listMedia,
  listQueue,
  MediaAsset,
  requestEdit,
  swapAsset,
} from "@/lib/api";
import { getAccessToken } from "@/lib/session";
import { IconScroll } from "@/components/pirate/Icons";
import { ShipHeader } from "@/components/pirate/ShipHeader";
import { AhoyReveal } from "@/components/AhoyReveal";

type FeedTab = "all" | "pending" | "approved";

function statusLabel(status: string) {
  if (status === "pending_client") return "Awaiting you";
  if (status === "approved") return "Approved";
  if (status === "published") return "Published";
  return status;
}

function ShipPostsInner() {
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as FeedTab | null) || "all";

  const [clientId, setClientId] = useState<string | null>(null);
  const [posts, setPosts] = useState<ContentQueueItem[]>([]);
  const [media, setMedia] = useState<MediaAsset[]>([]);
  const [mediaById, setMediaById] = useState<Record<string, MediaAsset>>({});
  const [tab, setTab] = useState<FeedTab>(
    initialTab === "pending" || initialTab === "approved" ? initialTab : "all",
  );
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [swapFor, setSwapFor] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setError("Not signed in");
      return;
    }
    const me = await fetchMe(token);
    const cid = me.clients[0]?.client_id ?? me.user.client_ids[0] ?? null;
    setClientId(cid);
    if (!cid) {
      setPosts([]);
      return;
    }
    const [queue, assets] = await Promise.all([
      listQueue(token, cid),
      listMedia(token, cid),
    ]);
    setPosts(
      queue.filter(
        (p) =>
          p.status === "pending_client" ||
          p.status === "approved" ||
          p.status === "published",
      ),
    );
    setMedia(assets);
    const map: Record<string, MediaAsset> = {};
    for (const a of assets) map[a.asset_id] = a;
    setMediaById(map);
  }, []);

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
  }, [load]);

  const pendingCount = useMemo(
    () => posts.filter((p) => p.status === "pending_client").length,
    [posts],
  );

  const visible = useMemo(() => {
    if (tab === "pending") return posts.filter((p) => p.status === "pending_client");
    if (tab === "approved")
      return posts.filter((p) => p.status === "approved" || p.status === "published");
    return posts;
  }, [posts, tab]);

  async function onApprove(postId: string) {
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    setError(null);
    setPosts((prev) =>
      prev.map((p) => (p.post_id === postId ? { ...p, status: "approved" } : p)),
    );
    try {
      await approvePost(token, postId);
      setMessage("Approved.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed");
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function onApproveAll() {
    const token = getAccessToken();
    if (!token || !clientId) return;
    setBusy(true);
    setError(null);
    try {
      const approved = await approveAllQueue(token, clientId);
      setMessage(`Approved ${approved.length} posts.`);
      await load();
      setTab("approved");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve all failed");
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function onRequestEdit(postId: string) {
    const token = getAccessToken();
    if (!token) return;
    const note = (feedback[postId] || "").trim();
    if (!note) {
      setError("Add feedback before requesting an edit.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await requestEdit(token, postId, note);
      setPosts((prev) => prev.map((p) => (p.post_id === postId ? updated : p)));
      setMessage(
        updated.status === "pending_client"
          ? "Caption rewritten — still awaiting you."
          : "Flagged for Crew (rewrite failed).",
      );
      setFeedback((prev) => ({ ...prev, [postId]: "" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request edit failed");
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function onSwap(postId: string, assetId: string) {
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await swapAsset(token, postId, assetId);
      setPosts((prev) => prev.map((p) => (p.post_id === postId ? updated : p)));
      setMessage("Media swapped.");
      setSwapFor(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Swap failed");
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
      <div className="flex flex-wrap items-end justify-between gap-3">
        <ShipHeader icon={<IconScroll />} title="Manifest">
          <p className="ahoy-muted mt-3">
            Captions awaiting your mark — and the ones already cleared for sail.
          </p>
        </ShipHeader>
        {pendingCount > 0 && (
          <button
            type="button"
            disabled={busy}
            onClick={onApproveAll}
            className="ahoy-btn"
          >
            Approve all ({pendingCount})
          </button>
        )}
      </div>

      {message && <p className="ahoy-success">{message}</p>}
      {error && error !== "Not signed in" && <p className="ahoy-error">{error}</p>}

      <div className="flex flex-wrap gap-2" role="tablist">
        {(
          [
            { id: "all" as const, label: "All" },
            { id: "pending" as const, label: `Awaiting you (${pendingCount})` },
            { id: "approved" as const, label: "Approved" },
          ] as const
        ).map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={tab === t.id ? "ahoy-tab ahoy-tab-active" : "ahoy-tab"}
          >
            {t.label}
          </button>
        ))}
      </div>

      <ul className="space-y-4">
        {visible.map((p, i) => {
          const asset = p.asset_id ? mediaById[p.asset_id] : undefined;
          const thumb = asset?.thumbnail_url || asset?.storage_url;
          const actionable = p.status === "pending_client";
          // Only animate the first screenful — 100+ observers on Manifest crush scroll.
          const animate = i < 12;
          const body = (
            <>
              <div className="flex gap-3">
                {thumb ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={thumb}
                    alt=""
                    className="h-20 w-20 shrink-0 rounded-md object-cover bg-[var(--ahoy-bg)]"
                  />
                ) : (
                  <div className="ahoy-label flex h-20 w-20 shrink-0 items-center justify-center rounded-md border border-[var(--ahoy-panel-border)] bg-[var(--ahoy-bg)]">
                    Text
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <p className="ahoy-label">
                    {p.channel} · {statusLabel(p.status)}
                  </p>
                  <p className="ahoy-prose mt-2 whitespace-pre-wrap">{p.caption_text}</p>
                  <p className="ahoy-muted mt-2">
                    {new Date(p.scheduled_publish_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {actionable && (
                <>
                  <textarea
                    className="ahoy-input mt-3"
                    rows={2}
                    placeholder="Feedback for request edit…"
                    value={feedback[p.post_id] || ""}
                    onChange={(e) =>
                      setFeedback((prev) => ({ ...prev, [p.post_id]: e.target.value }))
                    }
                  />
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => onApprove(p.post_id)}
                      className="ahoy-btn"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => onRequestEdit(p.post_id)}
                      className="ahoy-btn-ghost"
                    >
                      Request edit
                    </button>
                    <button
                      type="button"
                      disabled={busy || media.length === 0}
                      onClick={() => setSwapFor(swapFor === p.post_id ? null : p.post_id)}
                      className="ahoy-btn-ghost"
                    >
                      Swap media
                    </button>
                  </div>
                  {swapFor === p.post_id && (
                    <ul className="ahoy-inset mt-3 space-y-2">
                      {media.map((a) => (
                        <li key={a.asset_id} className="flex items-center gap-3">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={a.thumbnail_url || a.storage_url}
                            alt=""
                            className="h-12 w-12 rounded object-cover"
                          />
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => onSwap(p.post_id, a.asset_id)}
                            className="ahoy-link"
                          >
                            Use this ({a.asset_type})
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </>
          );
          if (!animate) {
            return (
              <li key={p.post_id} className="ahoy-panel p-5">
                {body}
              </li>
            );
          }
          return (
            <AhoyReveal
              key={p.post_id}
              as="li"
              variant={i % 2 === 0 ? "sail" : "heave"}
              delay={Math.min(i * 45, 220)}
              className="ahoy-panel p-5"
            >
              {body}
            </AhoyReveal>
          );
        })}
        {visible.length === 0 && !error && (
          <li className="ahoy-muted rounded-xl border border-dashed border-[var(--ahoy-panel-border)] px-4 py-8 text-center">
            No posts in this view yet. After Crew releases a batch, they show up under Awaiting
            you.
          </li>
        )}
      </ul>
    </main>
  );
}

export default function ShipPostsPage() {
  return (
    <Suspense fallback={<main className="p-8 ahoy-muted">Loading posts…</main>}>
      <ShipPostsInner />
    </Suspense>
  );
}
