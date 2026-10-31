"use client";

import { Suspense, useEffect } from "react";
import { useRouter } from "next/navigation";

function RedirectInner() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/ship/posts?tab=pending");
  }, [router]);
  return <main className="p-8 text-sm text-slate-600">Opening Posts…</main>;
}

/** Legacy path — approval queue lives on /ship/posts now. */
export default function ShipQueueRedirectPage() {
  return (
    <Suspense fallback={<main className="p-8 text-sm text-slate-600">Opening Posts…</main>}>
      <RedirectInner />
    </Suspense>
  );
}
