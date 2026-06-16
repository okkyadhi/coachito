"""Row Level Security: enable RLS + create all workspace-isolation policies.

FORCE ROW LEVEL SECURITY is applied to tables where workspace context is
strictly required, so the DB owner (coachito) is also subject to RLS.
Tables with platform-or-workspace policies use ENABLE without FORCE so
seeding (workspace_id=NULL rows) remains visible to the owner.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-11
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Helper function — returns current workspace UUID or NULL
    op.execute("""
        CREATE OR REPLACE FUNCTION current_workspace_id() RETURNS UUID AS $$
            SELECT NULLIF(current_setting('app.current_workspace_id', TRUE), '')::UUID
        $$ LANGUAGE SQL STABLE
    """)

    # ── workspaces ─────────────────────────────────────────────────
    op.execute("ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY workspace_self_access ON workspaces
            USING (id = current_workspace_id() OR current_workspace_id() IS NULL)
    """)

    # ── workspace_memberships ──────────────────────────────────────
    op.execute("ALTER TABLE workspace_memberships ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workspace_memberships FORCE  ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY membership_workspace_access ON workspace_memberships
            USING (workspace_id = current_workspace_id())
    """)

    # ── athletes ───────────────────────────────────────────────────
    op.execute("ALTER TABLE athletes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE athletes FORCE  ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY athlete_workspace_access ON athletes
            USING (workspace_id = current_workspace_id())
    """)

    # ── sessions ───────────────────────────────────────────────────
    op.execute("ALTER TABLE sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sessions FORCE  ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY session_workspace_access ON sessions
            USING (workspace_id = current_workspace_id())
    """)

    # ── assessments ────────────────────────────────────────────────
    op.execute("ALTER TABLE assessments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE assessments FORCE  ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY assessment_workspace_access ON assessments
            USING (workspace_id = current_workspace_id())
    """)

    # ── reports ────────────────────────────────────────────────────
    op.execute("ALTER TABLE reports ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE reports FORCE  ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY report_workspace_access ON reports
            USING (workspace_id = current_workspace_id())
    """)

    # ── invites ────────────────────────────────────────────────────
    op.execute("ALTER TABLE invites ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE invites FORCE  ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY invite_workspace_access ON invites
            USING (workspace_id = current_workspace_id())
    """)

    # ── subscriptions ──────────────────────────────────────────────
    op.execute("ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE subscriptions FORCE  ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY subscription_workspace_access ON subscriptions
            USING (workspace_id = current_workspace_id())
    """)

    # ── skills: platform (workspace_id NULL) + workspace custom ────
    op.execute("ALTER TABLE skills ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY skills_platform_or_workspace ON skills
            USING (workspace_id IS NULL OR workspace_id = current_workspace_id())
    """)

    # ── skill_level_descriptors ────────────────────────────────────
    op.execute("ALTER TABLE skill_level_descriptors ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY descriptors_platform_or_workspace ON skill_level_descriptors
            USING (workspace_id IS NULL OR workspace_id = current_workspace_id())
    """)

    # ── tiers ──────────────────────────────────────────────────────
    op.execute("ALTER TABLE tiers ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tiers_platform_or_workspace ON tiers
            USING (workspace_id IS NULL OR workspace_id = current_workspace_id())
    """)

    # ── curricula ──────────────────────────────────────────────────
    op.execute("ALTER TABLE curricula ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY curricula_platform_or_workspace ON curricula
            USING (workspace_id IS NULL OR workspace_id = current_workspace_id())
    """)

    # ── audit_log: workspace events + platform events (NULL ws) ───
    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY audit_workspace_access ON audit_log
            USING (workspace_id = current_workspace_id() OR workspace_id IS NULL)
    """)


def downgrade() -> None:
    tables_with_policies = [
        ("audit_log",            "audit_workspace_access"),
        ("curricula",            "curricula_platform_or_workspace"),
        ("tiers",                "tiers_platform_or_workspace"),
        ("skill_level_descriptors", "descriptors_platform_or_workspace"),
        ("skills",               "skills_platform_or_workspace"),
        ("subscriptions",        "subscription_workspace_access"),
        ("invites",              "invite_workspace_access"),
        ("reports",              "report_workspace_access"),
        ("assessments",          "assessment_workspace_access"),
        ("sessions",             "session_workspace_access"),
        ("athletes",             "athlete_workspace_access"),
        ("workspace_memberships","membership_workspace_access"),
        ("workspaces",           "workspace_self_access"),
    ]
    for table, policy in tables_with_policies:
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP FUNCTION IF EXISTS current_workspace_id()")
