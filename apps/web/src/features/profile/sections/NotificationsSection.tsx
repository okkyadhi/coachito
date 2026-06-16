import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { InlineSavedToast, type SaveStatus } from '@/components/InlineSavedToast';
import { Switch } from '@/components/Switch';

import type { NotificationsPrefs } from '../profile-api';

interface Props {
  prefs: NotificationsPrefs;
  onSave: (next: Partial<NotificationsPrefs>) => Promise<void>;
}

export function NotificationsSection({ prefs, onSave }: Props) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<SaveStatus>('idle');

  const toggle = async (key: keyof NotificationsPrefs, next: boolean) => {
    setStatus('saving');
    try {
      await onSave({ [key]: next } as Partial<NotificationsPrefs>);
      setStatus('saved');
    } catch {
      setStatus('failed');
    }
  };

  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center justify-between px-1">
        <h2 className="text-section uppercase tracking-wide text-text-color-secondary">
          {t('me.notifications.title')}
        </h2>
        <InlineSavedToast status={status} />
      </div>
      <div className="overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary">
        <Row
          title={t('me.notifications.sessionRemindersTitle')}
          subtitle={t('me.notifications.sessionRemindersBody')}
          checked={prefs.sessionReminders}
          onChange={(v) => void toggle('sessionReminders', v)}
        />
        <Row
          title={t('me.notifications.monthlyReportTitle')}
          subtitle={t('me.notifications.monthlyReportBody')}
          checked={prefs.monthlyReport}
          onChange={(v) => void toggle('monthlyReport', v)}
          borderTop
        />
      </div>
    </section>
  );
}

function Row({
  title,
  subtitle,
  checked,
  onChange,
  borderTop = false,
}: {
  title: string;
  subtitle: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  borderTop?: boolean;
}) {
  return (
    <div
      className={[
        'flex items-center gap-3 p-4',
        borderTop ? 'border-t-[0.5px] border-border-hairline' : '',
      ].join(' ')}
    >
      <div className="min-w-0 flex-1 pr-3">
        <p className="text-body text-text-color-primary">{title}</p>
        <p className="text-footnote text-text-color-secondary">{subtitle}</p>
      </div>
      <Switch checked={checked} onChange={onChange} ariaLabel={title} />
    </div>
  );
}
