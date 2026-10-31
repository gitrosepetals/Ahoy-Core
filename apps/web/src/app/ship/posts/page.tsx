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
type ManifestView = "feed" | "list";

const VIEW_KEY = "ahoy-manifest-view";

function statusLabel(status: string) {
  if (status === "pending_client") return "Awaiting you";
  if (status === "approved") return "Approved";
  if (status === "published") return "Published";
  return status;
}

function relativeTime(iso: string) {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const sec = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (sec < 60) return "just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m`;
  const hr = Math.floor(min / 60);
  if (hr < 48) return `${hr}h`;
  const day = Math.floor(hr / 24);
  if (day < 14) return `${day}d`;
  return new Date(iso).toLocaleDateString();
}

function PostActions({
  postId,
  busy,
  media,
  feedback,
  swapFor,
  onFeedback,
  onApprove,
  onRequestEdit,
  onToggleSwap,
  onSwap,
}: {
  postId: string;
  busy: boolean;
  media: MediaAsset[];
  feedback: string;
  swapFor: string | null;
  onFeedback: (value: string) => void;
  onApprove: () => void;
  onRequestEdit: () => void;
  onToggleSwap: () => void;
  onSwap: (assetId: string) => void;
}) {
  return (
    <>
      <textarea
        className="ahoy-input mt-3"
        rows={2}
        placeholder="Feedback for request edit…"
        value={feedback}
        onChange={(e) => onFeedback(e.target.value)}
      />
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" disabled={busy} onClick={onApprove} className="ahoy-btn">
          Approve
        </button>
        <button type="button" disabled={busy} onClick={onRequestEdit} className="ahoy-btn-ghost">
          Request edit
        </button>
        <button
          type="button"
          disabled={busy || media.length === 0}
          onClick={onToggleSwap}
          className="ahoy-btn-ghost"
        >
          Swap media
        </button>
      </div>
      {swapFor === postId && (
        <ul className="ahoy-feed-swap mt-3 space-y-2">
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
                onClick={() => onSwap(a.asset_id)}
                className="ahoy-link"
              >
                Use this ({a.asset_type})
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function ShipPostsInner() {
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get("tab") as FeedTab | null) || "all";

  const [clientId, setClientId] = useState<string | null>(null);
  const [businessName, setBusinessName] = useState("Your ship");
  const [posts, setPosts] = useState<ContentQueueItem[]>([]);
  const [media, setMedia] = useState<MediaAsset[]>([]);
  const [mediaById, setMediaById] = useState<Record<string, MediaAsset>>({});
  const [tab, setTab] = useState<FeedTab>(
    initialTab === "pending" || initialTab === "approved" ? initialTab : "all",
  );
  const [view, setView] = useState<ManifestView>("feed");
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [swapFor, setSwapFor] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(VIEW_KEY);
      if (saved === "feed" || saved === "list") setView(saved);
    } catch {
      /* ignore */
    }
  }, []);

  function chooseView(next: ManifestView) {
    setView(next);
    try {
      localStorage.setItem(VIEW_KEY, next);
    } catch {
      /* ignore */
    }
  }

  const load = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setError("Not signed in");
      return;
    }
    const me = await fetchMe(token);
    const client = me.clients[0];
    const cid = client?.client_id ?? me.user.client_ids[0] ?? null;
    setClientId(cid);
    if (client?.business_name) setBusinessName(client.business_name);
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

  const mark = businessName.trim().charAt(0).toUpperCase() || "A";
  const isFeed = view === "feed";

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
    <main className="mx-auto max-w-lg space-y-5 px-4 pb-12 pt-8 sm:px-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <ShipHeader icon={<IconScroll />} title="Manifest">
          <p className="ahoy-muted mt-3">
            {isFeed
              ? "Your feed — approve, edit, or swap before it sails."
              : "Captions awaiting your mark — and the ones already cleared for sail."}
          </p>
        </ShipHeader>
        {pendingCount > 0 && (
          <button type="button" disabled={busy} onClick={onApproveAll} className="ahoy-btn">
            Approve all ({pendingCount})
          </button>
        )}
      </div>

      {message && <p className="ahoy-success">{message}</p>}
      {error && error !== "Not signed in" && <p className="ahoy-error">{error}</p>}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Status filter">
          {(
            [
              { id: "all" as const, label: "All" },
              { id: "pending" as const, label: `Awaiting (${pendingCount})` },
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

        <div className="flex gap-1" role="group" aria-label="Manifest layout">
          <button
            type="button"
            aria-pressed={isFeed}
            onClick={() => chooseView("feed")}
            className={isFeed ? "ahoy-tab ahoy-tab-active" : "ahoy-tab"}
          >
            Feed
          </button>
          <button
            type="button"
            aria-pressed={!isFeed}
            onClick={() => chooseView("list")}
            className={!isFeed ? "ahoy-tab ahoy-tab-active" : "ahoy-tab"}
          >
            List
          </button>
        </div>
      </div>

      <ul
        className={
          isFeed ? "ahoy-feed m-0 list-none space-y-4 p-0" : "m-0 list-none space-y-4 p-0"
        }
      >
        {visible.map((p, i) => {
          const asset = p.asset_id ? mediaById[p.asset_id] : undefined;
          const thumb = asset?.thumbnail_url || asset?.storage_url;
          const actionable = p.status === "pending_client";
          const animate = i < 12;
          const when = relativeTime(p.created_at || p.scheduled_publish_at);

          const actions = actionable ? (
            <PostActions
              postId={p.post_id}
              busy={busy}
              media={media}
              feedback={feedback[p.post_id] || ""}
              swapFor={swapFor}
              onFeedback={(value) =>
                setFeedback((prev) => ({ ...prev, [p.post_id]: value }))
              }
              onApprove={() => onApprove(p.post_id)}
              onRequestEdit={() => onRequestEdit(p.post_id)}
              onToggleSwap={() => setSwapFor(swapFor === p.post_id ? null : p.post_id)}
              onSwap={(assetId) => onSwap(p.post_id, assetId)}
            />
          ) : null;

          const body = isFeed ? (
            <article className="ahoy-feed-post">
              <header className="ahoy-feed-head">
                <span className="ahoy-feed-avatar" aria-hidden>
                  {mark}
                </span>
                <div className="ahoy-feed-meta min-w-0 flex-1">
                  <p className="ahoy-feed-name">{businessName}</p>
                  <p className="ahoy-muted">
                    {p.channel}
                    {when ? ` · ${when}` : ""}
                  </p>
                </div>
                <span className="ahoy-feed-badge">{statusLabel(p.status)}</span>
              </header>

              <div className="ahoy-feed-media">
                {thumb ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={thumb} alt="" className="ahoy-feed-img" />
                ) : (
                  <div className="ahoy-feed-img ahoy-feed-img-empty">
                    <span className="ahoy-label">Text post</span>
                  </div>
                )}
              </div>

              <div className="ahoy-feed-body">
                <p className="ahoy-feed-caption">
                  <span className="ahoy-feed-name">{businessName} </span>
                  <span className="ahoy-prose whitespace-pre-wrap">{p.caption_text}</span>
                </p>
                <p className="ahoy-muted mt-2">
                  Sails {new Date(p.scheduled_publish_at).toLocaleString()}
                </p>
              </div>

              {actions ? <div className="ahoy-feed-actions">{actions}</div> : null}
            </article>
          ) : (
            <article className="ahoy-panel p-5">
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
              {actions}
            </article>
          );

          if (!animate) {
            return <li key={p.post_id}>{body}</li>;
          }
          return (
            <AhoyReveal
              key={p.post_id}
              as="li"
              variant={i % 2 === 0 ? "sail" : "heave"}
              delay={Math.min(i * 45, 220)}
            >
              {body}
            </AhoyReveal>
          );
        })}
        {visible.length === 0 && !error && (
          <li
            className={
              isFeed
                ? "ahoy-muted border border-dashed border-[var(--ahoy-panel-border)] px-4 py-10 text-center"
                : "ahoy-muted rounded-xl border border-dashed border-[var(--ahoy-panel-border)] px-4 py-8 text-center"
            }
          >
            No posts in this view yet. After Crew releases a batch, they show up under Awaiting.
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
