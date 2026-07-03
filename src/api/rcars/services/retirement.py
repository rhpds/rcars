"""Retirement workflow business logic."""
from __future__ import annotations

STEP_ORDER = [
    ("step_retired_at", "retired"),
    ("step_started_at", "started"),
    ("step_notified_at", "notified"),
    ("step_approved_at", "approved"),
    ("step_reviewed_at", "reviewed"),
]


def derive_status(fields: dict) -> str:
    """Derive the workflow status from the highest completed step."""
    for step_field, status in STEP_ORDER:
        if fields.get(step_field):
            return status
    return "reviewed"
