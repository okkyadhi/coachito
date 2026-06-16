import { useQuery } from '@tanstack/react-query';
import { format, parseISO } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { ChevronRight, FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { fetchMyReports } from '@/features/trainee-reports/reports-api';

const FRESH_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;
const DISMISSED_KEY = 'coachito.reportBanner.dismissedFor';

/**
 * Shows a one-line clay-bg pill on /home when the trainee has a report
 * generated within the last 7 days that they haven't dismissed yet.
 * Dismissal is local-only — when a newer report drops the banner returns.
 */
export function NewReportBanner() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const lang = i18n.language === 'id' ? idLocale : enUS;

  const { data: reports } = useQuery({
    queryKey: ['trainee', 'me', 'reports'],
    queryFn: fetchMyReports,
    staleTime: 60 * 1000,
  });

  const latest = reports?.[0];
  if (!latest) return null;
  const ageMs = Date.now() - new Date(latest.generatedAt).getTime();
  if (ageMs > FRESH_WINDOW_MS || ageMs < 0) return null;

  let dismissedFor: string | null = null;
  try {
    dismissedFor = window.localStorage.getItem(DISMISSED_KEY);
  } catch {
    /* private mode */
  }
  if (dismissedFor === latest.id) return null;

  const label = latest.isSessionReport
    ? format(parseISO(latest.periodStart), 'EEE d MMM', { locale: lang })
    : format(parseISO(latest.periodEnd), 'MMMM yyyy', { locale: lang });

  const onTap = () => {
    try {
      window.localStorage.setItem(DISMISSED_KEY, latest.id);
    } catch {
      /* ignore */
    }
    navigate('/me/reports');
  };

  return (
    <button
      type="button"
      onClick={onTap}
      className="flex w-full items-center gap-2 rounded-lg bg-accent-bg px-3 py-2 text-left"
    >
      <FileText size={14} strokeWidth={2} className="text-accent" aria-hidden />
      <span className="flex-1 text-caption font-medium text-accent">
        {t('trainee.home.newReportBanner', { label })}
      </span>
      <ChevronRight
        size={14}
        strokeWidth={2}
        className="text-accent"
        aria-hidden
      />
    </button>
  );
}
