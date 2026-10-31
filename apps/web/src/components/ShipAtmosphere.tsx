"use client";

import { usePathname } from "next/navigation";
import { AhoyScrollProgress } from "@/components/AhoyScrollProgress";

/** Grey trail on Manifest (no waves); deck waves on other Ship pages. */
export function ShipAtmosphere() {
  const pathname = usePathname() || "";
  const trail =
    pathname.startsWith("/ship/posts") || pathname.startsWith("/ship/queue");
  return <AhoyScrollProgress trail={trail} waves={!trail} />;
}
