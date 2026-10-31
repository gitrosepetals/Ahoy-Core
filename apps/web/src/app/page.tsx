import Link from "next/link";
import { AhoyLogo } from "@/components/pirate/AhoyLogo";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-8 px-6 py-16">
      <div className="ahoy-rise">
        <AhoyLogo markClassName="ahoy-logo-mark-lg" href={null} />
        <div className="ahoy-brass-rule" />
        <h1 className="ahoy-title mt-5">Rigged light. Sails fast.</h1>
        <p className="ahoy-muted mt-3 max-w-xl">
          Black or white deck — pirate in the fittings, marks, and motion.
        </p>
      </div>
      <div className="ahoy-rise-delay flex flex-wrap gap-3">
        <Link href="/ship" className="ahoy-btn">
          Board the Ship
        </Link>
        <Link href="/crew" className="ahoy-btn-ghost">
          Crew Deck
        </Link>
        <Link href="/auth/sign-in" className="ahoy-btn-ghost">
          Sign in
        </Link>
      </div>
      <p className="ahoy-rise-delay">
        <Link href="/welcome" className="ahoy-link">
          New here? See A-hoy
        </Link>
      </p>
    </main>
  );
}
