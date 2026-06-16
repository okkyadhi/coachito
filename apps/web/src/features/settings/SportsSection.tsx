import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useAuthStore } from '@/features/auth/auth-store';
import {
  archiveSport,
  enableSport,
  listPlatformSports,
  listWorkspaceSports,
  sportLabel,
} from '@/features/sports/sports-api';
import { ApiError } from '@/lib/api';

// Workspace settings panel: which sports this workspace runs, each with its
// curriculum.  Admins enable a platform sport (subject to plan limits) or
// archive one.  Single-sport plans surface an upgrade hint on the 402.
export function SportsSection({ readOnly = false }: { readOnly?: boolean }) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const workspaceId = useAuthStore((s) => s.currentWorkspaceId);
  const [error, setError] = useState<string | null>(null);

  const enabled = useQuery({
    queryKey: ['workspace-sports', workspaceId],
    queryFn: listWorkspaceSports,
    enabled: Boolean(workspaceId),
  });
  const platform = useQuery({
    queryKey: ['platform-sports'],
    queryFn: listPlatformSports,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['workspace-sports', workspaceId] });
  };

  const add = useMutation({
    mutationFn: (sportId: string) => enableSport(sportId),
    onSuccess: () => {
      setError(null);
      invalidate();
    },
    onError: (e) =>
      setError(e instanceof ApiError ? e.message : t('multisport.addFailed')),
  });

  const remove = useMutation({
    mutationFn: (sportId: string) => archiveSport(sportId),
    onSuccess: () => {
      setError(null);
      invalidate();
    },
    onError: (e) =>
      setError(e instanceof ApiError ? e.message : t('multisport.removeFailed')),
  });

  const enabledRows = enabled.data ?? [];
  const enabledIds = new Set(enabledRows.map((s) => s.sportId));
  const available = (platform.data ?? []).filter(
    (s) => !enabledIds.has(s.sportId),
  );

  return (
    <section className="flex flex-col gap-2">
      <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('multisport.title')}
      </h3>
      <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        {enabledRows.map((s) => (
          <div
            key={s.sportId}
            className="flex min-h-tap items-center gap-3 border-t-[0.5px] border-border-hairline p-3 first:border-t-0"
          >
            <div className="flex flex-1 flex-col">
              <span className="text-body text-text-color-primary">
                {sportLabel(s, i18n.language)}
              </span>
              {s.curriculumCode ? (
                <span className="text-footnote text-text-color-tertiary">
                  {t('multisport.curriculumLabel', { code: s.curriculumCode })}
                </span>
              ) : null}
            </div>
            {!readOnly && enabledRows.length > 1 ? (
              <button
                type="button"
                onClick={() => remove.mutate(s.sportId)}
                disabled={remove.isPending}
                aria-label={t('multisport.removeCta')}
                className="flex size-8 items-center justify-center rounded-md text-text-color-tertiary hover:bg-bg-secondary disabled:opacity-60"
              >
                <X size={15} strokeWidth={1.75} aria-hidden />
              </button>
            ) : null}
          </div>
        ))}

        {!readOnly &&
          available.map((s) => (
            <button
              key={s.sportId}
              type="button"
              onClick={() => add.mutate(s.sportId)}
              disabled={add.isPending}
              className="flex min-h-tap w-full items-center gap-2 border-t-[0.5px] border-border-hairline p-3 text-left text-accent hover:bg-bg-secondary disabled:opacity-60"
            >
              <Plus size={15} strokeWidth={1.75} aria-hidden />
              <span className="text-body">
                {t('multisport.addNamed', {
                  name: sportLabel(s, i18n.language),
                })}
              </span>
            </button>
          ))}
      </div>
      {error ? (
        <p className="px-1 text-footnote text-danger-text">{error}</p>
      ) : null}
    </section>
  );
}
