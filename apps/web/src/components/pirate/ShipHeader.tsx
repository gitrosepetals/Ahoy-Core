import type { ReactNode } from "react";

export function ShipHeader({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div data-ahoy-trail>
      <p className="ahoy-kicker">The Ship</p>
      <h1 className="ahoy-title mt-2 flex items-center gap-3">
        <span className="ahoy-mark-wrap text-[var(--ahoy-copper)]" aria-hidden>
          {icon}
        </span>
        {title}
      </h1>
      <div className="ahoy-brass-rule" />
      {children}
    </div>
  );
}
