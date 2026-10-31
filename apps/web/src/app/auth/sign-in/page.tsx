"use client";

import { FormEvent, useState } from "react";
import { requestMagicLink } from "@/lib/api";
import { AhoyLogo } from "@/components/pirate/AhoyLogo";
import { AhoyBackLink } from "@/components/AhoyBackLink";

const CREW_PHONE = "+15551234002";
const CAPTAIN_PHONE = "+15551234001";

function redirectForPhone(phone: string): string {
  const normalized = phone.trim();
  if (normalized === CREW_PHONE) return "/crew";
  return "/ship";
}

export default function SignInPage() {
  const [phone, setPhone] = useState(CAPTAIN_PHONE);
  const [message, setMessage] = useState<string | null>(null);
  const [devLink, setDevLink] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    setDevLink(null);
    try {
      const res = await requestMagicLink({
        phone_number: phone,
        redirect_path: redirectForPhone(phone),
      });
      setMessage(res.message);
      if (res.dev_magic_link) setDevLink(res.dev_magic_link);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 px-6">
      <AhoyBackLink href="/">Home</AhoyBackLink>
      <div className="ahoy-rise">
        <AhoyLogo className="ahoy-logo-compact" markClassName="ahoy-logo-mark-sm" />
        <p className="ahoy-title mt-6">Come aboard</p>
        <div className="ahoy-brass-rule" />
        <h1 className="ahoy-title-sm mt-4">Sign in</h1>
        <p className="ahoy-muted mt-2">
          Dev phones: Captain <code>{CAPTAIN_PHONE}</code> → Ship · Crew{" "}
          <code>{CREW_PHONE}</code> → Crew Deck.
        </p>
      </div>
      <form onSubmit={onSubmit} className="ahoy-panel ahoy-rise-delay flex flex-col gap-3 p-4">
        <label className="ahoy-label">
          Phone
          <input
            className="ahoy-input mt-1"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder={CAPTAIN_PHONE}
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="ahoy-btn-ghost !px-2 !py-1" onClick={() => setPhone(CAPTAIN_PHONE)}>
            Use Captain
          </button>
          <button type="button" className="ahoy-btn-ghost !px-2 !py-1" onClick={() => setPhone(CREW_PHONE)}>
            Use Crew
          </button>
        </div>
        <button type="submit" disabled={busy} className="ahoy-btn">
          {busy ? "Sending…" : "Send magic link"}
        </button>
      </form>
      {message && <p className="ahoy-muted">{message}</p>}
      {devLink && (
        <p className="ahoy-muted break-all">
          Dev link:{" "}
          <a
            className="ahoy-link"
            href={(() => {
              try {
                const u = new URL(devLink);
                return `${u.pathname}${u.search}`;
              } catch {
                return "/auth/verify";
              }
            })()}
          >
            Open verify
          </a>
        </p>
      )}
    </main>
  );
}
