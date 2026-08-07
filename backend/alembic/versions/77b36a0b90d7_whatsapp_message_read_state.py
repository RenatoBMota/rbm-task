"""whatsapp message read state

Revision ID: 77b36a0b90d7
Revises: 36889e1687cc
Create Date: 2026-08-07 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '77b36a0b90d7'
down_revision: Union[str, None] = '36889e1687cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'whatsapp_messages',
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Messages already sent to the AI were necessarily seen; treat them as read.
    op.execute("UPDATE whatsapp_messages SET is_read = true WHERE is_processed = true")
    op.alter_column('whatsapp_messages', 'is_read', server_default=None)


def downgrade() -> None:
    op.drop_column('whatsapp_messages', 'is_read')
