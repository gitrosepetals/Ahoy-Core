"use client";

import { FormEvent, useState } from "react";
import { submitMarketingLead } from "@/lib/api";

export function WelcomeLeadForm({
  id = "welcome-lead",
  className = "",
}: {
  id?: string;
  className?: string;
}) {
  const [email, setEmail] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await submitMarketingLead({
        email,
        business_name: businessName.trim() || undefined,
        source: "welcome",
      });
      setMessage("You're on the list — we'll be in touch.");
      setEmail("");
      setBusinessName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your email.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form id={id} onSubmit={onSubmit} className={`ahoy-welcome-form ${className}`}>
      <label className="block">
        <span className="ahoy-label">Work email</span>
        <input
          type="email"
          required
          autoComplete="email"
          className="ahoy-input mt-1"
          placeholder="you@yourbusiness.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </label>
      <label className="mt-3 block">
        <span className="ahoy-label">Business name (optional)</span>
        <input
          type="text"
          autoComplete="organization"
          className="ahoy-input mt-1"
          placeholder="Oak Lawn Eye Care"
          value={businessName}
          onChange={(e) => setBusinessName(e.target.value)}
        />
      </label>
      <button type="submit" disabled={busy} className="ahoy-btn mt-4 w-full sm:w-auto">
        {busy ? "Sending…" : "Get A-hoy updates"}
      </button>
      {message && <p className="ahoy-success mt-3">{message}</p>}
      {error && <p className="ahoy-error mt-3">{error}</p>}
    </form>
  );
}
