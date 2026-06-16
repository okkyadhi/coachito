import { Check, ChevronDown, UserPlus } from 'lucide-react';
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { TierPill, type TierCode } from './TierPill';

export interface ComboboxTrainee {
  id: string;
  displayName: string;
  currentTier: { code: TierCode } | null;
}

interface Props {
  value: string | null;
  onChange: (id: string) => void;
  trainees: ComboboxTrainee[];
  workspaceId: string | null;
  placeholder?: string;
  disabled?: boolean;
}

const RECENT_KEY_PREFIX = 'recent-trainees:';
const RECENT_MAX = 5;

function getRecent(workspaceId: string | null): string[] {
  if (!workspaceId) return [];
  try {
    const raw = window.localStorage.getItem(RECENT_KEY_PREFIX + workspaceId);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((x): x is string => typeof x === 'string');
  } catch {
    return [];
  }
}

export function rememberRecentTrainee(
  workspaceId: string | null,
  traineeId: string,
): void {
  if (!workspaceId) return;
  const cur = getRecent(workspaceId).filter((id) => id !== traineeId);
  cur.unshift(traineeId);
  try {
    window.localStorage.setItem(
      RECENT_KEY_PREFIX + workspaceId,
      JSON.stringify(cur.slice(0, RECENT_MAX)),
    );
  } catch {
    /* quota / private mode — best effort */
  }
}

/** Accent-strip + lowercase for forgiving search. */
function normalize(s: string): string {
  return s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();
}

export function TraineeCombobox({
  value,
  onChange,
  trainees,
  workspaceId,
  placeholder,
  disabled,
}: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIdx, setActiveIdx] = useState(0);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  const selected = useMemo(
    () => trainees.find((t) => t.id === value) ?? null,
    [trainees, value],
  );

  // `open` is included so the recent list re-reads from localStorage when
  // the popover opens (other instances may have updated it).  Suppress the
  // exhaustive-deps warning since that's intentional, not a missing dep.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const recentIds = useMemo(() => getRecent(workspaceId), [workspaceId, open]);

  const filtered = useMemo(() => {
    if (!query.trim()) {
      const recent = recentIds
        .map((id) => trainees.find((t) => t.id === id))
        .filter((t): t is ComboboxTrainee => !!t);
      const rest = trainees.filter((t) => !recentIds.includes(t.id));
      return { recent, rest };
    }
    const q = normalize(query);
    const matches = trainees.filter((t) =>
      normalize(t.displayName).includes(q),
    );
    return { recent: [], rest: matches };
  }, [trainees, query, recentIds]);

  const flat = useMemo(
    () => [...filtered.recent, ...filtered.rest],
    [filtered],
  );

  // Reset active index when the visible list shifts.
  useEffect(() => {
    setActiveIdx(0);
  }, [query, open]);

  // Click-outside.
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (popoverRef.current?.contains(e.target as Node)) return;
      if (triggerRef.current?.contains(e.target as Node)) return;
      setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  // Autofocus input when opened.
  useEffect(() => {
    if (open) {
      // queueMicrotask so the input is mounted.
      queueMicrotask(() => inputRef.current?.focus());
    }
  }, [open]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!open) {
        if (e.key === 'Enter' || e.key === 'ArrowDown' || e.key === ' ') {
          e.preventDefault();
          setOpen(true);
        }
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setOpen(false);
        triggerRef.current?.focus();
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIdx((i) => Math.min(i + 1, flat.length - 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIdx((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        const pick = flat[activeIdx];
        if (pick) {
          onChange(pick.id);
          rememberRecentTrainee(workspaceId, pick.id);
          setOpen(false);
          triggerRef.current?.focus();
        }
      }
    },
    [activeIdx, flat, onChange, open, workspaceId],
  );

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setOpen((v) => !v)}
        onKeyDown={handleKeyDown}
        className="flex min-h-tap w-full items-center justify-between rounded-md border-[0.5px] border-border-hairline bg-bg-primary px-3 text-left text-body text-text-color-primary focus:border-accent focus:outline-none disabled:opacity-60"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className={selected ? '' : 'text-text-color-tertiary'}>
          {selected
            ? selected.displayName
            : (placeholder ?? t('sessions.sheet.athletePick'))}
        </span>
        <ChevronDown
          size={14}
          strokeWidth={1.75}
          aria-hidden
          className="text-text-color-tertiary"
        />
      </button>

      {open ? (
        <div
          ref={popoverRef}
          role="listbox"
          className="absolute inset-x-0 top-[calc(100%+4px)] z-50 max-h-[280px] overflow-hidden rounded-md border-[0.5px] border-border-hairline bg-bg-primary"
        >
          <div className="border-b-[0.5px] border-border-hairline p-2">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                placeholder ?? t('sessions.sheet.athletePlaceholder')
              }
              className="w-full rounded-md bg-bg-secondary px-3 py-2 text-body text-text-color-primary focus:outline-none"
            />
          </div>
          <div className="max-h-[220px] overflow-y-auto">
            {flat.length === 0 ? (
              <div className="flex flex-col items-center gap-2 p-4 text-center">
                <p className="text-caption text-text-color-secondary">
                  {t('sessions.sheet.athleteEmpty')}
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    navigate('/trainees/new');
                  }}
                  className="inline-flex items-center gap-1 text-caption text-accent"
                >
                  <UserPlus size={14} strokeWidth={1.75} aria-hidden />
                  {t('sessions.sheet.athleteAddNew')}
                </button>
              </div>
            ) : (
              <ul className="py-1">
                {filtered.recent.length > 0 ? (
                  <li className="px-3 py-1 text-section uppercase tracking-wide text-text-color-tertiary">
                    {t('sessions.sheet.athleteRecent')}
                  </li>
                ) : null}
                {filtered.recent.map((trainee, i) => (
                  <Row
                    key={trainee.id}
                    trainee={trainee}
                    selected={trainee.id === value}
                    active={i === activeIdx}
                    onPick={() => {
                      onChange(trainee.id);
                      rememberRecentTrainee(workspaceId, trainee.id);
                      setOpen(false);
                      triggerRef.current?.focus();
                    }}
                  />
                ))}
                {filtered.recent.length > 0 && filtered.rest.length > 0 ? (
                  <li className="my-1 border-t-[0.5px] border-border-hairline" />
                ) : null}
                {filtered.rest.map((trainee, i) => {
                  const idx = filtered.recent.length + i;
                  return (
                    <Row
                      key={trainee.id}
                      trainee={trainee}
                      selected={trainee.id === value}
                      active={idx === activeIdx}
                      onPick={() => {
                        onChange(trainee.id);
                        rememberRecentTrainee(workspaceId, trainee.id);
                        setOpen(false);
                        triggerRef.current?.focus();
                      }}
                    />
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

interface RowProps {
  trainee: ComboboxTrainee;
  selected: boolean;
  active: boolean;
  onPick: () => void;
}

function Row({ trainee, selected, active, onPick }: RowProps) {
  return (
    <li>
      <button
        type="button"
        onClick={onPick}
        onMouseEnter={() => {
          /* visual hover already handled by Tailwind */
        }}
        className={
          active
            ? 'flex w-full items-center gap-2 bg-bg-secondary px-3 py-2 text-left'
            : 'flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-bg-secondary'
        }
      >
        <span className="flex-1 truncate text-body text-text-color-primary">
          {trainee.displayName}
        </span>
        {trainee.currentTier ? (
          <TierPill tier={trainee.currentTier.code} />
        ) : null}
        {selected ? (
          <Check
            size={14}
            strokeWidth={1.75}
            aria-hidden
            className="text-accent"
          />
        ) : null}
      </button>
    </li>
  );
}
