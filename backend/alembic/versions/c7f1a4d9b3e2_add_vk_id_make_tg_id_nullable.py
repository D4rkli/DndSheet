"""add vk_id to users, make tg_id nullable

Revision ID: c7f1a4d9b3e2
Revises: 21f2d96ca47b
Create Date: 2026-07-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f1a4d9b3e2'
down_revision: Union[str, Sequence[str], None] = '21f2d96ca47b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "tg_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.add_column(sa.Column("vk_id", sa.Integer(), nullable=True))
        batch_op.create_index(op.f("ix_users_vk_id"), ["vk_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index(op.f("ix_users_vk_id"))
        batch_op.drop_column("vk_id")
        batch_op.alter_column(
            "tg_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
