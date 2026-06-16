import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Avatar } from '@/components/Avatar';
import { InlineSavedToast, type SaveStatus } from '@/components/InlineSavedToast';

import { uploadAvatar } from '../profile-api';

interface Props {
  displayName: string;
  avatarUrl: string | null;
  onSave: (patch: { displayName?: string; avatarUrl?: string | null }) => Promise<void>;
}

export function IdentitySection({ displayName, avatarUrl, onSave }: Props) {
  const { t } = useTranslation();
  const [name, setName] = useState(displayName);
  const [status, setStatus] = useState<SaveStatus>('idle');
  const [avatarStatus, setAvatarStatus] = useState<SaveStatus>('idle');
  const fileRef = useRef<HTMLInputElement>(null);
  const initialName = useRef(displayName);

  useEffect(() => {
    setName(displayName);
    initialName.current = displayName;
  }, [displayName]);

  const flush = async () => {
    const trimmed = name.trim();
    if (trimmed === initialName.current || trimmed.length === 0) return;
    setStatus('saving');
    try {
      await onSave({ displayName: trimmed });
      initialName.current = trimmed;
      setStatus('saved');
    } catch {
      setStatus('failed');
    }
  };

  const handleFile = async (file: File) => {
    setAvatarStatus('saving');
    try {
      const url = await uploadAvatar(file);
      await onSave({ avatarUrl: url });
      setAvatarStatus('saved');
    } catch {
      setAvatarStatus('failed');
    }
  };

  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center justify-between px-1">
        <h2 className="text-section uppercase tracking-wide text-text-color-secondary">
          {t('me.identity.title')}
        </h2>
        <InlineSavedToast status={status} />
      </div>
      <div className="flex items-center gap-4 rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4">
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="relative shrink-0 rounded-full"
          aria-label={t('me.identity.changeAvatar')}
        >
          <Avatar name={name || displayName} src={avatarUrl} size={64} />
          <span className="absolute inset-x-0 bottom-0 rounded-b-full bg-black/45 py-0.5 text-center text-[10px] font-medium text-white">
            {avatarStatus === 'saving'
              ? t('me.identity.uploading')
              : t('me.identity.edit')}
          </span>
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleFile(f);
            e.target.value = '';
          }}
        />
        <div className="flex-1">
          <label className="block text-footnote text-text-color-secondary">
            {t('me.identity.displayNameLabel')}
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={() => void flush()}
            className="mt-0.5 w-full border-b-[0.5px] border-transparent bg-transparent py-1 text-body text-text-color-primary focus:border-accent focus:outline-none"
            maxLength={120}
          />
        </div>
      </div>
    </section>
  );
}
