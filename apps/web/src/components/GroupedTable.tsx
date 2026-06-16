import type { ReactNode } from 'react';

interface GroupedTableProps {
  header?: string;
  children: ReactNode;
  className?: string;
}

// iOS "grouped table" pattern: section header (small gray, outside) + white card
// with hairline-separated rows.  Pass row elements directly as children; the
// component wraps them in a white surface and inserts hairline dividers between them.
export function GroupedTable({ header, children, className = '' }: GroupedTableProps) {
  return (
    <div className={className}>
      {header ? (
        <p className="mb-1.5 px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {header}
        </p>
      ) : null}
      <div
        className={[
          'rounded-xl overflow-hidden',
          'bg-bg-primary',
          'border-[0.5px] border-border-hairline',
          // Hairline between rows using divide
          '[&>*+*]:border-t [&>*+*]:border-[0.5px] [&>*+*]:border-[color:var(--color-border-tertiary)]',
        ].join(' ')}
      >
        {children}
      </div>
    </div>
  );
}
