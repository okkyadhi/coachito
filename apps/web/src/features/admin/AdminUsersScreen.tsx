import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, Shield, ShieldOff } from 'lucide-react';
import { useState } from 'react';

import { PrimaryButton } from '@/components/PrimaryButton';
import { TextInput } from '@/components/TextInput';
import { ApiError } from '@/lib/api';

import type { AdminUserRow } from './admin-api';
import { listAdminUsers, resetAdminUserPassword, toggleAdminUser } from './admin-api';

function fmtDate(iso: string | null) {
  if (!iso) return 'Never';
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function ResetPasswordModal({
  user,
  onClose,
}: {
  user: AdminUserRow;
  onClose: () => void;
}) {
  const [newPassword, setNewPassword] = useState('');
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => resetAdminUserPassword(user.id, newPassword),
    onSuccess: () => { setDone(true); setError(null); },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Reset failed.'),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-sm rounded-2xl border-[0.5px] border-border-hairline bg-bg-primary p-6 shadow-lg">
        <h2 className="text-headline mb-1 text-text-color-primary">Reset password</h2>
        <p className="mb-4 text-body text-text-color-secondary">
          {user.display_name} · {user.email ?? 'no email'}
        </p>

        {done ? (
          <p className="mb-4 text-body text-green-700">Password reset successfully.</p>
        ) : (
          <>
            <TextInput
              type="password"
              label="New password"
              placeholder="Min. 8 characters"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
            />
            {error ? <p className="mt-2 text-caption text-danger-text">{error}</p> : null}
            <div className="mt-4 flex gap-2">
              <PrimaryButton
                type="button"
                onClick={() => mutation.mutate()}
                loading={mutation.isPending}
                disabled={newPassword.length < 8}
                className="flex-1"
              >
                Reset
              </PrimaryButton>
              <button
                type="button"
                onClick={onClose}
                className="flex-1 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary py-3 text-body text-text-color-primary"
              >
                Cancel
              </button>
            </div>
          </>
        )}

        {done ? (
          <button
            type="button"
            onClick={onClose}
            className="mt-2 w-full rounded-xl border-[0.5px] border-border-hairline bg-bg-primary py-3 text-body text-text-color-primary"
          >
            Close
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function AdminUsersScreen() {
  const [q, setQ] = useState('');
  const [resetTarget, setResetTarget] = useState<AdminUserRow | null>(null);
  const queryClient = useQueryClient();

  const trimmedQ = q.trim();

  const toggleMutation = useMutation({
    mutationFn: (userId: string) => toggleAdminUser(userId),
    onSuccess: (result) => {
      queryClient.setQueriesData<{ total: number; users: AdminUserRow[] }>(
        { queryKey: ['admin', 'users'] },
        (old) => old
          ? { ...old, users: old.users.map((u) => u.id === result.user_id ? { ...u, is_platform_admin: result.is_platform_admin } : u) }
          : old,
      );
    },
  });

  const { data, isPending, isError, error } = useQuery({
    queryKey: ['admin', 'users', trimmedQ],
    queryFn: () => {
      const params: Parameters<typeof listAdminUsers>[0] = {};
      if (trimmedQ) params.q = trimmedQ;
      return listAdminUsers(params);
    },
    staleTime: 30_000,
  });

  const users = data?.users ?? [];

  return (
    <div className="p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-large-title text-text-color-primary">Users</h1>
          {data ? (
            <p className="mt-0.5 text-footnote text-text-color-secondary">{data.total} total</p>
          ) : null}
        </div>
      </div>

      <div className="mb-4 w-64">
        <TextInput
          type="search"
          placeholder="Search name or email…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          autoComplete="off"
        />
      </div>

      <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        {isPending ? (
          <div className="px-6 py-12 text-center text-body text-text-color-secondary">Loading…</div>
        ) : isError ? (
          <div className="px-6 py-12 text-center text-body text-danger-text">
            {error instanceof ApiError
              ? `Failed to load users (${error.status}): ${error.message}`
              : 'Failed to load users. Please try again.'}
          </div>
        ) : users.length === 0 ? (
          <div className="px-6 py-12 text-center text-body text-text-color-secondary">No users found.</div>
        ) : (
          <table className="w-full text-left">
            <thead className="border-b-[0.5px] border-border-hairline">
              <tr>
                {['User', 'Workspaces', 'Last seen', 'Admin', 'Actions'].map((h) => (
                  <th key={h} className="px-4 py-3 text-caption font-medium text-text-color-secondary">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y-[0.5px] divide-border-hairline">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-bg-tertiary">
                  <td className="px-4 py-3">
                    <p className="text-body font-medium text-text-color-primary">{u.display_name}</p>
                    <p className="text-caption text-text-color-secondary">{u.email ?? '—'}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-body text-text-color-primary">{u.workspace_count}</p>
                    {u.workspace_summary ? (
                      <p className="max-w-xs truncate text-caption text-text-color-secondary">
                        {u.workspace_summary}
                      </p>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-body text-text-color-secondary">
                    {fmtDate(u.last_seen_at)}
                  </td>
                  <td className="px-4 py-3">
                    {u.is_platform_admin ? (
                      <Shield size={16} className="text-accent" strokeWidth={1.5} />
                    ) : (
                      <ShieldOff size={16} className="text-text-color-tertiary" strokeWidth={1.5} />
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => setResetTarget(u)}
                        className="flex items-center gap-1.5 text-caption text-accent hover:underline"
                      >
                        <KeyRound size={14} strokeWidth={1.5} />
                        Reset password
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleMutation.mutate(u.id)}
                        disabled={toggleMutation.isPending}
                        className="flex items-center gap-1.5 text-caption text-text-color-secondary hover:text-text-color-primary hover:underline disabled:opacity-40"
                      >
                        {u.is_platform_admin ? (
                          <><ShieldOff size={14} strokeWidth={1.5} />Revoke admin</>
                        ) : (
                          <><Shield size={14} strokeWidth={1.5} />Make admin</>
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {resetTarget ? (
        <ResetPasswordModal user={resetTarget} onClose={() => setResetTarget(null)} />
      ) : null}
    </div>
  );
}
