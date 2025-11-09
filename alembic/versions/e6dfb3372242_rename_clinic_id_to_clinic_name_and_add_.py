"""rename_clinic_id_to_clinic_name_and_add_unique_constraint

Revision ID: e6dfb3372242
Revises: ee16b33c310a
Create Date: 2025-11-09 20:05:08.451145

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6dfb3372242"
down_revision: Union[str, Sequence[str], None] = "ee16b33c310a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the old index
    op.drop_index("ix_documents_clinic_id", table_name="documents")

    # Rename the column from clinic_id to clinic_name
    op.alter_column("documents", "clinic_id", new_column_name="clinic_name")

    # Create a new unique index on clinic_name
    op.create_index(
        "ix_documents_clinic_name",
        "documents",
        ["clinic_name"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the unique index
    op.drop_index("ix_documents_clinic_name", table_name="documents")

    # Rename the column back from clinic_name to clinic_id
    op.alter_column("documents", "clinic_name", new_column_name="clinic_id")

    # Recreate the old non-unique index
    op.create_index("ix_documents_clinic_id", "documents", ["clinic_id"])
