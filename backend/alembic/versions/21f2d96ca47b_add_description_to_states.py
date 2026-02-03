"""add description to states

Revision ID: 21f2d96ca47b
Revises: dd94adb53d1d
Create Date: 2026-02-03 16:49:51.812426

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21f2d96ca47b'
down_revision: Union[str, Sequence[str], None] = 'dd94adb53d1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column(
        "states",
        sa.Column("description", sa.String(), server_default="", nullable=False)
    )

def downgrade():
    op.drop_column("states", "description")

