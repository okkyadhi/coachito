import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { InlineSavedToast, type SaveStatus } from '@/components/InlineSavedToast';

import type { SummaryStyle } from '../profile-api';

interface Props {
  email: string | null;
  preferredLocale: 'en' | 'id';
  summaryStyle: SummaryStyle;
  /** When true, render the AI draft-voice row. Hidden for trainees/parents
   *  who never write assessment summaries. */
  showSummaryStyle: boolean;
  onSave: (patch: {
    preferredLocale?: 'en' | 'id';
    summaryStyle?: SummaryStyle;
  }) => Promise<void>;
}

const STYLE_OPTIONS: SummaryStyle[] = ['encouraging', 'direct', 'warm'];

export function AccountSection({
  email,
  preferredLocale,
  summaryStyle,
  showSummaryStyle,
  onSave,
}: Props) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<SaveStatus>('idle');

  const setLocale = async (next: 'en' | 'id') => {
    if (next === preferredLocale) return;
    setStatus('saving');
    try {
      await onSave({ preferredLocale: next });
      setStatus('saved');
    } catch {
      setStatus('failed');
    }
  };

  const setStyle = async (next: SummaryStyle) => {
    if (next === summaryStyle) return;
    setStatus('saving');
    try {
      await onSave({ summaryStyle: next });
      setStatus('saved');
    } catch {
      setStatus('failed');
    }
  };

  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center justify-between px-1">
        <h2 className="text-section uppercase tracking-wide text-text-color-secondary">
          {t('me.account.title')}
        </h2>
        <InlineSavedToast status={status} />
      </div>
      <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        <div className="flex items-center justify-between p-4">
          <span className="text-body text-text-color-secondary">
            {t('me.account.email')}
          </span>
          <span className="text-body text-text-color-tertiary">
            {email ?? '—'}
          </span>
        </div>
        <div className="flex flex-col gap-2 border-t-[0.5px] border-border-hairline p-4">
          <span className="text-body text-text-color-secondary">
            {t('me.account.locale')}
          </span>
          <div className="flex w-full overflow-hidden rounded-lg border-[0.5px] border-border-hairline">
            {(['en', 'id'] as const).map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => void setLocale(l)}
                className={[
                  'flex-1 px-3 py-2 text-caption font-medium transition-colors',
                  preferredLocale === l
                    ? 'bg-accent text-white'
                    : 'bg-bg-primary text-text-color-secondary',
                ].join(' ')}
              >
                {l === 'en' ? 'English' : 'Bahasa Indonesia'}
              </button>
            ))}
          </div>
        </div>
        {showSummaryStyle ? (
          <div className="flex flex-col gap-2 border-t-[0.5px] border-border-hairline p-4">
            <div className="flex flex-col gap-0.5">
              <span className="text-body text-text-color-secondary">
                {t('me.account.draftVoice')}
              </span>
              <span className="text-footnote text-text-color-tertiary">
                {t('me.account.draftVoiceHint')}
              </span>
            </div>
            <div className="flex w-full overflow-hidden rounded-lg border-[0.5px] border-border-hairline">
              {STYLE_OPTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => void setStyle(s)}
                  className={[
                    'flex-1 px-3 py-2 text-caption font-medium transition-colors',
                    summaryStyle === s
                      ? 'bg-accent text-white'
                      : 'bg-bg-primary text-text-color-secondary',
                  ].join(' ')}
                >
                  {t(`draftVoice.${s}`)}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
