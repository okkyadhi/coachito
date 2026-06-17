import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { Building2, User } from 'lucide-react';

import { EditorialHeader } from '@/components/EditorialHeader';

// Role-chooser screen.  Two cards: solo coach vs club admin → respective signup
// forms.  Trainees join via invite (not surfaced here).
export function SignUpScreen() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <main className="flex min-h-screen flex-col bg-bg-tertiary">
      <div className="mx-auto flex w-full max-w-sm flex-1 flex-col px-6 pb-8 pt-16">
        <EditorialHeader
          title={t('signup.title')}
          subtitle={t('signup.subtitle')}
          logoSize={68}
        />

        <div className="mt-10 flex flex-col gap-3">
          <button
            type="button"
            onClick={() => navigate('/signup/coach')}
            className="flex min-h-tap items-start gap-4 rounded-lg border-[0.5px] border-border-hairline bg-bg-primary p-5 text-left transition-colors hover:bg-bg-secondary"
          >
            <div className="bg-accent/10 flex size-10 shrink-0 items-center justify-center rounded-full text-accent">
              <User size={20} strokeWidth={1.5} />
            </div>
            <div className="flex-1">
              <p className="text-body font-medium text-text-color-primary">
                {t('signup.roleCoach.title')}
              </p>
              <p className="mt-1 text-caption text-text-color-secondary">
                {t('signup.roleCoach.subtitle')}
              </p>
            </div>
          </button>

          <button
            type="button"
            onClick={() => navigate('/signup/club')}
            className="flex min-h-tap items-start gap-4 rounded-lg border-[0.5px] border-border-hairline bg-bg-primary p-5 text-left transition-colors hover:bg-bg-secondary"
          >
            <div className="bg-accent/10 flex size-10 shrink-0 items-center justify-center rounded-full text-accent">
              <Building2 size={20} strokeWidth={1.5} />
            </div>
            <div className="flex-1">
              <p className="text-body font-medium text-text-color-primary">
                {t('signup.roleClub.title')}
              </p>
              <p className="mt-1 text-caption text-text-color-secondary">
                {t('signup.roleClub.subtitle')}
              </p>
            </div>
          </button>
        </div>

        <div className="flex-1" />

        <div className="mt-6 flex flex-col items-center gap-3">
          <p className="text-center text-footnote text-text-color-tertiary">
            {t('signin.terms')}
          </p>
          <p className="text-footnote text-text-color-secondary">
            {t('signup.alreadyHave')}{' '}
            <Link to="/signin" className="text-accent">
              {t('signup.signInLink')}
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
