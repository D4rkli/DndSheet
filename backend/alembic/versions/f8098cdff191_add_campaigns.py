"""add campaigns, campaign_members, characters.campaign_id

Revision ID: f8098cdff191
Revises: c7f1a4d9b3e2
Create Date: 2026-07-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8098cdff191'
down_revision: Union[str, Sequence[str], None] = 'c7f1a4d9b3e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("first_name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("username", sa.String(length=120), nullable=True))

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("dm_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("invite_code", sa.String(length=32), nullable=False),
    )
    op.create_index(op.f("ix_campaigns_dm_user_id"), "campaigns", ["dm_user_id"])
    op.create_index(op.f("ix_campaigns_invite_code"), "campaigns", ["invite_code"], unique=True)

    op.create_table(
        "campaign_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint("campaign_id", "user_id", name="uq_campaign_member"),
    )
    op.create_index(op.f("ix_campaign_members_campaign_id"), "campaign_members", ["campaign_id"])
    op.create_index(op.f("ix_campaign_members_user_id"), "campaign_members", ["user_id"])

    with op.batch_alter_table("characters") as batch_op:
        batch_op.add_column(sa.Column("campaign_id", sa.Integer(), nullable=True))
        batch_op.create_index(op.f("ix_characters_campaign_id"), ["campaign_id"])
        batch_op.create_foreign_key(
            "fk_characters_campaign_id_campaigns",
            "campaigns",
            ["campaign_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("characters") as batch_op:
        batch_op.drop_constraint("fk_characters_campaign_id_campaigns", type_="foreignkey")
        batch_op.drop_index(op.f("ix_characters_campaign_id"))
        batch_op.drop_column("campaign_id")

    op.drop_index(op.f("ix_campaign_members_user_id"), table_name="campaign_members")
    op.drop_index(op.f("ix_campaign_members_campaign_id"), table_name="campaign_members")
    op.drop_table("campaign_members")

    op.drop_index(op.f("ix_campaigns_invite_code"), table_name="campaigns")
    op.drop_index(op.f("ix_campaigns_dm_user_id"), table_name="campaigns")
    op.drop_table("campaigns")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("username")
        batch_op.drop_column("first_name")
