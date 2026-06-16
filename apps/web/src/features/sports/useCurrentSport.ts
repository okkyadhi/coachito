import { useQuery } from '@tanstack/react-query';

import { useAuthStore } from '@/features/auth/auth-store';

import { useSportStore } from './sport-store';
import { listWorkspaceSports, type WorkspaceSport } from './sports-api';

export interface CurrentSport {
  /** Active sports on the current workspace (empty while loading). */
  sports: WorkspaceSport[];
  /** Resolved current sport id — the stored choice if still valid, else the
   *  first active sport.  Null while loading or if the workspace has none. */
  currentSportId: string | null;
  /** The resolved current sport object, if available. */
  current: WorkspaceSport | null;
  /** True when the workspace offers more than one sport (switcher visible). */
  isMultiSport: boolean;
  isLoading: boolean;
  setSport: (sportId: string) => void;
}

/**
 * Resolves the coach's active sport for the current workspace.  Single-sport
 * workspaces get an invisible, auto-resolved context; multi-sport workspaces
 * expose the switcher.  Mirrors the backend's "default to the single active
 * sport" rule so callers can pass ``currentSportId ?? undefined`` safely.
 */
export function useCurrentSport(): CurrentSport {
  const workspaceId = useAuthStore((s) => s.currentWorkspaceId);
  const stored = useSportStore((s) =>
    workspaceId ? s.byWorkspace[workspaceId] : undefined,
  );
  const setSportRaw = useSportStore((s) => s.setSport);

  const q = useQuery({
    queryKey: ['workspace-sports', workspaceId],
    queryFn: listWorkspaceSports,
    enabled: Boolean(workspaceId),
    staleTime: 60 * 1000,
  });

  const sports = q.data ?? [];
  const validStored =
    stored && sports.some((s) => s.sportId === stored) ? stored : null;
  const currentSportId = validStored ?? sports[0]?.sportId ?? null;
  const current = sports.find((s) => s.sportId === currentSportId) ?? null;

  return {
    sports,
    currentSportId,
    current,
    isMultiSport: sports.length > 1,
    isLoading: q.isPending,
    setSport: (sportId: string) => {
      if (workspaceId) setSportRaw(workspaceId, sportId);
    },
  };
}
