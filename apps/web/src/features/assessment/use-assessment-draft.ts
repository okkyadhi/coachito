// Local edit state for the assessment screen (v2).
//
// v1's offline-queued "fire and forget" pattern is gone — v2's lifecycle
// (draft → published → edited) needs server confirmation to advance, so we
// no longer write to Dexie's pending queue here.  We keep a Dexie-backed
// local cache of the in-progress draft so a refresh doesn't lose typing,
// but the source of truth for "what's saved" is the server.
//
// Hydration order: local-cache → /assessments/by-session (if we have a
// session id) → server scores override local.

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  type AssessmentSessionDetails,
  db,
} from '@/db/dexie';

import {
  type Assessment,
  type AssessmentStatus,
} from './assessment-api';

export interface DraftState {
  scores: Record<string, number>;
  notes: Record<string, string>;
  summary: string;
  sessionDetails: AssessmentSessionDetails;
}

const EMPTY_SESSION: AssessmentSessionDetails = {
  scheduledAt: null,
  durationMin: null,
  court: null,
  focus: null,
};

const EMPTY: DraftState = {
  scores: {},
  notes: {},
  summary: '',
  sessionDetails: EMPTY_SESSION,
};

export interface UseAssessmentDraft extends DraftState {
  loaded: boolean;
  isDirty: boolean;
  status: AssessmentStatus | null;
  assessmentId: string | null;
  sessionId: string | null;
  publishedAt: string | null;
  editedAt: string | null;
  coachId: string | null;
  coachDisplayName: string | null;
  traineeViewedAt: string | null;
  setScore: (skillCode: string, level: number | null) => void;
  setNote: (skillCode: string, note: string) => void;
  setSummary: (text: string) => void;
  setSessionDetails: (next: AssessmentSessionDetails) => void;
  hydrateFromServer: (a: Assessment, skillCodeById: Record<string, string>) => void;
  markClean: () => void;
  clearLocal: () => Promise<void>;
}

const DEBOUNCE_MS = 500;

export function useAssessmentDraft(athleteId: string): UseAssessmentDraft {
  const [state, setState] = useState<DraftState>(EMPTY);
  const [loaded, setLoaded] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [status, setStatus] = useState<AssessmentStatus | null>(null);
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [publishedAt, setPublishedAt] = useState<string | null>(null);
  const [editedAt, setEditedAt] = useState<string | null>(null);
  const [coachId, setCoachId] = useState<string | null>(null);
  const [coachDisplayName, setCoachDisplayName] = useState<string | null>(null);
  const [traineeViewedAt, setTraineeViewedAt] = useState<string | null>(null);
  const debounceRef = useRef<number | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      const draft = await db.drafts.get(athleteId);
      if (!active) return;
      if (draft) {
        setState({
          scores: draft.scores,
          notes: draft.notes,
          summary: draft.summary,
          sessionDetails: draft.sessionDetails ?? EMPTY_SESSION,
        });
      } else {
        setState(EMPTY);
      }
      setLoaded(true);
    })();
    return () => {
      active = false;
    };
  }, [athleteId]);

  // Debounced persist to Dexie when dirty.
  useEffect(() => {
    if (!loaded || !isDirty) return;
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      void db.drafts.put({
        athleteId,
        scores: state.scores,
        notes: state.notes,
        summary: state.summary,
        sessionDetails: state.sessionDetails,
        updatedAt: Date.now(),
      });
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [athleteId, loaded, isDirty, state]);

  const setScore = useCallback((skillCode: string, level: number | null) => {
    setIsDirty(true);
    setState((prev) => {
      const next = { ...prev.scores };
      if (level == null) delete next[skillCode];
      else next[skillCode] = level;
      return { ...prev, scores: next };
    });
  }, []);

  const setNote = useCallback((skillCode: string, note: string) => {
    setIsDirty(true);
    setState((prev) => {
      const next = { ...prev.notes };
      if (note.trim() === '') delete next[skillCode];
      else next[skillCode] = note;
      return { ...prev, notes: next };
    });
  }, []);

  const setSummary = useCallback((text: string) => {
    setIsDirty(true);
    setState((prev) => ({ ...prev, summary: text }));
  }, []);

  const setSessionDetails = useCallback((next: AssessmentSessionDetails) => {
    setIsDirty(true);
    setState((prev) => ({ ...prev, sessionDetails: next }));
  }, []);

  const hydrateFromServer = useCallback(
    (a: Assessment, skillCodeById: Record<string, string>) => {
      const scores: Record<string, number> = {};
      const notes: Record<string, string> = {};
      for (const s of a.scores) {
        const code = skillCodeById[s.skillId];
        if (!code) continue;
        scores[code] = s.level;
        if (s.note) notes[code] = s.note;
      }
      setState({
        scores,
        notes,
        summary: a.summary ?? '',
        sessionDetails: EMPTY_SESSION,
      });
      setStatus(a.status);
      setAssessmentId(a.id);
      setSessionId(a.sessionId);
      setPublishedAt(a.publishedAt);
      setEditedAt(a.editedAt);
      setCoachId(a.coachId);
      setCoachDisplayName(a.coach_display_name);
      setTraineeViewedAt(a.traineeViewedAt);
      setIsDirty(false);
    },
    [],
  );

  const markClean = useCallback(() => {
    setIsDirty(false);
  }, []);

  const clearLocal = useCallback(async () => {
    await db.drafts.delete(athleteId);
    setState(EMPTY);
    setIsDirty(false);
  }, [athleteId]);

  return {
    ...state,
    loaded,
    isDirty,
    status,
    assessmentId,
    sessionId,
    publishedAt,
    editedAt,
    coachId,
    coachDisplayName,
    traineeViewedAt,
    setScore,
    setNote,
    setSummary,
    setSessionDetails,
    hydrateFromServer,
    markClean,
    clearLocal,
  };
}
