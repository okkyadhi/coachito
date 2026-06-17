import { useQuery } from '@tanstack/react-query';
import { Plus, UserPlus } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { EmptyState as SharedEmptyState } from '@/components/EmptyState';
import { GroupedTable } from '@/components/GroupedTable';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SkeletonList } from '@/components/Skeleton';
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
          className="flex size-9 items-center justify-center rounded-full bg-accent text-white transition-transform hover:scale-105 active:scale-95"
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
        <SkeletonList rows={4} />
      ) : showEmptyState ? (
        <TraineesEmpty
          onAddAndInvite={() => navigate('/trainees/new?intent=invite')}
          onAddWithout={() => navigate('/trainees/new?intent=save')}
        />
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

interface TraineesEmptyProps {
  onAddAndInvite: () => void;
  onAddWithout: () => void;
}

function TraineesEmpty({ onAddAndInvite, onAddWithout }: TraineesEmptyProps) {
  const { t } = useTranslation();
  return (
    <SharedEmptyState
      icon={UserPlus}
      title={t('trainees.emptyTitle')}
      body={t('trainees.emptyBody')}
      className="pt-10"
      primaryAction={
        <PrimaryButton onClick={onAddAndInvite}>
          {t('trainees.addAndInvite')}
        </PrimaryButton>
      }
      secondaryAction={
        <button
          type="button"
          onClick={onAddWithout}
          className="min-h-tap text-caption text-accent underline-offset-2 hover:underline"
        >
          {t('trainees.addWithoutInvite')}
        </button>
      }
    />
  );
}
