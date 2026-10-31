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

const SWING = 780;

/** Serpentine from first container → last, in root-local px. */
function buildSlither(start: Pt, end: Pt, pageW: number): string {
  const mid = pageW / 2;
  // Wide into the gutters so the path isn't lost under the center column
  const amp = Math.min(pageW * 0.46, 520);
  const y0 = start.y;
  const y1 = Math.max(end.y, y0 + SWING);
  let d = `M${start.x} ${y0}`;
  let x = start.x;
  let y = y0;
  let toRight = start.x <= mid;
  let guard = 0;
  while (y < y1 - 8 && guard < 200) {
    guard += 1;
    const nextY = Math.min(y1, y + SWING);
    const nextX = toRight ? mid + amp : mid - amp;
    const dy = nextY - y;
    // Ease handles stay near each endpoint — long, soft arcs instead of sharp S-bends
    d += ` C${x} ${y + dy * 0.48} ${nextX} ${y + dy * 0.52} ${nextX} ${nextY}`;
    toRight = !toRight;
    x = nextX;
    y = nextY;
  }
  const dyEnd = Math.max(1, end.y - y);
  d += ` C${x} ${y + dyEnd * 0.45} ${end.x} ${end.y - dyEnd * 0.2} ${end.x} ${end.y}`;
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
  const first = list[0];
  const fr = first.getBoundingClientRect();
  const start: Pt = {
    x: fr.left - rr.left + fr.width / 2,
    y: fr.top - rr.top + Math.min(28, fr.height * 0.35),
  };

  // X sits below the main column — not on a post/card
  const main = root.querySelector("main");
  const mr = (main ?? list[list.length - 1]).getBoundingClientRect();
  const end: Pt = {
    x: mr.left - rr.left + mr.width / 2,
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
  const [pathLen, setPathLen] = useState(0);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [trail, setTrail] = useState("");
  const [drawn, setDrawn] = useState(0);
  const [anchors, setAnchors] = useState<{ start: Pt; end: Pt } | null>(null);
  const pathRef = useRef<SVGPathElement | null>(null);

  const placeDrawn = (page: number, top: number, clientH: number, span: { start: Pt; end: Pt }) => {
    const el = pathRef.current;
    if (!el) return;
    const len = el.getTotalLength();
    if (len <= 0) return;
    setPathLen(len);

    const y0 = span.start.y;
    const y1 = Math.max(span.end.y, y0 + 1);
    const focusY = top + clientH * 0.5;

    let along = 0;
    if (page >= 0.9 || focusY >= y1 - 12) {
      along = len;
    } else {
      let lo = 0;
      let hi = len;
      for (let i = 0; i < 20; i++) {
        const mid = (lo + hi) / 2;
        if (el.getPointAtLength(mid).y < focusY) lo = mid;
        else hi = mid;
      }
      along = hi;
      if (page >= 0.75) {
        const blend = (page - 0.75) / 0.15;
        along = along + (len - along) * Math.min(1, Math.max(0, blend));
      }
    }

    setDrawn(along);
  };

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) setEnabled(false);

    let raf = 0;
    const update = () => {
      raf = 0;
      const root =
        document.querySelector<HTMLElement>(".ahoy-trail-root") ?? document.documentElement;
      const w = root.offsetWidth || window.innerWidth;
      const h = Math.max(root.offsetHeight, document.documentElement.scrollHeight);
      setSize({ w, h });

      if (showTrail) {
        const next = findAnchors(root);
        if (next) {
          setAnchors(next);
          setTrail(buildSlither(next.start, next.end, w));
        }
      } else {
        setTrail("");
        setAnchors(null);
        setPathLen(0);
        setDrawn(0);
      }

      const doc = document.documentElement;
      const max = Math.max(1, doc.scrollHeight - doc.clientHeight);
      const top = window.scrollY || doc.scrollTop;
      const page = Math.min(1, Math.max(0, top / max));
      setPageP(page);
    };
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(update);
    };

    requestAnimationFrame(update);
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    const ro = new ResizeObserver(onScroll);
    const root = document.querySelector(".ahoy-trail-root");
    if (root) ro.observe(root);
    ro.observe(document.documentElement);

    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      ro.disconnect();
      if (raf) cancelAnimationFrame(raf);
    };
  }, [showTrail]);

  // Remeasure draw length after the path is in the DOM with the latest `d`
  useEffect(() => {
    if (!showTrail || !trail || !anchors || size.h <= 0) return;
    const top = window.scrollY || document.documentElement.scrollTop;
    const page =
      document.documentElement.scrollHeight <= document.documentElement.clientHeight
        ? 1
        : Math.min(
            1,
            top /
              Math.max(
                1,
                document.documentElement.scrollHeight - document.documentElement.clientHeight,
              ),
          );
    // Double rAF: wait for SVG layout after trail string commit
    const id = requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        placeDrawn(page, top, document.documentElement.clientHeight, anchors);
      });
    });
    return () => cancelAnimationFrame(id);
  }, [showTrail, trail, anchors, size.h, pageP]);

  const len = pathLen || 1;

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
                fill="none"
                stroke="white"
                strokeWidth="24"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeDasharray={pathLen > 0 ? `${Math.max(0.001, drawn)} ${len}` : "0 1"}
              />
            </mask>
          </defs>

          <path ref={pathRef} d={trail} fill="none" stroke="transparent" strokeWidth="1" />

          {enabled && pathLen > 0 ? (
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
