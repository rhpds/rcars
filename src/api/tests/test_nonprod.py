import pytest
from rcars.db.database import SCHEMA_SQL


class TestNonprodSchema:
    def test_nonprod_usage_table_in_schema(self):
        assert "CREATE TABLE IF NOT EXISTS nonprod_usage" in SCHEMA_SQL

    def test_nonprod_usage_has_windowed_metrics(self):
        assert "windowed_metrics" in SCHEMA_SQL.split("nonprod_usage")[1].split(");")[0]

    def test_nonprod_usage_has_ignored_until(self):
        assert "ignored_until" in SCHEMA_SQL.split("nonprod_usage")[1].split(");")[0]
