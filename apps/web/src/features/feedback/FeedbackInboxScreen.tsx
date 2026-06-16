import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, MessageCircle, UserCircle2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/features/auth/auth-store';
import {
  type FeedbackInboxItem,
  getFeedbackInbox,
  markFeedbackRead,
} from '@/features/assessment/feedback-api';

export function FeedbackInboxScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const currentWorkspaceId = useAuthStore((s) => s.currentWorkspaceId);

  const { data, isPending } = useQuery({
    queryKey: ['feedback-inbox', currentWorkspaceId],
    queryFn: getFeedbackInbox,
  });

  const readMut = useMutation({
    mutationFn: (id: string) => markFeedbackRead(id),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: ['feedback-inbox', currentWorkspaceId],
      }),
  });

  if (isPending) {
    return (
      <div className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 pt-6">
        <div className="h-6 w-32 rounded bg-bg-primary" />
        <div className="h-40 rounded-xl bg-bg-primary" />
      </div>
    );
  }

  const items = data ?? [];
  const unreadCount = items.filter((i) => !i.readAt).length;

  return (
    <div className="mx-auto w-full max-w-md px-4 pb-8 pt-3">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-large-title text-text-color-primary">
          {t('feedback.inbox.title')}
        </h1>
        {unreadCount > 0 ? (
          <span className="rounded-full bg-accent px-2 py-0.5 text-footnote text-white">
            {unreadCount}
          </span>
        ) : null}
      </header>

      {items.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <MessageCircle
            size={32}
            strokeWidth={1.5}
            aria-hidden
            className="text-text-color-tertiary"
          />
          <p className="text-body text-text-color-primary">
            {t('feedback.inbox.emptyTitle')}
          </p>
          <p className="text-caption text-text-color-secondary">
            {t('feedback.inbox.emptyBody')}
          </p>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {items.map((it) => (
            <FeedbackRow
              key={it.id}
              item={it}
              onMarkRead={() => readMut.mutate(it.id)}
              onOpenAssessment={() => navigate(`/feedback/${it.assessmentId}`)}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function FeedbackRow({
  item,
  onMarkRead,
}: {
  item: FeedbackInboxItem;
  onMarkRead: () => void;
  onOpenAssessment: () => void;
}) {
  const { t } = useTranslation();
  const unread = !item.readAt;
  const name = item.isAnonymous
    ? t(`feedback.anon.${item.submitterRole}`)
    : (item.athleteDisplayName ?? '—');
  return (
    <li
      className={
        unread
          ? 'border-accent/40 rounded-xl border-[0.5px] bg-bg-primary p-4 shadow-[0_0_0_1px_rgba(55,138,221,0.15)]'
          : 'rounded-xl border-[0.5px] border-border-hairline bg-bg-primary p-4'
      }
    >
      <div className="flex items-center gap-2">
        <UserCircle2
          size={20}
          strokeWidth={1.5}
          aria-hidden
          className="text-text-color-tertiary"
        />
        <span className="flex-1 text-body text-text-color-primary">{name}</span>
        <span className="text-h3 text-text-color-primary">
          {'★'.repeat(item.ratingOverall)}
          {'☆'.repeat(5 - item.ratingOverall)}
        </span>
      </div>
      {item.ratingFairness != null ? (
        <p className="mt-1 text-footnote text-text-color-tertiary">
          {t('feedback.fairness', { score: item.ratingFairness })}
        </p>
      ) : null}
      {item.comment ? (
        <p className="mt-2 text-body italic text-text-color-secondary">
          “{item.comment}”
        </p>
      ) : null}
      <div className="mt-3 flex items-center justify-between">
        <span className="text-footnote text-text-color-tertiary">
          {new Date(item.submittedAt).toLocaleString()}
        </span>
        {unread ? (
          <button
            type="button"
            onClick={onMarkRead}
            className="flex items-center gap-1 text-caption text-accent"
          >
            <Check size={14} strokeWidth={1.75} aria-hidden />
            {t('feedback.markRead')}
          </button>
        ) : (
          <span className="text-footnote text-text-color-tertiary">
            {t('feedback.seen')}
          </span>
        )}
      </div>
    </li>
  );
}
