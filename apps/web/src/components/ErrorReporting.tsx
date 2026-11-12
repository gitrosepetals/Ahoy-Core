"use client";

import { useEffect } from "react";

/** Sentry for the Ship / Crew Deck, loaded only when NEXT_PUBLIC_SENTRY_DSN is set. */
export function ErrorReporting() {
  useEffect(() => {
    const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
    if (!dsn) return;
    void import("@sentry/browser").then((Sentry) =>
      Sentry.init({
        dsn,
        environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? "development",
        sendDefaultPii: false,
        tracesSampleRate: 0,
      }),
    );
  }, []);
  return null;
}
