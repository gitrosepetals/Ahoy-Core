import type { ReactNode, SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { title?: string };

function Svg({ title, children, className, ...rest }: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className ?? "ahoy-mark"}
      aria-hidden={title ? undefined : true}
      role={title ? "img" : undefined}
      {...rest}
    >
      {title ? <title>{title}</title> : null}
      {children}
    </svg>
  );
}

/** Ship's wheel — helm / home brand */
export function IconWheel(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="3" />
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 3.5v3M12 17.5v3M3.5 12h3M17.5 12h3M6.2 6.2l2.1 2.1M15.7 15.7l2.1 2.1M17.8 6.2l-2.1 2.1M8.3 15.7l-2.1 2.1" />
    </Svg>
  );
}

/** Compass rose — Treasure Map */
export function IconCompass(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 4.5 14.2 12 12 19.5 9.8 12Z" fill="currentColor" stroke="none" opacity="0.9" />
      <path d="M4.5 12 12 9.8 19.5 12 12 14.2Z" fill="currentColor" stroke="none" opacity="0.35" />
      <circle cx="12" cy="12" r="1.25" fill="currentColor" stroke="none" />
    </Svg>
  );
}

/** Scroll / ship's papers — Manifest */
export function IconScroll(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M7 5.5h9.5a2 2 0 0 1 2 2V18a1.5 1.5 0 0 1-1.5 1.5H8" />
      <path d="M7 5.5A2.5 2.5 0 0 0 4.5 8v9.5A1.5 1.5 0 0 0 6 19h2" />
      <path d="M9.5 9.5h6M9.5 12.5h6M9.5 15.5h4" />
    </Svg>
  );
}

/** Treasure chest — Vault */
export function IconChest(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 10.5h16v8.5H4z" />
      <path d="M4 10.5 6.5 6h11L20 10.5" />
      <path d="M12 10.5v8.5M9.5 14.5h5" />
      <circle cx="12" cy="14.5" r="1" fill="currentColor" stroke="none" />
    </Svg>
  );
}

/** Spyglass — Reputation Radar */
export function IconSpyglass(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M14 6.5 19.5 4l.8 2.2-5.5 2.5z" />
      <path d="M13.5 7 5.5 18.5" />
      <path d="M4 17.5h4.5v3H4z" />
      <path d="M10 9.5 15 12" />
    </Svg>
  );
}

/** Anchor — Crew / berth */
export function IconAnchor(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="5.5" r="2" />
      <path d="M12 7.5v11.5" />
      <path d="M8 11h8" />
      <path d="M5.5 15.5A6.5 6.5 0 0 0 12 19a6.5 6.5 0 0 0 6.5-3.5" />
    </Svg>
  );
}

/** Sloop silhouette — landing mark */
export function IconSloop(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 17.5h16l-2 2.5H6z" fill="currentColor" stroke="none" opacity="0.9" />
      <path d="M7 17.5 12 5.5 12 17.5" />
      <path d="M12 8.5h5.5L12 14" />
      <path d="M12 5.5v-1" />
    </Svg>
  );
}

/** Coin stack — ROI / treasure */
export function IconCoins(props: IconProps) {
  return (
    <Svg {...props}>
      <ellipse cx="10" cy="16" rx="6" ry="2.5" />
      <path d="M4 16v-2.5c0-1.4 2.7-2.5 6-2.5s6 1.1 6 2.5V16" />
      <ellipse cx="14" cy="10.5" rx="5.5" ry="2.2" />
      <path d="M8.5 10.5V8c0-1.2 2.5-2.2 5.5-2.2s5.5 1 5.5 2.2v2.5" />
    </Svg>
  );
}
