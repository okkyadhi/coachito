// Locale-aware date helpers.  Wraps date-fns so the rest of the app doesn't
// need to import locales directly.
import { format, formatDistanceToNow } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';

type LocaleCode = 'en' | 'id' | string;

function dfLocale(locale: LocaleCode) {
  return locale === 'id' ? idLocale : enUS;
}

/** "Sunday, 10 May 2026" (en) / "Minggu, 10 Mei 2026" (id) */
export function formatFullDate(date: Date, locale: LocaleCode = 'en'): string {
  return format(date, 'EEEE, d MMMM yyyy', { locale: dfLocale(locale) });
}

/** "8:00" (en) / "08.00" (id — Indonesian uses period as the hh:mm separator) */
export function formatTime(date: Date, locale: LocaleCode = 'en'): string {
  return format(date, locale === 'id' ? 'HH.mm' : 'H:mm', { locale: dfLocale(locale) });
}

/** "3 days ago" / "3 hari yang lalu" — date-fns adds the suffix per locale. */
export function formatRelative(date: Date, locale: LocaleCode = 'en'): string {
  return formatDistanceToNow(date, { addSuffix: true, locale: dfLocale(locale) });
}
