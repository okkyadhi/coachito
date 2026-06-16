import { forwardRef, useId } from 'react';
import type { InputHTMLAttributes } from 'react';

interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string | undefined;
  error?: string | undefined;
}

export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(function TextInput(
  { label, error, id, className = '', ...rest },
  ref,
) {
  const autoId = useId();
  const inputId = id ?? autoId;
  return (
    <label htmlFor={inputId} className="flex flex-col gap-1.5">
      {label ? (
        <span className="text-section text-text-color-secondary">{label}</span>
      ) : null}
      <input
        ref={ref}
        id={inputId}
        className={[
          'min-h-tap rounded-sm px-3 py-2',
          'bg-bg-primary text-text-color-primary text-body',
          'border-[0.5px] border-border-hairline',
          'placeholder:text-text-color-tertiary',
          'focus:outline-none focus:border-accent',
          'transition-colors duration-100',
          error ? 'border-danger-text' : '',
          className,
        ].join(' ')}
        aria-invalid={error ? true : undefined}
        {...rest}
      />
      {error ? (
        <span role="alert" className="text-footnote text-danger-text">
          {error}
        </span>
      ) : null}
    </label>
  );
});
