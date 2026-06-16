import { forwardRef, useId } from 'react';
import type { InputHTMLAttributes } from 'react';

interface PhoneInputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'inputMode'> {
  label?: string | undefined;
  error?: string | undefined;
}

// E.164 phone input.  The full E.164 string (including `+` and country code)
// lives in the value; the visual format is whatever the user typed.  The
// AddTraineeScreen pre-fills "+62 " for ID-locale users and the user types the
// rest.  Validation is the form's job — this component is just a tel-typed
// TextInput with mobile-friendly defaults.
export const PhoneInput = forwardRef<HTMLInputElement, PhoneInputProps>(function PhoneInput(
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
        type="tel"
        inputMode="tel"
        autoComplete="tel"
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
