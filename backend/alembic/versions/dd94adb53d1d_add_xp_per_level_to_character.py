"""add xp_per_level to character

Revision ID: dd94adb53d1d
Revises: 7a2e7b661523
Create Date: 2026-02-03 01:45:11.741168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd94adb53d1d'
down_revision: Union[str, Sequence[str], None] = '7a2e7b661523'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "characters",
        sa.Column(
            "xp_per_level",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("characters", "xp_per_level")

