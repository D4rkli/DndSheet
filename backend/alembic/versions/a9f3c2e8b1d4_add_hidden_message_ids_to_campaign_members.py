"""add hidden_message_ids to campaign_members

Revision ID: a9f3c2e8b1d4
Revises: c8e5a1f4d6b7
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9f3c2e8b1d4'
down_revision: Union[str, Sequence[str], None] = 'c8e5a1f4d6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table("campaign_members") as b:
        b.add_column(sa.Column("hidden_message_ids", sa.Text(), nullable=False, server_default=""))

    with op.batch_alter_table("campaign_members") as b:
        b.alter_column("hidden_message_ids", server_default=None)


def downgrade():
    with op.batch_alter_table("campaign_members") as b:
        b.drop_column("hidden_message_ids")
