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

/**
 * Atmosphere: optional grey slither + deck waves.
 * Trail is Manifest-only; waves used on Ship + Crew Brand Brain.
 */
export function AhoyScrollProgress({
  trail: showTrail = false,
  waves: showWaves = true,
}: {
  trail?: boolean;
  waves?: boolean;
} = {}) {
  const maskId = useId().replace(/:/g, "");
  const [pageP, setPageP] = useState(0);
  const [enabled, setEnabled] = useState(true);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [trail, setTrail] = useState("");
  const svgRef = useRef<SVGSVGElement | null>(null);
  const layoutKeyRef = useRef("");
  const sizeRef = useRef({ w: 0, h: 0 });

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) setEnabled(false);

    let scrollRaf = 0;
    let layoutRaf = 0;
    let layoutTimer = 0;

    const syncSvgBox = (w: number, h: number) => {
      sizeRef.current = { w, h };
      const svg = svgRef.current;
      if (svg) {
        svg.setAttribute("width", String(w));
        svg.setAttribute("height", String(h));
        svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
      }
    };

    const readPage = () => {
      const doc = document.documentElement;
      if (doc.scrollHeight <= doc.clientHeight) return 1;
      const max = Math.max(1, doc.scrollHeight - doc.clientHeight);
      return Math.min(1, Math.max(0, (window.scrollY || doc.scrollTop) / max));
    };

    const onScroll = () => {
      if (scrollRaf) return;
      scrollRaf = requestAnimationFrame(() => {
        scrollRaf = 0;
        const root =
          document.querySelector<HTMLElement>(".ahoy-trail-root") ?? document.documentElement;
        const w = root.offsetWidth || window.innerWidth;
        const h = Math.max(root.offsetHeight, document.documentElement.scrollHeight);
        // Grow the SVG with the page without rebuilding the path (avoids vanish mid-scroll)
        if (h > sizeRef.current.h + 2 || Math.abs(w - sizeRef.current.w) > 2) {
          syncSvgBox(w, Math.max(h, sizeRef.current.h));
          setSize({ w, h: Math.max(h, sizeRef.current.h) });
        }
        setPageP(readPage());
      });
    };

    const rebuildPath = () => {
      layoutRaf = 0;
      const root =
        document.querySelector<HTMLElement>(".ahoy-trail-root") ?? document.documentElement;
      const w = root.offsetWidth || window.innerWidth;
      const h = Math.max(root.offsetHeight, document.documentElement.scrollHeight);
      syncSvgBox(w, h);
      setSize({ w, h });

      if (!showTrail) {
        layoutKeyRef.current = "";
        setTrail("");
        setPageP(readPage());
        return;
      }

      const next = findAnchors(root);
      if (!next) {
        setTrail("");
        setPageP(readPage());
        return;
      }

      // Coarse key — ignore small height jitter; extend path when page grows a lot
      const key = `${Math.round(w / 8)}:${Math.round(next.start.y / 16)}:${Math.round(next.end.y / 200)}`;
      if (key !== layoutKeyRef.current) {
        layoutKeyRef.current = key;
        setTrail(buildSlither(next.start, next.end, w));
      }
      setPageP(readPage());
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

  // pathLength=1 → reveal is just page progress (no getTotalLength flicker)
  const drawn = Math.max(0.001, pageP);

  return (
    <>
      {enabled ? (
        <div
          className="ahoy-scroll-progress"
          style={{ transform: `scaleX(${pageP})` }}
          aria-hidden
        />
      ) : null}

      {showTrail && size.w > 0 && size.h > 0 && trail ? (
        <svg
          ref={svgRef}
          className="ahoy-dotted-line ahoy-dotted-line-page"
          width={size.w}
          height={size.h}
          viewBox={`0 0 ${size.w} ${size.h}`}
          aria-hidden
        >
          <defs>
            <mask
              id={`ahoy-slither-${maskId}`}
              maskUnits="userSpaceOnUse"
              x="0"
              y="0"
              width={size.w}
              height={size.h}
            >
              <rect width={size.w} height={size.h} fill="black" />
              <path
                d={trail}
                pathLength={1}
                fill="none"
                stroke="white"
                strokeWidth="24"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeDasharray={`${drawn} 1`}
              />
            </mask>
          </defs>

          {enabled ? (
            <path
              d={trail}
              fill="none"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="5 20"
              mask={`url(#ahoy-slither-${maskId})`}
              style={{
                stroke: "var(--ahoy-dotted-stroke)",
                strokeOpacity: "var(--ahoy-dotted-opacity)",
              }}
            />
          ) : null}
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
