// Coachito monogram (app-icon scale): rounded clay tile, italic Fraunces
// "c", and the yellow ball nestled in the curve where the dot of an "i"
// would have been.  Per the brand sheet's "ball is sacred" rule, the ball
// appears here in the logo and nowhere else in the UI.
//
// Construction follows docs/coachito_brand_sheet.html (variations panel).

interface LogoProps {
  size?: number;
  className?: string;
  /**
   * Override the tile background.  Defaults to clay (#C66B47).  Pass
   * 'transparent' to render the monogram letter+ball against the
   * surrounding surface (e.g., on a coloured header).
   */
  background?: string;
}

const CLAY = '#C66B47';
const CREAM = '#F5EBD9';
const BALL = '#D4E157';
const BALL_DEEP = '#9BAA38';

export function Logo({ size = 72, className, background = CLAY }: LogoProps) {
  const radius = Math.round(size * 0.22);
  const showTile = background !== 'transparent';
  // The "c" colour flips so the mark stays legible on either surface.
  const letterColor = showTile ? CREAM : '#1F1B16';
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 72 72"
      fill="none"
      role="img"
      aria-label="Coachito"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      {showTile ? (
        <rect width="72" height="72" rx={radius} fill={background} />
      ) : null}

      {/* italic lowercase "c" — Fraunces feel, served from a system serif
          fallback so the icon renders before Google Fonts arrives.
          Coords place the combined c+ball group optically centered in the
          72×72 tile (measured bbox center == 36,36). */}
      <text
        x="19.4"
        y="49.4"
        fontFamily="Fraunces, Georgia, 'Times New Roman', serif"
        fontStyle="italic"
        fontWeight="400"
        fontSize="58"
        fill={letterColor}
      >
        c
      </text>

      {/* The ball: this is the dot of the "i" that lives next to the "c"
          in the full wordmark.  Sits where the dot would be — tight to
          the top-right of the letter. */}
      <circle cx="44.4" cy="37.4" r="6.5" fill={BALL} />
      {/* subtle seam line, the only piece of decoration on the ball */}
      <path
        d="M 38.9 37.4 Q 44.4 33.4 49.9 37.4"
        fill="none"
        stroke={BALL_DEEP}
        strokeWidth="0.4"
        opacity="0.7"
      />
    </svg>
  );
}
