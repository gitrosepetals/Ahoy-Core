import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-8 px-6 py-16">
      <div>
        <p className="text-sm uppercase tracking-[0.2em] text-sky-700">A-hoy</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-900">
          Chart your growth. Automate the rest.
        </h1>
        <p className="mt-3 max-w-xl text-slate-600">
          The Ship is for Captains (business owners). The Crew Deck is for A-hoy operators.
          Milestone A: sign-in, tenancy, and push-token plumbing.
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        <Link
          href="/ship"
          className="rounded-lg bg-sky-800 px-4 py-2.5 text-sm font-medium text-white hover:bg-sky-900"
        >
          Open the Ship
        </Link>
        <Link
          href="/crew"
          className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-800 hover:bg-slate-50"
        >
          Open Crew Deck
        </Link>
        <Link
          href="/auth/sign-in"
          className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-800 hover:bg-slate-50"
        >
          Sign in
        </Link>
      </div>
    </main>
  );
}
