import type { ButtonHTMLAttributes, ReactNode } from 'react';

interface SecondaryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  leftIcon?: ReactNode;
}

export function SecondaryButton({
  loading,
  leftIcon,
  children,
  disabled,
  className = '',
  type = 'button',
  ...rest
}: SecondaryButtonProps) {
  const isDisabled = disabled || loading;
  return (
    <button
      type={type}
      disabled={isDisabled}
      className={[
        'inline-flex w-full items-center justify-center gap-2',
        'min-h-tap rounded-md px-4 py-2.5',
        'bg-bg-primary text-text-color-primary text-[14px] font-medium',
        'border-[0.5px] border-border-hairline',
        'transition-opacity duration-150',
        'active:opacity-80 disabled:opacity-60 disabled:cursor-not-allowed',
        className,
      ].join(' ')}
      {...rest}
    >
      {loading ? (
        <span
          aria-hidden
          className="inline-block size-4 animate-spin rounded-full border-2 border-text-color-tertiary border-t-text-color-primary"
        />
      ) : (
        leftIcon
      )}
      <span>{children}</span>
    </button>
  );
}
