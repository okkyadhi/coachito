/**
 * Event detail.
 *
 * - `draft`     → roster + add-player + "Start event" CTA + cancel.
 * - `active`    → Courts | Leaderboard | Roster.  Courts shows each match
 *                 as a tap-to-score card (opens ScoreEntrySheet); also
 *                 surfaces resters, court rename, and reshuffle.
 * - `completed` → same Leaderboard, no edit, "Winner" pill on the top row.
 * - `cancelled` → bare summary, no controls.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, Pencil, Shuffle, Trophy, UserPlus, Users } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { api } from '@/lib/api';

import { ScoreEntrySheet } from './ScoreEntrySheet';
import {
  advanceRound,
  cancelEvent,
  completeEvent,
  courtDisplayName,
  extendRounds,
  getEvent,
  getLeaderboard,
  listRounds,
  recordScore,
  renameCourt,
  reshuffleCurrentRound,
  startEvent,
} from './events-api';
import type {
  EventDetail,
  LeaderboardRow,
  LeaderboardSort,
  Match,
  Round,
} from './events-types';

type LiveTab = 'courts' | 'leaderboard' | 'roster';

export function EventDetailScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { id } = useParams<{ id: string }>();

  const eventQ = useQuery({
    queryKey: ['events', 'detail', id],
    queryFn: () => getEvent(id!),
    enabled: !!id,
    staleTime: 10 * 1000,
  });

  if (eventQ.isPending || !eventQ.data) return <Skeleton />;
  const event = eventQ.data;

  return (
    <main className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 pb-8 pt-3">
      <header className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => navigate('/events')}
          aria-label={t('common.back')}
          className="-ml-2 flex size-9 items-center justify-center rounded-full text-text-color-secondary"
        >
          <ChevronLeft size={20} strokeWidth={1.75} aria-hidden />
        </button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-h2 text-text-color-primary">
            {event.title}
          </h1>
          {event.venue ? (
            <p className="text-caption text-text-color-secondary">
              {event.venue}
            </p>
          ) : null}
        </div>
        <StatusPill status={event.status} />
      </header>

      <section className="grid grid-cols-3 gap-2">
        <Stat
          icon={<Trophy size={14} strokeWidth={1.75} aria-hidden />}
          label={t(`events.format.${event.format}`)}
        />
        <Stat
          icon={<Users size={14} strokeWidth={1.75} aria-hidden />}
          label={t('events.players', { count: event.participantsCount })}
        />
        <Stat
          label={
            event.status === 'active' || event.status === 'completed'
              ? t('events.detail.roundOfTotal', {
                  n: event.currentRound,
                  m: event.totalRounds,
                })
              : t('events.courts', { count: event.courtCount })
          }
        />
      </section>

      {event.status === 'draft' ? (
        <DraftPanel event={event} eventId={id!} />
      ) : event.status === 'cancelled' ? (
        <p className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4 text-caption text-text-color-secondary">
          {t('events.detail.cancelledNote')}
        </p>
      ) : (
        <LivePanel event={event} eventId={id!} />
      )}

      {event.status === 'draft' || event.status === 'active' ? (
        <SecondaryButton
          onClick={async () => {
            await cancelEvent(id!);
            qc.invalidateQueries({ queryKey: ['events'] });
            navigate('/events');
          }}
        >
          {t('events.detail.cancelCta')}
        </SecondaryButton>
      ) : null}
    </main>
  );
}


// ── Draft state ────────────────────────────────────────────────────


function DraftPanel({ event, eventId }: { event: EventDetail; eventId: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [err, setErr] = useState<string | null>(null);

  const start = useMutation({
    mutationFn: () => startEvent(eventId),
    onSuccess: () => {
      setErr(null);
      qc.invalidateQueries({ queryKey: ['events'] });
    },
    onError: (e) =>
      setErr(e instanceof Error ? e.message : t('events.detail.startFailed')),
  });

  const canStart = event.participantsCount >= 4;

  return (
    <>
      <section className="flex flex-col gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
        <span className="text-section uppercase tracking-wide text-text-color-secondary">
          {t('events.detail.draftHint')}
        </span>
        <p className="text-caption text-text-color-secondary">
          {t('events.detail.draftBody')}
        </p>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {t('events.detail.rosterTitle')}
        </h2>
        <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
          {event.participants.length === 0 ? (
            <div className="flex flex-col items-center gap-1 p-6 text-center">
              <UserPlus
                size={18}
                strokeWidth={1.5}
                className="text-text-color-tertiary"
                aria-hidden
              />
              <p className="text-caption text-text-color-secondary">
                {t('events.detail.rosterEmpty')}
              </p>
            </div>
          ) : (
            event.participants.map((p, idx) => (
              <div
                key={p.id}
                className={[
                  'flex items-center justify-between p-4',
                  idx > 0 ? 'border-t-[0.5px] border-border-hairline' : '',
                ].join(' ')}
              >
                <span className="text-body text-text-color-primary">
                  {p.displayName}
                </span>
                {p.tag ? (
                  <span className="rounded-full border-[0.5px] border-border-hairline bg-bg-secondary px-2 py-0.5 text-pill text-text-color-secondary">
                    {p.tag}
                  </span>
                ) : null}
              </div>
            ))
          )}
        </div>
      </section>

      <AddPlayerForm eventId={eventId} />

      {err ? (
        <p className="px-1 text-footnote text-danger-text">{err}</p>
      ) : null}

      <PrimaryButton
        onClick={() => start.mutate()}
        disabled={!canStart || start.isPending}
      >
        {canStart
          ? t('events.detail.startCta')
          : t('events.detail.startNeedFour')}
      </PrimaryButton>
    </>
  );
}

function AddPlayerForm({ eventId }: { eventId: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [name, setName] = useState('');

  const add = useMutation({
    mutationFn: async (display: string) => {
      await api.post(`/events/${eventId}/participants`, {
        display_name: display,
      });
    },
    onSuccess: () => {
      setName('');
      qc.invalidateQueries({ queryKey: ['events', 'detail', eventId] });
    },
  });

  return (
    <section className="flex gap-2">
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder={t('events.detail.addPlaceholder')}
        className="flex-1 rounded-md border-[0.5px] border-border-hairline bg-bg-primary px-3 py-2 text-body text-text-color-primary placeholder:text-text-color-tertiary focus:outline-none"
      />
      <button
        type="button"
        onClick={() => name.trim() && add.mutate(name.trim())}
        disabled={!name.trim() || add.isPending}
        className="min-h-tap rounded-md bg-accent px-3 text-caption font-medium text-white disabled:opacity-60"
      >
        {t('events.detail.addCta')}
      </button>
    </section>
  );
}


// ── Live (active / completed) ──────────────────────────────────────


function LivePanel({ event, eventId }: { event: EventDetail; eventId: string }) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<LiveTab>('courts');
  const [sort, setSort] = useState<LeaderboardSort>(event.leaderboardSort);

  return (
    <>
      <div className="flex w-full overflow-hidden rounded-lg border-[0.5px] border-border-hairline">
        {(['courts', 'leaderboard', 'roster'] as LiveTab[]).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setTab(v)}
            className={[
              'flex-1 px-3 py-2 text-caption font-medium transition-colors',
              tab === v
                ? 'bg-accent text-white'
                : 'bg-bg-primary text-text-color-secondary',
            ].join(' ')}
          >
            {t(`events.tabs.${v}`)}
          </button>
        ))}
      </div>

      {tab === 'courts' ? (
        <CourtsTab event={event} eventId={eventId} />
      ) : tab === 'leaderboard' ? (
        <LeaderboardTab eventId={eventId} sort={sort} onSortChange={setSort} />
      ) : (
        <RosterTab event={event} />
      )}
    </>
  );
}

function CourtsTab({
  event,
  eventId,
}: {
  event: EventDetail;
  eventId: string;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const roundsQ = useQuery({
    queryKey: ['events', eventId, 'rounds'],
    queryFn: () => listRounds(eventId),
    staleTime: 5 * 1000,
  });

  const advance = useMutation({
    mutationFn: () => advanceRound(eventId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['events', 'detail', eventId] });
      qc.invalidateQueries({ queryKey: ['events', eventId, 'rounds'] });
      qc.invalidateQueries({ queryKey: ['events', eventId, 'leaderboard'] });
    },
  });
  const complete = useMutation({
    mutationFn: () => completeEvent(eventId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['events', 'detail', eventId] });
      qc.invalidateQueries({ queryKey: ['events', eventId, 'rounds'] });
    },
  });
  const reshuffle = useMutation({
    mutationFn: () => reshuffleCurrentRound(eventId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['events', 'detail', eventId] });
      qc.invalidateQueries({ queryKey: ['events', eventId, 'rounds'] });
    },
  });
  const extend = useMutation({
    mutationFn: () => extendRounds(eventId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['events', 'detail', eventId] });
      qc.invalidateQueries({ queryKey: ['events', eventId, 'rounds'] });
      qc.invalidateQueries({ queryKey: ['events', eventId, 'leaderboard'] });
    },
  });

  const [sheetMatch, setSheetMatch] = useState<Match | null>(null);

  if (roundsQ.isPending || !roundsQ.data) {
    return <div className="h-40 rounded-xl bg-bg-primary" />;
  }

  const currentRound: Round | undefined = roundsQ.data.find(
    (r) => r.roundNumber === event.currentRound,
  );

  if (!currentRound) {
    return (
      <p className="rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4 text-caption text-text-color-secondary">
        {t('events.detail.noActiveRound')}
      </p>
    );
  }

  const allScored = currentRound.matches.every(
    (m) => m.scoreA !== null && m.scoreB !== null,
  );
  const anyScored = currentRound.matches.some(
    (m) => m.scoreA !== null && m.scoreB !== null,
  );
  const isFinalRound = event.currentRound >= event.totalRounds;
  const isLive = event.status === 'active';

  const nameById = new Map<string, string>(
    event.participants.map((p) => [p.id, p.displayName]),
  );

  const playingIds = new Set<string>();
  for (const m of currentRound.matches) {
    for (const pid of m.sideA) playingIds.add(pid);
    for (const pid of m.sideB) playingIds.add(pid);
  }
  const resters = event.participants.filter(
    (p) => !playingIds.has(p.id) && p.withdrewRound == null,
  );

  const onSheetSubmit = async (sa: number, sb: number) => {
    if (!sheetMatch) return;
    await recordScore(eventId, sheetMatch.id, {
      scoreA: sa,
      scoreB: sb,
      clientRecordedAt: new Date().toISOString(),
    });
    qc.invalidateQueries({ queryKey: ['events', eventId, 'rounds'] });
    qc.invalidateQueries({ queryKey: ['events', eventId, 'leaderboard'] });
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between px-1">
        <p className="text-section uppercase tracking-wide text-text-color-secondary">
          {t('events.detail.roundLabel', {
            n: event.currentRound,
            m: event.totalRounds,
          })}
        </p>
        {isLive && !anyScored ? (
          <button
            type="button"
            onClick={() => {
              if (window.confirm(t('events.detail.reshuffleConfirm'))) {
                reshuffle.mutate();
              }
            }}
            disabled={reshuffle.isPending}
            className="flex items-center gap-1 rounded-full border-[0.5px] border-border-hairline bg-bg-primary px-2.5 py-1 text-footnote text-text-color-secondary disabled:opacity-60"
          >
            <Shuffle size={12} strokeWidth={1.75} aria-hidden />
            {t('events.detail.reshuffleCta')}
          </button>
        ) : null}
      </div>

      {currentRound.matches.map((m) => (
        <CourtCard
          key={m.id}
          match={m}
          event={event}
          nameById={nameById}
          locked={!isLive}
          onTap={() => isLive && setSheetMatch(m)}
        />
      ))}

      {isLive ? (
        <RestersCard event={event} resters={resters} />
      ) : null}

      {isLive ? (
        isFinalRound ? (
          <div className="flex flex-col gap-2">
            <PrimaryButton
              onClick={() => complete.mutate()}
              disabled={!allScored || complete.isPending}
            >
              {t('events.detail.completeCta')}
            </PrimaryButton>
            {event.format === 'americano' ? (
              <SecondaryButton
                onClick={() => extend.mutate()}
                disabled={!allScored || extend.isPending}
              >
                {t('events.detail.extendRoundsCta')}
              </SecondaryButton>
            ) : null}
          </div>
        ) : (
          <PrimaryButton
            onClick={() => advance.mutate()}
            disabled={!allScored || advance.isPending}
          >
            {allScored
              ? t('events.detail.nextRoundCta')
              : t('events.detail.scoreAllFirst')}
          </PrimaryButton>
        )
      ) : null}

      <ScoreEntrySheet
        open={sheetMatch !== null}
        match={sheetMatch}
        event={event}
        nameA={
          sheetMatch
            ? sideLabel(sheetMatch.sideA, nameById)
            : ''
        }
        nameB={
          sheetMatch
            ? sideLabel(sheetMatch.sideB, nameById)
            : ''
        }
        onClose={() => setSheetMatch(null)}
        onSubmit={onSheetSubmit}
      />
    </div>
  );
}

function sideLabel(ids: string[], nameById: Map<string, string>): string {
  return ids.map((id) => nameById.get(id) ?? '—').join(' & ');
}

function CourtCard({
  match,
  event,
  nameById,
  locked,
  onTap,
}: {
  match: Match;
  event: EventDetail;
  nameById: Map<string, string>;
  locked: boolean;
  onTap: () => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [renaming, setRenaming] = useState(false);
  const [draftName, setDraftName] = useState('');

  const courtLabel = courtDisplayName(
    match.courtNumber,
    event.courtNames,
    (n) => t('events.detail.courtN', { n }),
  );

  const rename = useMutation({
    mutationFn: (name: string | null) =>
      renameCourt(event.id, match.courtNumber, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['events', 'detail', event.id] });
      setRenaming(false);
    },
  });

  const nameA = sideLabel(match.sideA, nameById);
  const nameB = sideLabel(match.sideB, nameById);

  const scored = match.scoreA !== null && match.scoreB !== null;
  const winnerA = match.winnerSide === 'A';
  const winnerB = match.winnerSide === 'B';

  return (
    <div className="flex flex-col overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
      <div className="bg-cream/50 flex items-center justify-between border-b-[0.5px] border-border-hairline px-4 py-2">
        {renaming ? (
          <div className="flex flex-1 items-center gap-2">
            <input
              type="text"
              value={draftName}
              autoFocus
              onChange={(e) => setDraftName(e.target.value)}
              maxLength={40}
              placeholder={t('events.detail.renameCourtPlaceholder')}
              className="flex-1 rounded-md border-[0.5px] border-border-hairline bg-bg-primary px-2 py-1 text-caption text-text-color-primary focus:outline-none"
            />
            <button
              type="button"
              onClick={() => rename.mutate(draftName.trim() || null)}
              disabled={rename.isPending}
              className="rounded-md bg-accent px-2 py-1 text-footnote font-medium text-white"
            >
              {t('events.detail.renameSave')}
            </button>
            <button
              type="button"
              onClick={() => setRenaming(false)}
              className="text-footnote text-text-color-secondary"
            >
              {t('common.cancel')}
            </button>
          </div>
        ) : (
          <>
            <span className="text-section uppercase tracking-wide text-text-color-primary">
              {courtLabel}
            </span>
            <div className="flex items-center gap-2">
              {!locked ? (
                <button
                  type="button"
                  aria-label={t('events.detail.renameCourt')}
                  onClick={(e) => {
                    e.stopPropagation();
                    setDraftName(
                      event.courtNames[match.courtNumber - 1] ?? '',
                    );
                    setRenaming(true);
                  }}
                  className="text-text-color-tertiary"
                >
                  <Pencil size={13} strokeWidth={1.75} aria-hidden />
                </button>
              ) : null}
              <span className="text-footnote text-text-color-tertiary">
                {scored
                  ? t('events.detail.scored')
                  : t('events.detail.notStarted')}
              </span>
            </div>
          </>
        )}
      </div>

      <button
        type="button"
        onClick={onTap}
        disabled={locked}
        className="flex w-full flex-col gap-2 px-4 py-3 text-left disabled:cursor-default"
      >
        <SideRow
          name={nameA}
          score={match.scoreA}
          winner={winnerA}
          scored={scored}
        />
        <SideRow
          name={nameB}
          score={match.scoreB}
          winner={winnerB}
          scored={scored}
        />
        {!locked && !scored ? (
          <span className="mt-1 text-footnote text-text-color-tertiary">
            {t('events.detail.tapToScore')}
          </span>
        ) : null}
      </button>
    </div>
  );
}

function SideRow({
  name,
  score,
  winner,
  scored,
}: {
  name: string;
  score: number | null;
  winner: boolean;
  scored: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <p
        className={[
          'min-w-0 flex-1 truncate text-body',
          winner ? 'font-medium text-text-color-primary' : 'text-text-color-secondary',
        ].join(' ')}
      >
        {name}
      </p>
      <span
        className={[
          'flex h-9 min-w-[2.5rem] items-center justify-center rounded-md px-2 text-body font-medium tabular-nums',
          scored
            ? winner
              ? 'bg-ink text-cream'
              : 'bg-bg-secondary text-text-color-primary'
            : 'border-[0.5px] border-border-hairline bg-bg-primary text-text-color-tertiary',
        ].join(' ')}
      >
        {score == null ? '—' : score}
      </span>
    </div>
  );
}

function RestersCard({
  event,
  resters,
}: {
  event: EventDetail;
  resters: EventDetail['participants'];
}) {
  const { t } = useTranslation();
  if (event.participants.length <= 0) return null;
  return (
    <div className="flex flex-col gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
      <span className="text-section uppercase tracking-wide text-text-color-secondary">
        {t('events.detail.restingTitle')}
      </span>
      {resters.length === 0 ? (
        <p className="text-caption text-text-color-tertiary">
          {t('events.detail.restingNone')}
        </p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {resters.map((p) => (
            <span
              key={p.id}
              className="rounded-full border-[0.5px] border-border-hairline bg-bg-secondary px-2 py-0.5 text-pill text-text-color-primary"
            >
              {p.displayName}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function LeaderboardTab({
  eventId,
  sort,
  onSortChange,
}: {
  eventId: string;
  sort: LeaderboardSort;
  onSortChange: (s: LeaderboardSort) => void;
}) {
  const { t } = useTranslation();
  const lb = useQuery({
    queryKey: ['events', eventId, 'leaderboard', sort],
    queryFn: () => getLeaderboard(eventId, sort),
    staleTime: 5 * 1000,
  });

  return (
    <div className="flex flex-col gap-3">
      <div className="flex w-full overflow-hidden rounded-lg border-[0.5px] border-border-hairline">
        {(['points', 'wins'] as LeaderboardSort[]).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => onSortChange(v)}
            className={[
              'flex-1 px-3 py-2 text-caption font-medium transition-colors',
              sort === v
                ? 'bg-accent text-white'
                : 'bg-bg-primary text-text-color-secondary',
            ].join(' ')}
          >
            {t(`events.sort.${v}`)}
          </button>
        ))}
      </div>
      <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        {lb.isPending || !lb.data ? (
          <div className="h-24" />
        ) : lb.data.rows.length === 0 ? (
          <p className="p-6 text-center text-caption text-text-color-secondary">
            {t('events.detail.leaderboardEmpty')}
          </p>
        ) : (
          <>
            <LeaderboardHeader sort={sort} />
            {lb.data.rows.map((row, idx) => (
              <LeaderboardRowView
                key={row.participantId}
                row={row}
                rank={idx + 1}
                sort={sort}
              />
            ))}
          </>
        )}
      </div>
    </div>
  );
}

function LeaderboardHeader({ sort }: { sort: LeaderboardSort }) {
  const { t } = useTranslation();
  return (
    <div className="bg-cream/50 grid grid-cols-[1.5rem_minmax(0,1fr)_1.5rem_2.75rem_2.25rem_2rem_2rem] items-center gap-1 border-b-[0.5px] border-border-hairline px-3 py-2 text-pill uppercase tracking-wide text-text-color-tertiary">
      <span />
      <span />
      <span className="text-center">{t('events.detail.lbColG')}</span>
      <span className="text-center">
        {t('events.detail.lbColW')}-{t('events.detail.lbColL')}-{t('events.detail.lbColT')}
      </span>
      <span className="text-center">{t('events.detail.lbColDiff')}</span>
      <span className="text-center">{t('events.detail.lbColComp')}</span>
      <span className="text-center font-medium text-text-color-secondary">
        {sort === 'points'
          ? t('events.detail.lbColPts')
          : t('events.detail.lbColW')}
      </span>
    </div>
  );
}

function LeaderboardRowView({
  row,
  rank,
  sort,
}: {
  row: LeaderboardRow;
  rank: number;
  sort: LeaderboardSort;
}) {
  const isTop = rank === 1;
  const diffStr = row.pointDiff > 0 ? `+${row.pointDiff}` : `${row.pointDiff}`;
  const compStr = row.compensation > 0 ? `+${row.compensation}` : '0';
  return (
    <div
      className={[
        'grid grid-cols-[1.5rem_minmax(0,1fr)_1.5rem_2.75rem_2.25rem_2rem_2rem] items-center gap-1 border-t-[0.5px] border-border-hairline px-3 py-2.5',
        isTop ? 'bg-accent-bg' : '',
      ].join(' ')}
    >
      <span
        className={[
          'text-center text-caption font-medium tabular-nums',
          isTop ? 'text-accent' : 'text-text-color-tertiary',
        ].join(' ')}
      >
        {rank}
      </span>
      <span
        className={[
          'min-w-0 truncate text-body',
          isTop ? 'font-medium text-accent' : 'text-text-color-primary',
        ].join(' ')}
      >
        {row.displayName}
      </span>
      <span className="text-center text-caption tabular-nums text-text-color-secondary">
        {row.matchesPlayed}
      </span>
      <span className="text-center text-caption tabular-nums text-text-color-secondary">
        {row.wins}-{row.losses}-{row.ties}
      </span>
      <span
        className={[
          'text-center text-caption tabular-nums',
          row.pointDiff > 0
            ? 'text-success-text'
            : row.pointDiff < 0
              ? 'text-danger-text'
              : 'text-text-color-tertiary',
        ].join(' ')}
      >
        {diffStr}
      </span>
      <span className="text-center text-caption tabular-nums text-text-color-tertiary">
        {compStr}
      </span>
      <span className="text-center text-body font-medium tabular-nums text-text-color-primary">
        {sort === 'points' ? row.points : row.wins}
      </span>
    </div>
  );
}

function RosterTab({ event }: { event: EventDetail }) {
  const { t } = useTranslation();
  return (
    <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
      {event.participants.length === 0 ? (
        <p className="p-6 text-center text-caption text-text-color-secondary">
          {t('events.detail.rosterEmpty')}
        </p>
      ) : (
        event.participants.map((p, idx) => (
          <div
            key={p.id}
            className={[
              'flex items-center justify-between p-4',
              idx > 0 ? 'border-t-[0.5px] border-border-hairline' : '',
            ].join(' ')}
          >
            <span className="text-body text-text-color-primary">
              {p.displayName}
            </span>
            {p.withdrewRound ? (
              <span className="text-footnote text-text-color-tertiary">
                {t('events.detail.withdrewAt', { n: p.withdrewRound })}
              </span>
            ) : null}
          </div>
        ))
      )}
    </div>
  );
}


// ── Tiny presentational helpers ────────────────────────────────────


function Stat({
  icon,
  label,
}: {
  icon?: React.ReactNode;
  label: string;
}) {
  return (
    <div className="flex items-center justify-center gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3">
      {icon ? <span className="text-text-color-tertiary">{icon}</span> : null}
      <span className="truncate text-caption text-text-color-secondary">
        {label}
      </span>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const { t } = useTranslation();
  return (
    <span
      className={[
        'shrink-0 rounded-full px-2 py-0.5 text-pill font-medium',
        status === 'active'
          ? 'bg-accent text-white'
          : status === 'completed'
            ? 'bg-success-bg text-success-text'
            : status === 'cancelled'
              ? 'bg-danger-bg text-danger-text'
              : 'bg-bg-secondary text-text-color-secondary',
      ].join(' ')}
    >
      {t(`events.statusPill.${status}`)}
    </span>
  );
}

function Skeleton() {
  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-3 px-4 pt-6">
      <div className="h-8 w-48 rounded bg-bg-primary" />
      <div className="h-16 rounded-xl bg-bg-primary" />
      <div className="h-40 rounded-xl bg-bg-primary" />
    </div>
  );
}
