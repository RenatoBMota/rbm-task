"""fix task fk ondelete behavior

Revision ID: 22d81ae50bd8
Revises: 74bfdbf6784d
Create Date: 2026-07-12 15:13:05.314472

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '22d81ae50bd8'
down_revision: Union[str, None] = '74bfdbf6784d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("notifications_task_id_fkey", "notifications", type_="foreignkey")
    op.create_foreign_key(
        "notifications_task_id_fkey", "notifications", "tasks", ["task_id"], ["id"], ondelete="SET NULL"
    )

    op.drop_constraint("automation_logs_task_id_fkey", "automation_logs", type_="foreignkey")
    op.create_foreign_key(
        "automation_logs_task_id_fkey", "automation_logs", "tasks", ["task_id"], ["id"], ondelete="SET NULL"
    )

    op.drop_constraint("task_dependencies_task_id_fkey", "task_dependencies", type_="foreignkey")
    op.create_foreign_key(
        "task_dependencies_task_id_fkey", "task_dependencies", "tasks", ["task_id"], ["id"], ondelete="CASCADE"
    )

    op.drop_constraint("task_dependencies_depends_on_id_fkey", "task_dependencies", type_="foreignkey")
    op.create_foreign_key(
        "task_dependencies_depends_on_id_fkey", "task_dependencies", "tasks", ["depends_on_id"], ["id"], ondelete="CASCADE"
    )

    op.drop_constraint("tasks_parent_id_fkey", "tasks", type_="foreignkey")
    op.create_foreign_key(
        "tasks_parent_id_fkey", "tasks", "tasks", ["parent_id"], ["id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    op.drop_constraint("tasks_parent_id_fkey", "tasks", type_="foreignkey")
    op.create_foreign_key("tasks_parent_id_fkey", "tasks", "tasks", ["parent_id"], ["id"])

    op.drop_constraint("task_dependencies_depends_on_id_fkey", "task_dependencies", type_="foreignkey")
    op.create_foreign_key(
        "task_dependencies_depends_on_id_fkey", "task_dependencies", "tasks", ["depends_on_id"], ["id"]
    )

    op.drop_constraint("task_dependencies_task_id_fkey", "task_dependencies", type_="foreignkey")
    op.create_foreign_key("task_dependencies_task_id_fkey", "task_dependencies", "tasks", ["task_id"], ["id"])

    op.drop_constraint("automation_logs_task_id_fkey", "automation_logs", type_="foreignkey")
    op.create_foreign_key("automation_logs_task_id_fkey", "automation_logs", "tasks", ["task_id"], ["id"])

    op.drop_constraint("notifications_task_id_fkey", "notifications", type_="foreignkey")
    op.create_foreign_key("notifications_task_id_fkey", "notifications", "tasks", ["task_id"], ["id"])
