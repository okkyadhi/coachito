// Shared empty state — consolidates the pattern duplicated across Coach
// Today, Trainees, Trainee Home (FirstRunHome), Sessions. Icon sits in a
// soft cream circle (60px), Fraunces feel optional via the title element.

import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  body?: ReactNode;
  primaryAction?: ReactNode;
  secondaryAction?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  body,
  primaryAction,
  secondaryAction,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={[
        'flex flex-col items-center gap-3 px-6 py-10 text-center',
        className ?? '',
      ].join(' ')}
    >
      <span
        aria-hidden
        className="flex size-[60px] items-center justify-center rounded-full bg-bg-secondary"
      >
        <Icon size={24} strokeWidth={1.75} className="text-text-color-secondary" aria-hidden />
      </span>
      <h2
        className="font-display text-[20px] leading-tight text-text-color-primary"
        style={{ fontWeight: 400 }}
      >
        {title}
      </h2>
      {body ? (
        <p className="max-w-[28ch] text-caption text-text-color-secondary">{body}</p>
      ) : null}
      {primaryAction || secondaryAction ? (
        <div className="mt-2 flex flex-col items-center gap-2">
          {primaryAction}
          {secondaryAction}
        </div>
      ) : null}
    </div>
  );
}
