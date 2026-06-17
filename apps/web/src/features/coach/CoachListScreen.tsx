import { useQuery } from '@tanstack/react-query';
import { MapPin, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import type { CoachListWorkspace } from './coach-types';

import { CoachListRow } from './components/CoachListRow';
import { fetchMyCoaches } from './coach-api';

export function CoachListScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const { data, isPending } = useQuery({
    queryKey: ['trainee', 'me', 'coaches'],
    queryFn: fetchMyCoaches,
    staleTime: 30 * 1000,
  });

  if (isPending) return <Skeleton />;

  const workspace = data?.workspace;
  const entries = data?.coaches ?? [];

  // Tint the page with the workspace brand color so the trainee's "where do I
  // train" page reads as theirs, not generic.
  const rootStyle: React.CSSProperties = workspace?.brandColor
    ? ({ ['--accent' as never]: workspace.brandColor } as React.CSSProperties)
    : {};

  return (
    <main
      className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 pb-8 pt-4"
      style={rootStyle}
    >
      <header className="px-1">
        <h1 className="text-large-title text-text-color-primary">
          {t('coach.list.title')}
        </h1>
        <p className="mt-1 text-caption text-text-color-secondary">
          {t('coach.list.subtitle')}
        </p>
      </header>

      {workspace ? <WorkspaceCard workspace={workspace} /> : null}

      <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('coach.list.coachesHeader')}
      </h2>

      {entries.length === 0 ? (
        <section className="flex flex-col items-center gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-6 text-center">
          <div className="flex size-12 items-center justify-center rounded-full border-[0.5px] border-border-hairline bg-bg-secondary">
            <Users size={20} strokeWidth={1.5} className="text-text-color-tertiary" aria-hidden />
          </div>
          <h2 className="text-h3 text-text-color-primary">
            {t('coach.list.emptyTitle')}
          </h2>
          <p className="max-w-[260px] text-caption text-text-color-secondary">
            {t('coach.list.emptyBody')}
          </p>
        </section>
      ) : (
        <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
          {entries.map((e, idx) => (
            <div
              key={e.coachId}
              className={
                idx === 0 ? '' : 'border-t-[0.5px] border-border-hairline'
              }
            >
              <CoachListRow
                entry={e}
                onTap={() => navigate(`/coach/${e.coachId}`)}
              />
            </div>
          ))}
        </div>
      )}
    </main>
  );
}

function WorkspaceCard({ workspace }: { workspace: CoachListWorkspace }) {
  const { t } = useTranslation();
  const initial = (workspace.name[0] ?? '?').toUpperCase();
  return (
    <section className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
      <div className="flex items-center gap-3 p-4">
        <div
          aria-hidden
          className="flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-accent text-white"
        >
          {workspace.logoUrl ? (
            <img
              src={workspace.logoUrl}
              alt=""
              className="size-full object-cover"
            />
          ) : (
            <span className="text-h3 text-white">{initial}</span>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-body text-text-color-primary">
            {workspace.name}
          </p>
          <p className="mt-0.5 flex items-center gap-1 text-footnote text-text-color-secondary">
            {workspace.type === 'club'
              ? t('coach.list.clubLabel')
              : t('coach.list.personalLabel')}
            {workspace.city ? (
              <>
                <span aria-hidden>·</span>
                <MapPin size={12} strokeWidth={1.75} aria-hidden />
                <span className="truncate">{workspace.city}</span>
              </>
            ) : null}
          </p>
        </div>
      </div>
    </section>
  );
}

function Skeleton() {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-3 px-4 pt-6">
      <div className="h-7 w-36 rounded bg-bg-primary" />
      <div className="h-20 rounded-xl bg-bg-primary" />
      <div className="h-20 rounded-xl bg-bg-primary" />
    </div>
  );
}
