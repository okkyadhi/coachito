import { ChevronDown, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { TextInput } from '@/components/TextInput';
import { TraineeCombobox } from '@/components/TraineeCombobox';
import { useAuthStore } from '@/features/auth/auth-store';
import { listMembers } from '@/features/settings/members-api';
import { sportLabel } from '@/features/sports/sports-api';
import { useCurrentSport } from '@/features/sports/useCurrentSport';
import { listTrainees } from '@/features/trainees/trainees-api';
import { useQuery } from '@tanstack/react-query';
import { ApiError } from '@/lib/api';

import {
  type Session,
  type SessionConflict,
  type SessionFocus,
  createSession,
  getSessionConflicts,
  updateSession,
} from './sessions-api';

const FOCUSES: SessionFocus[] = [
  'drilling',
  'match_play',
  'technique_focus',
  'conditioning',
  'mental_training',
  'general',
];
const DURATIONS = [30, 45, 60, 75, 90, 120];

interface Props {
  open: boolean;
  /** Edit mode when provided; create mode when null. */
  initial: Session | null;
  /** When set, pre-fills + locks the athlete picker — useful when launched
   *  from a trainee profile. */
  forAthleteId?: string;
  onClose: () => void;
  onSaved: (s: Session) => void;
}

export function ScheduleSessionSheet({
  open,
  initial,
  forAthleteId,
  onClose,
  onSaved,
}: Props) {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const workspaceId = useAuthStore((s) => s.currentWorkspaceId);
  const { sports, currentSportId, isMultiSport } = useCurrentSport();
  const isPrivileged = user?.role === 'club_admin' || user?.role === 'head_coach';
  const [sportId, setSportId] = useState<string>(
    initial?.sportId ?? currentSportId ?? '',
  );
  const [athleteId, setAthleteId] = useState<string>(
    initial?.athlete.id ?? forAthleteId ?? '',
  );
  const [assignedCoachId, setAssignedCoachId] = useState<string>(
    initial?.coach.id ?? user?.id ?? '',
  );
  const [date, setDate] = useState<string>(
    initial?.scheduledAt
      ? toLocalInputValue(initial.scheduledAt)
      : toLocalInputValue(new Date(Date.now() + 86_400_000).toISOString()),
  );
  const [duration, setDuration] = useState<number>(
    initial?.durationMin ?? 60,
  );
  const [court, setCourt] = useState<string>(initial?.court ?? '');
  const [focuses, setFocuses] = useState<SessionFocus[]>(
    initial?.focuses && initial.focuses.length > 0 ? initial.focuses : [],
  );
  const [notes, setNotes] = useState<string>(initial?.notes ?? '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflicts, setConflicts] = useState<SessionConflict | null>(null);

  const { data: traineesList } = useQuery({
    queryKey: ['trainees', 'all'],
    queryFn: () => listTrainees({}),
    enabled: open && !forAthleteId,
  });

  const { data: membersList } = useQuery({
    queryKey: ['workspace-members'],
    queryFn: listMembers,
    enabled: open && isPrivileged,
  });

  if (!open) return null;

  const checkConflicts = async () => {
    if (!athleteId || !date) return;
    try {
      const isoUtc = new Date(date).toISOString();
      const c = await getSessionConflicts({
        scheduledAt: isoUtc,
        durationMin: duration,
        athleteId,
        ...(initial ? { excludeSessionId: initial.id } : {}),
      });
      setConflicts(c);
    } catch {
      /* non-blocking — leave existing warnings alone */
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!athleteId) {
      setError(t('sessions.sheet.athleteRequired'));
      return;
    }
    setLoading(true);
    try {
      const isoUtc = new Date(date).toISOString();
      const coachChanged =
        initial != null &&
        isPrivileged &&
        assignedCoachId !== '' &&
        assignedCoachId !== initial.coach.id;
      const saved = initial
        ? await updateSession(initial.id, {
            scheduledAt: isoUtc,
            durationMin: duration,
            court: court.trim() || null,
            focuses,
            notes: notes.trim() || null,
            ...(coachChanged ? { coachId: assignedCoachId } : {}),
          })
        : await createSession({
            athleteId,
            scheduledAt: isoUtc,
            durationMin: duration,
            court: court.trim() || null,
            focuses,
            notes: notes.trim() || null,
            sportId: sportId || null,
            coachId: isPrivileged && assignedCoachId !== user?.id
              ? assignedCoachId || null
              : null,
          });
      onSaved(saved);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : t('sessions.sheet.genericError'),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={
        initial ? t('sessions.sheet.editTitle') : t('sessions.sheet.title')
      }
      className="fixed inset-0 z-40 flex items-end justify-center bg-black/40 sm:items-center"
    >
      <form
        onSubmit={handleSubmit}
        className="flex max-h-[90vh] w-full max-w-md flex-col rounded-t-2xl bg-bg-primary sm:rounded-2xl"
      >
        <header className="flex items-center justify-between border-b-[0.5px] border-border-hairline px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            aria-label={t('common.cancel')}
            className="flex size-9 items-center justify-center rounded-full text-text-color-secondary"
          >
            <X size={18} strokeWidth={1.75} aria-hidden />
          </button>
          <span className="text-h3 text-text-color-primary">
            {initial
              ? t('sessions.sheet.editTitle')
              : t('sessions.sheet.title')}
          </span>
          <span className="size-9" aria-hidden />
        </header>

        <div className="flex flex-col gap-4 overflow-y-auto p-4">
          {isMultiSport ? (
            <div className="flex flex-col gap-1">
              <span className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
                {t('multisport.sportLabel')}
              </span>
              <div className="flex flex-wrap gap-2">
                {sports.map((s) => (
                  <button
                    key={s.sportId}
                    type="button"
                    onClick={() => setSportId(s.sportId)}
                    className={
                      sportId === s.sportId
                        ? 'bg-accent/10 rounded-full border-[0.5px] border-accent px-3 py-1 text-caption text-accent'
                        : 'rounded-full border-[0.5px] border-border-hairline bg-bg-primary px-3 py-1 text-caption text-text-color-secondary'
                    }
                  >
                    {sportLabel(s, i18n.language)}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {isPrivileged && membersList && membersList.members.length > 1 ? (
            <div className="flex flex-col gap-1">
              <span className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
                {t('sessions.sheet.coachLabel')}
              </span>
              <div className="relative">
                <select
                  value={assignedCoachId}
                  onChange={(e) => setAssignedCoachId(e.target.value)}
                  className="min-h-tap w-full appearance-none rounded-xl border-[0.5px] border-border-hairline bg-bg-primary px-3 text-body text-text-color-primary focus:outline-none focus:ring-1 focus:ring-accent"
                >
                  {membersList.members.map((m) => (
                    <option key={m.userId} value={m.userId}>
                      {m.displayName}{m.isSelf ? ` (${t('sessions.sheet.coachSelf')})` : ''}
                    </option>
                  ))}
                </select>
                <ChevronDown
                  size={16}
                  strokeWidth={1.75}
                  aria-hidden
                  className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-text-color-tertiary"
                />
              </div>
            </div>
          ) : null}

          {!initial && !forAthleteId ? (
            <div className="flex flex-col gap-1">
              <span className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
                {t('sessions.sheet.athleteLabel')}
              </span>
              <TraineeCombobox
                value={athleteId || null}
                onChange={(id) => setAthleteId(id)}
                trainees={(traineesList?.trainees ?? []).map((tr) => ({
                  id: tr.id,
                  displayName: tr.displayName,
                  currentTier: tr.currentTier
                    ? { code: tr.currentTier.code }
                    : null,
                }))}
                workspaceId={workspaceId}
              />
            </div>
          ) : null}

          <div className="flex flex-col gap-1">
            <label
              htmlFor="ss-date"
              className="px-1 text-section uppercase tracking-wide text-text-color-secondary"
            >
              {t('sessions.sheet.whenLabel')}
            </label>
            <input
              id="ss-date"
              type="datetime-local"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              onBlur={() => void checkConflicts()}
              required
              className="min-h-tap rounded-md border-[0.5px] border-border-hairline bg-bg-primary px-3 text-body text-text-color-primary"
            />
            {conflicts &&
            (conflicts.coachConflicts.length > 0 ||
              conflicts.traineeConflicts.length > 0) ? (
              <div className="mt-1 rounded-md border-[0.5px] border-warning-text bg-warning-bg p-2">
                {conflicts.coachConflicts.length > 0 ? (
                  <p className="text-caption text-warning-text">
                    {t('sessions.conflicts.coach')}
                  </p>
                ) : null}
                {conflicts.traineeConflicts.length > 0 ? (
                  <p className="text-caption text-warning-text">
                    {t('sessions.conflicts.trainee', {
                      name:
                        conflicts.traineeConflicts[0]?.athlete.displayName ??
                        '—',
                    })}
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="flex flex-col gap-1">
            <span className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
              {t('sessions.sheet.durationLabel')}
            </span>
            <div className="flex flex-wrap gap-2">
              {DURATIONS.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDuration(d)}
                  className={
                    duration === d
                      ? 'bg-accent/10 rounded-full border-[0.5px] border-accent px-3 py-1 text-caption text-accent'
                      : 'rounded-full border-[0.5px] border-border-hairline bg-bg-primary px-3 py-1 text-caption text-text-color-secondary'
                  }
                >
                  {d}m
                </button>
              ))}
            </div>
          </div>

          <TextInput
            label={t('sessions.sheet.courtLabel')}
            value={court}
            onChange={(e) => setCourt(e.target.value)}
            placeholder="Court 1"
          />

          <div className="flex flex-col gap-1">
            <span className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
              {t('sessions.sheet.focusLabel')}
            </span>
            <div className="flex flex-wrap gap-2">
              {FOCUSES.map((f) => {
                const selected = focuses.includes(f);
                const atCap = !selected && focuses.length >= 4;
                return (
                  <button
                    key={f}
                    type="button"
                    onClick={() =>
                      setFocuses((prev) =>
                        prev.includes(f)
                          ? prev.filter((x) => x !== f)
                          : [...prev, f],
                      )
                    }
                    disabled={atCap}
                    className={
                      selected
                        ? 'bg-accent/10 rounded-full border-[0.5px] border-accent px-3 py-1 text-caption text-accent'
                        : 'rounded-full border-[0.5px] border-border-hairline bg-bg-primary px-3 py-1 text-caption text-text-color-secondary disabled:opacity-40'
                    }
                  >
                    {t(`sessionFocus.${f}`)}
                  </button>
                );
              })}
            </div>
            <p className="px-1 text-footnote text-text-color-tertiary">
              {t('sessions.sheet.focusHint')}
            </p>
          </div>

          <div className="flex flex-col gap-1">
            <label
              htmlFor="ss-notes"
              className="px-1 text-section uppercase tracking-wide text-text-color-secondary"
            >
              {t('sessions.sheet.notesLabel')}
            </label>
            <textarea
              id="ss-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={500}
              rows={2}
              placeholder={t('sessions.sheet.notesPlaceholder')}
              className="rounded-md border-[0.5px] border-border-hairline bg-bg-primary p-3 text-body text-text-color-primary"
            />
          </div>

          {error ? (
            <div className="rounded-md border-[0.5px] border-danger-text bg-danger-bg p-3">
              <p className="text-caption text-danger-text">{error}</p>
            </div>
          ) : null}
        </div>

        <footer className="flex flex-col gap-2 border-t-[0.5px] border-border-hairline px-4 py-3">
          <PrimaryButton type="submit" loading={loading}>
            {initial
              ? t('sessions.sheet.saveCta')
              : t('sessions.sheet.scheduleCta')}
          </PrimaryButton>
          <SecondaryButton type="button" onClick={onClose} disabled={loading}>
            {t('common.cancel')}
          </SecondaryButton>
        </footer>
      </form>
    </div>
  );
}

/** Convert a server ISO datetime (UTC) into the local form used by
 *  <input type="datetime-local">.  The input expects "YYYY-MM-DDTHH:MM"
 *  with no timezone. */
function toLocalInputValue(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
