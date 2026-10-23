"""Retirement workflow business logic."""
from __future__ import annotations

STEP_ORDER = [
    ("step_retired_at", "retired"),
    ("step_started_at", "started"),
    ("step_notified_at", "notified"),
    ("step_approved_at", "approved"),
    ("step_reviewed_at", "reviewed"),
]


RETIREMENT_LABELS = {
    "approved": "recommended",
    "notified": "recommended",
    "started": "in_progress",
    "retired": "retired",
}


def retirement_label(status: str | None) -> str | None:
    """API-friendly label for an approved workflow status (None if not retiring)."""
    return RETIREMENT_LABELS.get(status) if status else None


def derive_status(fields: dict) -> str:
    """Derive the workflow status from the highest completed step."""
    for step_field, status in STEP_ORDER:
        if fields.get(step_field):
            return status
    return "reviewed"
