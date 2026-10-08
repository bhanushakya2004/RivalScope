"""enterprise_features

Revision ID: b1b23ffafa81
Revises: a0a73ffafa80
Create Date: 2026-10-08 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1b23ffafa81"
down_revision: str | Sequence[str] | None = "a0a73ffafa80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add name to users
    op.add_column("users", sa.Column("name", sa.String(length=100), nullable=True))

    # 2. Add columns to mcp_servers & mcp_policies
    op.add_column("mcp_servers", sa.Column("discovered_tools", sa.JSON(), nullable=True, server_default="[]"))
    op.add_column("mcp_policies", sa.Column("agent_scope", sa.String(length=50), nullable=True, server_default="all"))
    op.add_column("mcp_policies", sa.Column("description", sa.Text(), nullable=True))

    # 3. Create internal_documents table if not exists
    op.create_table(
        "internal_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("column_names", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(op.f("ix_internal_documents_file_type"), "internal_documents", ["file_type"], unique=False, if_not_exists=True)
    op.create_index(op.f("ix_internal_documents_tenant_id"), "internal_documents", ["tenant_id"], unique=False, if_not_exists=True)


def downgrade() -> None:
    op.drop_table("internal_documents")
    op.drop_column("mcp_policies", "description")
    op.drop_column("mcp_policies", "agent_scope")
    op.drop_column("mcp_servers", "discovered_tools")
    op.drop_column("users", "name")
