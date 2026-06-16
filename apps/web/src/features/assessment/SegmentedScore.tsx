interface Props {
  value: number | null; // 1-5, null = not rated
  onChange: (level: number | null) => void;
  ariaLabel: string;
}

// 5-segment selector, 44pt tall.  Tap a segment to select; tap the same
// segment again to toggle off (per docs/04 — score toggle behavior).
export function SegmentedScore({ value, onChange, ariaLabel }: Props) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      className="flex gap-1 rounded-md border-[0.5px] border-border-hairline bg-bg-tertiary p-1"
    >
      {[1, 2, 3, 4, 5].map((n) => {
        const selected = value === n;
        return (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={selected}
            aria-label={`Level ${n}`}
            onClick={() => onChange(selected ? null : n)}
            className={[
              'flex-1 min-h-tap rounded-sm text-[15px] font-medium transition-colors duration-100',
              selected
                ? 'bg-bg-primary text-accent border-[0.5px] border-accent'
                : 'bg-transparent text-text-color-secondary',
            ].join(' ')}
          >
            {n}
          </button>
        );
      })}
    </div>
  );
}
