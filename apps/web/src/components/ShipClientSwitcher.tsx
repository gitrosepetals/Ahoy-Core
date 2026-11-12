"use client";

import { useEffect, useState } from "react";
import { fetchMe, MeResponse } from "@/lib/api";
import { getAccessToken, pickActiveClient, setActiveClientId } from "@/lib/session";

/** Shown only when the Captain owns more than one business (BUG-004). */
export function ShipClientSwitcher() {
  const [me, setMe] = useState<MeResponse | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) return;
    fetchMe(token)
      .then(setMe)
      .catch(() => setMe(null));
  }, []);

  if (!me || me.clients.length < 2) return null;
  const active = pickActiveClient(me);

  return (
    <label className="shrink-0">
      <span className="sr-only">Business</span>
      <select
        className="ahoy-input !w-auto !py-1 text-sm"
        value={active?.client_id ?? ""}
        onChange={(e) => {
          setActiveClientId(e.target.value);
          window.location.reload();
        }}
      >
        {me.clients.map((c) => (
          <option key={c.client_id} value={c.client_id}>
            {c.business_name}
          </option>
        ))}
      </select>
    </label>
  );
}
