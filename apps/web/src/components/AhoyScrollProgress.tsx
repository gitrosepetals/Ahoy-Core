"use client";

import { useEffect, useId, useRef, useState } from "react";

function sineCrest(y: number, amp: number) {
  return [
    `M0 ${y}`,
    `C100 ${y - amp} 100 ${y - amp} 200 ${y}`,
    `C300 ${y + amp} 300 ${y + amp} 400 ${y}`,
    `C500 ${y - amp} 500 ${y - amp} 600 ${y}`,
    `C700 ${y + amp} 700 ${y + amp} 800 ${y}`,
  ].join(" ");
}

function WaveTile({
  y,
  amp,
  fill,
  fillOpacity,
  stroke,
  strokeOpacity,
}: {
  y: number;
  amp: number;
  fill: string;
  fillOpacity: number;
  stroke: string;
  strokeOpacity: number;
}) {
  const crest = sineCrest(y, amp);
  return (
    <svg className="ahoy-wave-tile" viewBox="0 0 800 220" preserveAspectRatio="none" aria-hidden>
      <path d={`${crest} L800 220 L0 220 Z`} fill={fill} fillOpacity={fillOpacity} />
      <path
        d={crest}
        fill="none"
        stroke={stroke}
        strokeOpacity={strokeOpacity}
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function WaveTrack({
  className,
  y,
  amp,
  fill,
  fillOpacity,
  stroke,
  strokeOpacity,
}: {
  className: string;
  y: number;
  amp: number;
  fill: string;
  fillOpacity: number;
  stroke: string;
  strokeOpacity: number;
}) {
  const props = { y, amp, fill, fillOpacity, stroke, strokeOpacity };
  return (
    <div className={`ahoy-wave-track ${className}`}>
      <WaveTile {...props} />
      <WaveTile {...props} />
    </div>
  );
}

type Pt = { x: number; y: number };

/** Stable for the page session so scroll remounts don’t reshuffle the path. */
const TRAIL_SESSION = Math.floor(Math.random() * 1e9);

function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function trailSeed(start: Pt, end: Pt, pageW: number) {
  const h =
    TRAIL_SESSION ^
    (Math.round(start.y / 8) * 73856093) ^
    (Math.round(end.y / 8) * 19349663) ^
    (Math.round(pageW / 16) * 83492791);
  return h >>> 0;
}

function trailAmp(pageW: number) {
  const mid = pageW / 2;
  // Keep swings inside the viewport with a clear gutter margin
  return Math.max(48, Math.min(pageW * 0.28, mid - 36));
}

/** Serpentine L↔R down the page — swing size & reach vary; soft easing; always down. */
function buildSlither(start: Pt, end: Pt, pageW: number): string {
  const rand = mulberry32(trailSeed(start, end, pageW));
  const mid = pageW / 2;
  const maxAmp = trailAmp(pageW);
  const y0 = start.y;
  const y1 = Math.max(end.y, y0 + 520);
  let d = `M${start.x} ${y0}`;
  let x = start.x;
  let y = y0;
  let toRight = start.x < mid;
  let guard = 0;
  while (y < y1 - 8 && guard < 120) {
    guard += 1;
    const swing = 520 + rand() * 420;
    const amp = maxAmp * (0.72 + rand() * 0.28);
    const nextY = Math.min(y1, y + swing);
    const nextX = toRight ? mid + amp : mid - amp;
    const dy = Math.max(1, nextY - y);
    const t1 = 0.48 + rand() * 0.04;
    const t2 = 0.5 + rand() * 0.04;
    d += ` C${x} ${y + dy * t1} ${nextX} ${y + dy * t2} ${nextX} ${nextY}`;
    toRight = !toRight;
    x = nextX;
    y = nextY;
  }
  const dyEnd = Math.max(1, end.y - y);
  d += ` C${x} ${y + dyEnd * 0.5} ${end.x} ${end.y - dyEnd * 0.15} ${end.x} ${end.y}`;
  return d;
}

function findAnchors(root: HTMLElement): { start: Pt; end: Pt } | null {
  const marked = [...root.querySelectorAll<HTMLElement>("[data-ahoy-trail]")].filter(
    (el) => el.getBoundingClientRect().height > 2,
  );
  const fallback = [
    ...root.querySelectorAll<HTMLElement>("main h1, main .ahoy-panel"),
  ].filter((el) => el.getBoundingClientRect().height > 2);

  const list = marked.length >= 1 ? marked : fallback;
  if (list.length === 0) return null;

  const rr = root.getBoundingClientRect();
  const pageW = root.offsetWidth || window.innerWidth;
  const mid = pageW / 2;
  const amp = trailAmp(pageW);
  const first = list[0];
  const fr = first.getBoundingClientRect();
  // Start under the header block, in-frame left gutter — never through title/subtitle
  const start: Pt = {
    x: mid - amp,
    y: fr.bottom - rr.top + 16,
  };

  // End below the main column — not on a post/card
  const main = root.querySelector("main");
  const mr = (main ?? list[list.length - 1]).getBoundingClientRect();
  const end: Pt = {
    x: mid + amp * 0.55,
    y: Math.min(root.offsetHeight - 20, mr.bottom - rr.top + 36),
  };

  return { start, end };
}

/** Where the trail's drawn tip sits, as a fraction of the viewport height. */
const TIP_VIEWPORT_FRACTION = 0.65;

/**
 * Atmosphere: optional grey slither + deck waves.
 * Trail is Manifest-only; waves used on Ship + Crew Brand Brain.
 *
 * Scrolling never re-renders React: the progress bar and the trail's reveal clip are
 * updated straight on the DOM inside one rAF. The reveal is a clip rectangle that ends a
 * fixed distance down the viewport, so the trail's tip always stays on screen (a page-size
 * mask re-rasterized every frame was the source of the lag).
 */
export function AhoyScrollProgress({
  trail: showTrail = false,
  waves: showWaves = true,
}: {
  trail?: boolean;
  waves?: boolean;
} = {}) {
  const clipId = `ahoy-slither-${useId().replace(/:/g, "")}`;
  const [enabled, setEnabled] = useState(true);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [trail, setTrail] = useState("");
  const barRef = useRef<HTMLDivElement | null>(null);
  const clipRectRef = useRef<SVGRectElement | null>(null);
  const layoutKeyRef = useRef("");

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) setEnabled(false);

    let scrollRaf = 0;
    let layoutRaf = 0;
    let layoutTimer = 0;

    const getRoot = () =>
      document.querySelector<HTMLElement>(".ahoy-trail-root") ?? document.documentElement;

    /** Pure DOM writes — safe to run every frame. */
    const paint = () => {
      const doc = document.documentElement;
      const scrollY = window.scrollY || doc.scrollTop;
      const max = doc.scrollHeight - doc.clientHeight;
      const progress = max <= 0 ? 1 : Math.min(1, Math.max(0, scrollY / max));
      if (barRef.current) barRef.current.style.transform = `scaleX(${progress})`;

      const rect = clipRectRef.current;
      if (rect) {
        const rootTop = getRoot().getBoundingClientRect().top + scrollY;
        const atBottom = max > 0 && scrollY >= max - 2;
        const reveal = atBottom
          ? doc.scrollHeight
          : scrollY + window.innerHeight * TIP_VIEWPORT_FRACTION - rootTop;
        rect.setAttribute("height", String(Math.max(0, reveal)));
      }
    };

    const onScroll = () => {
      if (scrollRaf) return;
      scrollRaf = requestAnimationFrame(() => {
        scrollRaf = 0;
        paint();
      });
    };

    const rebuildPath = () => {
      layoutRaf = 0;
      const root = getRoot();
      const w = root.offsetWidth || window.innerWidth;
      const h = Math.max(root.offsetHeight, document.documentElement.scrollHeight);
      setSize((prev) => (Math.abs(prev.w - w) > 2 || Math.abs(prev.h - h) > 2 ? { w, h } : prev));

      const next = showTrail ? findAnchors(root) : null;
      if (!next) {
        layoutKeyRef.current = "";
        setTrail("");
      } else {
        // Coarse key — ignore small height jitter; extend path when page grows a lot
        const key = `${Math.round(w / 8)}:${Math.round(next.start.y / 16)}:${Math.round(next.end.y / 200)}`;
        if (key !== layoutKeyRef.current) {
          layoutKeyRef.current = key;
          setTrail(buildSlither(next.start, next.end, w));
        }
      }
      requestAnimationFrame(paint);
    };

    const onLayout = () => {
      // Debounce: mobile chrome / content reveals fire many resizes while scrolling
      if (layoutTimer) window.clearTimeout(layoutTimer);
      layoutTimer = window.setTimeout(() => {
        layoutTimer = 0;
        if (layoutRaf) return;
        layoutRaf = requestAnimationFrame(rebuildPath);
      }, 120);
    };

    requestAnimationFrame(rebuildPath);
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onLayout, { passive: true });
    // Observe the ship root only — documentElement resize fires on scroll in many browsers
    const ro = new ResizeObserver(onLayout);
    const root = document.querySelector(".ahoy-trail-root");
    if (root) ro.observe(root);

    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onLayout);
      ro.disconnect();
      if (scrollRaf) cancelAnimationFrame(scrollRaf);
      if (layoutRaf) cancelAnimationFrame(layoutRaf);
      if (layoutTimer) window.clearTimeout(layoutTimer);
    };
  }, [showTrail]);

  return (
    <>
      {enabled ? <div ref={barRef} className="ahoy-scroll-progress" aria-hidden /> : null}

      {showTrail && enabled && size.w > 0 && size.h > 0 && trail ? (
        <svg
          className="ahoy-dotted-line ahoy-dotted-line-page"
          width={size.w}
          height={size.h}
          viewBox={`0 0 ${size.w} ${size.h}`}
          aria-hidden
        >
          <defs>
            <clipPath id={clipId} clipPathUnits="userSpaceOnUse">
              <rect ref={clipRectRef} x="0" y="0" width={size.w} height="0" />
            </clipPath>
          </defs>
          <path
            d={trail}
            fill="none"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray="5 20"
            clipPath={`url(#${clipId})`}
            style={{
              stroke: "var(--ahoy-dotted-stroke)",
              strokeOpacity: "var(--ahoy-dotted-opacity)",
            }}
          />
        </svg>
      ) : null}

      {showWaves ? (
        <div className="ahoy-deck-overlay" aria-hidden>
          <div className="ahoy-deck-waves">
            <WaveTrack
              className="ahoy-wave-scroll-a"
              y={80}
              amp={22}
              fill="var(--ahoy-fg)"
              fillOpacity={0.03}
              stroke="var(--ahoy-fg)"
              strokeOpacity={0.14}
            />
            <WaveTrack
              className="ahoy-wave-scroll-b"
              y={120}
              amp={16}
              fill="var(--ahoy-fg)"
              fillOpacity={0.02}
              stroke="var(--ahoy-lantern)"
              strokeOpacity={0.22}
            />
          </div>
          <div className="ahoy-deck-vignette" />
        </div>
      ) : null}
    </>
  );
}
