"""add level to spells and abilities

Revision ID: 7a2e7b661523
Revises: 1854b87999ab
Create Date: 2026-02-02 03:43:43.796136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a2e7b661523'
down_revision: Union[str, Sequence[str], None] = '1854b87999ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # spells.level
    spell_cols = [c["name"] for c in insp.get_columns("spells")]
    if "level" not in spell_cols:
        with op.batch_alter_table("spells") as batch:
            batch.add_column(
                sa.Column("level", sa.Integer(), nullable=False, server_default="0")
            )

    # abilities.level
    abil_cols = [c["name"] for c in insp.get_columns("abilities")]
    if "level" not in abil_cols:
        with op.batch_alter_table("abilities") as batch:
            batch.add_column(
                sa.Column("level", sa.Integer(), nullable=False, server_default="0")
            )


def downgrade():
    op.drop_column("abilities", "level")
    op.drop_column("spells", "level")
