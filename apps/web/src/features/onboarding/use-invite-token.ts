// Public lookup of an invite token's metadata so the welcome / landing
// screens can render workspace branding without auth.  The BE endpoint
// lands in the next step (GET /invites/public/:token); until then we
// hit /api/i/:token and scrape the server-rendered template, OR fall
// back to a stub so the FE can render.  Default is the stub — once the
// public JSON endpoint exists this module flips to api.get without any
// callsite churn.

import { useEffect, useState } from 'react';

export interface InviteMeta {
  token: string;
  workspaceName: string;
  workspaceLogoUrl: string | null;
  brandColor: string | null;
  coachDisplayName: string | null;
  traineeFirstName: string | null;
  primaryLocale: 'en' | 'id';
  expiresInDays: number;
  state: 'active' | 'expired' | 'consumed' | 'invalid';
}

interface PublicInviteApi {
  token: string;
  workspace_name: string;
  workspace_logo_url: string | null;
  brand_color: string | null;
  coach_display_name: string | null;
  trainee_first_name: string | null;
  primary_locale: 'en' | 'id';
  expires_in_days: number;
  state: 'active' | 'expired' | 'consumed' | 'invalid';
}

async function fetchInviteMeta(token: string): Promise<InviteMeta> {
  // The dev proxy / prod nginx route /api/* to FastAPI.  We try the JSON
  // endpoint first; on 404 (not yet shipped) we fall back to a render-time
  // stub derived from the token so the UX is still demoable.
  try {
    const res = await fetch(`/api/invites/public/${encodeURIComponent(token)}`);
    if (res.ok) {
      const j = (await res.json()) as PublicInviteApi;
      return {
        token: j.token,
        workspaceName: j.workspace_name,
        workspaceLogoUrl: j.workspace_logo_url,
        brandColor: j.brand_color,
        coachDisplayName: j.coach_display_name,
        traineeFirstName: j.trainee_first_name,
        primaryLocale: j.primary_locale,
        expiresInDays: j.expires_in_days,
        state: j.state,
      };
    }
    if (res.status === 410) return stub(token, 'expired');
    if (res.status === 404) return stub(token, 'invalid');
  } catch {
    // Network error — fall through to stub.
  }
  return stub(token, 'active');
}

function stub(token: string, state: InviteMeta['state']): InviteMeta {
  // Token format: {workspace_slug}-{trainee_handle}-{random}
  const [, handle] = token.split('-');
  const firstName = handle
    ? handle.charAt(0).toUpperCase() + handle.slice(1)
    : null;
  return {
    token,
    workspaceName: 'Coachito',
    workspaceLogoUrl: null,
    brandColor: null,
    coachDisplayName: null,
    traineeFirstName: firstName,
    primaryLocale: 'en',
    expiresInDays: 7,
    state,
  };
}

export function useInviteToken(token: string | undefined) {
  const [meta, setMeta] = useState<InviteMeta | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setMeta(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    void fetchInviteMeta(token).then((m) => {
      if (!cancelled) {
        setMeta(m);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return { meta, loading };
}

/** Naive OS detection for the install CTA on PublicLandingPage. */
export function detectOS(): 'ios' | 'android' | 'desktop' {
  if (typeof navigator === 'undefined') return 'desktop';
  const ua = navigator.userAgent || '';
  if (/iPhone|iPad|iPod/i.test(ua)) return 'ios';
  if (/Android/i.test(ua)) return 'android';
  return 'desktop';
}
