"""remove_unique_constraint_from_clinic_name

Revision ID: f7a8b9c0d1e2
Revises: 098fd5fc596b
Create Date: 2025-11-10 23:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8116ee71140f"
down_revision: Union[str, Sequence[str], None] = "098fd5fc596b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the unique index
    op.drop_index("ix_documents_clinic_name", table_name="documents")

    # Create a new non-unique index on clinic_name
    op.create_index(
        "ix_documents_clinic_name",
        "documents",
        ["clinic_name"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the non-unique index
    op.drop_index("ix_documents_clinic_name", table_name="documents")

    # Recreate the unique index
    op.create_index(
        "ix_documents_clinic_name",
        "documents",
        ["clinic_name"],
        unique=True,
    )
