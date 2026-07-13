"""add action_log_entries

Revision ID: c8e5a1f4d6b7
Revises: b4d1f7a2c9e3
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8e5a1f4d6b7'
down_revision: Union[str, Sequence[str], None] = 'b4d1f7a2c9e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "action_log_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id"), nullable=False),
        sa.Column("text", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_action_log_entries_character_id",
        "action_log_entries",
        ["character_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_action_log_entries_character_id", table_name="action_log_entries")
    op.drop_table("action_log_entries")
