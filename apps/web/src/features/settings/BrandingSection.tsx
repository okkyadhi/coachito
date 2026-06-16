import { Check } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { LogoUploader } from './LogoUploader';
import type { WorkspaceSettings } from './settings-api';

interface Props {
  settings: WorkspaceSettings;
  /** Optimistic in-flight overrides not yet PATCHed.  Falls back to settings. */
  draft: Partial<WorkspaceSettings>;
  onChange: (patch: Partial<WorkspaceSettings>) => void;
  /** When true, render values without inputs / color buttons / upload affordance.
   *  Coach + head-coach see this on club workspaces — only club_admin / the
   *  personal-workspace owner may mutate branding. */
  readOnly?: boolean;
}

// 4 presets aligned to the Coachito palette: clay (default), forest,
// teal, plum.  Clay is the brand-true choice; the others give clubs room
// to differentiate without breaking the warm earthy palette.
const PRESETS: { value: string; label: string }[] = [
  { value: '#C66B47', label: 'Clay' },
  { value: '#2F7D5A', label: 'Forest' },
  { value: '#1B8A87', label: 'Teal' },
  { value: '#6E4A8A', label: 'Plum' },
];

function fallbackInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return 'C';
  if (words.length === 1) return (words[0]?.[0] ?? 'C').toUpperCase();
  return ((words[0]?.[0] ?? '') + (words[1]?.[0] ?? '')).toUpperCase();
}

export function BrandingSection({
  settings,
  draft,
  onChange,
  readOnly = false,
}: Props) {
  const { t } = useTranslation();
  const isClub = settings.type === 'club';
  const name = draft.name ?? settings.name;
  const city = draft.city ?? settings.city ?? '';
  const accent = draft.brandColor ?? settings.brandColor ?? '#C66B47';
  const logo = draft.logoUrl ?? settings.logoUrl ?? null;

  const [showCustom, setShowCustom] = useState(false);
  const customMatches = !PRESETS.some((p) => p.value.toLowerCase() === accent.toLowerCase());

  return (
    <Section title={t('settings.branding.title')}>
      {/* Name row */}
      <Row
        label={
          isClub
            ? t('settings.branding.clubName')
            : t('settings.branding.displayName')
        }
      >
        {readOnly ? (
          <span className="block w-full text-right text-body text-text-color-primary">
            {name}
          </span>
        ) : (
          <input
            type="text"
            value={name}
            onChange={(e) => onChange({ name: e.target.value })}
            onBlur={(e) => onChange({ name: e.target.value })}
            className="w-full bg-transparent text-right text-body text-text-color-primary placeholder:text-text-color-tertiary focus:outline-none"
            placeholder={
              isClub
                ? t('settings.branding.clubNamePlaceholder')
                : t('settings.branding.displayNamePlaceholder')
            }
          />
        )}
      </Row>

      {/* City (personal only) */}
      {!isClub ? (
        <Row label={t('settings.branding.city')}>
          {readOnly ? (
            <span className="block w-full text-right text-body text-text-color-primary">
              {city || '—'}
            </span>
          ) : (
            <input
              type="text"
              value={city}
              onChange={(e) => onChange({ city: e.target.value || null })}
              onBlur={(e) => onChange({ city: e.target.value || null })}
              className="w-full bg-transparent text-right text-body text-text-color-primary placeholder:text-text-color-tertiary focus:outline-none"
              placeholder={t('settings.branding.cityPlaceholder')}
            />
          )}
        </Row>
      ) : null}

      {/* Accent color */}
      <Row label={t('settings.branding.accent')} stack>
        {readOnly ? (
          <div className="flex items-center gap-2">
            <span
              aria-hidden
              className="size-6 rounded-full border-[0.5px] border-border-hairline"
              style={{ background: accent }}
            />
            <span className="text-caption text-text-color-secondary">
              {accent.toUpperCase()}
            </span>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              {PRESETS.map((p) => {
                const active = p.value.toLowerCase() === accent.toLowerCase();
                return (
                  <button
                    key={p.value}
                    type="button"
                    aria-label={p.label}
                    aria-pressed={active}
                    onClick={() => onChange({ brandColor: p.value })}
                    className="relative flex size-8 items-center justify-center rounded-full"
                    style={{ background: p.value }}
                  >
                    {active ? (
                      <Check
                        size={14}
                        strokeWidth={2.5}
                        className="text-white"
                        aria-hidden
                      />
                    ) : null}
                  </button>
                );
              })}
              <button
                type="button"
                onClick={() => setShowCustom((v) => !v)}
                aria-pressed={showCustom || customMatches}
                className={[
                  'flex h-8 items-center gap-1.5 rounded-full border-[0.5px] px-2.5 text-caption',
                  showCustom || customMatches
                    ? 'border-accent bg-accent-bg text-accent'
                    : 'border-border-hairline bg-bg-primary text-text-color-secondary',
                ].join(' ')}
              >
                {customMatches ? (
                  <span
                    aria-hidden
                    className="size-3.5 rounded-full"
                    style={{ background: accent }}
                  />
                ) : null}
                {t('settings.branding.custom')}
              </button>
            </div>
            {showCustom || customMatches ? (
              <div className="mt-2 flex items-center gap-2">
                <input
                  type="color"
                  value={accent}
                  onChange={(e) => onChange({ brandColor: e.target.value })}
                  aria-label={t('settings.branding.custom')}
                  className="h-9 w-12 cursor-pointer rounded-md border-[0.5px] border-border-hairline bg-bg-primary"
                />
                <input
                  type="text"
                  value={accent.toUpperCase()}
                  onChange={(e) => {
                    const next = e.target.value;
                    if (/^#[0-9A-Fa-f]{0,6}$/.test(next)) {
                      onChange({ brandColor: next });
                    }
                  }}
                  maxLength={7}
                  className="w-24 rounded-md border-[0.5px] border-border-hairline bg-bg-primary px-2 py-1.5 text-caption text-text-color-primary focus:border-accent focus:outline-none"
                />
              </div>
            ) : null}
          </>
        )}
      </Row>

      {/* Logo */}
      <div className="p-3">
        <LogoUploader
          logoUrl={logo}
          variant={isClub ? 'square' : 'circle'}
          fallbackInitials={fallbackInitials(name)}
          onUploaded={(url) => onChange({ logoUrl: url })}
          readOnly={readOnly}
        />
      </div>
    </Section>
  );
}

interface SectionProps {
  title: string;
  children: React.ReactNode;
}

function Section({ title, children }: SectionProps) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="px-1 text-section uppercase tracking-wide text-text-color-secondary">
        {title}
      </h3>
      <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        {children}
      </div>
    </section>
  );
}

interface RowProps {
  label: string;
  children: React.ReactNode;
  stack?: boolean;
}

function Row({ label, children, stack }: RowProps) {
  return (
    <div
      className={[
        'flex gap-3 border-t-[0.5px] border-border-hairline px-3 py-3 first:border-t-0',
        stack ? 'flex-col items-start' : 'min-h-tap items-center',
      ].join(' ')}
    >
      <span
        className={[
          'text-body text-text-color-secondary',
          stack ? '' : 'shrink-0',
        ].join(' ')}
      >
        {label}
      </span>
      <div className={stack ? 'w-full' : 'flex-1'}>{children}</div>
    </div>
  );
}
