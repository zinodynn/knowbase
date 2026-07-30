"""Add documents.is_active for version switch visibility

Revision ID: 005_document_is_active
Revises: 004_version_management
Create Date: 2026-07-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_document_is_active"
down_revision: Union[str, None] = "004_version_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="是否在当前激活版本中可见",
        ),
    )
    op.create_index("ix_documents_is_active", "documents", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_documents_is_active", table_name="documents")
    op.drop_column("documents", "is_active")
