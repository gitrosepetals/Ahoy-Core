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
        <p className="text-sm text-red-700">{error}</p>
        <Link href="/auth/sign-in" className="mt-4 inline-block text-sky-800 underline">
          Sign in
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl space-y-6 px-6 py-12">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.16em] text-sky-800">The Ship</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Posts</h1>
          <p className="ahoy-muted mt-2">
            One place for history and approvals. Act on items that are awaiting you.
          </p>
        </div>
        {pendingCount > 0 && (
          <button
            type="button"
            disabled={busy}
            onClick={onApproveAll}
            className="rounded-md bg-sky-800 px-4 py-2.5 text-base font-medium text-white disabled:opacity-50"
          >
            Approve all ({pendingCount})
          </button>
        )}
      </div>

      {message && <p className="text-sm text-emerald-800">{message}</p>}
      {error && error !== "Not signed in" && <p className="text-sm text-red-700">{error}</p>}

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
            className={`rounded-md px-3 py-2 text-sm font-medium ${
              tab === t.id
                ? "bg-sky-800 text-white"
                : "border border-slate-300 bg-white text-slate-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <ul className="space-y-4">
        {visible.map((p) => {
          const asset = p.asset_id ? mediaById[p.asset_id] : undefined;
          const thumb = asset?.thumbnail_url || asset?.storage_url;
          const actionable = p.status === "pending_client";
          return (
            <li
              key={p.post_id}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex gap-3">
                {thumb ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={thumb}
                    alt=""
                    className="h-20 w-20 shrink-0 rounded-md object-cover bg-slate-100"
                  />
                ) : (
                  <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-md bg-slate-100 text-xs text-slate-500">
                    Text
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-600">
                    {p.channel} · {statusLabel(p.status)}
                  </p>
                  <p className="ahoy-prose mt-2 whitespace-pre-wrap">{p.caption_text}</p>
                  <p className="ahoy-muted mt-2 text-sm">
                    {new Date(p.scheduled_publish_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {actionable && (
                <>
                  <textarea
                    className="ahoy-prose mt-3 w-full rounded-md border border-slate-300 px-3 py-2"
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
                      className="rounded-md bg-sky-800 px-4 py-2.5 text-base font-medium text-white disabled:opacity-50"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => onRequestEdit(p.post_id)}
                      className="rounded-md border border-slate-300 px-4 py-2.5 text-base font-medium text-slate-800 disabled:opacity-50"
                    >
                      Request edit
                    </button>
                    <button
                      type="button"
                      disabled={busy || media.length === 0}
                      onClick={() => setSwapFor(swapFor === p.post_id ? null : p.post_id)}
                      className="rounded-md border border-slate-300 px-4 py-2.5 text-base font-medium text-slate-800 disabled:opacity-50"
                    >
                      Swap media
                    </button>
                  </div>
                  {swapFor === p.post_id && (
                    <ul className="mt-3 space-y-2 rounded-md border border-slate-200 bg-slate-50 p-3">
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
                            className="text-sm font-medium text-sky-800 underline"
                          >
                            Use this ({a.asset_type})
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </li>
          );
        })}
        {visible.length === 0 && !error && (
          <li className="ahoy-muted rounded-xl border border-dashed border-slate-300 px-4 py-8 text-center">
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
    <Suspense fallback={<main className="p-8 text-sm text-slate-600">Loading posts…</main>}>
      <ShipPostsInner />
    </Suspense>
  );
}
