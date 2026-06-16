import { format, parseISO } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { ExternalLink, FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import type { TraineeReport } from './reports-api';

interface Props {
  report: TraineeReport;
  borderTop?: boolean;
}

export function ReportRow({ report, borderTop }: Props) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'id' ? idLocale : enUS;

  // Monthly reports → "April 2026" (use end-of-period).
  // Per-session reports → "Tue 14 May" (use start = end = session date).
  const periodLabel = report.isSessionReport
    ? format(parseISO(report.periodStart), 'EEE d MMM', { locale: lang })
    : format(parseISO(report.periodEnd), 'MMMM yyyy', { locale: lang });
  const tag = report.isSessionReport
    ? t('trainee.reports.perSessionTag')
    : t('trainee.reports.monthlyTag');

  return (
    <div
      className={[
        'flex items-center gap-3 p-4',
        borderTop ? 'border-t-[0.5px] border-border-hairline' : '',
      ].join(' ')}
    >
      <span
        className="flex size-9 shrink-0 items-center justify-center rounded-full bg-accent-bg text-accent"
        aria-hidden
      >
        <FileText size={18} strokeWidth={1.75} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-body text-text-color-primary">
          {periodLabel}
        </p>
        <p className="text-footnote text-text-color-secondary">
          {t('trainee.reports.byCoach', { name: report.coachDisplayName })} · {tag}
        </p>
        {report.viewCount > 0 ? (
          <p className="text-footnote text-text-color-tertiary">
            {t('trainee.reports.viewCountLabel', { count: report.viewCount })}
          </p>
        ) : null}
      </div>
      <a
        href={report.pdfUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex min-h-tap items-center gap-1 rounded-md bg-accent px-3 py-2 text-caption font-medium text-white"
      >
        {t('trainee.reports.viewCta')}
        <ExternalLink size={14} strokeWidth={1.75} aria-hidden />
      </a>
    </div>
  );
}
