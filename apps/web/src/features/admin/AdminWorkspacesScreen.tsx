import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { TextInput } from '@/components/TextInput';

import type { WorkspacePlan, WorkspaceType, AdminWorkspaceRow } from './admin-api';
import { listAdminWorkspaces, patchAdminWorkspace } from './admin-api';

const PLAN_LABELS: Record<WorkspacePlan, string> = {
  free_trial: 'Free trial',
  solo_coach: 'Solo coach',
  club_starter: 'Club starter',
  club_pro: 'Club pro',
};

function billingBadge(row: AdminWorkspaceRow) {
  if (row.archived_at) return { label: 'Archived', cls: 'bg-bg-tertiary text-text-color-tertiary' };
  const now = Date.now();
  if (row.paid_until && new Date(row.paid_until).getTime() > now)
    return { label: 'Paid', cls: 'bg-green-50 text-green-700' };
  if (row.trial_ends_at && new Date(row.trial_ends_at).getTime() > now)
    return { label: 'Trial', cls: 'bg-amber-50 text-amber-700' };
  if (row.paid_until || row.trial_ends_at)
    return { label: 'Lapsed', cls: 'bg-red-50 text-red-700' };
  return { label: 'Unknown', cls: 'bg-bg-tertiary text-text-color-tertiary' };
}

function fmtDate(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

type PlanFilter = '' | WorkspacePlan;
type TypeFilter = '' | WorkspaceType;

export function AdminWorkspacesScreen() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [q, setQ] = useState('');
  const [planFilter, setPlanFilter] = useState<PlanFilter>('');
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('');
  const [showArchived, setShowArchived] = useState(false);

  const extendTrialMutation = useMutation({
    mutationFn: (wsId: string) => {
      const trialEndsAt = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();
      return patchAdminWorkspace(wsId, { trial_ends_at: trialEndsAt });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'workspaces'] });
    },
  });

  const trimmedQ = q.trim();

  const { data, isPending } = useQuery({
    queryKey: ['admin', 'workspaces', trimmedQ, planFilter, typeFilter, showArchived],
    queryFn: () => {
      const params: Parameters<typeof listAdminWorkspaces>[0] = {};
      if (trimmedQ) params.q = trimmedQ;
      if (planFilter) params.plan = planFilter;
      if (typeFilter) params.type = typeFilter;
      if (!showArchived) params.archived = false;
      return listAdminWorkspaces(params);
    },
    staleTime: 30_000,
  });

  const workspaces = data?.workspaces ?? [];

  return (
    <div className="p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-large-title text-text-color-primary">Workspaces</h1>
          {data ? (
            <p className="mt-0.5 text-footnote text-text-color-secondary">{data.total} total</p>
          ) : null}
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="w-64">
          <TextInput
            type="search"
            placeholder="Search name, email…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            autoComplete="off"
          />
        </div>

        <select
          value={planFilter}
          onChange={(e) => setPlanFilter(e.target.value as PlanFilter)}
          className="h-11 rounded-lg border-[0.5px] border-border-hairline bg-bg-primary px-3 text-body text-text-color-primary focus:outline-none focus:ring-1 focus:ring-accent"
        >
          <option value="">All plans</option>
          {(Object.entries(PLAN_LABELS) as [WorkspacePlan, string][]).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as TypeFilter)}
          className="h-11 rounded-lg border-[0.5px] border-border-hairline bg-bg-primary px-3 text-body text-text-color-primary focus:outline-none focus:ring-1 focus:ring-accent"
        >
          <option value="">All types</option>
          <option value="club">Club</option>
          <option value="personal">Personal</option>
        </select>

        <label className="flex cursor-pointer items-center gap-2 text-body text-text-color-secondary">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
            className="h-4 w-4 rounded border-border-hairline accent-accent"
          />
          Show archived
        </label>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        {isPending ? (
          <div className="px-6 py-12 text-center text-body text-text-color-secondary">Loading…</div>
        ) : workspaces.length === 0 ? (
          <div className="px-6 py-12 text-center text-body text-text-color-secondary">No workspaces found.</div>
        ) : (
          <table className="w-full text-left">
            <thead className="border-b-[0.5px] border-border-hairline">
              <tr>
                {['Workspace', 'Type', 'Plan', 'Coaches', 'Trainees', 'Status', 'Created', ''].map((h) => (
                  <th key={h} className="px-4 py-3 text-caption font-medium text-text-color-secondary">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y-[0.5px] divide-border-hairline">
              {workspaces.map((ws) => {
                const badge = billingBadge(ws);
                return (
                  <tr
                    key={ws.id}
                    onClick={() => navigate(`/admin/workspaces/${ws.id}`)}
                    className="cursor-pointer hover:bg-bg-tertiary"
                  >
                    <td className="px-4 py-3">
                      <p className="text-body font-medium text-text-color-primary">{ws.name}</p>
                      <p className="text-caption text-text-color-secondary">{ws.owner_email ?? ws.owner_display_name}</p>
                    </td>
                    <td className="px-4 py-3 text-body text-text-color-secondary capitalize">{ws.type}</td>
                    <td className="px-4 py-3 text-body text-text-color-secondary">{PLAN_LABELS[ws.plan]}</td>
                    <td className="px-4 py-3 text-body text-text-color-primary">{ws.coach_count}</td>
                    <td className="px-4 py-3 text-body text-text-color-primary">{ws.trainee_count}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block rounded-full px-2.5 py-0.5 text-caption font-medium ${badge.cls}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-body text-text-color-secondary">{fmtDate(ws.created_at)}</td>
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => extendTrialMutation.mutate(ws.id)}
                        disabled={extendTrialMutation.isPending}
                        className="whitespace-nowrap text-caption text-accent hover:underline disabled:opacity-40"
                      >
                        +30 days
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
