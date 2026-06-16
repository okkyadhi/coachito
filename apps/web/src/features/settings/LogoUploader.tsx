import { Loader2 } from 'lucide-react';
import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { uploadLogo } from './settings-api';

interface Props {
  logoUrl: string | null;
  variant: 'square' | 'circle';
  fallbackInitials: string;
  /** Called once the upload completes with the new URL.  Caller is
   *  responsible for persisting it via the settings PATCH. */
  onUploaded: (url: string) => void;
  /** When true, hide the Change/Add CTA — non-admins still see the logo. */
  readOnly?: boolean;
}

export function LogoUploader({
  logoUrl,
  variant,
  fallbackInitials,
  onUploaded,
  readOnly = false,
}: Props) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const shapeClass = variant === 'circle' ? 'rounded-full' : 'rounded-md';

  const handleFile = async (file: File) => {
    setError(null);
    setProgress(0);
    try {
      const url = await uploadLogo(file, setProgress);
      onUploaded(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed.');
    } finally {
      setProgress(null);
    }
  };

  return (
    <div className="flex items-center gap-3">
      <div
        className={[
          'relative flex size-[50px] shrink-0 items-center justify-center overflow-hidden bg-accent text-white',
          shapeClass,
        ].join(' ')}
      >
        {logoUrl ? (
          <img src={logoUrl} alt="" className="size-full object-cover" />
        ) : (
          <span className="text-h3">{fallbackInitials}</span>
        )}
        {progress !== null ? (
          <div
            className={[
              'absolute inset-0 flex items-center justify-center bg-black/40 text-white',
              shapeClass,
            ].join(' ')}
          >
            <Loader2 size={18} className="animate-spin" aria-hidden />
          </div>
        ) : null}
      </div>

      <div className="min-w-0 flex-1">
        <p className="text-body text-text-color-primary">
          {variant === 'circle'
            ? t('settings.branding.profilePhotoLabel')
            : t('settings.branding.logoLabel')}
        </p>
        <p className="text-footnote text-text-color-secondary">
          {variant === 'circle'
            ? t('settings.branding.profilePhotoHint')
            : t('settings.branding.logoHint')}
        </p>
        {error ? (
          <p className="mt-0.5 text-footnote text-danger-text">{error}</p>
        ) : progress !== null ? (
          <p className="mt-0.5 text-footnote text-text-color-tertiary">
            {t('settings.branding.uploading', { pct: progress })}
          </p>
        ) : null}
      </div>

      {readOnly ? null : (
        <>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={progress !== null}
            className="min-h-tap rounded-md border-[0.5px] border-border-hairline bg-bg-primary px-3 text-caption font-medium text-text-color-primary disabled:opacity-60"
          >
            {logoUrl
              ? t('settings.branding.change')
              : t('settings.branding.add')}
          </button>

          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleFile(file);
              // Reset so picking the same file twice re-fires onChange.
              e.target.value = '';
            }}
          />
        </>
      )}
    </div>
  );
}
