import { useId } from 'react';

import type { RadarAxis } from '../skills-types';

interface Props {
  axes: RadarAxis[];
  max?: number;
  size?: number;
  unassessedStyle?: 'gray-dotted' | 'hidden';
  /** Per-axis tap handler; receives axis code. Used by overview to navigate. */
  onAxisTap?: (code: string) => void;
  /** Polygon fill / stroke + default vertex dot color. */
  accent?: string;
  /** Optional per-axis vertex-dot color override (keyed by axis code). */
  vertexAccents?: Record<string, string>;
  /** Force compact (short-label) rendering regardless of axis count. */
  compactLabels?: boolean;
  ariaLabel?: string;
}

// Adaptive layout — labels and ring padding scale with axis count so the
// 13-axis breakdown radar doesn't collide.  See docs/17 § "Adaptive rules"
// for the table this implements.
interface LayoutTuning {
  labelRadius: number;
  fontSize: number;
  rotate: boolean;
  ringInset: number;
  vertexDotR: number;
}

function tuningFor(n: number): LayoutTuning {
  if (n <= 4) return { labelRadius: 1.18, fontSize: 11, rotate: false, ringInset: 36, vertexDotR: 2.5 };
  if (n <= 6) return { labelRadius: 1.22, fontSize: 11, rotate: false, ringInset: 44, vertexDotR: 2.5 };
  if (n <= 10) return { labelRadius: 1.30, fontSize: 10, rotate: true,  ringInset: 52, vertexDotR: 2.5 };
  return       { labelRadius: 1.34, fontSize: 10, rotate: true,  ringInset: 60, vertexDotR: 2.0 };
}

export function SkillRadar({
  axes,
  max = 5,
  size = 280,
  unassessedStyle = 'gray-dotted',
  onAxisTap,
  accent = 'var(--accent)',
  vertexAccents,
  compactLabels = false,
  ariaLabel,
}: Props) {
  const titleId = useId();
  const n = axes.length;
  if (n === 0) return null;

  const tuning = tuningFor(n);
  const center = size / 2;
  const maxRadius = size / 2 - tuning.ringInset;
  const useShort = compactLabels || n >= 7;

  const pt = (i: number, fraction: number) => {
    const angle = -Math.PI / 2 + (i / n) * 2 * Math.PI;
    return {
      x: center + Math.cos(angle) * fraction * maxRadius,
      y: center + Math.sin(angle) * fraction * maxRadius,
      angle,
    };
  };

  const rings = Array.from({ length: max }, (_, i) => i + 1).map((level) => {
    const f = level / max;
    return axes.map((_, i) => {
      const p = pt(i, f);
      return `${p.x.toFixed(1)},${p.y.toFixed(1)}`;
    }).join(' ');
  });

  const assessedPoints: { x: number; y: number; i: number; code: string }[] = [];
  axes.forEach((a, i) => {
    if (a.score == null) return;
    const f = Math.max(a.score / max, 0.04);
    const p = pt(i, f);
    assessedPoints.push({ x: p.x, y: p.y, i, code: a.code });
  });
  const polygon = assessedPoints
    .map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`)
    .join(' ');

  const labels = axes.map((axis, i) => {
    const p = pt(i, tuning.labelRadius);
    const deg = (p.angle * 180) / Math.PI;
    // Tangential rotation: text reads outward from centre, flipped on the
    // bottom half so it never reads upside down.
    let rotation = 0;
    if (tuning.rotate) {
      const upright = deg > 90 || deg < -90;
      rotation = upright ? deg + 180 : deg;
    }
    let anchor: 'middle' | 'start' | 'end' = 'middle';
    if (!tuning.rotate) {
      const cos = Math.cos(p.angle);
      if (cos > 0.3) anchor = 'start';
      else if (cos < -0.3) anchor = 'end';
    }
    return { axis, x: p.x, y: p.y, anchor, rotation, i };
  });

  return (
    <svg
      role="img"
      aria-labelledby={ariaLabel ? titleId : undefined}
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      style={{ overflow: 'visible', maxWidth: '100%' }}
    >
      {ariaLabel ? <title id={titleId}>{ariaLabel}</title> : null}

      {/* Concentric ring polygons */}
      {rings.map((pts, i) => (
        <polygon
          key={i}
          points={pts}
          fill="none"
          stroke="var(--color-border-tertiary, rgba(0,0,0,0.1))"
          strokeWidth="0.5"
        />
      ))}

      {/* Spokes */}
      {axes.map((a, i) => {
        const end = pt(i, 1);
        const isAssessed = a.score != null;
        if (!isAssessed && unassessedStyle === 'hidden') return null;
        return (
          <line
            key={`spoke-${i}`}
            x1={center}
            y1={center}
            x2={end.x}
            y2={end.y}
            stroke="var(--color-border-tertiary, rgba(0,0,0,0.16))"
            strokeWidth="0.5"
            strokeDasharray={isAssessed ? undefined : '2 3'}
          />
        );
      })}

      {/* Polygon */}
      {assessedPoints.length >= 3 ? (
        <polygon
          points={polygon}
          fill={accent}
          fillOpacity={0.18}
          stroke={accent}
          strokeWidth={1.5}
          strokeLinejoin="round"
        />
      ) : assessedPoints.length === 2 ? (
        <line
          x1={assessedPoints[0]!.x}
          y1={assessedPoints[0]!.y}
          x2={assessedPoints[1]!.x}
          y2={assessedPoints[1]!.y}
          stroke={accent}
          strokeWidth={1.5}
        />
      ) : null}

      {/* Vertex dots for assessed axes */}
      {assessedPoints.map((p) => (
        <circle
          key={`v-${p.i}`}
          cx={p.x}
          cy={p.y}
          r={tuning.vertexDotR}
          fill={vertexAccents?.[p.code] ?? accent}
        />
      ))}

      {/* Labels + invisible hit targets */}
      {labels.map(({ axis, x, y, anchor, rotation, i }) => {
        const hitW = 56;
        const hitH = 24;
        const interactive = !!onAxisTap;
        const text = (useShort && axis.shortLabel) ? axis.shortLabel : axis.label;
        const textTransform = rotation
          ? `rotate(${rotation.toFixed(1)} ${x.toFixed(1)} ${y.toFixed(1)})`
          : undefined;
        return (
          <g key={`l-${i}`}>
            <text
              x={x}
              y={y}
              textAnchor={anchor}
              dominantBaseline="middle"
              transform={textTransform}
              style={{
                fontFamily:
                  "-apple-system,BlinkMacSystemFont,'SF Pro Text',system-ui,sans-serif",
                fontSize: `${tuning.fontSize}px`,
                fontWeight: 500,
                fill: 'var(--color-text-secondary)',
                letterSpacing: '0.02em',
                pointerEvents: 'none',
              }}
            >
              {text}
            </text>
            {interactive ? (
              <rect
                x={x - hitW / 2}
                y={y - hitH / 2}
                width={hitW}
                height={hitH}
                fill="transparent"
                style={{ cursor: 'pointer' }}
                onClick={() => onAxisTap?.(axis.code)}
              >
                <title>{axis.label}</title>
              </rect>
            ) : null}
          </g>
        );
      })}
    </svg>
  );
}
