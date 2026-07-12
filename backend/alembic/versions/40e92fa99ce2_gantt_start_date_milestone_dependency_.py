"""gantt: task start_date/is_milestone, dependency type/lag/hardness

Revision ID: 40e92fa99ce2
Revises: 0ccf73633dde
Create Date: 2026-07-12 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '40e92fa99ce2'
down_revision: Union[str, None] = '0ccf73633dde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('start_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'tasks',
        sa.Column('is_milestone', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    dependency_type_enum = postgresql.ENUM(
        'FINISH_START', 'START_START', 'FINISH_FINISH', 'START_FINISH', name='dependencytype'
    )
    dependency_type_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'task_dependencies',
        sa.Column(
            'dependency_type', dependency_type_enum, nullable=False, server_default='FINISH_START'
        ),
    )
    op.add_column(
        'task_dependencies',
        sa.Column('lag_days', sa.Integer(), nullable=False, server_default='0'),
    )
    dependency_hardness_enum = postgresql.ENUM('STRONG', 'RUBBER', name='dependencyhardness')
    dependency_hardness_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'task_dependencies',
        sa.Column('hardness', dependency_hardness_enum, nullable=False, server_default='STRONG'),
    )


def downgrade() -> None:
    op.drop_column('task_dependencies', 'hardness')
    postgresql.ENUM(name='dependencyhardness').drop(op.get_bind(), checkfirst=True)
    op.drop_column('task_dependencies', 'lag_days')
    op.drop_column('task_dependencies', 'dependency_type')
    postgresql.ENUM(name='dependencytype').drop(op.get_bind(), checkfirst=True)
    op.drop_column('tasks', 'is_milestone')
    op.drop_column('tasks', 'start_date')
