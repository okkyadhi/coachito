import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Remembers the coach's selected sport per workspace.  Sport context is a
// per-workspace UI concern (a hybrid coach may run padel in one club and
// tennis in another), so we key by workspace id.  When unset, the resolver
// (useCurrentSport) falls back to the workspace's first active sport.
interface SportState {
  byWorkspace: Record<string, string>;
  setSport: (workspaceId: string, sportId: string) => void;
}

export const useSportStore = create<SportState>()(
  persist(
    (set) => ({
      byWorkspace: {},
      setSport: (workspaceId, sportId) =>
        set((s) => ({
          byWorkspace: { ...s.byWorkspace, [workspaceId]: sportId },
        })),
    }),
    {
      name: 'coachito.sport',
      partialize: (s) => ({ byWorkspace: s.byWorkspace }),
      version: 1,
    },
  ),
);
