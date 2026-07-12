"""add campaign_battles, campaign_battle_participants

Revision ID: 6e2f726a9019
Revises: 065571c889e0
Create Date: 2026-07-12 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e2f726a9019'
down_revision: Union[str, Sequence[str], None] = '065571c889e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_battles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("turn_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reveal_resources", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(op.f("ix_campaign_battles_campaign_id"), "campaign_battles", ["campaign_id"], unique=True)

    op.create_table(
        "campaign_battle_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("battle_id", sa.Integer(), sa.ForeignKey("campaign_battles.id"), nullable=False),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(op.f("ix_campaign_battle_participants_battle_id"), "campaign_battle_participants", ["battle_id"])
    op.create_index(op.f("ix_campaign_battle_participants_character_id"), "campaign_battle_participants", ["character_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_battle_participants_character_id"), table_name="campaign_battle_participants")
    op.drop_index(op.f("ix_campaign_battle_participants_battle_id"), table_name="campaign_battle_participants")
    op.drop_table("campaign_battle_participants")

    op.drop_index(op.f("ix_campaign_battles_campaign_id"), table_name="campaign_battles")
    op.drop_table("campaign_battles")
