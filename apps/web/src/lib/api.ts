// Thin fetch wrapper. Prepends /api, attaches the bearer token from the
// auth store, and surfaces the FastAPI `detail` field on errors.
import { useAuthStore } from '@/features/auth/auth-store';

// In dev, Vite proxies /api/* → http://api:8000 (see vite.config.ts), so
// the default base is /api.  In the single-container prod deploy (FastAPI
// serves the FE static itself) build with VITE_API_BASE_URL="" so calls
// resolve relatively against the same origin.  ?? — not || — so an empty
// string from the build env isn't accidentally re-defaulted back to /api.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  headers?: HeadersInit;
  /** Send the Authorization header.  Defaults to true. */
  authenticated?: boolean;
  /** Use the refresh token instead of access.  Used by /auth/refresh only. */
  useRefreshToken?: boolean;
  /** Internal: skip the 401 → refresh retry to avoid infinite loops. */
  _isRetry?: boolean;
  /** Internal: use this token directly instead of reading from the store.
   *  Set by the 401 retry so the fresh token is used even when the store
   *  update was skipped (e.g. user object absent in an edge case). */
  _overrideToken?: string;
}

// Singleton promise so concurrent 401s all wait on the same refresh call.
let _refreshingPromise: Promise<string | null> | null = null;

async function _tryRefresh(): Promise<string | null> {
  if (_refreshingPromise) return _refreshingPromise;

  _refreshingPromise = (async () => {
    const state = useAuthStore.getState();
    if (!state.refreshToken) {
      state.signOut();
      return null;
    }
    try {
      const res = await fetch(`${BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${state.refreshToken}` },
      });
      if (!res.ok) throw new Error('refresh failed');
      const pair = (await res.json()) as {
        access_token: string;
        refresh_token: string;
        workspace_id: string | null;
        role: string | null;
      };
      // Re-use the existing user object — only token + workspace context changes.
      const current = useAuthStore.getState();
      if (current.user) {
        useAuthStore.getState().signIn({
          token: pair.access_token,
          refreshToken: pair.refresh_token,
          user: current.user,
          workspaceId: pair.workspace_id ?? current.currentWorkspaceId,
        });
      }
      return pair.access_token;
    } catch {
      useAuthStore.getState().signOut();
      return null;
    } finally {
      _refreshingPromise = null;
    }
  })();

  return _refreshingPromise;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    method = 'GET',
    body,
    headers,
    authenticated = true,
    useRefreshToken = false,
    _isRetry = false,
    _overrideToken,
  } = options;

  const finalHeaders = new Headers(headers);
  if (body !== undefined) {
    finalHeaders.set('Content-Type', 'application/json');
  }

  if (authenticated) {
    const state = useAuthStore.getState();
    const token = _overrideToken ?? (useRefreshToken ? state.refreshToken : state.token);
    if (token) finalHeaders.set('Authorization', `Bearer ${token}`);
  }

  // cache: 'no-store' — never read/write the HTTP disk cache for API calls.
  // In the single-container prod build BASE_URL is "" so an API path like
  // /admin/users collides with the SPA document URL; without this the browser
  // could serve a cached index.html to the fetch and JSON parsing would fail.
  const init: RequestInit = { method, headers: finalHeaders, cache: 'no-store' };
  if (body !== undefined) init.body = JSON.stringify(body);
  const res = await fetch(`${BASE_URL}${path}`, init);

  if (res.status === 204) return undefined as T;

  // On 401, attempt a silent token refresh and retry once.
  if (res.status === 401 && authenticated && !useRefreshToken && !_isRetry) {
    const newToken = await _tryRefresh();
    if (newToken) {
      // Pass the fresh token directly so the retry works even if the store
      // update inside _tryRefresh was skipped.
      return request<T>(path, { ...options, _isRetry: true, _overrideToken: newToken });
    }
    // Refresh failed; signOut already called — throw so callers see the error.
    throw new ApiError(401, 'Session expired. Please sign in again.');
  }

  if (!res.ok) {
    let detail: string = res.statusText;
    try {
      const data = (await res.json()) as { detail?: string };
      if (data.detail) detail = data.detail;
    } catch {
      // Body wasn't JSON; keep statusText.
    }
    throw new ApiError(res.status, detail);
  }

  return (await res.json()) as T;
}

/** Fetch a binary response with Bearer auth — for PDF/file downloads. */
export async function fetchAuthBlob(path: string): Promise<Blob> {
  const state = useAuthStore.getState();
  const res = await fetch(`${BASE_URL}${path}`, {
    cache: 'no-store',
    headers: state.token ? { Authorization: `Bearer ${state.token}` } : {},
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = (await res.json()) as { detail?: string };
      if (data.detail) detail = data.detail;
    } catch { /* keep statusText */ }
    throw new ApiError(res.status, detail);
  }
  return res.blob();
}

export const api = {
  get: <T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'POST', body }),
  patch: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'PATCH', body }),
  del: <T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'DELETE' }),
};
