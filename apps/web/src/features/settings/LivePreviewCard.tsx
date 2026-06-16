import { FileBarChart2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import type { TierStyle, WorkspaceSettings } from './settings-api';

interface Props {
  settings: WorkspaceSettings;
}

// Auto-derived monogram from the workspace name — first letter of the first
// two whitespace-separated words.  Falls back to "R".
function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return 'R';
  if (words.length === 1) return (words[0]?.[0] ?? 'R').toUpperCase();
  return ((words[0]?.[0] ?? '') + (words[1]?.[0] ?? '')).toUpperCase();
}

// Tier display labels per the chosen naming style.  Only the first three
// MVP tiers are surfaced (Silver+ ship later) per docs/06 § Localization note.
const TIER_LABELS: Record<TierStyle, { en: [string, string, string]; id: [string, string, string] }> = {
  game: {
    en: ['Beginner', 'Lower Bronze', 'Bronze'],
    id: ['Beginner', 'Lower Bronze', 'Bronze'], // tier names stay English (memory: feedback_naming_locale)
  },
  skill: {
    en: ['Foundations', 'Developing', 'Functional'],
    id: ['Foundations', 'Developing', 'Functional'],
  },
  custom: {
    en: ['Level 1', 'Level 2', 'Level 3'],
    id: ['Level 1', 'Level 2', 'Level 3'],
  },
};

export function LivePreviewCard({ settings }: Props) {
  const { t, i18n } = useTranslation();
  const locale = i18n.language === 'id' ? 'id' : 'en';
  const isCircle = settings.type === 'personal';
  const tierLabels = TIER_LABELS[settings.tierStyle][locale];

  // Inline --accent so the preview re-tints instantly when the admin clicks
  // a swatch, without waiting for the network PATCH to land.
  const previewStyle: React.CSSProperties = settings.brandColor
    ? ({ ['--accent' as never]: settings.brandColor } as React.CSSProperties)
    : {};

  const planLabelKey = `settings.plans.${settings.plan}`;
  const metaLine =
    settings.type === 'club'
      ? `${t(planLabelKey)} · ${t('settings.preview.coachCount', { count: settings.coachCount })} · ${t('settings.preview.traineeCount', { count: settings.traineeCount })}`
      : `${t('settings.preview.soloCoach')} · ${t('settings.preview.traineeCount', { count: settings.traineeCount })}`;

  return (
    <section
      className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline"
      style={{ ...previewStyle, background: 'var(--accent-bg)' }}
    >
      <div className="flex flex-col gap-3 p-5">
        <p
          className="text-pill uppercase text-accent"
          style={{ letterSpacing: '0.08em' }}
        >
          {t('settings.preview.tag')}
        </p>

        <div className="flex items-center gap-3">
          <div
            className={[
              'flex size-12 shrink-0 items-center justify-center overflow-hidden bg-accent text-white',
              isCircle ? 'rounded-full' : 'rounded-md',
            ].join(' ')}
          >
            {settings.logoUrl ? (
              <img src={settings.logoUrl} alt="" className="size-full object-cover" />
            ) : (
              <span className="text-h3">{initials(settings.name)}</span>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-h2 text-text-color-primary">
              {settings.name || t('settings.preview.placeholder')}
            </p>
            <p className="truncate text-caption text-text-color-secondary">{metaLine}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {tierLabels.map((label) => (
            <span
              key={label}
              className="whitespace-nowrap rounded-full bg-bg-primary px-2.5 py-0.5 text-pill text-accent"
            >
              {label}
            </span>
          ))}
        </div>

        <button
          type="button"
          disabled
          className="mt-1 inline-flex w-fit items-center gap-1.5 rounded-md bg-accent px-3 py-2 text-caption font-medium text-white opacity-90"
        >
          <FileBarChart2 size={14} strokeWidth={1.75} aria-hidden />
          {t('settings.preview.sampleCta')}
        </button>
      </div>

      <p className="border-t-[0.5px] border-border-hairline bg-bg-primary px-5 py-3 text-footnote text-text-color-tertiary">
        {t('settings.preview.footer')}
      </p>
    </section>
  );
}
