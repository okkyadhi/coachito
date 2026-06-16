import { useTranslation } from 'react-i18next';

/** Render up to two focus pills with " · " separator, then "+N" overflow. */
export function FocusList({
  focuses,
  size = 'sm',
}: {
  focuses: string[] | null | undefined;
  size?: 'sm' | 'md';
}) {
  const { t } = useTranslation();
  const list = focuses ?? [];
  if (list.length === 0) return null;
  const visible = list.slice(0, 2);
  const overflow = list.length - visible.length;
  const cls =
    size === 'md'
      ? 'rounded-full bg-accent-bg px-2 py-0.5 text-caption text-accent'
      : 'rounded-full bg-accent-bg px-2 py-0.5 text-pill text-accent';
  return (
    <>
      {visible.map((f) => (
        <span key={f} className={cls}>
          {t(`sessionFocus.${f}`)}
        </span>
      ))}
      {overflow > 0 ? (
        <span className={cls}>+{overflow}</span>
      ) : null}
    </>
  );
}
