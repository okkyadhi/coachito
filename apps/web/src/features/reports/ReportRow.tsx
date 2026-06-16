import { format } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { ChevronRight, Eye, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Avatar } from '@/components/Avatar';

import type { Report } from './reports-api';

interface Props {
  report: Report;
  locale: 'en' | 'id';
  onOpen: () => void;
}

export function ReportRow({ report, locale, onOpen }: Props) {
  const { t } = useTranslation();
  const dfLocale = locale === 'id' ? idLocale : enUS;
  const periodLabel = format(new Date(report.periodStart), 'MMM yyyy', {
    locale: dfLocale,
  });
  const generatingPill = report.status === 'generating';
  const generatedLabel = report.generatedAt
    ? t('reports.generatedOn', {
        date: format(new Date(report.generatedAt), 'd MMM yyyy', { locale: dfLocale }),
      })
    : null;

  return (
    <button
      type="button"
      onClick={onOpen}
      disabled={generatingPill}
      className="flex min-h-tap w-full items-center gap-3 px-4 py-3 text-left disabled:cursor-default"
    >
      <Avatar name={report.traineeName} size={40} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-body font-medium text-text-color-primary">
          {report.traineeName}
        </p>
        <p className="truncate text-caption text-text-color-secondary">
          {periodLabel}
          {generatedLabel ? ` · ${generatedLabel}` : ''}
        </p>
      </div>
      {generatingPill ? (
        <span className="inline-flex items-center gap-1 rounded-full bg-bg-tertiary px-2 py-0.5 text-pill text-text-color-secondary">
          <Loader2 size={12} strokeWidth={2} className="animate-spin" aria-hidden />
          {t('reports.generating')}
        </span>
      ) : (
        <>
          {report.viewCount > 0 ? (
            <span className="inline-flex items-center gap-1 text-pill text-text-color-tertiary">
              <Eye size={12} strokeWidth={1.75} aria-hidden />
              {report.viewCount}
            </span>
          ) : null}
          <ChevronRight
            aria-hidden
            size={18}
            strokeWidth={1.75}
            className="shrink-0 text-text-color-tertiary"
          />
        </>
      )}
    </button>
  );
}
