"""add subscription_expires_at to users and access_codes table

Revision ID: e1a7c4f9b2d6
Revises: a9f3c2e8b1d4
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1a7c4f9b2d6'
down_revision: Union[str, Sequence[str], None] = 'a9f3c2e8b1d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table("users") as b:
        b.add_column(sa.Column("subscription_expires_at", sa.DateTime(), nullable=True))

    op.create_table(
        "access_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("redeemed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("redeemed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_access_codes_code", "access_codes", ["code"], unique=True)


def downgrade():
    op.drop_index("ix_access_codes_code", table_name="access_codes")
    op.drop_table("access_codes")

    with op.batch_alter_table("users") as b:
        b.drop_column("subscription_expires_at")
