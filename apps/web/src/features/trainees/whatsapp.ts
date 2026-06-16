// WhatsApp deep-link helpers.  The actual templated copy lives in i18n
// (trainees.inviteMessage in en.json / id.json) so it can be translated.

/**
 * Normalize a phone string into the digits-only form that wa.me expects
 * (no leading "+", no spaces).  Returns null if no digits.
 */
export function normalizeWhatsAppNumber(raw: string): string | null {
  const digits = raw.replace(/\D+/g, '');
  return digits.length > 0 ? digits : null;
}

/**
 * Build a https://wa.me/<number>?text=<url-encoded-message> URL.  The
 * caller is responsible for opening it (window.open + _blank).
 */
export function buildWhatsAppUrl(phoneE164: string, message: string): string | null {
  const digits = normalizeWhatsAppNumber(phoneE164);
  if (!digits) return null;
  return `https://wa.me/${digits}?text=${encodeURIComponent(message)}`;
}

/**
 * First word of a name — used as the {trainee_first_name} placeholder so
 * the invite message reads "Hi Andi" instead of "Hi Andi Pratama".
 */
export function firstName(fullName: string): string {
  return fullName.trim().split(/\s+/)[0] ?? fullName.trim();
}
