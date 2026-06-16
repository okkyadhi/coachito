import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText, Plus } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { GroupedTable } from '@/components/GroupedTable';
import { SecondaryButton } from '@/components/SecondaryButton';
import { useAuthStore } from '@/features/auth/auth-store';

import { GenerateReportSheet } from './GenerateReportSheet';
import { ReportRow } from './ReportRow';
import {
  anyPending,
  generateReport,
  incrementViewCount,
  listReports,
} from './reports-api';

export function ReportsScreen() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const locale = (user?.preferredLocale ?? i18n.language) === 'id' ? 'id' : 'en';

  const [sheetOpen, setSheetOpen] = useState(false);

  const { data, isPending } = useQuery({
    queryKey: ['reports'],
    queryFn: listReports,
    staleTime: 5_000,
    // Poll while any row is still generating; otherwise leave it alone.
    refetchInterval: (q) => (anyPending(q.state.data ?? []) ? 2_500 : false),
  });
  const reports = data ?? [];
  const showEmptyState = !isPending && reports.length === 0;

  const handleOpenReport = (id: string, pdfUrl: string | null) => {
    if (!pdfUrl) return;
    void incrementViewCount(id).then(() =>
      queryClient.invalidateQueries({ queryKey: ['reports'] }),
    );
    window.open(pdfUrl, '_blank', 'noopener');
  };

  const handleGenerate = async (args: {
    traineeId: string;
    traineeName: string;
    mode: 'monthly' | 'session';
    sessionId?: string;
    periodStart?: string;
    periodEnd?: string;
  }) => {
    await generateReport(
      args.mode === 'session' && args.sessionId
        ? { traineeId: args.traineeId, sessionId: args.sessionId }
        : {
            traineeId: args.traineeId,
            periodStart: args.periodStart ?? '',
            periodEnd: args.periodEnd ?? '',
          },
    );
    setSheetOpen(false);
    // Refetch immediately so the new pending row shows up; the
    // `refetchInterval` on the query then polls until it flips to completed.
    void queryClient.invalidateQueries({ queryKey: ['reports'] });
  };

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-6 pt-5">
      <header className="mb-4 flex items-baseline justify-between">
        <h1 className="text-large-title text-text-color-primary">
          {t('nav.reports')}
        </h1>
        {!showEmptyState ? (
          <button
            type="button"
            onClick={() => setSheetOpen(true)}
            aria-label={t('reports.create')}
            className="flex size-9 items-center justify-center rounded-full bg-accent text-white"
          >
            <Plus size={20} strokeWidth={2} aria-hidden />
          </button>
        ) : null}
      </header>

      {isPending ? (
        <SkeletonList />
      ) : showEmptyState ? (
        <EmptyState onCreate={() => setSheetOpen(true)} />
      ) : (
        <GroupedTable>
          {reports.map((r) => (
            <ReportRow
              key={r.id}
              report={r}
              locale={locale}
              onOpen={() => handleOpenReport(r.id, r.pdfUrl)}
            />
          ))}
        </GroupedTable>
      )}

      <GenerateReportSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        onConfirm={handleGenerate}
      />
    </div>
  );
}

function SkeletonList() {
  return (
    <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className={[
            'flex items-center gap-3 p-3',
            i > 0 ? 'border-t-[0.5px] border-border-hairline' : '',
          ].join(' ')}
        >
          <div className="size-10 rounded-full bg-bg-tertiary" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3 w-2/5 rounded bg-bg-tertiary" />
            <div className="h-2.5 w-3/5 rounded bg-bg-tertiary" />
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center gap-3 pt-12 text-center">
      <div className="flex size-[60px] items-center justify-center rounded-full border-[0.5px] border-border-hairline bg-bg-secondary">
        <FileText
          aria-hidden
          size={26}
          strokeWidth={1.5}
          className="text-text-color-tertiary"
        />
      </div>
      <h2 className="mt-2 text-h3 text-text-color-primary">
        {t('reports.emptyTitle')}
      </h2>
      <p className="max-w-[280px] text-caption text-text-color-secondary">
        {t('reports.emptyBody')}
      </p>
      <div className="mt-2 w-full max-w-[240px]">
        <SecondaryButton onClick={onCreate}>{t('reports.create')}</SecondaryButton>
      </div>
    </div>
  );
}
