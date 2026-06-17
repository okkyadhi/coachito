import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Mail, MessageCircle, X } from 'lucide-react';
import { useState } from 'react';

import { ApiError } from '@/lib/api';

import type {
  UpgradeRequestRow,
  UpgradeRequestStatus,
} from './admin-api';
import { listUpgradeRequests, patchUpgradeRequest } from './admin-api';

const PLAN_LABELS: Record<string, string> = {
  solo_coach: 'Personal',
  solo_coach_unlimited: 'Personal Unlimited',
  club_starter: 'Club',
  club_pro: 'Club Annual',
};

type Filter = UpgradeRequestStatus | 'all';

function fmtDateTime(iso: string) {
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function AdminUpgradeRequestsScreen() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<Filter>('pending');

  const { data, isPending } = useQuery({
    queryKey: ['admin', 'upgrade-requests', filter],
    queryFn: () => listUpgradeRequests(filter),
    staleTime: 30_000,
  });

  const mutation = useMutation({
    mutationFn: ({
      id,
      status,
    }: {
      id: string;
      status: UpgradeRequestStatus;
    }) => patchUpgradeRequest(id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'upgrade-requests'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'stats'] });
    },
  });

  return (
    <div className="p-6">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-large-title text-text-color-primary">
            Upgrade requests
          </h1>
          <p className="mt-1 text-body text-text-color-secondary">
            Coaches that picked a plan from the in-app plan picker. Follow up
            via email, then mark resolved.
          </p>
        </div>
      </div>

      <div className="mb-4 flex w-fit gap-1 rounded-lg border-[0.5px] border-border-hairline bg-bg-tertiary p-1">
        {(['pending', 'resolved', 'dismissed', 'all'] as Filter[]).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`rounded-md px-4 py-1.5 text-body capitalize transition-colors ${
              filter === f
                ? 'bg-bg-primary text-text-color-primary shadow-sm'
                : 'text-text-color-secondary hover:text-text-color-primary'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {isPending ? (
        <div className="text-body text-text-color-secondary">Loading…</div>
      ) : !data?.requests.length ? (
        <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-10 text-center text-body text-text-color-secondary">
          No {filter === 'all' ? '' : filter} requests.
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
          <table className="w-full text-left">
            <thead className="border-b-[0.5px] border-border-hairline bg-bg-tertiary">
              <tr>
                {[
                  'Workspace',
                  'Requester',
                  'Plan',
                  'Requested',
                  'Status',
                  '',
                ].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-caption font-medium uppercase tracking-wide text-text-color-secondary"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y-[0.5px] divide-border-hairline">
              {data.requests.map((r) => (
                <Row key={r.id} row={r} onAction={(s) => mutation.mutate({ id: r.id, status: s })} pending={mutation.isPending} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {mutation.isError ? (
        <p className="mt-3 text-caption text-danger-text">
          {mutation.error instanceof ApiError
            ? mutation.error.message
            : 'Update failed.'}
        </p>
      ) : null}
    </div>
  );
}

// wa.me requires a digits-only phone (no leading "+").
function waNumber(phone: string | null): string | null {
  if (!phone) return null;
  const digits = phone.replace(/\D+/g, '');
  return digits.length > 0 ? digits : null;
}

function Row({
  row,
  onAction,
  pending,
}: {
  row: UpgradeRequestRow;
  onAction: (s: UpgradeRequestStatus) => void;
  pending: boolean;
}) {
  const followUpEmail = row.requester_email ?? row.owner_email;
  const wa = waNumber(row.requester_phone_e164 ?? row.owner_phone_e164);
  const waMsg = encodeURIComponent(
    `Halo, terkait permintaan upgrade workspace "${row.workspace_name}" ke plan ${
      PLAN_LABELS[row.requested_plan] ?? row.requested_plan
    }. Saya dari Coachito, mohon konfirmasi pembayaran ya.`,
  );
  return (
    <tr>
      <td className="px-4 py-3">
        <p className="text-body font-medium text-text-color-primary">
          {row.workspace_name}
        </p>
        {row.owner_email ? (
          <p className="text-caption text-text-color-secondary">
            Owner: {row.owner_display_name ?? '—'} · {row.owner_email}
          </p>
        ) : null}
      </td>
      <td className="px-4 py-3">
        <p className="text-body text-text-color-primary">
          {row.requester_display_name ?? '—'}
        </p>
        <p className="text-caption text-text-color-secondary">
          {row.requester_email ?? '—'}
        </p>
        {row.requester_phone_e164 ? (
          <p className="text-caption text-text-color-secondary">
            {row.requester_phone_e164}
          </p>
        ) : null}
      </td>
      <td className="px-4 py-3 text-body text-text-color-primary">
        {PLAN_LABELS[row.requested_plan] ?? row.requested_plan}
      </td>
      <td className="px-4 py-3 text-body text-text-color-secondary">
        {fmtDateTime(row.created_at)}
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={row.status} />
        {row.resolved_at ? (
          <p className="mt-0.5 text-caption text-text-color-tertiary">
            {fmtDateTime(row.resolved_at)}
          </p>
        ) : null}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-2">
          {wa ? (
            <a
              href={`https://wa.me/${wa}?text=${waMsg}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex h-8 items-center gap-1.5 rounded-md bg-green-50 px-2.5 text-caption font-medium text-green-700 hover:bg-green-100"
              title={`WhatsApp ${row.requester_phone_e164 ?? row.owner_phone_e164}`}
            >
              <MessageCircle size={14} strokeWidth={1.75} />
              WhatsApp
            </a>
          ) : null}
          {followUpEmail ? (
            <a
              href={`mailto:${followUpEmail}?subject=${encodeURIComponent(
                `Upgrade ${row.workspace_name} to ${
                  PLAN_LABELS[row.requested_plan] ?? row.requested_plan
                }`,
              )}`}
              className="flex h-8 items-center gap-1.5 rounded-md border-[0.5px] border-border-hairline bg-bg-primary px-2.5 text-caption text-text-color-primary hover:bg-bg-tertiary"
              title={`Email ${followUpEmail}`}
            >
              <Mail size={14} strokeWidth={1.75} />
              Email
            </a>
          ) : null}
          {row.status === 'pending' ? (
            <>
              <button
                type="button"
                disabled={pending}
                onClick={() => onAction('resolved')}
                className="flex h-8 items-center gap-1.5 rounded-md bg-green-50 px-2.5 text-caption font-medium text-green-700 hover:bg-green-100 disabled:opacity-50"
              >
                <Check size={14} strokeWidth={2} />
                Resolved
              </button>
              <button
                type="button"
                disabled={pending}
                onClick={() => onAction('dismissed')}
                className="flex h-8 items-center gap-1.5 rounded-md bg-bg-tertiary px-2.5 text-caption text-text-color-secondary hover:bg-bg-primary disabled:opacity-50"
              >
                <X size={14} strokeWidth={2} />
                Dismiss
              </button>
            </>
          ) : (
            <button
              type="button"
              disabled={pending}
              onClick={() => onAction('pending')}
              className="flex h-8 items-center gap-1.5 rounded-md border-[0.5px] border-border-hairline px-2.5 text-caption text-text-color-secondary hover:bg-bg-tertiary disabled:opacity-50"
            >
              Re-open
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

function StatusBadge({ status }: { status: UpgradeRequestStatus }) {
  const cls =
    status === 'pending'
      ? 'bg-amber-50 text-amber-700'
      : status === 'resolved'
        ? 'bg-green-50 text-green-700'
        : 'bg-bg-tertiary text-text-color-tertiary';
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-caption font-medium capitalize ${cls}`}
    >
      {status}
    </span>
  );
}
