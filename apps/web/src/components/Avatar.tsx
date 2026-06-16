interface AvatarProps {
  name: string;
  size?: number;
  className?: string;
  src?: string | null | undefined;
}

function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return '?';
  if (words.length === 1) return (words[0]?.[0] ?? '').toUpperCase();
  return ((words[0]?.[0] ?? '') + (words[words.length - 1]?.[0] ?? '')).toUpperCase();
}

export function Avatar({ name, size = 40, className = '', src }: AvatarProps) {
  if (src) {
    return (
      <img
        src={src}
        alt=""
        width={size}
        height={size}
        style={{ width: size, height: size, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }}
        className={['border-[0.5px] border-border-hairline', className].join(' ')}
      />
    );
  }
  return (
    <div
      aria-hidden
      style={{ width: size, height: size, borderRadius: '50%', flexShrink: 0 }}
      className={[
        'flex items-center justify-center',
        'bg-accent-bg text-accent',
        'border-[0.5px] border-border-hairline',
        'select-none',
        className,
      ].join(' ')}
    >
      <span
        style={{ fontSize: Math.round(size * 0.38), fontWeight: 500, lineHeight: 1 }}
      >
        {initials(name)}
      </span>
    </div>
  );
}
