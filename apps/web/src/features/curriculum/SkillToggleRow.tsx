// Admin/owner row in the curriculum list — toggle on the right.
//
// Tapping the row navigates to the skill detail.  Tapping the toggle stops
// propagation so the row navigation doesn't fire.  When the user toggles
// OFF a skill that has active assessments, the parent screen shows a
// confirmation sheet (this row just emits the request).

import { ChevronRight } from 'lucide-react';

import { Switch } from '@/components/Switch';
import { UpdatedBadge } from './UpdatedBadge';
import type { SkillRow } from './curriculum-api';

interface Props {
  skill: SkillRow;
  onOpen: () => void;
  onToggle: (nextEnabled: boolean) => void;
  busy?: boolean;
}

export function SkillToggleRow({ skill, onOpen, onToggle, busy }: Props) {
  return (
    <div className="flex min-h-tap items-center gap-3 border-t-[0.5px] border-border-hairline first:border-t-0">
      <button
        type="button"
        onClick={onOpen}
        className="flex flex-1 items-center gap-3 p-3 text-left"
      >
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="flex items-center gap-2">
            <span className="truncate text-body text-text-color-primary">
              {skill.name_en}
            </span>
            {skill.last_changed_at ? <UpdatedBadge /> : null}
          </span>
          {skill.description_en ? (
            <span className="truncate text-footnote text-text-color-tertiary">
              {skill.description_en}
            </span>
          ) : null}
        </div>
        <ChevronRight
          size={16}
          strokeWidth={1.75}
          className="text-text-color-tertiary"
          aria-hidden
        />
      </button>
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex shrink-0 items-center pr-4"
      >
        <Switch
          checked={skill.is_enabled}
          onChange={onToggle}
          disabled={busy}
          ariaLabel={`Enable ${skill.name_en}`}
        />
      </div>
    </div>
  );
}
