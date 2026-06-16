import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from '@/locales/en.json';
import id from '@/locales/id.json';

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    id: { translation: id },
  },
  lng: 'en',
  fallbackLng: 'en',
  // ICU v4 plural-suffix matching (`_one`, `_other`) — used by today.sessionCount, today.minutes.
  compatibilityJSON: 'v4',
  interpolation: { escapeValue: false },
  returnNull: false,
});

export default i18n;
