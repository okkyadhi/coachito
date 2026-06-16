// iOS-style single-select segmented control with optional count badges.
// No library — Tailwind only.

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
  /** Optional count to render as a small pill next to the label. */
  count?: number | undefined;
  /** When the count > 0 and this is true, the pill uses accent styling
   *  (used to highlight "To assess" with attention). */
  emphasize?: boolean | undefined;
}

interface Props<T extends string> {
  value: T;
  onChange: (v: T) => void;
  options: SegmentOption<T>[];
  ariaLabel?: string;
}

export function SegmentedControl<T extends string>({
  value,
  onChange,
  options,
  ariaLabel,
}: Props<T>) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className="flex w-full overflow-x-auto rounded-full bg-bg-secondary p-0.5"
    >
      {options.map((opt) => {
        const selected = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(opt.value)}
            className={[
              'inline-flex shrink-0 items-center gap-1 rounded-full px-3 py-1.5 text-caption transition-colors',
              selected
                ? 'bg-bg-primary text-text-color-primary shadow-[0_0_0_0.5px_rgba(0,0,0,0.05)]'
                : 'text-text-color-secondary',
            ].join(' ')}
          >
            <span>{opt.label}</span>
            {opt.count !== undefined && opt.count > 0 ? (
              <span
                className={
                  opt.emphasize
                    ? 'rounded-full bg-accent px-1.5 text-pill text-white'
                    : 'rounded-full bg-bg-tertiary px-1.5 text-pill text-text-color-secondary'
                }
              >
                {opt.count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
