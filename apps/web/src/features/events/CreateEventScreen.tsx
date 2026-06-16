/**
 * Create Event — Phase 1 stops at Step 1 (Format).  Tapping "Continue"
 * persists the draft via POST /events and lands on the event detail
 * screen, where Step 2 (Roster) will live once it's built in a later
 * phase.  Docs/20 §12.2.
 */

import { useMutation } from '@tanstack/react-query';
import { ChevronLeft, Loader2 } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { PrimaryButton } from '@/components/PrimaryButton';

import { createEvent } from './events-api';
import {
  FORMATS,
  type EventFamily,
  type EventFormat,
  type LeaderboardSort,
  type MexicanoPairing,
  type ScoringMode,
  MEXICANO_FAMILY,
} from './events-types';

// Pairing engine ships in phases; team variants + Mix come later.  The
// picker shows everything but disables formats whose pairing engine
// isn't wired up yet — keeps the surface honest without hiding the
// roadmap from the host.
const SUPPORTED_FORMATS: ReadonlySet<EventFormat> = new Set<EventFormat>([
  'americano',
  'mexicano',
  'koth',
]);

const FAMILIES: { family: EventFamily }[] = [
  { family: 'americano' },
  { family: 'mexicano' },
  { family: 'koth' },
];

const POINT_TARGETS = [16, 21, 24, 32] as const;

export function CreateEventScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [title, setTitle] = useState('');
  const [venue, setVenue] = useState('');
  const [family, setFamily] = useState<EventFamily>('americano');
  const [format, setFormat] = useState<EventFormat>('americano');
  const [scoringMode, setScoringMode] = useState<ScoringMode>('point');
  const [scoringTarget, setScoringTarget] = useState<number | null>(21);
  const [courtCount, setCourtCount] = useState(2);
  const [mexicanoPairing, setMexicanoPairing] = useState<MexicanoPairing>('1_3_vs_2_4');
  const [leaderboardSort, setLeaderboardSort] = useState<LeaderboardSort>('points');

  const variantsForFamily = useMemo(
    () => FORMATS.filter((f) => f.family === family),
    [family],
  );

  // When the family changes, land on the first SUPPORTED variant so the
  // host doesn't get stuck on a "soon" disabled row.
  const pickFamily = (next: EventFamily) => {
    if (next === family) return;
    setFamily(next);
    const first =
      FORMATS.find((f) => f.family === next && SUPPORTED_FORMATS.has(f.format))
      ?? FORMATS.find((f) => f.family === next)!;
    setFormat(first.format);
  };

  const isMexicanoLike = MEXICANO_FAMILY.has(format);

  const create = useMutation({
    mutationFn: () =>
      createEvent({
        title: title.trim(),
        venue: venue.trim() || null,
        format,
        scoringMode,
        scoringTarget: scoringMode === 'point' ? scoringTarget : null,
        courtCount,
        mexicanoPairing: isMexicanoLike ? mexicanoPairing : null,
        leaderboardSort,
        isPublic: true,
      }),
    onSuccess: (event) => {
      navigate(`/events/${event.id}`, { replace: true });
    },
  });

  const canSubmit = title.trim().length > 0 && !create.isPending;

  return (
    <main className="mx-auto flex w-full max-w-md flex-col gap-5 px-4 pb-8 pt-3">
      <header className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => navigate('/events')}
          aria-label={t('common.back')}
          className="-ml-2 flex size-9 items-center justify-center rounded-full text-text-color-secondary"
        >
          <ChevronLeft size={20} strokeWidth={1.75} aria-hidden />
        </button>
        <h1 className="text-h2 text-text-color-primary">
          {t('events.create.title')}
        </h1>
      </header>

      {/* Title + venue */}
      <section className="flex flex-col gap-2">
        <label className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {t('events.create.basicsTitle')}
        </label>
        <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={t('events.create.titlePlaceholder')}
            className="w-full p-3 text-body text-text-color-primary placeholder:text-text-color-tertiary focus:outline-none"
            maxLength={120}
          />
          <input
            type="text"
            value={venue}
            onChange={(e) => setVenue(e.target.value)}
            placeholder={t('events.create.venuePlaceholder')}
            className="w-full border-t-[0.5px] border-border-hairline p-3 text-body text-text-color-primary placeholder:text-text-color-tertiary focus:outline-none"
            maxLength={200}
          />
        </div>
      </section>

      {/* Format family + variant */}
      <section className="flex flex-col gap-2">
        <label className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {t('events.create.formatTitle')}
        </label>
        <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
          <Segmented
            options={FAMILIES.map((f) => ({
              value: f.family,
              label: t(`events.family.${f.family}`),
            }))}
            value={family}
            onChange={(v) => pickFamily(v as EventFamily)}
          />
          <div className="border-t-[0.5px] border-border-hairline">
            {variantsForFamily.map((v, idx) => {
              const supported = SUPPORTED_FORMATS.has(v.format);
              return (
                <button
                  key={v.format}
                  type="button"
                  onClick={() => supported && setFormat(v.format)}
                  disabled={!supported}
                  className={[
                    'flex w-full min-h-tap items-center justify-between gap-3 px-4 py-3 text-left',
                    idx > 0 ? 'border-t-[0.5px] border-border-hairline' : '',
                    format === v.format ? 'bg-accent-bg' : '',
                    !supported ? 'opacity-50' : '',
                  ].join(' ')}
                >
                  <span className="flex-1 text-body text-text-color-primary">
                    {t(`events.format.${v.format}`)}
                  </span>
                  <span className="flex flex-wrap gap-1">
                    {v.isTeam ? (
                      <FormatChip label={t('events.tagTeam')} />
                    ) : null}
                    {v.isMix ? (
                      <FormatChip label={t('events.tagMix')} />
                    ) : null}
                    {!supported ? (
                      <FormatChip label={t('events.tagSoon')} />
                    ) : null}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* Scoring */}
      <section className="flex flex-col gap-2">
        <label className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {t('events.create.scoringTitle')}
        </label>
        <div className="flex flex-col gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3">
          <Segmented
            options={[
              { value: 'point', label: t('events.scoring.point') },
              { value: 'normal_first_to', label: t('events.scoring.firstTo') },
              { value: 'normal_total', label: t('events.scoring.totalOf') },
            ]}
            value={scoringMode}
            onChange={(v) => setScoringMode(v as ScoringMode)}
          />
          {scoringMode === 'point' ? (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {POINT_TARGETS.map((n) => (
                <TargetChip
                  key={n}
                  label={String(n)}
                  active={scoringTarget === n}
                  onClick={() => setScoringTarget(n)}
                />
              ))}
              <TargetChip
                label={t('events.scoring.untimed')}
                active={scoringTarget === null}
                onClick={() => setScoringTarget(null)}
              />
            </div>
          ) : (
            <p className="text-footnote text-text-color-tertiary">
              {t('events.create.scoringHint')}
            </p>
          )}
        </div>
      </section>

      {/* Courts */}
      <section className="flex flex-col gap-2">
        <label className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {t('events.create.courtsTitle')}
        </label>
        <div className="flex items-center justify-between rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
          <span className="text-body text-text-color-primary">
            {t('events.courts', { count: courtCount })}
          </span>
          <Stepper
            value={courtCount}
            min={1}
            max={20}
            onChange={setCourtCount}
          />
        </div>
      </section>

      {/* Mexicano pairing (only when relevant) */}
      {isMexicanoLike && format !== 'team_mexicano' ? (
        <section className="flex flex-col gap-2">
          <label className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
            {t('events.create.pairingTitle')}
          </label>
          <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3">
            <Segmented
              options={[
                { value: '1_3_vs_2_4', label: '1-3 vs 2-4' },
                { value: '1_4_vs_2_3', label: '1-4 vs 2-3' },
              ]}
              value={mexicanoPairing}
              onChange={(v) => setMexicanoPairing(v as MexicanoPairing)}
            />
          </div>
        </section>
      ) : null}

      {/* Leaderboard sort */}
      <section className="flex flex-col gap-2">
        <label className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {t('events.create.sortTitle')}
        </label>
        <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-3">
          <Segmented
            options={[
              { value: 'points', label: t('events.sort.points') },
              { value: 'wins', label: t('events.sort.wins') },
            ]}
            value={leaderboardSort}
            onChange={(v) => setLeaderboardSort(v as LeaderboardSort)}
          />
        </div>
      </section>

      {create.isError ? (
        <p className="px-1 text-footnote text-danger-text">
          {t('events.create.failed')}
        </p>
      ) : null}

      <PrimaryButton
        onClick={() => create.mutate()}
        disabled={!canSubmit}
        leftIcon={
          create.isPending ? (
            <Loader2 size={18} className="animate-spin" aria-hidden />
          ) : undefined
        }
      >
        {t('events.create.continue')}
      </PrimaryButton>
    </main>
  );
}

// ── Tiny presentational helpers ───────────────────────────────────

function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex w-full overflow-hidden rounded-lg border-[0.5px] border-border-hairline">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={[
            'flex-1 px-3 py-2 text-caption font-medium transition-colors',
            value === o.value
              ? 'bg-accent text-white'
              : 'bg-bg-primary text-text-color-secondary',
          ].join(' ')}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function TargetChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'rounded-full border-[0.5px] px-3 py-1 text-pill font-medium',
        active
          ? 'border-accent bg-accent-bg text-accent'
          : 'border-border-hairline bg-bg-primary text-text-color-secondary',
      ].join(' ')}
    >
      {label}
    </button>
  );
}

function FormatChip({ label }: { label: string }) {
  return (
    <span className="rounded-full border-[0.5px] border-border-hairline bg-bg-secondary px-2 py-0.5 text-pill text-text-color-secondary">
      {label}
    </span>
  );
}

function Stepper({
  value,
  min,
  max,
  onChange,
}: {
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={() => onChange(Math.max(min, value - 1))}
        disabled={value <= min}
        className="flex size-8 items-center justify-center rounded-full border-[0.5px] border-border-hairline bg-bg-primary text-text-color-secondary disabled:opacity-40"
      >
        −
      </button>
      <span className="w-8 text-center text-body font-medium tabular-nums text-text-color-primary">
        {value}
      </span>
      <button
        type="button"
        onClick={() => onChange(Math.min(max, value + 1))}
        disabled={value >= max}
        className="flex size-8 items-center justify-center rounded-full border-[0.5px] border-border-hairline bg-bg-primary text-text-color-secondary disabled:opacity-40"
      >
        +
      </button>
    </div>
  );
}
