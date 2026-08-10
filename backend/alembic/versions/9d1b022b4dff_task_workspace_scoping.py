"""task workspace scoping

Revision ID: 9d1b022b4dff
Revises: 77b36a0b90d7
Create Date: 2026-08-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9d1b022b4dff'
down_revision: Union[str, None] = '77b36a0b90d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('workspace_id', sa.Integer(), nullable=True))

    # Project-linked tasks: inherit the project's workspace.
    op.execute(
        """
        UPDATE tasks SET workspace_id = projects.workspace_id
        FROM projects
        WHERE tasks.project_id = projects.id
        """
    )

    # Standalone ("Agenda diária") tasks never had a workspace concept -
    # backfill to the assignee's earliest workspace membership (for most
    # users, their only one).
    op.execute(
        """
        UPDATE tasks SET workspace_id = sub.workspace_id
        FROM (
            SELECT DISTINCT ON (user_id) user_id, workspace_id
            FROM workspace_members
            ORDER BY user_id, id ASC
        ) sub
        WHERE tasks.workspace_id IS NULL AND tasks.assignee_id = sub.user_id
        """
    )

    # Last-resort fallback for any task with no assignee and no project
    # (shouldn't happen - create_task always sets an assignee).
    op.execute(
        """
        UPDATE tasks SET workspace_id = (SELECT MIN(id) FROM workspaces)
        WHERE tasks.workspace_id IS NULL
        """
    )

    op.alter_column('tasks', 'workspace_id', nullable=False)
    op.create_foreign_key(
        "fk_tasks_workspace_id_workspaces", "tasks", "workspaces", ["workspace_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_tasks_workspace_id_workspaces", "tasks", type_='foreignkey')
    op.drop_column('tasks', 'workspace_id')
