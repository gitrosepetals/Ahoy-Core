"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { verifyMagicLink } from "@/lib/api";
import { saveAccessToken } from "@/lib/session";

function VerifyInner() {
  const params = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setError("Missing token");
      return;
    }
    verifyMagicLink(token)
      .then((res) => {
        saveAccessToken(res.access_token);
        router.replace(res.redirect_path || (res.user.role === "crew" ? "/crew" : "/ship"));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Verify failed"));
  }, [params, router]);

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center justify-center px-6">
      <p className="text-sm text-slate-700">{error ?? "Signing you in…"}</p>
    </main>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<main className="p-8 text-sm">Loading…</main>}>
      <VerifyInner />
    </Suspense>
  );
}
