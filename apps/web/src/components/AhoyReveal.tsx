"use client";

import {
  type CSSProperties,
  type ElementType,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from "react";

export type AhoyRevealVariant = "rise" | "sail" | "heave" | "drop";

type AhoyRevealProps = {
  children: ReactNode;
  className?: string;
  /** Stagger delay in ms once the element enters view */
  delay?: number;
  as?: ElementType;
  /** Play once (default) or every time it re-enters */
  once?: boolean;
  /**
   * Pirate motion:
   * - rise: soft lift (default)
   * - sail: fills in from port with a slight yaw
   * - heave: rises from the bilge with a sway
   * - drop: drops like an anchor from above
   */
  variant?: AhoyRevealVariant;
};

/** Scroll-triggered pirate motion — transform + opacity only. */
export function AhoyReveal({
  children,
  className = "",
  delay = 0,
  as: Tag = "div",
  once = true,
  variant = "rise",
}: AhoyRevealProps) {
  const ref = useRef<HTMLElement | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setInView(true);
      return;
    }

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          if (once) io.disconnect();
        } else if (!once) {
          setInView(false);
        }
      },
      { threshold: 0.14, rootMargin: "0px 0px -6% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [once]);

  const style: CSSProperties | undefined =
    delay > 0 ? ({ ["--ahoy-reveal-delay" as string]: `${delay}ms` } as CSSProperties) : undefined;

  return (
    <Tag
      ref={ref}
      className={`ahoy-reveal ahoy-reveal-${variant}${inView ? " ahoy-reveal-in" : ""}${className ? ` ${className}` : ""}`}
      style={style}
    >
      {children}
    </Tag>
  );
}
