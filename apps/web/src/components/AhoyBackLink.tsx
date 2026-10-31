import Link from "next/link";
import type { ReactNode } from "react";

type AhoyBackLinkProps = {
  href: string;
  children: ReactNode;
  className?: string;
};

/** Large, clear return control — min 44px touch target. */
export function AhoyBackLink({ href, children, className = "" }: AhoyBackLinkProps) {
  return (
    <Link href={href} className={`ahoy-back ${className}`.trim()}>
      <span className="ahoy-back-arrow" aria-hidden>
        ←
      </span>
      <span>{children}</span>
    </Link>
  );
}
