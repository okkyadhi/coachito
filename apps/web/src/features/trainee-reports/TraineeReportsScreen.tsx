import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { ReportRow } from './ReportRow';
import { fetchMyReports } from './reports-api';

export function TraineeReportsScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const { data, isPending } = useQuery({
    queryKey: ['trainee', 'me', 'reports'],
    queryFn: fetchMyReports,
    staleTime: 30 * 1000,
  });

  return (
    <main className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 pb-8 pt-3">
      <header className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => navigate('/me')}
          aria-label={t('common.back')}
          className="-ml-2 flex size-9 items-center justify-center rounded-full text-text-color-secondary"
        >
          <ChevronLeft size={20} strokeWidth={1.75} aria-hidden />
        </button>
        <div>
          <h1 className="text-h2 text-text-color-primary">
            {t('trainee.reports.title')}
          </h1>
          <p className="text-caption text-text-color-secondary">
            {t('trainee.reports.subtitle')}
          </p>
        </div>
      </header>

      {isPending ? (
        <Skeleton />
      ) : (data?.length ?? 0) === 0 ? (
        <EmptyState />
      ) : (
        <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
          {data!.map((r, idx) => (
            <ReportRow key={r.id} report={r} borderTop={idx > 0} />
          ))}
        </div>
      )}
    </main>
  );
}

function EmptyState() {
  const { t } = useTranslation();
  return (
    <section className="flex flex-col items-center gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-6 text-center">
      <span className="flex size-12 items-center justify-center rounded-full border-[0.5px] border-border-hairline bg-bg-secondary text-text-color-tertiary">
        <FileText size={20} strokeWidth={1.5} aria-hidden />
      </span>
      <h2 className="text-h3 text-text-color-primary">
        {t('trainee.reports.emptyTitle')}
      </h2>
      <p className="max-w-[260px] text-caption text-text-color-secondary">
        {t('trainee.reports.emptyBody')}
      </p>
    </section>
  );
}

function Skeleton() {
  return (
    <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
      {[0, 1].map((i) => (
        <div
          key={i}
          className={[
            'h-20',
            i > 0 ? 'border-t-[0.5px] border-border-hairline' : '',
          ].join(' ')}
        />
      ))}
    </div>
  );
}
