"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchMe, listMedia, MediaAsset } from "@/lib/api";
import { getAccessToken } from "@/lib/session";
import { IconChest } from "@/components/pirate/Icons";
import { ShipHeader } from "@/components/pirate/ShipHeader";
import { AhoyReveal } from "@/components/AhoyReveal";

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
        <ShipHeader icon={<IconChest />} title="The Vault">
          <p className="ahoy-muted mt-3">Crew-stowed assets — read-only aboard the Ship.</p>
        </ShipHeader>
      </AhoyReveal>
      {error && <p className="ahoy-error">{error}</p>}
      <ul className="space-y-3">
        {media.map((a, i) => (
          <AhoyReveal
            key={a.asset_id}
            as="li"
            variant={i % 2 === 0 ? "heave" : "sail"}
            delay={Math.min(i * 45, 220)}
            className="flex items-center gap-3 ahoy-panel p-3"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={a.thumbnail_url || a.storage_url}
              alt=""
              className="h-16 w-16 rounded-md object-cover"
            />
            <div>
              <p className="ahoy-label">{a.asset_type}</p>
              <p className="ahoy-muted">{(a.ai_tags || []).join(", ") || "no tags"}</p>
            </div>
          </AhoyReveal>
        ))}
        {media.length === 0 && !error && (
          <li className="ahoy-muted rounded-xl border border-dashed border-[var(--ahoy-panel-border)] px-4 py-8 text-center">
            No media yet.
          </li>
        )}
      </ul>
    </main>
  );
}
