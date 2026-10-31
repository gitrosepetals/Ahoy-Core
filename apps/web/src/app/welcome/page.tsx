import Link from "next/link";
import { AhoyLogo } from "@/components/pirate/AhoyLogo";
import { WelcomeAtmosphere } from "@/components/WelcomeAtmosphere";
import { WelcomeLeadForm } from "@/components/WelcomeLeadForm";

export const metadata = {
  title: "A-hoy — Chart your growth. Automate the rest.",
  description:
    "AI marketing captain and creative partner for small businesses. Monitor ROI, approve posts, and let Crew handle the rest.",
};

export default function WelcomePage() {
  return (
    <div className="ahoy-welcome-root relative min-h-screen">
      <WelcomeAtmosphere />
      <div className="relative z-10">
        <header className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-6 py-5">
          <AhoyLogo href="/welcome" className="ahoy-logo-compact" markClassName="ahoy-logo-mark-sm" />
          <Link href="/auth/sign-in" className="ahoy-link">
            Already a Captain?
          </Link>
        </header>

        <main>
          <section className="ahoy-welcome-hero mx-auto flex min-h-[calc(100vh-4.5rem)] max-w-5xl flex-col justify-center px-6 pb-16 pt-6">
            <div className="ahoy-rise max-w-2xl">
              <p className="ahoy-brand">A-hoy</p>
              <div className="ahoy-brass-rule" />
              <h1 className="ahoy-title mt-5">Chart your growth. Automate the rest.</h1>
              <p className="ahoy-muted mt-4 max-w-xl">
                Your AI first mate for small business growth — authentic shoots, AI-multiplied
                content, and a Bridge where you approve in one click.
              </p>
            </div>
            <div className="ahoy-rise-delay mt-8 max-w-md">
              <WelcomeLeadForm />
              <p className="ahoy-muted mt-3">
                No spam. Updates on plans, shoots, and when the Ship opens for your berth.
              </p>
            </div>
          </section>

          <section className="border-t border-[var(--ahoy-panel-border)] px-6 py-16">
            <div className="mx-auto max-w-5xl">
              <p className="ahoy-kicker">How it works</p>
              <h2 className="ahoy-title-sm mt-2">Bridge &amp; Engine Room</h2>
              <div className="ahoy-brass-rule" />
              <div className="mt-8 grid gap-10 md:grid-cols-2">
                <div>
                  <h3 className="ahoy-label">The Bridge</h3>
                  <p className="ahoy-prose mt-2">
                    You monitor ROI, leads, and reviews — then approve posts and Reels in seconds.
                    Stay on the helm; we handle the sails.
                  </p>
                </div>
                <div>
                  <h3 className="ahoy-label">The Engine Room</h3>
                  <p className="ahoy-prose mt-2">
                    Crew captures real photo and video of your business. AI multiplies that into a
                    month of social, email, and local updates — still unmistakably yours.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="border-t border-[var(--ahoy-panel-border)] px-6 py-16">
            <div className="mx-auto max-w-5xl">
              <p className="ahoy-kicker">Built for</p>
              <h2 className="ahoy-title-sm mt-2">Local businesses that live on the tools</h2>
              <div className="ahoy-brass-rule" />
              <ul className="mt-8 space-y-6">
                <li>
                  <p className="ahoy-label">Home services</p>
                  <p className="ahoy-muted mt-1">
                    HVAC, plumbing, landscaping — consistent leads while you&apos;re on the job.
                  </p>
                </li>
                <li>
                  <p className="ahoy-label">Local retail &amp; cafes</p>
                  <p className="ahoy-muted mt-1">
                    Foot traffic and social without a daily content grind.
                  </p>
                </li>
                <li>
                  <p className="ahoy-label">Boutique wellness &amp; clinics</p>
                  <p className="ahoy-muted mt-1">
                    Reviews, recalls, and educational Reels that still sound like your practice.
                  </p>
                </li>
              </ul>
            </div>
          </section>

          <section className="border-t border-[var(--ahoy-panel-border)] px-6 py-16">
            <div className="mx-auto max-w-5xl">
              <p className="ahoy-kicker">Plans</p>
              <h2 className="ahoy-title-sm mt-2">Pick your berth</h2>
              <div className="ahoy-brass-rule" />
              <ul className="mt-8 space-y-6">
                <li className="flex flex-wrap items-baseline justify-between gap-2 border-b border-[var(--ahoy-panel-border)] pb-4">
                  <div>
                    <p className="ahoy-label">Harbor</p>
                    <p className="ahoy-muted mt-1">Remote / AI-polished hybrid</p>
                  </div>
                  <p className="ahoy-stat text-[1.25rem]">$499/mo</p>
                </li>
                <li className="flex flex-wrap items-baseline justify-between gap-2 border-b border-[var(--ahoy-panel-border)] pb-4">
                  <div>
                    <p className="ahoy-label">Cruiser</p>
                    <p className="ahoy-muted mt-1">Quarterly on-site shoot + automation</p>
                  </div>
                  <p className="ahoy-stat text-[1.25rem]">$1,250/mo</p>
                </li>
                <li className="flex flex-wrap items-baseline justify-between gap-2 pb-2">
                  <div>
                    <p className="ahoy-label">Flagship</p>
                    <p className="ahoy-muted mt-1">Monthly shoots + full growth partner</p>
                  </div>
                  <p className="ahoy-stat text-[1.25rem]">$2,500+/mo</p>
                </li>
              </ul>
              <div className="mt-10 max-w-md">
                <p className="ahoy-prose mb-4">
                  Leave your email — we&apos;ll share openings and how to board.
                </p>
                <WelcomeLeadForm id="welcome-lead-plans" />
              </div>
            </div>
          </section>
        </main>

        <footer className="border-t border-[var(--ahoy-panel-border)] px-6 py-10">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4">
            <span className="ahoy-muted">A-hoy Marketing Solutions</span>
            <nav className="flex flex-wrap gap-4" aria-label="Footer">
              <Link href="/welcome" className="ahoy-link">
                Welcome
              </Link>
              <Link href="/auth/sign-in" className="ahoy-link">
                Sign in
              </Link>
              <Link href="/ship" className="ahoy-link">
                Ship
              </Link>
            </nav>
          </div>
        </footer>
      </div>
    </div>
  );
}
