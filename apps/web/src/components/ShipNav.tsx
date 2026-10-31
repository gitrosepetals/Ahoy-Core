"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AhoyLogo } from "@/components/pirate/AhoyLogo";
import { ThemeToggle } from "@/components/ThemeToggle";

const LINKS = [
  {
    href: "/ship",
    label: "Map",
    match: (p: string) => p === "/ship",
  },
  {
    href: "/ship/posts",
    label: "Manifest",
    match: (p: string) => p.startsWith("/ship/posts") || p.startsWith("/ship/queue"),
  },
  {
    href: "/ship/media",
    label: "Vault",
    match: (p: string) => p.startsWith("/ship/media"),
  },
  {
    href: "/ship/reviews",
    label: "Radar",
    match: (p: string) => p.startsWith("/ship/reviews"),
  },
];

export function ShipNav() {
  const pathname = usePathname() || "/ship";
  return (
    <header className="sticky top-0 z-40 border-b border-[var(--ahoy-panel-border)] bg-[var(--ahoy-bg)]">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-6 px-6">
        <AhoyLogo
          href="/ship"
          className="ahoy-logo-compact shrink-0"
          markClassName="ahoy-logo-mark-sm"
          title="A-hoy Ship"
        />
        <nav className="min-w-0 flex-1" aria-label="Ship">
          <ul className="m-0 flex list-none items-center gap-5 p-0">
            {LINKS.map((link) => {
              const active = link.match(pathname);
              return (
                <li key={link.href} className="m-0 p-0">
                  <Link
                    href={link.href}
                    className={
                      active
                        ? "inline-flex h-10 items-center border-b-2 border-[var(--ahoy-lantern)] px-1 font-bold text-[var(--ahoy-fg)] no-underline"
                        : "inline-flex h-10 items-center border-b-2 border-transparent px-1 font-bold text-[var(--ahoy-muted)] no-underline hover:text-[var(--ahoy-fg)]"
                    }
                    aria-current={active ? "page" : undefined}
                  >
                    {link.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <ThemeToggle className="shrink-0" />
      </div>
    </header>
  );
}
