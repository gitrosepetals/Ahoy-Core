/** Gentle hawser sag — solid strokes only (no dashes, no beaded caps). */
function hawserPath(y: number, amp: number) {
  return [
    `M0 ${y}`,
    `C100 ${y + amp} 100 ${y + amp} 200 ${y}`,
    `C300 ${y - amp} 300 ${y - amp} 400 ${y}`,
    `C500 ${y + amp} 500 ${y + amp} 600 ${y}`,
    `C700 ${y - amp} 700 ${y - amp} 800 ${y}`,
  ].join(" ");
}

function RopeTile({
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
  const d = hawserPath(y, amp);
  return (
    <svg
      className="ahoy-wave-tile"
      viewBox="0 0 800 220"
      preserveAspectRatio="none"
      aria-hidden
    >
      <path d={`${d} L800 220 L0 220 Z`} fill={fill} fillOpacity={fillOpacity} />
      <path
        d={d}
        fill="none"
        stroke={stroke}
        strokeOpacity={strokeOpacity}
        strokeWidth="1.75"
        strokeLinecap="butt"
        strokeLinejoin="miter"
        strokeDasharray="none"
      />
    </svg>
  );
}

function RopeTrack({
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
      <RopeTile {...props} />
      <RopeTile {...props} />
    </div>
  );
}

/**
 * Crew backdrop — quiet solid hawsers only.
 */
export function CrewAtmosphere() {
  return (
    <div className="ahoy-crew-overlay" aria-hidden>
      <div className="ahoy-crew-bands">
        <RopeTrack
          className="ahoy-wave-scroll-a"
          y={88}
          amp={18}
          fill="var(--ahoy-kelp)"
          fillOpacity={0.03}
          stroke="var(--ahoy-kelp)"
          strokeOpacity={0.18}
        />
        <RopeTrack
          className="ahoy-wave-scroll-b"
          y={128}
          amp={14}
          fill="var(--ahoy-copper)"
          fillOpacity={0.025}
          stroke="var(--ahoy-copper)"
          strokeOpacity={0.24}
        />
      </div>
      <div className="ahoy-crew-vignette" />
    </div>
  );
}
