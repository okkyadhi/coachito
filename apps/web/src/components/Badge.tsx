// Shared badge / pill. Consolidates 5+ ad-hoc implementations across the
// app (workspace badge, sport badge, level pill, status pill, role pill).
// Sentence case per brand voice — never UPPERCASE the label text.

import type { ReactNode } from 'react';

type Variant = 'subtle' | 'accent' | 'success' | 'warning' | 'danger' | 'outline';
type Size = 'sm' | 'md';

interface BadgeProps {
  children: ReactNode;
  variant?: Variant;
  size?: Size;
  className?: string;
}

const VARIANT_CLASS: Record<Variant, string> = {
  subtle: 'bg-bg-secondary text-text-color-secondary',
  accent: 'bg-accent-bg text-accent',
  success: 'bg-success-bg text-success-text',
  warning: 'bg-warning-bg text-warning-text',
  danger: 'bg-danger-bg text-danger-text',
  outline: 'border-[0.5px] border-border-hairline bg-transparent text-text-color-secondary',
};

const SIZE_CLASS: Record<Size, string> = {
  sm: 'px-2 py-0.5 text-[10px]',
  md: 'px-2.5 py-1 text-pill',
};

export function Badge({ children, variant = 'subtle', size = 'sm', className }: BadgeProps) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1 rounded-full leading-none',
        VARIANT_CLASS[variant],
        SIZE_CLASS[size],
        className ?? '',
      ].join(' ')}
    >
      {children}
    </span>
  );
}
