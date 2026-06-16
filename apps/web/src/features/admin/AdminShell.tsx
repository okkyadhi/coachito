import { Building2, LogOut, Users } from 'lucide-react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import { Logo } from '@/components/Logo';
import { useAuthStore } from '@/features/auth/auth-store';

function NavItem({ to, icon: Icon, label }: { to: string; icon: typeof Building2; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-2.5 rounded-lg px-3 py-2 text-body transition-colors ${
          isActive
            ? 'bg-accent/10 text-accent'
            : 'text-text-color-secondary hover:bg-bg-tertiary hover:text-text-color-primary'
        }`
      }
    >
      <Icon size={18} strokeWidth={1.5} />
      {label}
    </NavLink>
  );
}

export function AdminShell() {
  const signOut = useAuthStore((s) => s.signOut);
  const navigate = useNavigate();

  function handleSignOut() {
    signOut();
    navigate('/signin', { replace: true });
  }

  return (
    <div className="flex h-screen bg-bg-tertiary">
      {/* Sidebar */}
      <aside className="flex w-52 flex-shrink-0 flex-col border-r-[0.5px] border-border-hairline bg-bg-primary">
        <div className="flex items-center gap-2.5 border-b-[0.5px] border-border-hairline px-4 py-3.5">
          <Logo size={24} />
          <div>
            <p className="text-footnote font-medium text-text-color-primary">Coachito</p>
            <p className="text-caption text-text-color-secondary">Admin</p>
          </div>
        </div>

        <nav className="flex-1 space-y-0.5 p-3">
          <NavItem to="/admin/workspaces" icon={Building2} label="Workspaces" />
          <NavItem to="/admin/users" icon={Users} label="Users" />
        </nav>

        <div className="border-t-[0.5px] border-border-hairline p-3">
          <button
            type="button"
            onClick={handleSignOut}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-body text-text-color-secondary hover:bg-bg-tertiary hover:text-danger-text"
          >
            <LogOut size={18} strokeWidth={1.5} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
