import type { WorkspaceRole } from './auth-store';

// Centralizes the "where do I land after signing in?" decision so each
// auth entry point doesn't reimplement it.
export function postSignInPath(
  workspaceId: string | null,
  role: WorkspaceRole | null = null,
): string {
  if (!workspaceId) return '/onboarding/create-workspace';
  if (role === 'trainee' || role === 'parent') return '/home';
  return '/today';
}
