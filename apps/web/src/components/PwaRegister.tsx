"use client";

import { useEffect } from "react";
import { registerServiceWorker } from "@/lib/push";

/** Registers the service worker once per load so the Ship is installable and can get push. */
export function PwaRegister() {
  useEffect(() => {
    void registerServiceWorker();
  }, []);
  return null;
}
