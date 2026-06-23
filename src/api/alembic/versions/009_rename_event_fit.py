"""Rename event_fit_json to format_suitability_json in showroom_analysis.

Removes legacy "event" terminology from the schema. The field tracks
whether content is suitable as a demo vs hands-on lab, not event fit.

Revision ID: 009
Revises: 008
Create Date: 2026-06-23
"""
from typing import Sequence, Union

from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE showroom_analysis
        RENAME COLUMN event_fit_json TO format_suitability_json;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE showroom_analysis
        RENAME COLUMN format_suitability_json TO event_fit_json;
    """)
