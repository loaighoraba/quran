"""lock down supabase data api

Keep every table out of Supabase's Data API (REST): the app connects as the table
owner, which RLS doesn't apply to, so only the API roles are affected.

- Enable RLS with no policies on every table (all environments).
- On Supabase only (where the API roles exist): revoke the automatic grants to
  anon/authenticated/service_role, and stop them being granted on future objects.

New tables need RLS enabled in their own migration; autogenerate doesn't add it.

Revision ID: 3f8eb9f392f5
Revises: b5acc4770508
Create Date: 2026-10-08 01:30:50.928228

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f8eb9f392f5"
down_revision: str | Sequence[str] | None = "b5acc4770508"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ["alembic_version", "surahs", "ayas", "words", "segments"]
API_ROLES = "anon, authenticated, service_role"

# Runs the given statements only when Supabase's API roles exist
SUPABASE_ONLY = """
DO $$
BEGIN
    IF (SELECT count(*) FROM pg_roles
        WHERE rolname IN ('anon', 'authenticated', 'service_role')) = 3 THEN
{statements}
    END IF;
END
$$;
"""


def supabase_only(*statements: str) -> None:
    body = "\n".join(f"        {statement};" for statement in statements)
    op.execute(SUPABASE_ONLY.format(statements=body))


def upgrade() -> None:
    """Upgrade schema."""
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")

    supabase_only(
        f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {API_ROLES}",
        f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {API_ROLES}",
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public"
        f" REVOKE ALL ON TABLES FROM {API_ROLES}",
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public"
        f" REVOKE ALL ON SEQUENCES FROM {API_ROLES}",
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public"
        f" REVOKE EXECUTE ON FUNCTIONS FROM {API_ROLES}",
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public"
        " REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC",
    )


def downgrade() -> None:
    """Downgrade schema."""
    supabase_only(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public"
        " GRANT EXECUTE ON FUNCTIONS TO PUBLIC",
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public"
        f" GRANT EXECUTE ON FUNCTIONS TO {API_ROLES}",
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public"
        f" GRANT ALL ON SEQUENCES TO {API_ROLES}",
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public"
        f" GRANT ALL ON TABLES TO {API_ROLES}",
        f"GRANT ALL ON ALL TABLES IN SCHEMA public TO {API_ROLES}",
    )

    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
