"""initial schema

Revision ID: 20260527_0001
Revises:
Create Date: 2026-05-27 19:59:00
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "20260527_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Initial baseline migration. Add table creation ops as models are added.
    pass


def downgrade() -> None:
    pass

