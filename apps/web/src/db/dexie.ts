// IndexedDB-backed local store. Three tables:
//   - drafts: in-progress assessment edits, keyed by athleteId so reload
//             preserves coach work
//   - assessmentsPending: completed assessments waiting to POST to the BE
//   - sessionsPending: future use (session create/edit while offline)
//
// All writes go to local first; the sync engine drains the *Pending tables
// when navigator.onLine.

import Dexie, { type Table } from 'dexie';

export interface PendingScore {
  skillId: string;
  skillCode: string; // kept for debugging / draft restoration
  level: number; // 1-5
  note: string;
  clientAssessmentId: string; // UUID minted on FE — idempotency key
  clientRecordedAt: string; // ISO timestamp
}

export type SessionFocus =
  | 'drilling'
  | 'match_play'
  | 'conditioning'
  | 'mental_training'
  | 'technique_focus'
  | 'general';

/** Editable metadata for the session this assessment batch will create.
 *  null means "let the BE default to NOW / 60min / general". */
export interface AssessmentSessionDetails {
  scheduledAt: string | null; // ISO datetime; null → server NOW()
  durationMin: number | null;
  court: string | null;
  focus: SessionFocus | null;
}

export interface PendingAssessment {
  id?: number;
  athleteId: string;
  workspaceId: string | null;
  scores: PendingScore[];
  summary: string;
  sessionId: string | null;
  sessionDetails: AssessmentSessionDetails;
  createdAt: number; // ms epoch
  attemptCount: number;
  lastAttemptAt: number | null;
  lastError: string | null;
}

export interface PendingSession {
  id?: number;
  athleteId: string;
  workspaceId: string | null;
  scheduledAt: number;
  durationMin: number;
  focus: string | null;
  court: string | null;
  createdAt: number;
  attemptCount: number;
  lastAttemptAt: number | null;
  lastError: string | null;
}

export interface AssessmentDraft {
  athleteId: string; // primary key
  scores: Record<string, number>; // skill_code → level
  notes: Record<string, string>; // skill_code → note
  summary: string;
  sessionDetails: AssessmentSessionDetails;
  updatedAt: number;
}

class RacademyDB extends Dexie {
  drafts!: Table<AssessmentDraft, string>;
  assessmentsPending!: Table<PendingAssessment, number>;
  sessionsPending!: Table<PendingSession, number>;

  constructor() {
    super('coachito');
    this.version(1).stores({
      drafts: 'athleteId, updatedAt',
      assessmentsPending: '++id, athleteId, createdAt',
      sessionsPending: '++id, athleteId, createdAt',
    });
    // v2: PendingScore gained skillId/clientAssessmentId/clientRecordedAt
    // when /assessments shipped (Step 12).  Pre-v2 rows are missing those
    // fields and the BE returns 422 on retry — clear them out so the queue
    // doesn't loop forever.
    this.version(2)
      .stores({
        drafts: 'athleteId, updatedAt',
        assessmentsPending: '++id, athleteId, createdAt',
        sessionsPending: '++id, athleteId, createdAt',
      })
      .upgrade((tx) => tx.table('assessmentsPending').clear());
    // v3: PendingAssessment + AssessmentDraft now carry sessionDetails
    // (scheduled_at / duration / court / focus).  Old rows are missing the
    // field — clear pending so the BE doesn't reject, and reset drafts so
    // they start clean.
    this.version(3)
      .stores({
        drafts: 'athleteId, updatedAt',
        assessmentsPending: '++id, athleteId, createdAt',
        sessionsPending: '++id, athleteId, createdAt',
      })
      .upgrade(async (tx) => {
        await tx.table('assessmentsPending').clear();
        await tx.table('drafts').clear();
      });
  }
}

export const db = new RacademyDB();
