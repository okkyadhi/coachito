// Editorial frame used on auth + onboarding hero blocks. Mirrors the
// splash language: hairline rule above + small caps microcopy, Logo
// centerpiece, Fraunces title, optional body subtitle, hairline below.
// Anchors all brand-edge pages to the same first-impression vocabulary.

import type { ReactNode } from 'react';

import { Logo } from './Logo';

interface EditorialHeaderProps {
  /** Page title — rendered in Fraunces. */
  title: string;
  /** Body subtitle below the title. */
  subtitle?: ReactNode;
  /** Small-caps microcopy displayed above the rule. Defaults to brand microcopy. */
  microcopy?: string;
  /** Logo tile size. Default 64. */
  logoSize?: number;
  /** Optional override for the logo (e.g., workspace logo on invite). */
  logo?: ReactNode;
  className?: string;
}

export function EditorialHeader({
  title,
  subtitle,
  microcopy = '· EST · MMXXVI · MADE FOR THE COURT ·',
  logoSize = 64,
  logo,
  className,
}: EditorialHeaderProps) {
  return (
    <header
      className={[
        'flex flex-col items-center gap-4 text-center',
        className ?? '',
      ].join(' ')}
    >
      <div className="flex w-full max-w-[280px] items-center gap-3">
        <span className="h-px flex-1 bg-border-hairline" />
        <span
          className="text-text-color-tertiary"
          style={{
            fontFamily: 'var(--font-display)',
            letterSpacing: '0.3em',
            fontSize: 9,
          }}
        >
          {microcopy}
        </span>
        <span className="h-px flex-1 bg-border-hairline" />
      </div>

      {logo ?? <Logo size={logoSize} />}

      <div className="flex flex-col items-center gap-2">
        <h1
          className="font-display text-[28px] font-normal leading-tight text-text-color-primary"
          style={{ letterSpacing: '-0.4px' }}
        >
          {title}
        </h1>
        {subtitle ? (
          <p className="max-w-[32ch] text-body text-text-color-secondary">{subtitle}</p>
        ) : null}
      </div>
    </header>
  );
}
