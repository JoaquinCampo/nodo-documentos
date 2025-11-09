"""Initial migration

Revision ID: ee16b33c310a
Revises:
Create Date: 2025-11-09 14:40:17.284210

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ee16b33c310a"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create documents table
    op.create_table(
        "documents",
        sa.Column("doc_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", sa.String(length=8), nullable=False),
        sa.Column("health_user_ci", sa.String(length=8), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("s3_url", sa.String(length=512), nullable=False),
        sa.PrimaryKeyConstraint("doc_id"),
    )
    # Create indexes for documents table
    op.create_index("ix_documents_created_by", "documents", ["created_by"])
    op.create_index("ix_documents_health_user_ci", "documents", ["health_user_ci"])
    op.create_index("ix_documents_clinic_id", "documents", ["clinic_id"])

    # Create clinical_history_access_logs table
    op.create_table(
        "clinical_history_access_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("health_user_ci", sa.String(length=8), nullable=False),
        sa.Column("health_worker_ci", sa.String(length=8), nullable=False),
        sa.Column("clinic_id", sa.String(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("viewed", sa.Boolean(), nullable=False),
        sa.Column("decision_reason", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Create indexes for clinical_history_access_logs table
    op.create_index(
        "ix_clinical_history_access_logs_health_user_ci",
        "clinical_history_access_logs",
        ["health_user_ci"],
    )
    op.create_index(
        "ix_clinical_history_access_logs_health_worker_ci",
        "clinical_history_access_logs",
        ["health_worker_ci"],
    )
    op.create_index(
        "ix_clinical_history_access_logs_clinic_id",
        "clinical_history_access_logs",
        ["clinic_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index(
        "ix_clinical_history_access_logs_clinic_id",
        table_name="clinical_history_access_logs",
    )
    op.drop_index(
        "ix_clinical_history_access_logs_health_worker_ci",
        table_name="clinical_history_access_logs",
    )
    op.drop_index(
        "ix_clinical_history_access_logs_health_user_ci",
        table_name="clinical_history_access_logs",
    )
    op.drop_index("ix_documents_clinic_id", table_name="documents")
    op.drop_index("ix_documents_health_user_ci", table_name="documents")
    op.drop_index("ix_documents_created_by", table_name="documents")

    # Drop tables
    op.drop_table("clinical_history_access_logs")
    op.drop_table("documents")
