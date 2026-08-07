"""whatsapp multi-chat support

Revision ID: 36889e1687cc
Revises: 8c340f4d38c6
Create Date: 2026-08-07 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '36889e1687cc'
down_revision: Union[str, None] = '8c340f4d38c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('whatsapp_messages', sa.Column('chat_jid', sa.String(length=128), nullable=True))
    op.add_column('whatsapp_messages', sa.Column('chat_name', sa.String(length=255), nullable=True))
    op.add_column(
        'whatsapp_messages',
        sa.Column('is_from_me', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column('whatsapp_messages', 'is_from_me', server_default=None)

    # Backfill existing rows from the (now removed) single monitored chat per connection.
    op.execute(
        """
        UPDATE whatsapp_messages
        SET chat_jid = whatsapp_connections.monitored_chat_jid,
            chat_name = whatsapp_connections.monitored_chat_name
        FROM whatsapp_connections
        WHERE whatsapp_messages.connection_id = whatsapp_connections.id
        """
    )

    op.drop_column('whatsapp_connections', 'monitored_chat_jid')
    op.drop_column('whatsapp_connections', 'monitored_chat_name')


def downgrade() -> None:
    op.add_column('whatsapp_connections', sa.Column('monitored_chat_jid', sa.String(length=128), nullable=True))
    op.add_column('whatsapp_connections', sa.Column('monitored_chat_name', sa.String(length=255), nullable=True))

    op.drop_column('whatsapp_messages', 'is_from_me')
    op.drop_column('whatsapp_messages', 'chat_name')
    op.drop_column('whatsapp_messages', 'chat_jid')
