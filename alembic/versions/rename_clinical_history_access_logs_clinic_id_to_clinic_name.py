"""rename_clinical_history_access_logs_clinic_id_to_clinic_name

Revision ID: a1b2c3d4e5f6
Revises: e6dfb3372242
Create Date: 2025-11-10 23:34:11.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "098fd5fc596b"
down_revision: Union[str, Sequence[str], None] = "e6dfb3372242"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the old index
    op.drop_index(
        "ix_clinical_history_access_logs_clinic_id",
        table_name="clinical_history_access_logs",
    )

    # Rename the column from clinic_id to clinic_name
    op.alter_column(
        "clinical_history_access_logs", "clinic_id", new_column_name="clinic_name"
    )

    # Create a new index on clinic_name
    op.create_index(
        "ix_clinical_history_access_logs_clinic_name",
        "clinical_history_access_logs",
        ["clinic_name"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the new index
    op.drop_index(
        "ix_clinical_history_access_logs_clinic_name",
        table_name="clinical_history_access_logs",
    )

    # Rename the column back from clinic_name to clinic_id
    op.alter_column(
        "clinical_history_access_logs", "clinic_name", new_column_name="clinic_id"
    )

    # Recreate the old index
    op.create_index(
        "ix_clinical_history_access_logs_clinic_id",
        "clinical_history_access_logs",
        ["clinic_id"],
    )
