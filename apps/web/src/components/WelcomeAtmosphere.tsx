"use client";

import { AhoyScrollProgress } from "@/components/AhoyScrollProgress";

/** Quiet deck waves for the public welcome page — no Manifest trail. */
export function WelcomeAtmosphere() {
  return <AhoyScrollProgress trail={false} waves />;
}
