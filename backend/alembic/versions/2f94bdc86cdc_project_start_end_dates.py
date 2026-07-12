"""project start end dates

Revision ID: 2f94bdc86cdc
Revises: 22d81ae50bd8
Create Date: 2026-07-12 15:51:45.459737

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2f94bdc86cdc'
down_revision: Union[str, None] = '22d81ae50bd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("start_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("end_date", sa.DateTime(timezone=True), nullable=True))

    # Backfill so the new NOT NULL constraint doesn't clash with existing task dates:
    # the project window is widened to cover the earliest/latest dates already used
    # by its tasks (falling back to created_at / created_at+90d when there are none).
    op.execute(
        """
        UPDATE projects p
        SET start_date = LEAST(
                p.created_at,
                COALESCE(
                    (SELECT MIN(t.start_date) FROM tasks t WHERE t.project_id = p.id AND t.start_date IS NOT NULL),
                    p.created_at
                )
            ),
            end_date = GREATEST(
                p.created_at + interval '90 days',
                COALESCE(
                    (SELECT MAX(t.due_date) FROM tasks t WHERE t.project_id = p.id AND t.due_date IS NOT NULL),
                    p.created_at + interval '90 days'
                )
            )
        """
    )

    op.alter_column("projects", "start_date", nullable=False)
    op.alter_column("projects", "end_date", nullable=False)


def downgrade() -> None:
    op.drop_column("projects", "end_date")
    op.drop_column("projects", "start_date")
