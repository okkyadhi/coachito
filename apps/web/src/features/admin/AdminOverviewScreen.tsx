import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowUpCircle, Building2, TrendingUp, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { getAdminStats } from './admin-api';

const PLAN_LABELS: Record<string, string> = {
  free_trial: 'Free trial',
  solo_coach: 'Solo coach',
  club_starter: 'Club starter',
  club_pro: 'Club pro',
};

const PLAN_COLOR: Record<string, string> = {
  free_trial: 'bg-bg-tertiary',
  solo_coach: 'bg-blue-100',
  club_starter: 'bg-amber-100',
  club_pro: 'bg-green-100',
};

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  alert,
  onClick,
}: {
  icon: typeof Building2;
  label: string;
  value: string | number;
  sub?: string;
  alert?: boolean;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={`rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-5 ${onClick ? 'cursor-pointer hover:bg-bg-tertiary' : ''}`}
    >
      <div className="flex items-start justify-between">
        <div className={`flex size-10 items-center justify-center rounded-full ${alert ? 'bg-red-50 text-red-600' : 'bg-accent/10 text-accent'}`}>
          <Icon size={20} strokeWidth={1.5} />
        </div>
        {alert ? (
          <span className="rounded-full bg-red-50 px-2 py-0.5 text-caption font-medium text-red-600">
            Needs action
          </span>
        ) : null}
      </div>
      <p className="text-title-3 mt-3 font-medium text-text-color-primary">{value}</p>
      <p className="text-body text-text-color-secondary">{label}</p>
      {sub ? <p className="mt-0.5 text-caption text-text-color-tertiary">{sub}</p> : null}
    </div>
  );
}

export function AdminOverviewScreen() {
  const navigate = useNavigate();
  const { data, isPending } = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: getAdminStats,
    staleTime: 60_000,
  });

  return (
    <div className="p-6">
      <h1 className="mb-6 text-large-title text-text-color-primary">Overview</h1>

      {isPending ? (
        <div className="text-body text-text-color-secondary">Loading…</div>
      ) : data ? (
        <div className="space-y-6">
          {/* Top stats */}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard
              icon={Building2}
              label="Workspaces"
              value={data.workspaces_total}
              sub={`+${data.workspaces_new_this_month} this month`}
              onClick={() => navigate('/admin/workspaces')}
            />
            <StatCard
              icon={Users}
              label="Users"
              value={data.users_total}
              sub={`+${data.users_new_this_month} this month`}
              onClick={() => navigate('/admin/users')}
            />
            <StatCard
              icon={TrendingUp}
              label="Trainees"
              value={data.trainees_total}
            />
            <StatCard
              icon={AlertTriangle}
              label="Trials expiring"
              value={data.trials_expiring_soon}
              sub="within 7 days"
              alert={data.trials_expiring_soon > 0}
              onClick={() => navigate('/admin/workspaces')}
            />
            <StatCard
              icon={ArrowUpCircle}
              label="Upgrade requests"
              value={data.upgrade_requests_pending}
              sub="pending"
              alert={data.upgrade_requests_pending > 0}
              onClick={() => navigate('/admin/upgrade-requests')}
            />
          </div>

          {/* By plan breakdown */}
          <div className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-5">
            <h2 className="text-headline mb-4 text-text-color-primary">Workspaces by plan</h2>
            <div className="space-y-2">
              {Object.entries(PLAN_LABELS).map(([plan, label]) => {
                const count = data.workspaces_by_plan[plan] ?? 0;
                const pct = data.workspaces_total > 0 ? (count / data.workspaces_total) * 100 : 0;
                return (
                  <div key={plan}>
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-body text-text-color-secondary">{label}</span>
                      <span className="text-body font-medium text-text-color-primary">{count}</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-bg-tertiary">
                      <div
                        className={`h-1.5 rounded-full ${PLAN_COLOR[plan]?.replace('bg-', 'bg-') ?? 'bg-accent'}`}
                        style={{ width: `${pct}%`, backgroundColor: plan === 'club_pro' ? 'var(--accent)' : undefined }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
