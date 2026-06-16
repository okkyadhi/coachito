import { Suspense, lazy, type ReactElement } from 'react';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';

import { Logo } from '@/components/Logo';
import { ForgotPasswordScreen } from '@/features/auth/ForgotPasswordScreen';
import { GoogleCallback } from '@/features/auth/GoogleCallback';
import { MagicLinkLanding } from '@/features/auth/MagicLinkLanding';
import { ResetPasswordScreen } from '@/features/auth/ResetPasswordScreen';
import { SignInScreen } from '@/features/auth/SignInScreen';
import { SignUpClubScreen } from '@/features/auth/SignUpClubScreen';
import { SignUpCoachScreen } from '@/features/auth/SignUpCoachScreen';
import { SignUpScreen } from '@/features/auth/SignUpScreen';
import { useAuthStore } from '@/features/auth/auth-store';
import { CoachTodayScreen } from '@/features/today/CoachTodayScreen';
import { TraineeHomeScreen } from '@/features/trainee-home/TraineeHomeScreen';
import { CoachShell } from '@/layouts/CoachShell';
import { TraineeShell } from '@/layouts/TraineeShell';

// Everything below is split into its own chunk and downloaded on demand.
// Keeps the post-login first-paint small (only SignIn/SignUp + Today/Home +
// shells are in the initial bundle).
const AdminOverviewScreen = lazy(() =>
  import('@/features/admin/AdminOverviewScreen').then((m) => ({ default: m.AdminOverviewScreen })),
);
const AdminShell = lazy(() =>
  import('@/features/admin/AdminShell').then((m) => ({ default: m.AdminShell })),
);
const AdminUsersScreen = lazy(() =>
  import('@/features/admin/AdminUsersScreen').then((m) => ({ default: m.AdminUsersScreen })),
);
const AdminWorkspaceDetailScreen = lazy(() =>
  import('@/features/admin/AdminWorkspaceDetailScreen').then((m) => ({
    default: m.AdminWorkspaceDetailScreen,
  })),
);
const AdminWorkspacesScreen = lazy(() =>
  import('@/features/admin/AdminWorkspacesScreen').then((m) => ({
    default: m.AdminWorkspacesScreen,
  })),
);
const AssessmentScreen = lazy(() =>
  import('@/features/assessment/AssessmentScreen').then((m) => ({ default: m.AssessmentScreen })),
);
const CurriculumFeedbackInboxScreen = lazy(() =>
  import('@/features/curriculum/CurriculumFeedbackInboxScreen').then((m) => ({
    default: m.CurriculumFeedbackInboxScreen,
  })),
);
const CurriculumScreen = lazy(() =>
  import('@/features/curriculum/CurriculumScreen').then((m) => ({ default: m.CurriculumScreen })),
);
const MyFeedbackScreen = lazy(() =>
  import('@/features/curriculum/MyFeedbackScreen').then((m) => ({ default: m.MyFeedbackScreen })),
);
const SkillDetailScreen = lazy(() =>
  import('@/features/curriculum/SkillDetailScreen').then((m) => ({ default: m.SkillDetailScreen })),
);
const TiersScreen = lazy(() =>
  import('@/features/curriculum/TiersScreen').then((m) => ({ default: m.TiersScreen })),
);
const InviteSignupScreen = lazy(() =>
  import('@/features/onboarding/InviteSignupScreen').then((m) => ({
    default: m.InviteSignupScreen,
  })),
);
const InviteWelcomeScreen = lazy(() =>
  import('@/features/onboarding/InviteWelcomeScreen').then((m) => ({
    default: m.InviteWelcomeScreen,
  })),
);
const PublicLandingPage = lazy(() =>
  import('@/features/onboarding/PublicLandingPage').then((m) => ({ default: m.PublicLandingPage })),
);
const CoachBioScreen = lazy(() =>
  import('@/features/coach/CoachBioScreen').then((m) => ({ default: m.CoachBioScreen })),
);
const CoachListScreen = lazy(() =>
  import('@/features/coach/CoachListScreen').then((m) => ({ default: m.CoachListScreen })),
);
const TraineeMyProfileScreen = lazy(() =>
  import('@/features/profile/TraineeProfileScreen').then((m) => ({
    default: m.TraineeProfileScreen,
  })),
);
const TraineeReportsScreen = lazy(() =>
  import('@/features/trainee-reports/TraineeReportsScreen').then((m) => ({
    default: m.TraineeReportsScreen,
  })),
);
const CreateEventScreen = lazy(() =>
  import('@/features/events/CreateEventScreen').then((m) => ({ default: m.CreateEventScreen })),
);
const EventDetailScreen = lazy(() =>
  import('@/features/events/EventDetailScreen').then((m) => ({ default: m.EventDetailScreen })),
);
const EventsListScreen = lazy(() =>
  import('@/features/events/EventsListScreen').then((m) => ({ default: m.EventsListScreen })),
);
const ReportsScreen = lazy(() =>
  import('@/features/reports/ReportsScreen').then((m) => ({ default: m.ReportsScreen })),
);
const SessionsScreen = lazy(() =>
  import('@/features/sessions/SessionsScreen').then((m) => ({ default: m.SessionsScreen })),
);
const SkillsCategoryScreen = lazy(() =>
  import('@/features/skills/SkillsCategoryScreen').then((m) => ({
    default: m.SkillsCategoryScreen,
  })),
);
const SkillsOverviewScreen = lazy(() =>
  import('@/features/skills/SkillsOverviewScreen').then((m) => ({
    default: m.SkillsOverviewScreen,
  })),
);
const FeedbackInboxScreen = lazy(() =>
  import('@/features/feedback/FeedbackInboxScreen').then((m) => ({
    default: m.FeedbackInboxScreen,
  })),
);
const TraineeMySessionsScreen = lazy(() =>
  import('@/features/trainee-sessions/TraineeMySessionsScreen').then((m) => ({
    default: m.TraineeMySessionsScreen,
  })),
);
const TraineeSessionDetailScreen = lazy(() =>
  import('@/features/trainee-sessions/TraineeSessionDetailScreen').then((m) => ({
    default: m.TraineeSessionDetailScreen,
  })),
);
const CoachesScreen = lazy(() =>
  import('@/features/settings/CoachesScreen').then((m) => ({ default: m.CoachesScreen })),
);
const WorkspaceSettingsScreen = lazy(() =>
  import('@/features/settings/WorkspaceSettingsScreen').then((m) => ({
    default: m.WorkspaceSettingsScreen,
  })),
);
const TraineeProfileScreen = lazy(() =>
  import('@/features/trainee-profile/TraineeProfileScreen').then((m) => ({
    default: m.TraineeProfileScreen,
  })),
);
const AddTraineeScreen = lazy(() =>
  import('@/features/trainees/AddTraineeScreen').then((m) => ({ default: m.AddTraineeScreen })),
);
const TraineesScreen = lazy(() =>
  import('@/features/trainees/TraineesScreen').then((m) => ({ default: m.TraineesScreen })),
);
const CreateWorkspaceScreen = lazy(() =>
  import('@/features/workspaces/CreateWorkspaceScreen').then((m) => ({
    default: m.CreateWorkspaceScreen,
  })),
);

function RouteFallback() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-bg-tertiary">
      <Logo size={56} />
    </main>
  );
}

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
    <Suspense fallback={<RouteFallback />}>
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
          <Route path="/admin" element={<AdminOverviewScreen />} />
          <Route path="/admin/workspaces" element={<AdminWorkspacesScreen />} />
          <Route path="/admin/workspaces/:id" element={<AdminWorkspaceDetailScreen />} />
          <Route path="/admin/users" element={<AdminUsersScreen />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/signin" replace />} />
      </Routes>
    </Suspense>
  );
}

// Keep this export so the bundler doesn't emit an unused-import warning in
// the layout module (CoachShell uses Outlet internally; this is a hint to the
// reader that nested children render there).
void Outlet;
