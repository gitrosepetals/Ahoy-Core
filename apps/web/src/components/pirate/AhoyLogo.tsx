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

/**
 * A-hoy mark: sail / tent chevron + mast pennant + hull crescent.
 * Transparent SVG — theme-aware via currentColor (no background fill).
 */
export function AhoyMark({
  className = "ahoy-logo-mark",
  title,
}: {
  className?: string;
  title?: string;
}) {
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
      {/* Mast stub */}
      <path
        d="M32 6v10"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinecap="round"
      />
      {/* Swallowtail pennant */}
      <path d="M34 7.5h16l-4.5 4.5 4.5 4.5H34V7.5Z" fill="currentColor" />
      {/* Outer sail (open base) */}
      <path
        d="M32 14 50 46H14L32 14Z"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {/* Inner chevron / tent opening */}
      <path
        d="M23 46 32 28 41 46"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {/* Hull crescent */}
      <path
        d="M12 54c6 5.5 34 5.5 40 0"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinecap="round"
      />
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
      <AhoyMark
        className={`ahoy-logo-mark ${markClassName}`.trim()}
        title={withWordmark ? undefined : title}
      />
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
