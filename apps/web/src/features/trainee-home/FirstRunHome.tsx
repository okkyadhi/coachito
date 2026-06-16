import { CalendarDays, Info } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import type { TraineeHome } from './trainee-home-api';
import { UpcomingSession } from './UpcomingSession';

interface Props {
  home: TraineeHome;
}

// Day-zero state per docs/05 "First-run".  No achievement / wins / rhythm.
// Highlights the first session and explains what happens next.
export function FirstRunHome({ home }: Props) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-5">
      {/* Greeting */}
      <div>
        <h1 className="text-large-title text-text-color-primary">
          {t('traineeHome.welcomeName', { name: home.traineeFirstName })}
        </h1>
        <p className="mt-1 text-caption text-text-color-secondary">
          {t('traineeHome.welcomeBody')}
        </p>
      </div>

      <UpcomingSession session={home.upcomingSession} />

      {/* Empty radar */}
      <section
        className="flex flex-col items-center gap-2 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary px-4 py-8 text-center"
      >
        <div className="flex size-[60px] items-center justify-center rounded-full border-[0.5px] border-border-hairline bg-bg-secondary">
          <Info size={26} strokeWidth={1.5} className="text-text-color-tertiary" aria-hidden />
        </div>
        <h2 className="mt-1 text-h3 text-text-color-primary">
          {t('traineeHome.emptyRadar.title')}
        </h2>
        <p className="max-w-[260px] text-caption text-text-color-secondary">
          {t('traineeHome.emptyRadar.body')}
        </p>
      </section>

      {/* What happens next — 3 step list */}
      <section className="flex flex-col gap-2">
        <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
          {t('traineeHome.whatNext.title')}
        </h3>
        <ol className="flex flex-col gap-0 overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
          {(['s1', 's2', 's3'] as const).map((step, idx) => (
            <li
              key={step}
              className={[
                'flex items-start gap-3 px-4 py-3',
                idx > 0 ? 'border-t-[0.5px] border-border-hairline' : '',
              ].join(' ')}
            >
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-accent-bg text-pill text-accent">
                {idx + 1}
              </span>
              <p className="text-body text-text-color-primary">
                {t(`traineeHome.whatNext.${step}`)}
              </p>
            </li>
          ))}
        </ol>
      </section>

      {/* Footer */}
      <p className="px-1 text-footnote text-text-color-tertiary">
        <CalendarDays
          size={12}
          strokeWidth={1.75}
          className="-mt-0.5 mr-1 inline align-middle"
          aria-hidden
        />
        {t('traineeHome.firstRunFooter')}
      </p>
    </div>
  );
}
