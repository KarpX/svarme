"""Add chat_id to game table

Revision ID: add_chat_id_to_game
Revises: 32dc53ea9fba
Create Date: 2026-03-11 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'add_chat_id_to_game'
down_revision: Union[str, None] = '32dc53ea9fba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('game', sa.Column('chat_id', sa.BigInteger(), nullable=False, server_default='0'))
    op.alter_column('game', 'chat_id', server_default=None)


def downgrade() -> None:
    op.drop_column('game', 'chat_id')
