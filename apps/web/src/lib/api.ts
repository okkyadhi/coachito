// Thin fetch wrapper. Prepends /api, attaches the bearer token from the
// auth store, and surfaces the FastAPI `detail` field on errors.
import { useAuthStore } from '@/features/auth/auth-store';

// In dev, Vite proxies /api/* → http://api:8000 (see vite.config.ts).
// In prod, set VITE_API_BASE_URL at build time to point at the API service
// directly (e.g. "https://coachito-api.up.railway.app").  Defaults to /api
// so behind-a-reverse-proxy deployments keep working unchanged.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

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
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers, authenticated = true, useRefreshToken = false } = options;

  const finalHeaders = new Headers(headers);
  if (body !== undefined) {
    finalHeaders.set('Content-Type', 'application/json');
  }

  if (authenticated) {
    const state = useAuthStore.getState();
    const token = useRefreshToken ? state.refreshToken : state.token;
    if (token) finalHeaders.set('Authorization', `Bearer ${token}`);
  }

  const init: RequestInit = { method, headers: finalHeaders };
  if (body !== undefined) init.body = JSON.stringify(body);
  const res = await fetch(`${BASE_URL}${path}`, init);

  if (res.status === 204) return undefined as T;

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
