import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Calendar, UserCheck, Users } from 'lucide-react';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { PrimaryButton } from '@/components/PrimaryButton';
import { ApiError } from '@/lib/api';

import type { AdminWorkspacePatch, BillingStatus, WorkspacePlan } from './admin-api';
import {
  getAdminWorkspace,
  getAdminWorkspaceMembers,
  patchAdminWorkspace,
} from './admin-api';

const PLAN_LABELS: Record<WorkspacePlan, string> = {
  free_trial: 'Free trial',
  solo_coach: 'Solo coach',
  club_starter: 'Club starter',
  club_pro: 'Club pro',
};

const BILLING_BADGE: Record<BillingStatus, { label: string; cls: string }> = {
  trial:    { label: 'Trial',    cls: 'bg-amber-50 text-amber-700' },
  paid:     { label: 'Paid',     cls: 'bg-green-50 text-green-700' },
  lapsed:   { label: 'Lapsed',   cls: 'bg-red-50 text-red-700' },
  archived: { label: 'Archived', cls: 'bg-bg-tertiary text-text-color-tertiary' },
  unknown:  { label: 'Unknown',  cls: 'bg-bg-tertiary text-text-color-tertiary' },
};

const ROLE_LABELS: Record<string, string> = {
  club_admin: 'Club admin',
  head_coach: 'Head coach',
  coach: 'Coach',
};

function toDateInput(iso: string | null) {
  if (!iso) return '';
  return iso.slice(0, 10);
}

function fmtDate(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function StatCard({ icon: Icon, label, value }: { icon: typeof Users; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
      <div className="bg-accent/10 flex size-10 items-center justify-center rounded-full text-accent">
        <Icon size={20} strokeWidth={1.5} />
      </div>
      <div>
        <p className="text-caption text-text-color-secondary">{label}</p>
        <p className="text-headline text-text-color-primary">{value}</p>
      </div>
    </div>
  );
}

type Tab = 'billing' | 'members';

export function AdminWorkspaceDetailScreen() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>('billing');

  const { data: ws, isPending } = useQuery({
    queryKey: ['admin', 'workspace', id],
    queryFn: () => getAdminWorkspace(id!),
    enabled: !!id,
  });

  const { data: members, isPending: membersPending } = useQuery({
    queryKey: ['admin', 'workspace-members', id],
    queryFn: () => getAdminWorkspaceMembers(id!),
    enabled: !!id && tab === 'members',
    staleTime: 60_000,
  });

  const [plan, setPlan] = useState<WorkspacePlan | ''>('');
  const [trialEndsAt, setTrialEndsAt] = useState('');
  const [paidUntil, setPaidUntil] = useState('');
  const [quota, setQuota] = useState('');
  const [archived, setArchived] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [initialized, setInitialized] = useState(false);
  if (ws && !initialized) {
    setPlan(ws.plan);
    setTrialEndsAt(toDateInput(ws.trial_ends_at));
    setPaidUntil(toDateInput(ws.paid_until));
    setQuota(String(ws.active_trainee_quota));
    setArchived(ws.archived_at !== null);
    setInitialized(true);
  }

  const mutation = useMutation({
    mutationFn: (patch: AdminWorkspacePatch) => patchAdminWorkspace(id!, patch),
    onSuccess: (updated) => {
      queryClient.setQueryData(['admin', 'workspace', id], updated);
      queryClient.invalidateQueries({ queryKey: ['admin', 'workspaces'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      setError(null);
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Save failed.'),
  });

  function handleSave() {
    if (!ws) return;
    const patch: AdminWorkspacePatch = {};
    if (plan && plan !== ws.plan) patch.plan = plan as WorkspacePlan;
    const trialIso = trialEndsAt ? new Date(trialEndsAt).toISOString() : null;
    if (trialIso !== (ws.trial_ends_at
      ? ws.trial_ends_at.slice(0, 10) === trialEndsAt ? ws.trial_ends_at : trialIso
      : null)) patch.trial_ends_at = trialIso;
    const paidIso = paidUntil ? new Date(paidUntil).toISOString() : null;
    if (paidIso !== (ws.paid_until
      ? ws.paid_until.slice(0, 10) === paidUntil ? ws.paid_until : paidIso
      : null)) patch.paid_until = paidIso;
    const quotaNum = parseInt(quota, 10);
    if (!isNaN(quotaNum) && quotaNum !== ws.active_trainee_quota) patch.active_trainee_quota = quotaNum;
    const isArchived = ws.archived_at !== null;
    if (archived !== null && archived !== isArchived) patch.archived = archived;
    if (Object.keys(patch).length === 0) return;
    mutation.mutate(patch);
  }

  if (isPending) return <div className="p-6 text-body text-text-color-secondary">Loading…</div>;
  if (!ws) return <div className="p-6 text-body text-text-color-secondary">Workspace not found.</div>;

  const badge = BILLING_BADGE[ws.billing_status];

  return (
    <div className="p-6">
      <button
        type="button"
        onClick={() => navigate('/admin/workspaces')}
        className="mb-4 flex items-center gap-1.5 text-body text-accent"
      >
        <ArrowLeft size={16} strokeWidth={1.5} />
        Workspaces
      </button>

      <div className="mb-6 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-large-title text-text-color-primary">{ws.name}</h1>
            <span className={`rounded-full px-2.5 py-0.5 text-caption font-medium ${badge.cls}`}>
              {badge.label}
            </span>
          </div>
          <p className="mt-1 text-body text-text-color-secondary">
            {ws.owner_email ?? ws.owner_display_name} · {ws.type === 'club' ? 'Club' : 'Personal'} · Created {fmtDate(ws.created_at)}
          </p>
          {ws.owner_phone_e164 ? (
            <p className="mt-0.5 text-caption text-text-color-secondary">
              <a
                href={`https://wa.me/${ws.owner_phone_e164.replace(/\D+/g, '')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-green-700 hover:underline"
              >
                WhatsApp {ws.owner_phone_e164}
              </a>
            </p>
          ) : null}
        </div>
      </div>

      {/* Stats */}
      <div className="mb-6 grid grid-cols-3 gap-3">
        <StatCard icon={UserCheck} label="Coaches" value={String(ws.coach_count)} />
        <StatCard icon={Users} label="Trainees" value={String(ws.trainee_count)} />
        <StatCard icon={Calendar} label="Last session" value={fmtDate(ws.last_session_at)} />
      </div>

      {/* Tabs */}
      <div className="mb-4 flex w-fit gap-1 rounded-lg border-[0.5px] border-border-hairline bg-bg-tertiary p-1">
        {(['billing', 'members'] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded-md px-4 py-1.5 text-body capitalize transition-colors ${
              tab === t
                ? 'bg-bg-primary text-text-color-primary shadow-sm'
                : 'text-text-color-secondary hover:text-text-color-primary'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'billing' ? (
        <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-5">
          <h2 className="text-headline mb-4 text-text-color-primary">Billing & settings</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-caption text-text-color-secondary">Plan</label>
              <select
                value={plan}
                onChange={(e) => setPlan(e.target.value as WorkspacePlan)}
                className="h-11 w-full rounded-lg border-[0.5px] border-border-hairline bg-bg-primary px-3 text-body text-text-color-primary focus:outline-none focus:ring-1 focus:ring-accent"
              >
                {(Object.entries(PLAN_LABELS) as [WorkspacePlan, string][]).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-caption text-text-color-secondary">Trainee quota</label>
              <input
                type="number"
                min={0}
                max={100000}
                value={quota}
                onChange={(e) => setQuota(e.target.value)}
                className="h-11 w-full rounded-lg border-[0.5px] border-border-hairline bg-bg-primary px-3 text-body text-text-color-primary focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-caption text-text-color-secondary">Trial ends</label>
              <input
                type="date"
                value={trialEndsAt}
                onChange={(e) => setTrialEndsAt(e.target.value)}
                className="h-11 w-full rounded-lg border-[0.5px] border-border-hairline bg-bg-primary px-3 text-body text-text-color-primary focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-caption text-text-color-secondary">Paid until</label>
              <input
                type="date"
                value={paidUntil}
                onChange={(e) => setPaidUntil(e.target.value)}
                className="h-11 w-full rounded-lg border-[0.5px] border-border-hairline bg-bg-primary px-3 text-body text-text-color-primary focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <label className="flex cursor-pointer items-center gap-2 text-body text-text-color-secondary">
              <input
                type="checkbox"
                checked={archived ?? false}
                onChange={(e) => setArchived(e.target.checked)}
                className="size-4 rounded border-border-hairline accent-accent"
              />
              Archived
            </label>
          </div>
          {error ? <p className="mt-3 text-caption text-danger-text">{error}</p> : null}
          <div className="mt-4">
            <PrimaryButton type="button" onClick={handleSave} loading={mutation.isPending} className="w-auto px-6">
              {saved ? 'Saved' : 'Save changes'}
            </PrimaryButton>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Coaches */}
          <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
            <div className="border-b-[0.5px] border-border-hairline px-5 py-3">
              <h2 className="text-headline text-text-color-primary">Coaches</h2>
            </div>
            {membersPending ? (
              <div className="px-5 py-8 text-center text-body text-text-color-secondary">Loading…</div>
            ) : !members?.coaches.length ? (
              <div className="px-5 py-8 text-center text-body text-text-color-secondary">No coaches.</div>
            ) : (
              <table className="w-full text-left">
                <thead className="border-b-[0.5px] border-border-hairline">
                  <tr>
                    {['Name', 'Role', 'Trainees coached', 'Sessions'].map((h) => (
                      <th key={h} className="px-5 py-3 text-caption font-medium text-text-color-secondary">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y-[0.5px] divide-border-hairline">
                  {members.coaches.map((c) => (
                    <tr key={c.id}>
                      <td className="px-5 py-3">
                        <p className="text-body font-medium text-text-color-primary">{c.display_name}</p>
                        <p className="text-caption text-text-color-secondary">{c.email ?? '—'}</p>
                      </td>
                      <td className="px-5 py-3 text-body text-text-color-secondary">
                        {ROLE_LABELS[c.role] ?? c.role}
                      </td>
                      <td className="px-5 py-3 text-body text-text-color-primary">{c.distinct_trainee_count}</td>
                      <td className="px-5 py-3 text-body text-text-color-primary">{c.session_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Trainees */}
          <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
            <div className="border-b-[0.5px] border-border-hairline px-5 py-3">
              <h2 className="text-headline text-text-color-primary">
                Trainees
                {members ? <span className="ml-2 text-body font-normal text-text-color-secondary">({members.trainees.length})</span> : null}
              </h2>
            </div>
            {membersPending ? (
              <div className="px-5 py-8 text-center text-body text-text-color-secondary">Loading…</div>
            ) : !members?.trainees.length ? (
              <div className="px-5 py-8 text-center text-body text-text-color-secondary">No trainees yet.</div>
            ) : (
              <table className="w-full text-left">
                <thead className="border-b-[0.5px] border-border-hairline">
                  <tr>
                    {['Name', 'Tier', 'Last session'].map((h) => (
                      <th key={h} className="px-5 py-3 text-caption font-medium text-text-color-secondary">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y-[0.5px] divide-border-hairline">
                  {members.trainees.map((t) => (
                    <tr key={t.id}>
                      <td className="px-5 py-3">
                        <p className="text-body font-medium text-text-color-primary">{t.display_name}</p>
                        <p className="text-caption text-text-color-secondary">{t.email ?? '—'}</p>
                      </td>
                      <td className="px-5 py-3 text-body text-text-color-secondary">
                        {t.tier_name ?? 'Untiered'}
                      </td>
                      <td className="px-5 py-3 text-body text-text-color-secondary">{fmtDate(t.last_session_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
