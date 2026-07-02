"""Tests for retirement workflow business logic (derive_status)."""

import pytest
from datetime import datetime, timezone

from rcars.services.retirement import derive_status, STEP_ORDER


class TestDeriveStatus:
    """Test derive_status with various step combinations."""

    def test_no_steps_returns_reviewed(self):
        """With no step timestamps, status defaults to 'reviewed'."""
        assert derive_status({}) == "reviewed"

    def test_empty_fields_returns_reviewed(self):
        """Explicitly None/falsy fields still return 'reviewed'."""
        fields = {
            "step_reviewed_at": None,
            "step_approved_at": None,
            "step_notified_at": None,
            "step_started_at": None,
            "step_retired_at": None,
        }
        assert derive_status(fields) == "reviewed"

    def test_reviewed_step_only(self):
        """With only step_reviewed_at set, status is 'reviewed'."""
        fields = {"step_reviewed_at": datetime.now(timezone.utc)}
        assert derive_status(fields) == "reviewed"

    def test_approved_step(self):
        """With step_approved_at set, status is 'approved'."""
        fields = {
            "step_reviewed_at": datetime.now(timezone.utc),
            "step_approved_at": datetime.now(timezone.utc),
        }
        assert derive_status(fields) == "approved"

    def test_notified_step(self):
        """With step_notified_at set, status is 'notified'."""
        fields = {
            "step_reviewed_at": datetime.now(timezone.utc),
            "step_approved_at": datetime.now(timezone.utc),
            "step_notified_at": datetime.now(timezone.utc),
        }
        assert derive_status(fields) == "notified"

    def test_started_step(self):
        """With step_started_at set, status is 'started'."""
        fields = {
            "step_reviewed_at": datetime.now(timezone.utc),
            "step_approved_at": datetime.now(timezone.utc),
            "step_notified_at": datetime.now(timezone.utc),
            "step_started_at": datetime.now(timezone.utc),
        }
        assert derive_status(fields) == "started"

    def test_retired_step(self):
        """With step_retired_at set, status is 'retired'."""
        fields = {
            "step_reviewed_at": datetime.now(timezone.utc),
            "step_approved_at": datetime.now(timezone.utc),
            "step_notified_at": datetime.now(timezone.utc),
            "step_started_at": datetime.now(timezone.utc),
            "step_retired_at": datetime.now(timezone.utc),
        }
        assert derive_status(fields) == "retired"

    def test_highest_step_wins(self):
        """If retired_at is set but earlier steps are missing, retired still wins."""
        fields = {
            "step_retired_at": datetime.now(timezone.utc),
        }
        assert derive_status(fields) == "retired"

    def test_skipped_intermediate_steps(self):
        """If started_at is set but notified is not, started still wins."""
        fields = {
            "step_reviewed_at": datetime.now(timezone.utc),
            "step_started_at": datetime.now(timezone.utc),
        }
        assert derive_status(fields) == "started"

    def test_unrelated_fields_ignored(self):
        """Extra fields in the dict don't affect status derivation."""
        fields = {
            "catalog_base_name": "some/item",
            "curator_notes": "test note",
            "jira_key": "RHDPCD-99",
            "step_approved_at": datetime.now(timezone.utc),
        }
        assert derive_status(fields) == "approved"

    def test_falsy_zero_value_treated_as_no_step(self):
        """Falsy values (0, empty string, False) are treated as step not completed."""
        fields = {
            "step_retired_at": 0,
            "step_started_at": "",
            "step_notified_at": False,
            "step_approved_at": datetime.now(timezone.utc),
        }
        assert derive_status(fields) == "approved"


class TestStepOrder:
    """Validate STEP_ORDER constant structure."""

    def test_step_order_has_five_entries(self):
        assert len(STEP_ORDER) == 5

    def test_step_order_highest_first(self):
        """Retired should be first (highest priority), reviewed last."""
        assert STEP_ORDER[0][1] == "retired"
        assert STEP_ORDER[-1][1] == "reviewed"

    def test_all_statuses_present(self):
        statuses = {s for _, s in STEP_ORDER}
        assert statuses == {"reviewed", "approved", "notified", "started", "retired"}
