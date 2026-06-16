import type { ReactElement } from 'react';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';

import { AdminShell } from '@/features/admin/AdminShell';
import { AdminUsersScreen } from '@/features/admin/AdminUsersScreen';
import { AdminWorkspaceDetailScreen } from '@/features/admin/AdminWorkspaceDetailScreen';
import { AdminWorkspacesScreen } from '@/features/admin/AdminWorkspacesScreen';

import { AssessmentScreen } from '@/features/assessment/AssessmentScreen';
import { CurriculumFeedbackInboxScreen } from '@/features/curriculum/CurriculumFeedbackInboxScreen';
import { CurriculumScreen } from '@/features/curriculum/CurriculumScreen';
import { MyFeedbackScreen } from '@/features/curriculum/MyFeedbackScreen';
import { SkillDetailScreen } from '@/features/curriculum/SkillDetailScreen';
import { TiersScreen } from '@/features/curriculum/TiersScreen';
import { ForgotPasswordScreen } from '@/features/auth/ForgotPasswordScreen';
import { GoogleCallback } from '@/features/auth/GoogleCallback';
import { MagicLinkLanding } from '@/features/auth/MagicLinkLanding';
import { ResetPasswordScreen } from '@/features/auth/ResetPasswordScreen';
import { SignInScreen } from '@/features/auth/SignInScreen';
import { SignUpClubScreen } from '@/features/auth/SignUpClubScreen';
import { SignUpCoachScreen } from '@/features/auth/SignUpCoachScreen';
import { SignUpScreen } from '@/features/auth/SignUpScreen';
import { useAuthStore } from '@/features/auth/auth-store';
import { InviteSignupScreen } from '@/features/onboarding/InviteSignupScreen';
import { InviteWelcomeScreen } from '@/features/onboarding/InviteWelcomeScreen';
import { PublicLandingPage } from '@/features/onboarding/PublicLandingPage';
import { CoachBioScreen } from '@/features/coach/CoachBioScreen';
import { CoachListScreen } from '@/features/coach/CoachListScreen';
import { TraineeProfileScreen as TraineeMyProfileScreen } from '@/features/profile/TraineeProfileScreen';
import { TraineeReportsScreen } from '@/features/trainee-reports/TraineeReportsScreen';
import { CreateEventScreen } from '@/features/events/CreateEventScreen';
import { EventDetailScreen } from '@/features/events/EventDetailScreen';
import { EventsListScreen } from '@/features/events/EventsListScreen';
import { ReportsScreen } from '@/features/reports/ReportsScreen';
import { SessionsScreen } from '@/features/sessions/SessionsScreen';
import { SkillsCategoryScreen } from '@/features/skills/SkillsCategoryScreen';
import { SkillsOverviewScreen } from '@/features/skills/SkillsOverviewScreen';
import { FeedbackInboxScreen } from '@/features/feedback/FeedbackInboxScreen';
import { TraineeMySessionsScreen } from '@/features/trainee-sessions/TraineeMySessionsScreen';
import { TraineeSessionDetailScreen } from '@/features/trainee-sessions/TraineeSessionDetailScreen';
import { CoachesScreen } from '@/features/settings/CoachesScreen';
import { WorkspaceSettingsScreen } from '@/features/settings/WorkspaceSettingsScreen';
import { CoachTodayScreen } from '@/features/today/CoachTodayScreen';
import { TraineeHomeScreen } from '@/features/trainee-home/TraineeHomeScreen';
import { TraineeProfileScreen } from '@/features/trainee-profile/TraineeProfileScreen';
import { AddTraineeScreen } from '@/features/trainees/AddTraineeScreen';
import { TraineesScreen } from '@/features/trainees/TraineesScreen';
import { CreateWorkspaceScreen } from '@/features/workspaces/CreateWorkspaceScreen';
import { CoachShell } from '@/layouts/CoachShell';
import { TraineeShell } from '@/layouts/TraineeShell';

function RequireAuth({ children }: { children: ReactElement }) {
  const token = useAuthStore((s) => s.token);
  return token ? children : <Navigate to="/signin" replace />;
}

// Same gate as CoachShellGate but renders children directly — used by
// full-screen modal routes (Add Trainee) that shouldn't show the bottom nav.
function RequireWorkspace({ children }: { children: ReactElement }) {
  const token = useAuthStore((s) => s.token);
  const workspaceId = useAuthStore((s) => s.currentWorkspaceId);
  if (!token) return <Navigate to="/signin" replace />;
  if (!workspaceId) return <Navigate to="/onboarding/create-workspace" replace />;
  return children;
}

// Layout route gate: authenticated + has a workspace. Renders <CoachShell />
// which in turn renders the nested route via <Outlet />.
function CoachShellGate() {
  const token = useAuthStore((s) => s.token);
  const workspaceId = useAuthStore((s) => s.currentWorkspaceId);
  const role = useAuthStore((s) => s.user?.role ?? null);
  if (!token) return <Navigate to="/signin" replace />;
  if (!workspaceId) return <Navigate to="/onboarding/create-workspace" replace />;
  // Trainees / parents see the trainee-side shell.  Any coaching role (or
  // null, e.g. workspace owner during initial setup) gets the coach shell.
  if (role === 'trainee' || role === 'parent') return <Navigate to="/home" replace />;
  return <CoachShell />;
}

function TraineeShellGate() {
  const token = useAuthStore((s) => s.token);
  const role = useAuthStore((s) => s.user?.role ?? null);
  if (!token) return <Navigate to="/signin" replace />;
  if (role !== 'trainee' && role !== 'parent') {
    return <Navigate to="/today" replace />;
  }
  return <TraineeShell />;
}

// Shared gate for routes that both coaches and trainees can use (Events
// today; potentially more later).  Picks the right shell based on the
// user's role so the bottom-nav stays consistent with their other screens
// — without forcing us to duplicate route entries under both gates
// (React Router 6 matches the first declaration, which would shadow one
// role's view of the surface).
function SharedShellGate() {
  const token = useAuthStore((s) => s.token);
  const workspaceId = useAuthStore((s) => s.currentWorkspaceId);
  const role = useAuthStore((s) => s.user?.role ?? null);
  if (!token) return <Navigate to="/signin" replace />;
  if (!workspaceId) return <Navigate to="/onboarding/create-workspace" replace />;
  return (role === 'trainee' || role === 'parent')
    ? <TraineeShell />
    : <CoachShell />;
}

function AdminShellGate() {
  const token = useAuthStore((s) => s.token);
  const isPlatformAdmin = useAuthStore((s) => s.user?.isPlatformAdmin ?? false);
  if (!token) return <Navigate to="/signin" replace />;
  if (!isPlatformAdmin) return <Navigate to="/today" replace />;
  return <AdminShell />;
}

function PublicOnly({ children }: { children: ReactElement }) {
  const token = useAuthStore((s) => s.token);
  const workspaceId = useAuthStore((s) => s.currentWorkspaceId);
  const role = useAuthStore((s) => s.user?.role ?? null);
  if (!token) return children;
  const dest =
    role === 'trainee' || role === 'parent'
      ? '/home'
      : workspaceId
        ? '/today'
        : '/onboarding/create-workspace';
  return <Navigate to={dest} replace />;
}

export function Router() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/today" replace />} />

      {/* Public */}
      <Route path="/signin" element={<PublicOnly><SignInScreen /></PublicOnly>} />
      <Route path="/signup" element={<PublicOnly><SignUpScreen /></PublicOnly>} />
      <Route path="/signup/coach" element={<PublicOnly><SignUpCoachScreen /></PublicOnly>} />
      <Route path="/signup/club" element={<PublicOnly><SignUpClubScreen /></PublicOnly>} />
      <Route path="/auth/callback" element={<GoogleCallback />} />
      <Route path="/auth/magic" element={<MagicLinkLanding />} />
      <Route path="/auth/forgot" element={<PublicOnly><ForgotPasswordScreen /></PublicOnly>} />
      <Route path="/auth/reset" element={<PublicOnly><ResetPasswordScreen /></PublicOnly>} />
      <Route path="/welcome/:token" element={<PublicLandingPage />} />
      <Route path="/invite/:token" element={<InviteWelcomeScreen />} />
      <Route path="/invite/:token/signup" element={<InviteSignupScreen />} />

      {/* Authenticated, no workspace yet */}
      <Route
        path="/onboarding/create-workspace"
        element={
          <RequireAuth>
            <CreateWorkspaceScreen />
          </RequireAuth>
        }
      />

      {/* Shared between roles — same /events surface for coaches and
          trainees, with each role's own shell.  Must come BEFORE both
          role-specific gates so the SharedShellGate match wins. */}
      <Route element={<SharedShellGate />}>
        <Route path="/events" element={<EventsListScreen />} />
        <Route path="/events/new" element={<CreateEventScreen />} />
        <Route path="/events/:id" element={<EventDetailScreen />} />
      </Route>

      {/* Authenticated + has workspace → coach shell with bottom nav */}
      <Route element={<CoachShellGate />}>
        <Route path="/today" element={<CoachTodayScreen />} />
        <Route path="/trainees" element={<TraineesScreen />} />
        <Route path="/trainees/:id" element={<TraineeProfileScreen />} />
        <Route path="/sessions" element={<SessionsScreen />} />
        <Route path="/reports" element={<ReportsScreen />} />
        <Route path="/settings" element={<WorkspaceSettingsScreen />} />
        <Route path="/settings/coaches" element={<CoachesScreen />} />
        <Route path="/settings/curriculum" element={<CurriculumScreen />} />
        <Route
          path="/settings/curriculum/feedback"
          element={<CurriculumFeedbackInboxScreen />}
        />
        <Route
          path="/settings/curriculum/feedback/mine"
          element={<MyFeedbackScreen />}
        />
        <Route
          path="/settings/curriculum/:skillCode"
          element={<SkillDetailScreen />}
        />
        <Route path="/settings/tiers" element={<TiersScreen />} />
        <Route path="/feedback" element={<FeedbackInboxScreen />} />
      </Route>

      {/* Trainee-side shell */}
      <Route element={<TraineeShellGate />}>
        <Route path="/home" element={<TraineeHomeScreen />} />
        <Route path="/progress" element={<Navigate to="/skills" replace />} />
        <Route path="/skills" element={<SkillsOverviewScreen />} />
        <Route path="/skills/:categoryCode" element={<SkillsCategoryScreen />} />
        <Route path="/my-sessions" element={<TraineeMySessionsScreen />} />
        <Route path="/my-sessions/:assessmentId" element={<TraineeSessionDetailScreen />} />
        <Route path="/coach" element={<CoachListScreen />} />
        <Route path="/coach/:coachId" element={<CoachBioScreen />} />
        <Route path="/me" element={<TraineeMyProfileScreen />} />
        <Route path="/me/reports" element={<TraineeReportsScreen />} />
      </Route>

      {/* Modal-style routes — full-screen, no bottom nav */}
      <Route
        path="/trainees/new"
        element={
          <RequireWorkspace>
            <AddTraineeScreen />
          </RequireWorkspace>
        }
      />
      <Route
        path="/trainees/:id/assess"
        element={
          <RequireWorkspace>
            <AssessmentScreen />
          </RequireWorkspace>
        }
      />

      {/* Platform admin shell */}
      <Route element={<AdminShellGate />}>
        <Route path="/admin" element={<Navigate to="/admin/workspaces" replace />} />
        <Route path="/admin/workspaces" element={<AdminWorkspacesScreen />} />
        <Route path="/admin/workspaces/:id" element={<AdminWorkspaceDetailScreen />} />
        <Route path="/admin/users" element={<AdminUsersScreen />} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/signin" replace />} />
    </Routes>
  );
}

// Keep this export so the bundler doesn't emit an unused-import warning in
// the layout module (CoachShell uses Outlet internally; this is a hint to the
// reader that nested children render there).
void Outlet;
