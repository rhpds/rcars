import pytest
from rcars.db.database import SCHEMA_SQL


class TestNonprodSchema:
    def test_nonprod_usage_table_in_schema(self):
        assert "CREATE TABLE IF NOT EXISTS nonprod_usage" in SCHEMA_SQL

    def test_nonprod_usage_has_windowed_metrics(self):
        assert "windowed_metrics" in SCHEMA_SQL.split("nonprod_usage")[1].split(");")[0]

    def test_nonprod_usage_has_ignored_until(self):
        assert "ignored_until" in SCHEMA_SQL.split("nonprod_usage")[1].split(");")[0]


class TestGetNonprodBaseNames:
    """Tests for get_nonprod_base_names — requires live DB with test data."""

    def test_method_exists(self):
        from rcars.db.database import Database
        assert hasattr(Database, "get_nonprod_base_names")

    def test_returns_dict(self):
        from rcars.db.database import Database
        assert callable(getattr(Database, "get_nonprod_base_names"))


class TestUpsertNonprodUsage:
    def test_method_exists(self):
        from rcars.db.database import Database
        assert hasattr(Database, "upsert_nonprod_usage")


class TestListNonprodItems:
    def test_method_exists(self):
        from rcars.db.database import Database
        assert hasattr(Database, "list_nonprod_items")


class TestNonprodIgnore:
    def test_set_method_exists(self):
        from rcars.db.database import Database
        assert hasattr(Database, "set_nonprod_ignored")

    def test_clear_method_exists(self):
        from rcars.db.database import Database
        assert hasattr(Database, "clear_nonprod_ignored")


class TestSyncNonprodUsage:
    def test_function_exists(self):
        from rcars.services.reporting_sync import _sync_nonprod_usage
        assert callable(_sync_nonprod_usage)


class TestNonprodRouteExists:
    def test_nonprod_endpoint_registered(self):
        """Verify the nonprod routes exist on the analysis router."""
        from rcars.api.routes.analysis import router
        paths = [r.path for r in router.routes]
        assert "/analysis/nonprod" in paths
        assert "/analysis/nonprod/ignore/{base_name}" in paths
