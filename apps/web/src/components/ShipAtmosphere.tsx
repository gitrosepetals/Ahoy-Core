"use client";

import { usePathname } from "next/navigation";
import { AhoyScrollProgress } from "@/components/AhoyScrollProgress";

/** Ship deck waves everywhere; grey trail only on Manifest. */
export function ShipAtmosphere() {
  const pathname = usePathname() || "";
  const trail =
    pathname.startsWith("/ship/posts") || pathname.startsWith("/ship/queue");
  return <AhoyScrollProgress trail={trail} waves />;
}
