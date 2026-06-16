import { z } from 'zod';

// E.164: leading +, then 1-9, then 1-14 more digits.  We collapse internal
// whitespace before validating so users can type "+62 812 3456 7890".
const e164 = z
  .string()
  .transform((s) => s.replace(/\s+/g, ''))
  .pipe(
    z
      .string()
      .regex(/^\+[1-9]\d{1,14}$/, 'phone.invalid'),
  );

// Optional parent phone: empty string OK; otherwise must be valid E.164.
const optionalE164 = z
  .string()
  .transform((s) => s.replace(/\s+/g, ''))
  .refine(
    (s) => s === '' || /^\+[1-9]\d{1,14}$/.test(s),
    { message: 'phone.invalid' },
  );

const optionalDate = z
  .string()
  .refine((s) => s === '' || /^\d{4}-\d{2}-\d{2}$/.test(s), {
    message: 'dob.invalid',
  });

export const traineeFormSchema = z.object({
  name: z.string().trim().min(1, 'name.required').max(120),
  phone: e164,
  dateOfBirth: optionalDate,
  parentPhone: optionalE164,
});

export type TraineeFormInput = z.input<typeof traineeFormSchema>;
export type TraineeFormValues = z.output<typeof traineeFormSchema>;
