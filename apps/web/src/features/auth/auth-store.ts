import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type WorkspaceRole =
  | 'club_admin'
  | 'head_coach'
  | 'coach'
  | 'trainee'
  | 'parent';

export interface AuthUser {
  id: string;
  email: string | null;
  displayName: string;
  preferredLocale: string;
  isMinor: boolean;
  role: WorkspaceRole | null;
}

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  currentWorkspaceId: string | null;
  signIn: (args: {
    token: string;
    refreshToken: string;
    user: AuthUser;
    workspaceId?: string | null;
  }) => void;
  switchWorkspace: (args: {
    token: string;
    refreshToken: string;
    workspaceId: string;
    role: WorkspaceRole | null;
  }) => void;
  signOut: () => void;
}

// TODO(auth-cookies): switch to an httpOnly Set-Cookie-backed refresh token
// before any real user data touches production.  Persisting the access +
// refresh tokens in localStorage is XSS-readable; the only reason it's here
// is to keep dev-loop friction low between magic-link sign-ins.  The proper
// path is in memory/auth_shell.md "Open question".
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      user: null,
      currentWorkspaceId: null,
      signIn: ({ token, refreshToken, user, workspaceId }) =>
        set({
          token,
          refreshToken,
          user,
          currentWorkspaceId: workspaceId ?? null,
        }),
      switchWorkspace: ({ token, refreshToken, workspaceId, role }) =>
        set((s) => ({
          token,
          refreshToken,
          currentWorkspaceId: workspaceId,
          // Same user identity — just the active-workspace context (and the
          // role they have there) is changing.
          user: s.user ? { ...s.user, role } : s.user,
        })),
      signOut: () =>
        set({
          token: null,
          refreshToken: null,
          user: null,
          currentWorkspaceId: null,
        }),
    }),
    {
      name: 'coachito.auth',
      // Only persist data, not function references.
      partialize: (s) => ({
        token: s.token,
        refreshToken: s.refreshToken,
        user: s.user,
        currentWorkspaceId: s.currentWorkspaceId,
      }),
      // Bumping `version` invalidates persisted state across breaking shape changes.
      version: 2,
    },
  ),
);
