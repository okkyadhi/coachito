// Sync engine — v2.
//
// Assessment v2 is server-confirmed: each Save Draft / Publish / PATCH call
// awaits an HTTP response, so we no longer queue assessments locally for
// later POST.  The Dexie ``drafts`` table is just a refresh-survival cache
// for in-progress typing; nothing leaves the device without a server reply.
//
// We keep the v1 ``assessmentsPending`` table around for one release so any
// rows left over from upgrading users get cleared off rather than silently
// retried against the new endpoint shape (which would 422).

import { db } from '@/db/dexie';

type SyncListener = (event: {
  kind: 'started' | 'success' | 'failure' | 'idle';
  pending: number;
}) => void;

const listeners = new Set<SyncListener>();

function emit(kind: 'idle', pending: number): void {
  for (const l of listeners) l({ kind, pending });
}

export function onSyncEvent(fn: SyncListener): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

/** v1 → v2 cleanup.  Drops any leftover rows from the old offline queue so
 *  they don't get retried against the new endpoint.  Idempotent. */
async function clearLegacyPending(): Promise<void> {
  const count = await db.assessmentsPending.count();
  if (count > 0) {
    await db.assessmentsPending.clear();
  }
}

export async function syncPendingAssessments(): Promise<void> {
  await clearLegacyPending();
  emit('idle', 0);
}

export function startSyncEngine(): () => void {
  void syncPendingAssessments();
  return () => {
    /* nothing to teardown in v2 */
  };
}

export async function pendingAssessmentCount(): Promise<number> {
  return 0;
}
