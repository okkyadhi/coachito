// iOS-style toggle switch.  Two states, no intermediate.  Tap target stays
// 44×44 even though the visual is smaller (the parent row provides padding).
//
// Layout: flex container centers the knob vertically, so we don't depend on
// fragile absolute positioning that can render unevenly across browsers.
// Track is 28×48, knob is 24×24, gap is 2px on each side.

interface Props {
  checked: boolean;
  onChange: (next: boolean) => void;
  ariaLabel?: string | undefined;
  disabled?: boolean | undefined;
}

export function Switch({ checked, onChange, ariaLabel, disabled }: Props) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={[
        'relative inline-flex h-7 w-12 shrink-0 items-center rounded-full p-0.5 transition-colors duration-150',
        checked ? 'bg-accent' : 'bg-bg-tertiary',
        disabled ? 'opacity-50' : '',
      ].join(' ')}
    >
      <span
        aria-hidden
        className={[
          'inline-block size-6 rounded-full bg-white shadow-sm transition-transform duration-150 ease-out',
          checked ? 'translate-x-5' : 'translate-x-0',
        ].join(' ')}
      />
    </button>
  );
}
