// Shared skeleton primitives — replaces the static gray boxes scattered
// across CoachToday / Trainees / TraineeHome with shimmer that mirrors
// the real card geometry. Shimmer keyframe lives in styles/global.css
// (.animate-shimmer) so the gradient slides cream → tertiary → cream.

import type { CSSProperties, HTMLAttributes } from 'react';

type DivProps = HTMLAttributes<HTMLDivElement>;

function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(' ');
}

export function SkeletonLine({
  width = '100%',
  height = 12,
  className,
  style,
  ...rest
}: { width?: number | string; height?: number | string } & DivProps) {
  const merged: CSSProperties = { width, height, ...style };
  return (
    <div
      aria-hidden
      className={cx('animate-shimmer rounded-full', className)}
      style={merged}
      {...rest}
    />
  );
}

export function SkeletonCircle({
  size = 36,
  className,
  style,
  ...rest
}: { size?: number } & DivProps) {
  const merged: CSSProperties = { width: size, height: size, ...style };
  return (
    <div
      aria-hidden
      className={cx('animate-shimmer rounded-full', className)}
      style={merged}
      {...rest}
    />
  );
}

export function SkeletonBlock({
  height = 80,
  className,
  style,
  ...rest
}: { height?: number | string } & DivProps) {
  const merged: CSSProperties = { height, ...style };
  return (
    <div
      aria-hidden
      className={cx('animate-shimmer rounded-xl', className)}
      style={merged}
      {...rest}
    />
  );
}

// Contextual row: avatar circle + 2 stacked lines + trailing chevron
// stand-in. Used in Coach Today + Coach Trainees + Sessions lists.
export function SkeletonListRow({ className }: { className?: string }) {
  return (
    <div
      className={cx(
        'flex items-center gap-3 border-b-[0.5px] border-border-hairline bg-bg-primary px-4 py-3 last:border-b-0',
        className,
      )}
    >
      <SkeletonCircle size={36} />
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <SkeletonLine width="55%" height={10} />
        <SkeletonLine width="35%" height={8} />
      </div>
      <SkeletonLine width={14} height={14} className="!rounded-md" />
    </div>
  );
}

// Vertical list wrapper that renders N rows inside a single rounded card.
export function SkeletonList({
  rows = 3,
  className,
}: {
  rows?: number;
  className?: string;
}) {
  return (
    <div
      className={cx(
        'overflow-hidden rounded-xl border-[0.5px] border-border-hairline bg-bg-primary',
        className,
      )}
    >
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonListRow key={i} />
      ))}
    </div>
  );
}
