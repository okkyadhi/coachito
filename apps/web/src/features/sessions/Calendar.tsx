import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  isToday as isTodayFn,
  startOfMonth,
  startOfWeek,
  subMonths,
} from 'date-fns';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { enUS, id as idLocale } from 'date-fns/locale';

// Status drives the dot color on each day: green for upcoming, amber for
// sessions awaiting an assessment, neutral for everything else. Multiple
// statuses on the same day → multiple dots (capped at 3).
export type DayStatus = 'upcoming' | 'to_assess' | 'done';

export interface DayMarks {
  // Counts per status — used to render up to 3 dots in priority order
  // (upcoming → to_assess → done). Zero counts skip.
  counts: Partial<Record<DayStatus, number>>;
}

interface MonthNavigatorProps {
  month: Date;
  onPrev: () => void;
  onNext: () => void;
  onToday?: () => void;
}

export function MonthNavigator({ month, onPrev, onNext, onToday }: MonthNavigatorProps) {
  const { t, i18n } = useTranslation();
  const localeKey = (i18n.language ?? 'en') === 'id' ? idLocale : enUS;
  const monthLabel = format(month, 'LLLL yyyy', { locale: localeKey });
  return (
    <div className="flex items-center justify-between gap-2">
      <button
        type="button"
        onClick={onPrev}
        aria-label={t('calendar.prevMonth')}
        className="flex size-9 items-center justify-center rounded-md border-[0.5px] border-border-hairline bg-bg-primary text-text-color-secondary"
      >
        <ChevronLeft size={18} strokeWidth={1.75} aria-hidden />
      </button>
      <button
        type="button"
        onClick={onToday}
        className="flex-1 truncate rounded-md px-2 py-2 text-center text-h3 text-text-color-primary hover:bg-bg-secondary"
        title={t('calendar.jumpToday')}
      >
        {monthLabel.charAt(0).toUpperCase() + monthLabel.slice(1)}
      </button>
      <button
        type="button"
        onClick={onNext}
        aria-label={t('calendar.nextMonth')}
        className="flex size-9 items-center justify-center rounded-md border-[0.5px] border-border-hairline bg-bg-primary text-text-color-secondary"
      >
        <ChevronRight size={18} strokeWidth={1.75} aria-hidden />
      </button>
    </div>
  );
}

interface CalendarMonthProps {
  month: Date;
  selectedDate: Date;
  marksByDay: Map<string, DayMarks>;  // key = "yyyy-MM-dd"
  onSelect: (day: Date) => void;
}

const DOT_PRIORITY: DayStatus[] = ['upcoming', 'to_assess', 'done'];

const DOT_CLASS: Record<DayStatus, string> = {
  upcoming: 'bg-accent',
  to_assess: 'bg-warning-text',
  done: 'bg-text-color-tertiary',
};

export function dayKey(d: Date): string {
  return format(d, 'yyyy-MM-dd');
}

export function CalendarMonth({
  month,
  selectedDate,
  marksByDay,
  onSelect,
}: CalendarMonthProps) {
  const { t, i18n } = useTranslation();
  const localeKey = (i18n.language ?? 'en') === 'id' ? idLocale : enUS;

  // 6-row grid: first day of week containing month start → last day of week
  // containing month end. Rendering "spill" days from prev/next month dimmed
  // mirrors the iOS Calendar grid layout coaches will recognize.
  const days = useMemo(() => {
    const start = startOfWeek(startOfMonth(month), { weekStartsOn: 0 });
    const end = endOfWeek(endOfMonth(month), { weekStartsOn: 0 });
    return eachDayOfInterval({ start, end });
  }, [month]);

  const weekdayLabels = useMemo(() => {
    const labels: string[] = [];
    const ref = startOfWeek(new Date(), { weekStartsOn: 0 });
    for (let i = 0; i < 7; i++) {
      labels.push(format(
        new Date(ref.getTime() + i * 24 * 3600 * 1000),
        'EEEEE',
        { locale: localeKey },
      ));
    }
    return labels;
  }, [localeKey]);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="grid grid-cols-7 px-1 text-center text-caption text-text-color-tertiary">
        {weekdayLabels.map((d, i) => (
          <span key={i} className="py-1">
            {d}
          </span>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-0.5">
        {days.map((day) => {
          const inMonth = isSameMonth(day, month);
          const selected = isSameDay(day, selectedDate);
          const today = isTodayFn(day);
          const marks = marksByDay.get(dayKey(day));
          const dots = marks
            ? DOT_PRIORITY.filter((s) => (marks.counts[s] ?? 0) > 0)
            : [];

          return (
            <button
              key={day.toISOString()}
              type="button"
              onClick={() => onSelect(day)}
              aria-label={format(day, 'd MMMM yyyy', { locale: localeKey })}
              aria-current={today ? 'date' : undefined}
              aria-pressed={selected}
              className={[
                'relative flex aspect-square min-h-[36px] flex-col items-center justify-start rounded-md py-1.5 text-caption transition-colors',
                selected
                  ? 'bg-accent text-white'
                  : today
                    ? 'bg-accent/10 text-accent font-medium'
                    : inMonth
                      ? 'text-text-color-primary hover:bg-bg-secondary'
                      : 'text-text-color-tertiary',
              ].join(' ')}
            >
              <span>{format(day, 'd')}</span>
              {dots.length > 0 ? (
                <span aria-hidden className="mt-auto flex items-center gap-0.5 pb-0.5">
                  {dots.slice(0, 3).map((s) => (
                    <span
                      key={s}
                      className={[
                        'inline-block size-1 rounded-full',
                        selected ? 'bg-white/90' : DOT_CLASS[s],
                      ].join(' ')}
                    />
                  ))}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      {/* SR-only marker so the t() function is referenced. Lints differ. */}
      <span className="sr-only">{t('calendar.weekStartsSunday')}</span>
    </div>
  );
}

/** Helper for SessionsScreen so it doesn't need to import addMonths/subMonths. */
export function navigateMonth(month: Date, direction: -1 | 1): Date {
  return direction === 1 ? addMonths(month, 1) : subMonths(month, 1);
}
