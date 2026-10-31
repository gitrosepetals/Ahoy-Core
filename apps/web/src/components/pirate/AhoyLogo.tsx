import Link from "next/link";

type AhoyLogoProps = {
  /** Show wordmark beside the mark */
  withWordmark?: boolean;
  /** Link to home */
  href?: string | null;
  className?: string;
  markClassName?: string;
  /** Accessible name */
  title?: string;
};

/** A-hoy mark: sail as letter A + hull — theme-aware via currentColor + pennant accent. */
export function AhoyMark({ className = "ahoy-logo-mark", title }: { className?: string; title?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role={title ? "img" : "presentation"}
      aria-hidden={title ? undefined : true}
    >
      {title ? <title>{title}</title> : null}
      {/* Mast */}
      <path d="M32 8v36" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      {/* Mainsail as A */}
      <path
        d="M32 10 48 42H36.5L32 32 27.5 42H16L32 10Z"
        fill="currentColor"
        fillOpacity="0.12"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      {/* A crossbar */}
      <path d="M24 30h16" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      {/* Hull */}
      <path
        d="M12 50c4 6 36 6 40 0H12Z"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      {/* Pennant */}
      <path d="M32 8h14l-4 4 4 4H32V8Z" fill="var(--ahoy-lantern)" />
    </svg>
  );
}

export function AhoyLogo({
  withWordmark = true,
  href = "/",
  className = "",
  markClassName = "",
  title = "A-hoy",
}: AhoyLogoProps) {
  const inner = (
    <span className={`ahoy-logo ${className}`.trim()}>
      <AhoyMark className={`ahoy-logo-mark ${markClassName}`.trim()} title={withWordmark ? undefined : title} />
      {withWordmark ? <span className="ahoy-logo-word">A-hoy</span> : null}
    </span>
  );

  if (href) {
    return (
      <Link href={href} className="ahoy-logo-link" aria-label={title}>
        {inner}
      </Link>
    );
  }

  return inner;
}
