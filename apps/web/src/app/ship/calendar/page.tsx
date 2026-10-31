"use client";

import { IconScroll } from "@/components/pirate/Icons";
import { ShipHeader } from "@/components/pirate/ShipHeader";
import { AhoyBackLink } from "@/components/AhoyBackLink";

export default function ShipCalendarPage() {
  return (
    <main className="mx-auto max-w-2xl space-y-4 px-6 py-12">
      <AhoyBackLink href="/ship/posts">Manifest</AhoyBackLink>
      <ShipHeader icon={<IconScroll />} title="Logbook">
        <p className="ahoy-muted mt-3">
          Stub — scheduled sails land with Ayrshare in Milestone D. Browse the Manifest for now.
        </p>
      </ShipHeader>
    </main>
  );
}
