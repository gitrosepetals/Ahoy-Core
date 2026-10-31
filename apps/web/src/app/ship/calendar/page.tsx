"use client";

import Link from "next/link";

export default function ShipCalendarPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <p className="text-sm font-medium uppercase tracking-[0.16em] text-sky-800">The Ship</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Calendar</h1>
      <p className="ahoy-muted mt-3">
        Stub — date layout ships with Ayrshare in Milestone D. For now, browse captions on{" "}
        <Link href="/ship/posts" className="font-medium text-sky-800 underline">
          Posts
        </Link>
        .
      </p>
    </main>
  );
}
