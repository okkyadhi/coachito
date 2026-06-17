import { format } from 'date-fns';
import { enUS, id as idLocale } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';

import { Avatar } from '@/components/Avatar';

import type { CoachNoteDto } from './trainee-home-api';

interface Props {
  note: CoachNoteDto;
  onOpen?: () => void;
}

// "Latest from Coach Novia" — the single highest-retention surface per docs/05.
// Oversized opening quote glyph, italic serif body.  Trainees who feel seen
// retain.
export function CoachNoteCard({ note, onOpen }: Props) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === 'id' ? 'id' : 'en';
  const dateLabel = format(new Date(note.sessionDate), 'd MMM', {
    locale: locale === 'id' ? idLocale : enUS,
  });

  return (
    <section className="flex flex-col gap-2">
      <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {t('traineeHome.coachNote.title', { coach: note.coachDisplayName })}
      </h3>
      <button
        type="button"
        onClick={onOpen}
        className="relative rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4 text-left"
      >
        <div className="flex items-center gap-2">
          <Avatar name={note.coachDisplayName} size={20} />
          <span className="text-footnote text-text-color-secondary">
            {note.coachDisplayName} ·{' '}
            {t('traineeHome.coachNote.after', { date: dateLabel })}
          </span>
        </div>

        <div className="relative mt-2 pl-7">
          <span
            aria-hidden
            className="animate-fade-in absolute -left-1 top-0 select-none font-display text-accent"
            style={{ fontSize: '54px', lineHeight: '0.85' }}
          >
            “
          </span>
          <p
            className="font-display text-body italic text-text-color-primary"
            style={{ lineHeight: 1.5 }}
          >
            {note.summary}
          </p>
        </div>
      </button>
    </section>
  );
}
