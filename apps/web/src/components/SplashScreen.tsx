// Coachito splash — the first impression. Editorial language pulled
// directly from the brand sheet: clay full-bleed, Fraunces wordmark with
// italic "ito", the yellow ball drops in (the only place ball is allowed),
// hairline rules frame microcopy, English tagline.
//
// Two variants:
//   - "full"    : BootstrapGate / first paint — full editorial frame on clay.
//   - "compact" : route-level Suspense fallback. Subtle by design: same app
//                 background, small wordmark, no animation. Suspense flips
//                 in and out fast during lazy-chunk loads — a flashy clay
//                 full-bleed there reads like a hard refresh.

import { Logo } from './Logo';
import { Wordmark } from './Wordmark';

interface SplashScreenProps {
  variant?: 'full' | 'compact';
}

export function SplashScreen({ variant = 'full' }: SplashScreenProps) {
  if (variant === 'compact') {
    return (
      <main
        className="flex min-h-screen w-full flex-col items-center justify-center bg-bg-tertiary"
        aria-label="Coachito"
      >
        <Logo size={48} />
      </main>
    );
  }

  return (
    <main
      className="relative flex min-h-screen w-full flex-col items-center justify-center overflow-hidden bg-[var(--accent)]"
      aria-label="Coachito"
    >
      <div className="pointer-events-none absolute inset-x-0 top-[12%] flex justify-center px-6">
        <span
          className="splash-microcopy text-cream/55"
          style={{ fontFamily: 'var(--font-display)', letterSpacing: '0.38em', fontSize: 10 }}
        >
          · EST · MMXXVI · MADE FOR THE COURT ·
        </span>
      </div>
      <div className="pointer-events-none absolute inset-x-[12%] top-[15.5%]">
        <div className="splash-rule-top bg-cream/30 h-px" />
      </div>

      <div className="splash-stage flex flex-col items-center">
        <div className="splash-word">
          <Wordmark size={68} variant="cream" />
        </div>
        <div className="splash-rule-bottom bg-ball/40 mt-7 h-px w-56" />
        <p
          className="splash-tagline text-cream/85 mt-5"
          style={{
            fontFamily: 'var(--font-display)',
            fontStyle: 'italic',
            letterSpacing: '0.22em',
            fontSize: 13,
          }}
        >
          your coach, in your pocket
        </p>
      </div>

      <div className="splash-bar bg-cream/15 absolute bottom-12 h-px w-16 overflow-hidden rounded-full">
        <span className="splash-bar-fill bg-cream/70 block h-full w-0 rounded-full" />
      </div>
    </main>
  );
}
