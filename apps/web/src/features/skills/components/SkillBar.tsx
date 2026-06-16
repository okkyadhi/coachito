interface Props {
  level: number | null;
  max?: number;
  requiredLevel?: number;
  accent?: string;
}

// 5-cell mini bar. Filled cells show the current level; an outlined cell at
// `requiredLevel` (when greater than current) draws a one-pixel accent ring
// to hint where the next tier needs them.
export function SkillBar({ level, max = 5, requiredLevel, accent = 'var(--accent)' }: Props) {
  const filled = level ?? 0;
  return (
    <div className="flex items-center gap-[3px]" aria-hidden>
      {Array.from({ length: max }, (_, i) => i + 1).map((cell) => {
        const isFilled = cell <= filled;
        const isRequiredBeyond =
          requiredLevel != null && cell <= requiredLevel && cell > filled;
        return (
          <span
            key={cell}
            className="block h-2 w-3 rounded-sm"
            style={{
              backgroundColor: isFilled
                ? accent
                : isRequiredBeyond
                  ? 'transparent'
                  : 'var(--color-bg-tertiary, #efeff4)',
              boxShadow: isRequiredBeyond ? `inset 0 0 0 1px ${accent}` : undefined,
            }}
          />
        );
      })}
    </div>
  );
}
