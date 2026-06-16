// Coachito wordmark — "coach" upright + "ıto" italic (dotless i) + yellow
// ball as the dot of the i.  Per the brand sheet, this is the only place
// the ball appears in the UI.  Use the Logo monogram for square contexts
// (app icon, favicon, top-bar bullet) and this Wordmark for headers,
// email, and any horizontal masthead.

interface WordmarkProps {
  /** Font size in px for the wordmark itself.  Default 22. */
  size?: number;
  /**
   * Visual variant.  'ink' (default) reads dark on cream / bone, with the
   * italic part in clay.  'cream' inverts for use on clay or ink surfaces.
   */
  variant?: 'ink' | 'cream';
  /** Whether to render the tagline underneath.  Default false. */
  tagline?: boolean;
  className?: string;
}

const CLAY = '#C66B47';
const INK = '#1F1B16';
const CREAM = '#F5EBD9';
const BALL = '#D4E157';
const STONE = '#8A8278';

export function Wordmark({
  size = 22,
  variant = 'ink',
  tagline = false,
  className,
}: WordmarkProps) {
  const onInk = variant === 'cream';
  const coachColor = onInk ? CREAM : INK;
  const italicColor = onInk ? CREAM : CLAY;
  const captionColor = onInk ? CREAM : STONE;

  // Tagline shifts the SVG height + content; baseline math stays in px so
  // the wordmark sits on a clean baseline regardless of size.
  const width = Math.round(size * 6);
  const height = Math.round(size * (tagline ? 2.0 : 1.2));
  const baseline = Math.round(size * 1.05);

  // Ball position: nestled just above the italic "i" — its dot.
  // Calibrated against the "coach" + "ıto" wordmark at the default size.
  const ballX = Math.round(size * 3.62);
  const ballY = Math.round(size * 0.30);
  const ballR = Math.max(2, Math.round(size * 0.085));

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Coachito"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <text
        x={width / 2}
        y={baseline}
        textAnchor="middle"
        fontFamily="Fraunces, Georgia, 'Times New Roman', serif"
        fontWeight="400"
        fontSize={size}
        letterSpacing="-0.01em"
        fill={coachColor}
      >
        <tspan fontStyle="normal">coach</tspan>
        <tspan fontStyle="italic" fill={italicColor}>{'ıto'}</tspan>
      </text>

      {/* Ball as the dot of the dotless i.  Brand-sacred — never reuse this
          colour elsewhere. */}
      <circle cx={ballX} cy={ballY} r={ballR} fill={BALL} />

      {tagline ? (
        <text
          x={width / 2}
          y={Math.round(size * 1.78)}
          textAnchor="middle"
          fontFamily="Fraunces, Georgia, 'Times New Roman', serif"
          fontStyle="italic"
          fontWeight="400"
          fontSize={Math.max(9, Math.round(size * 0.42))}
          letterSpacing="0.18em"
          fill={captionColor}
        >
          tu coach, en tu bolsillo
        </text>
      ) : null}
    </svg>
  );
}
