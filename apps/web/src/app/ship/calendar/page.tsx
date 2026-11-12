"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ContentQueueItem, fetchMe, listQueue } from "@/lib/api";
import { activeClientId, getAccessToken } from "@/lib/session";
import { IconScroll } from "@/components/pirate/Icons";
import { ShipHeader } from "@/components/pirate/ShipHeader";
import { AhoyBackLink } from "@/components/AhoyBackLink";

const CHANNEL_LABEL: Record<string, string> = {
  instagram_post: "Instagram",
  instagram_reel: "Instagram Reel",
  facebook: "Facebook",
  tiktok: "TikTok",
  gbp_update: "Google",
  email_blast: "Email",
  sms_promo: "SMS",
};

export default function ShipCalendarPage() {
  const [posts, setPosts] = useState<ContentQueueItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setError("Not signed in");
      return;
    }
    fetchMe(token)
      .then(async (me) => {
        const cid = activeClientId(me);
        if (!cid) return;
        const all = await listQueue(token, cid);
        setPosts(all.filter((p) => p.status === "approved" || p.status === "published"));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Load failed"));
  }, []);

  const days = useMemo(() => {
    const groups = new Map<string, ContentQueueItem[]>();
    for (const p of posts) {
      const key = new Date(p.scheduled_publish_at).toDateString();
      groups.set(key, [...(groups.get(key) ?? []), p]);
    }
    return Array.from(groups.entries());
  }, [posts]);

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
      <AhoyBackLink href="/ship/posts">Manifest</AhoyBackLink>
      <ShipHeader icon={<IconScroll />} title="Logbook">
        <p className="ahoy-muted mt-3">
          Everything the Captain cleared for sail, by day. Posts go out automatically at their scheduled time.
        </p>
      </ShipHeader>
      {error && <p className="ahoy-error">{error}</p>}
      {days.map(([day, items]) => (
        <section key={day} className="ahoy-panel p-4">
          <h2 className="ahoy-title-sm">{day}</h2>
          <ul className="mt-2 space-y-2">
            {items.map((p) => (
              <li
                key={p.post_id}
                className="flex flex-wrap justify-between gap-2 border-t border-[var(--ahoy-panel-border)] pt-2"
              >
                <span className="ahoy-label">
                  {new Date(p.scheduled_publish_at).toLocaleTimeString([], {
                    hour: "numeric",
                    minute: "2-digit",
                  })}{" "}
                  · {CHANNEL_LABEL[p.channel] ?? p.channel}
                </span>
                <span className="ahoy-muted">
                  {p.status === "published" ? "Sailed ✓" : "Scheduled"}
                </span>
                <p className="ahoy-muted w-full truncate">{p.caption_text}</p>
              </li>
            ))}
          </ul>
        </section>
      ))}
      {days.length === 0 && !error && (
        <p className="ahoy-muted">
          Nothing scheduled yet — approve posts in the <Link href="/ship/posts">Manifest</Link>.
        </p>
      )}
    </main>
  );
}
