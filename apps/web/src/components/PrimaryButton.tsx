import type { ButtonHTMLAttributes, ReactNode } from 'react';

interface PrimaryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  leftIcon?: ReactNode;
}

export function PrimaryButton({
  loading,
  leftIcon,
  children,
  disabled,
  className = '',
  type = 'button',
  ...rest
}: PrimaryButtonProps) {
  const isDisabled = disabled || loading;
  return (
    <button
      type={type}
      disabled={isDisabled}
      className={[
        'inline-flex w-full items-center justify-center gap-2',
        'min-h-tap rounded-md px-4 py-2.5',
        'bg-accent text-white text-[14px] font-medium',
        'transition-opacity duration-150',
        'active:opacity-80 disabled:opacity-60 disabled:cursor-not-allowed',
        className,
      ].join(' ')}
      {...rest}
    >
      {loading ? (
        <span
          aria-hidden
          className="inline-block size-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
        />
      ) : (
        leftIcon
      )}
      <span>{children}</span>
    </button>
  );
}
