// Compact pill that flags which workspace a session/report/coach belongs to.
// Personal workspaces render nothing (default context, no need to label) —
// the badge appears only for clubs, mirroring the user's mental model: "I
// know it's mine unless it says otherwise."

interface Props {
  workspace: {
    name: string;
    type: string;
    brandColor: string | null;
  } | null | undefined;
  className?: string;
}

export function WorkspaceBadge({ workspace, className = '' }: Props) {
  if (!workspace) return null;
  if (workspace.type === 'personal') return null;

  const color = workspace.brandColor || 'var(--accent)';

  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-full border-[0.5px] border-border-hairline',
        'bg-bg-secondary px-2 py-0.5 text-footnote text-text-color-secondary',
        className,
      ].join(' ')}
    >
      <span
        aria-hidden
        className="inline-block size-1.5 rounded-full"
        style={{ background: color }}
      />
      <span className="max-w-[160px] truncate">{workspace.name}</span>
    </span>
  );
}
