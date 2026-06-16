import { useQuery } from '@tanstack/react-query';
import { Plus, UserPlus } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { GroupedTable } from '@/components/GroupedTable';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { TextInput } from '@/components/TextInput';
import { useAuthStore } from '@/features/auth/auth-store';

import { TraineeListRow } from './TraineeListRow';
import { listTrainees } from './trainees-api';

export function TraineesScreen() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const locale = user?.preferredLocale ?? i18n.language ?? 'en';

  const [q, setQ] = useState('');
  const trimmedQ = q.trim();

  const { data, isPending } = useQuery({
    queryKey: ['trainees', trimmedQ || null],
    queryFn: () => listTrainees(trimmedQ ? { q: trimmedQ } : {}),
  });

  const trainees = data?.trainees ?? [];
  const showEmptyState = !isPending && !trimmedQ && trainees.length === 0;

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-6 pt-5">
      {/* Header */}
      <header className="mb-4 flex items-baseline justify-between">
        <h1 className="text-large-title text-text-color-primary">
          {t('nav.trainees')}
        </h1>
        <button
          type="button"
          onClick={() => navigate('/trainees/new')}
          aria-label={t('trainees.addAction')}
          className="flex size-9 items-center justify-center rounded-full bg-accent text-white"
        >
          <Plus size={20} strokeWidth={2} aria-hidden />
        </button>
      </header>

      {/* Search (hide while empty-state is showing) */}
      {!showEmptyState ? (
        <div className="mb-4">
          <TextInput
            type="search"
            placeholder={t('trainees.searchPlaceholder')}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            autoComplete="off"
          />
        </div>
      ) : null}

      {/* List */}
      {isPending ? (
        <SkeletonList />
      ) : showEmptyState ? (
        <EmptyState onAddAndInvite={() => navigate('/trainees/new?intent=invite')} onAddWithout={() => navigate('/trainees/new?intent=save')} />
      ) : trainees.length === 0 ? (
        <p className="px-1 text-caption text-text-color-secondary">
          {t('trainees.noResults', { q: trimmedQ })}
        </p>
      ) : (
        <GroupedTable>
          {trainees.map((tr) => (
            <TraineeListRow key={tr.id} trainee={tr} locale={locale} />
          ))}
        </GroupedTable>
      )}
    </div>
  );
}

function SkeletonList() {
  return (
    <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
      {[0, 1, 2, 3].map((i) => (
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

interface EmptyStateProps {
  onAddAndInvite: () => void;
  onAddWithout: () => void;
}

function EmptyState({ onAddAndInvite, onAddWithout }: EmptyStateProps) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center gap-3 pt-12 text-center">
      <div className="flex size-[60px] items-center justify-center rounded-full border-[0.5px] border-border-hairline bg-bg-secondary">
        <UserPlus aria-hidden size={26} strokeWidth={1.5} className="text-text-color-tertiary" />
      </div>
      <h2 className="mt-2 text-h3 text-text-color-primary">
        {t('trainees.emptyTitle')}
      </h2>
      <p className="max-w-[260px] text-caption text-text-color-secondary">
        {t('trainees.emptyBody')}
      </p>
      <div className="mt-2 flex w-full max-w-[240px] flex-col gap-2">
        <PrimaryButton onClick={onAddAndInvite}>
          {t('trainees.addAndInvite')}
        </PrimaryButton>
        <SecondaryButton onClick={onAddWithout}>
          {t('trainees.addWithoutInvite')}
        </SecondaryButton>
      </div>
    </div>
  );
}
