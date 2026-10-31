"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { requestMagicLink } from "@/lib/api";

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
      <div>
        <Link href="/" className="text-sm text-sky-800 hover:underline">
          ← Home
        </Link>
        <h1 className="mt-3 text-2xl font-semibold">Sign in</h1>
        <p className="mt-1 text-sm text-slate-600">
          Dev phones: Captain <code>{CAPTAIN_PHONE}</code> → Ship · Crew{" "}
          <code>{CREW_PHONE}</code> → Crew Deck (Brand Brain).
        </p>
      </div>
      <form onSubmit={onSubmit} className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="text-sm font-medium text-slate-700">
          Phone
          <input
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder={CAPTAIN_PHONE}
          />
        </label>
        <div className="flex flex-wrap gap-2 text-sm">
          <button
            type="button"
            className="rounded-md border border-slate-300 px-2 py-1 text-slate-700"
            onClick={() => setPhone(CAPTAIN_PHONE)}
          >
            Use Captain
          </button>
          <button
            type="button"
            className="rounded-md border border-slate-300 px-2 py-1 text-slate-700"
            onClick={() => setPhone(CREW_PHONE)}
          >
            Use Crew
          </button>
        </div>
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-sky-800 px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {busy ? "Sending…" : "Send magic link"}
        </button>
      </form>
      {message && <p className="text-sm text-slate-700">{message}</p>}
      {devLink && (
        <p className="break-all text-sm">
          Dev link:{" "}
          <a
            className="text-sky-800 underline"
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
