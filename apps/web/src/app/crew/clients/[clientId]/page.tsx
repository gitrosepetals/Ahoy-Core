"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  BrandProfile,
  ContentQueueItem,
  generateCampaign,
  getBrandProfile,
  listMedia,
  listQueue,
  MediaAsset,
  putBrandProfile,
  releaseQueue,
  uploadMedia,
} from "@/lib/api";
import { getAccessToken } from "@/lib/session";

export default function CrewClientPage() {
  const params = useParams();
  const clientId = String(params.clientId);

  const [brand, setBrand] = useState<BrandProfile | null>(null);
  const [voice, setVoice] = useState("");
  const [zips, setZips] = useState("");
  const [compliance, setCompliance] = useState("");
  const [servicesJson, setServicesJson] = useState("{}");
  const [media, setMedia] = useState<MediaAsset[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [queue, setQueue] = useState<ContentQueueItem[]>([]);
  const [count, setCount] = useState(4);
  const [days, setDays] = useState(7);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [postsTab, setPostsTab] = useState<"drafts" | "pending" | "approved">("drafts");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const token = typeof window !== "undefined" ? getAccessToken() : null;

  const refresh = useCallback(async () => {
    const access = getAccessToken();
    if (!access) {
      setError("Not signed in");
      return;
    }
    const [b, m, q] = await Promise.all([
      getBrandProfile(access, clientId),
      listMedia(access, clientId),
      listQueue(access, clientId),
    ]);
    setBrand(b);
    setVoice(b.brand_voice_guidelines);
    setZips((b.target_zip_codes || []).join(", "));
    setCompliance(b.compliance_rules || "");
    setServicesJson(JSON.stringify(b.services_offered ?? {}, null, 2));
    setMedia(m);
    setQueue(q);
    setSelected(new Set(m.map((a) => a.asset_id)));
  }, [clientId]);

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
  }, [refresh]);

  async function saveBrand() {
    const access = getAccessToken();
    if (!access) return;
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      let services: unknown = {};
      try {
        services = JSON.parse(servicesJson || "{}");
      } catch {
        throw new Error("services_offered must be valid JSON");
      }
      const updated = await putBrandProfile(access, clientId, {
        brand_voice_guidelines: voice,
        target_zip_codes: zips
          .split(",")
          .map((z) => z.trim())
          .filter(Boolean),
        compliance_rules: compliance,
        services_offered: services,
      });
      setBrand(updated);
      setMessage(
        updated.has_embedding
          ? "Brand Brain saved (embedding updated)."
          : "Brand Brain saved.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(file: File | null) {
    const access = getAccessToken();
    if (!access || !file) return;
    setBusy(true);
    setError(null);
    try {
      await uploadMedia(access, clientId, file);
      await refresh();
      setMessage(`Uploaded ${file.name}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function onGenerate() {
    const access = getAccessToken();
    if (!access) return;
    setBusy(true);
    setError(null);
    try {
      const posts = await generateCampaign(access, clientId, {
        asset_ids: Array.from(selected),
        channels: ["instagram_post", "facebook", "gbp_update"],
        days,
        count,
      });
      setMessage(`Generated ${posts.length} draft posts.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generate failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRelease() {
    const access = getAccessToken();
    if (!access) return;
    setBusy(true);
    setError(null);
    try {
      const drafts = queue.filter((p) => p.status === "draft_internal").map((p) => p.post_id);
      const released = await releaseQueue(access, clientId, drafts.length ? drafts : undefined);
      setMessage(`Released ${released.length} posts to Captain.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Release failed");
    } finally {
      setBusy(false);
    }
  }

  function toggleAsset(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (!token && error === "Not signed in") {
    return (
      <main className="mx-auto max-w-lg px-6 py-16">
        <p className="text-sm text-red-700">Not signed in</p>
        <Link href="/auth/sign-in" className="mt-4 inline-block text-sky-800 underline">
          Sign in
        </Link>
      </main>
    );
  }

  if (!brand && !error) {
    return <main className="p-8 text-sm text-slate-600">Loading client…</main>;
  }

  const drafts = queue.filter((p) => p.status === "draft_internal");
  const pending = queue.filter((p) => p.status === "pending_client");
  const approved = queue.filter(
    (p) => p.status === "approved" || p.status === "published",
  );
  const tabPosts =
    postsTab === "drafts" ? drafts : postsTab === "pending" ? pending : approved;
  const emptyCopy =
    postsTab === "drafts"
      ? "No drafts — Generate drafts above."
      : postsTab === "pending"
        ? "Nothing awaiting the Captain — Release drafts when ready."
        : "No approved posts yet.";

  return (
    <main className="mx-auto max-w-4xl space-y-10 px-6 py-12">
      <div>
        <Link href="/crew" className="text-sm text-sky-800 underline">
          ← Crew Deck
        </Link>
        <p className="mt-3 text-sm uppercase tracking-[0.2em] text-slate-500">Crew Deck</p>
        <h1 className="mt-2 text-3xl font-semibold">Client workspace</h1>
        <p className="mt-1 font-mono text-xs text-slate-500">{clientId}</p>
      </div>

      {message && <p className="text-sm text-emerald-800">{message}</p>}
      {error && <p className="text-sm text-red-700">{error}</p>}

      <section className="space-y-3">
        <h2 className="text-xl font-semibold text-slate-900">Brand Brain</h2>
        <p className="ahoy-muted">
          Voice, zips, compliance, and services. Embedding recomputed on save when LLM is available
          (or in LLM_DEV_MODE).
          {brand?.has_embedding ? " Embedding present." : ""}
        </p>
        <label className="block text-base">
          <span className="font-medium text-slate-700">Brand voice</span>
          <textarea
            className="ahoy-prose mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            rows={4}
            value={voice}
            onChange={(e) => setVoice(e.target.value)}
          />
        </label>
        <label className="block text-base">
          <span className="font-medium text-slate-700">Target ZIP codes (comma-separated)</span>
          <input
            className="ahoy-prose mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            value={zips}
            onChange={(e) => setZips(e.target.value)}
          />
        </label>
        <label className="block text-base">
          <span className="font-medium text-slate-700">Compliance</span>
          <textarea
            className="ahoy-prose mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            rows={3}
            value={compliance}
            onChange={(e) => setCompliance(e.target.value)}
          />
        </label>
        <label className="block text-base">
          <span className="font-medium text-slate-700">Services (JSON)</span>
          <textarea
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm leading-relaxed text-slate-900"
            rows={6}
            value={servicesJson}
            onChange={(e) => setServicesJson(e.target.value)}
          />
        </label>
        <button
          type="button"
          disabled={busy}
          onClick={saveBrand}
          className="rounded-md bg-sky-800 px-4 py-2.5 text-base font-medium text-white disabled:opacity-50"
        >
          Save Brand Brain
        </button>
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Media vault</h2>
          <p className="ahoy-muted mt-1">
            Below Brand Brain. Upload photos for campaign generate, or use seeded placeholders.
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="sr-only"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0] ?? null;
            void onUpload(file);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          disabled={busy}
          onClick={() => fileInputRef.current?.click()}
          className="rounded-md bg-sky-800 px-4 py-2.5 text-base font-medium text-white disabled:opacity-50"
        >
          Upload photo
        </button>
        <ul className="space-y-3">
          {media.map((a) => {
            const thumb = a.thumbnail_url || a.storage_url;
            return (
              <li
                key={a.asset_id}
                className="flex items-start gap-3 rounded-md border border-slate-200 bg-white p-3"
              >
                <input
                  type="checkbox"
                  className="mt-2"
                  checked={selected.has(a.asset_id)}
                  onChange={() => toggleAsset(a.asset_id)}
                />
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={thumb}
                  alt={a.ai_tags?.join(", ") || a.asset_type}
                  className="h-20 w-20 shrink-0 rounded-md border border-slate-200 object-cover bg-slate-100"
                />
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-slate-900">{a.asset_type}</p>
                  <p className="ahoy-muted mt-1">
                    {(a.ai_tags || []).join(", ") || "no tags"}
                    {a.is_used ? " · used" : ""}
                  </p>
                </div>
              </li>
            );
          })}
          {media.length === 0 && (
            <li className="rounded-md border border-dashed border-slate-300 px-4 py-8 text-center">
              <p className="ahoy-muted">No media yet.</p>
              <button
                type="button"
                disabled={busy}
                onClick={() => fileInputRef.current?.click()}
                className="mt-3 rounded-md bg-sky-800 px-4 py-2.5 text-base font-medium text-white disabled:opacity-50"
              >
                Upload photo
              </button>
              <p className="ahoy-muted mt-2 text-sm">
                Or apply seed migration 003 for Oak Lawn placeholders.
              </p>
            </li>
          )}
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Generate campaign</h2>
        <div className="flex flex-wrap gap-4 text-sm">
          <label>
            Posts{" "}
            <input
              type="number"
              min={1}
              max={20}
              className="ml-1 w-16 rounded border border-slate-300 px-2 py-1"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
            />
          </label>
          <label>
            Days{" "}
            <input
              type="number"
              min={1}
              max={60}
              className="ml-1 w-16 rounded border border-slate-300 px-2 py-1"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            />
          </label>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled={busy}
            onClick={onGenerate}
            className="rounded-md bg-sky-800 px-3 py-2 text-sm text-white disabled:opacity-50"
          >
            Generate drafts
          </button>
          <button
            type="button"
            disabled={busy || drafts.length === 0}
            onClick={onRelease}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm disabled:opacity-50"
          >
            Release to Captain ({drafts.length})
          </button>
        </div>
      </section>

      <section className="space-y-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Posts</h2>
          <p className="ahoy-muted mt-1">
            Split by stage — drafts stay internal until you release them to the Captain.
          </p>
        </div>
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Post status">
          {(
            [
              { id: "drafts" as const, label: "Drafts", count: drafts.length },
              { id: "pending" as const, label: "Awaiting Captain", count: pending.length },
              { id: "approved" as const, label: "Approved", count: approved.length },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={postsTab === tab.id}
              onClick={() => setPostsTab(tab.id)}
              className={`rounded-md px-3 py-2 text-sm font-medium ${
                postsTab === tab.id
                  ? "bg-sky-800 text-white"
                  : "border border-slate-300 bg-white text-slate-800"
              }`}
            >
              {tab.label} ({tab.count})
            </button>
          ))}
        </div>
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-left text-base">
            <thead className="bg-slate-50 text-slate-700">
              <tr>
                <th className="px-3 py-3 font-medium">Channel</th>
                <th className="px-3 py-3 font-medium">Caption</th>
                <th className="px-3 py-3 font-medium">When</th>
              </tr>
            </thead>
            <tbody>
              {tabPosts.map((p) => (
                <tr key={p.post_id} className="border-t border-slate-100 align-top">
                  <td className="px-3 py-3 whitespace-nowrap text-slate-800">{p.channel}</td>
                  <td className="ahoy-prose max-w-md px-3 py-3">{p.caption_text}</td>
                  <td className="ahoy-muted px-3 py-3 whitespace-nowrap">
                    {new Date(p.scheduled_publish_at).toLocaleString()}
                  </td>
                </tr>
              ))}
              {tabPosts.length === 0 && (
                <tr>
                  <td colSpan={3} className="ahoy-muted px-3 py-4">
                    {emptyCopy}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
