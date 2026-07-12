"""add campaign_messages, campaign_members.last_read_at

Revision ID: 065571c889e0
Revises: f8098cdff191
Create Date: 2026-07-12 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '065571c889e0'
down_revision: Union[str, Sequence[str], None] = 'f8098cdff191'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("campaign_members") as batch_op:
        batch_op.add_column(sa.Column("last_read_at", sa.DateTime(), nullable=True))

    op.create_table(
        "campaign_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_campaign_messages_campaign_id"), "campaign_messages", ["campaign_id"])
    op.create_index(op.f("ix_campaign_messages_target_user_id"), "campaign_messages", ["target_user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_messages_target_user_id"), table_name="campaign_messages")
    op.drop_index(op.f("ix_campaign_messages_campaign_id"), table_name="campaign_messages")
    op.drop_table("campaign_messages")

    with op.batch_alter_table("campaign_members") as batch_op:
        batch_op.drop_column("last_read_at")
