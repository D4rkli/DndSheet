"""add level to spells and abilities

Revision ID: 1854b87999ab
Revises: aae43e1e23be
Create Date: 2026-01-31 14:15:31.277811

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1854b87999ab'
down_revision: Union[str, Sequence[str], None] = 'aae43e1e23be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade():
    with op.batch_alter_table("spells") as b:
        b.add_column(sa.Column("level", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("abilities") as b:
        b.add_column(sa.Column("level", sa.Integer(), nullable=False, server_default="0"))

    # можно убрать дефолт на сервере, чтобы дальше управляла модель
    with op.batch_alter_table("spells") as b:
        b.alter_column("level", server_default=None)

    with op.batch_alter_table("abilities") as b:
        b.alter_column("level", server_default=None)

def downgrade():
    with op.batch_alter_table("abilities") as b:
        b.drop_column("level")

    with op.batch_alter_table("spells") as b:
        b.drop_column("level")