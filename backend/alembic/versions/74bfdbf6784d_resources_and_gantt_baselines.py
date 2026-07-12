"""resources, resource assignments, gantt baselines

Revision ID: 74bfdbf6784d
Revises: 40e92fa99ce2
Create Date: 2026-07-12 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '74bfdbf6784d'
down_revision: Union[str, None] = '40e92fa99ce2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'resources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('standard_rate', sa.Float(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'resource_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=False),
        sa.Column('allocation_percent', sa.Integer(), nullable=False),
        sa.Column('is_coordinator', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
        sa.ForeignKeyConstraint(['resource_id'], ['resources.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', 'resource_id', name='uq_resource_assignment'),
    )
    op.create_table(
        'gantt_baselines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'gantt_baseline_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('baseline_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['baseline_id'], ['gantt_baselines.id']),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('baseline_id', 'task_id', name='uq_baseline_task'),
    )


def downgrade() -> None:
    op.drop_table('gantt_baseline_tasks')
    op.drop_table('gantt_baselines')
    op.drop_table('resource_assignments')
    op.drop_table('resources')
