import { useTranslation } from 'react-i18next';

import type { CategoryAverage, SkillCategory } from './profile-types';

interface Props {
  averages: CategoryAverage[];
}

const SIZE = 240;
const CENTER = SIZE / 2;
const MAX_RADIUS = SIZE / 2 - 28;

// Categories at cardinal points, starting top going clockwise:
// Technical ↑ · Tactical → · Physical ↓ · Mental ←
const AXES: { category: SkillCategory; angle: number; anchor: 'middle' | 'start' | 'end' }[] = [
  { category: 'technical', angle: -Math.PI / 2, anchor: 'middle' },
  { category: 'tactical',  angle: 0,            anchor: 'start' },
  { category: 'physical',  angle: Math.PI / 2,  anchor: 'middle' },
  { category: 'mental',    angle: Math.PI,      anchor: 'end' },
];

const LEVEL_RINGS = [1, 2, 3, 4, 5];

function pointOnAxis(angle: number, fractionOfMax: number) {
  const r = fractionOfMax * MAX_RADIUS;
  return {
    x: CENTER + r * Math.cos(angle),
    y: CENTER + r * Math.sin(angle),
  };
}

export function SkillRadar({ averages }: Props) {
  const { t } = useTranslation();

  // Diamond rings (squares rotated 45°) at each integer level 1-5.
  const ringPolygons = LEVEL_RINGS.map((level) => {
    const f = level / 5;
    const pts = AXES.map((a) => pointOnAxis(a.angle, f));
    return pts.map((p) => `${p.x},${p.y}`).join(' ');
  });

  // Data polygon
  const dataPoints = AXES.map((a) => {
    const avg = averages.find((x) => x.category === a.category)?.average ?? 0;
    return pointOnAxis(a.angle, Math.max(avg, 0.05) / 5);
  });
  const dataPolygon = dataPoints.map((p) => `${p.x},${p.y}`).join(' ');

  return (
    <section className="flex flex-col gap-3">
      <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('profile.radar.title')}
      </h2>

      <div className="flex flex-col items-center gap-4 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
        <svg
          width={SIZE + 80}
          height={SIZE + 24}
          viewBox={`-40 -12 ${SIZE + 80} ${SIZE + 24}`}
          role="img"
          aria-label={t('profile.radar.title')}
          style={{ overflow: 'visible', maxWidth: '100%' }}
        >
          {/* Concentric diamond rings */}
          {ringPolygons.map((pts, i) => (
            <polygon
              key={i}
              points={pts}
              fill="none"
              stroke="var(--color-border-tertiary)"
              strokeWidth="0.5"
            />
          ))}

          {/* Axis lines */}
          {AXES.map((a, i) => {
            const end = pointOnAxis(a.angle, 1);
            return (
              <line
                key={i}
                x1={CENTER}
                y1={CENTER}
                x2={end.x}
                y2={end.y}
                stroke="var(--color-border-tertiary)"
                strokeWidth="0.5"
              />
            );
          })}

          {/* Data polygon */}
          <polygon
            points={dataPolygon}
            fill="var(--accent)"
            fillOpacity="0.18"
            stroke="var(--accent)"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />

          {/* Vertex dots */}
          {dataPoints.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r="2.5" fill="var(--accent)" />
          ))}

          {/* Axis labels */}
          {AXES.map((a, i) => {
            const labelPoint = pointOnAxis(a.angle, 1.13);
            return (
              <text
                key={i}
                x={labelPoint.x}
                y={labelPoint.y}
                textAnchor={a.anchor}
                dominantBaseline="middle"
                style={{
                  fontFamily:
                    "-apple-system,BlinkMacSystemFont,'SF Pro Text',system-ui,sans-serif",
                  fontSize: '11px',
                  fill: 'var(--color-text-secondary)',
                  letterSpacing: '0.04em',
                }}
              >
                {t(`profile.categories.${a.category}`).toUpperCase()}
              </text>
            );
          })}
        </svg>

        {/* Legend with 1-decimal averages */}
        <div className="grid w-full grid-cols-2 gap-x-4 gap-y-2 text-caption">
          {averages.map((a) => (
            <div key={a.category} className="flex items-baseline justify-between">
              <span className="text-text-color-secondary">{t(`profile.categories.${a.category}`)}</span>
              <span className="text-text-color-primary">
                {a.skillsRated === 0 ? '—' : a.average.toFixed(1)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
