"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/ship", label: "Home", match: (p: string) => p === "/ship" },
  {
    href: "/ship/posts",
    label: "Posts",
    match: (p: string) => p.startsWith("/ship/posts") || p.startsWith("/ship/queue"),
  },
  { href: "/ship/media", label: "Media", match: (p: string) => p.startsWith("/ship/media") },
  { href: "/ship/reviews", label: "Reviews", match: (p: string) => p.startsWith("/ship/reviews") },
];

export function ShipNav() {
  const pathname = usePathname() || "/ship";
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-slate-200 bg-white/95 backdrop-blur">
      <ul className="mx-auto flex max-w-lg items-stretch justify-between px-2 py-2">
        {LINKS.map((link) => {
          const active = link.match(pathname);
          return (
            <li key={link.href} className="flex-1">
              <Link
                href={link.href}
                className={`block rounded-md px-1 py-2 text-center text-sm font-medium ${
                  active ? "bg-sky-50 text-sky-900" : "text-slate-600"
                }`}
              >
                {link.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
