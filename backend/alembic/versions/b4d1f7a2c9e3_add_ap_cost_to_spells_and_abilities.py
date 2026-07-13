"""add ap_cost to spells and abilities

Revision ID: b4d1f7a2c9e3
Revises: e280efe94b90
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4d1f7a2c9e3'
down_revision: Union[str, Sequence[str], None] = 'e280efe94b90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table("spells") as b:
        b.add_column(sa.Column("ap_cost", sa.Integer(), nullable=False, server_default="5"))

    with op.batch_alter_table("abilities") as b:
        b.add_column(sa.Column("ap_cost", sa.Integer(), nullable=False, server_default="1"))

    # можно убрать дефолт на сервере, чтобы дальше управляла модель
    with op.batch_alter_table("spells") as b:
        b.alter_column("ap_cost", server_default=None)

    with op.batch_alter_table("abilities") as b:
        b.alter_column("ap_cost", server_default=None)


def downgrade():
    with op.batch_alter_table("abilities") as b:
        b.drop_column("ap_cost")

    with op.batch_alter_table("spells") as b:
        b.drop_column("ap_cost")
