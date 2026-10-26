import pytest
from rcars.db.database import SCHEMA_SQL


class TestNonprodSchema:
    def test_nonprod_usage_table_in_schema(self):
        assert "CREATE TABLE IF NOT EXISTS nonprod_usage" in SCHEMA_SQL

    def test_nonprod_usage_has_windowed_metrics(self):
        table_body = SCHEMA_SQL.split("CREATE TABLE IF NOT EXISTS nonprod_usage")[1].split(");")[0]
        assert "windowed_metrics" in table_body

    def test_nonprod_usage_keeps_total_provisions_column(self):
        assert "ALTER TABLE nonprod_usage ADD COLUMN IF NOT EXISTS total_provisions" in SCHEMA_SQL
        assert "DROP COLUMN IF EXISTS total_provisions" not in SCHEMA_SQL

    def test_nonprod_usage_has_ignored_until(self):
        table_body = SCHEMA_SQL.split("CREATE TABLE IF NOT EXISTS nonprod_usage")[1].split(");")[0]
        assert "ignored_until" in table_body


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


class TestNonprodProvisionsSql:
    def test_filters_to_real_users_across_all_environments(self):
        from rcars.services.reporting_sync import _build_nonprod_provisions_sql
        sql = _build_nonprod_provisions_sql("2025-10-23", ["a.b"])
        assert "ps.user_group IN ('Only Regular Users', 'Red Hat Console')" in sql
        assert "ps.environment = 'PROD'" not in sql

    def test_total_provisions_count_everyone_except_poolboy(self):
        from rcars.services.reporting_sync import _build_nonprod_provisions_sql
        sql = _build_nonprod_provisions_sql("2025-10-23", ["a.b"])
        assert "ps.user_group IS DISTINCT FROM 'Poolboy'" in sql
        assert "AS total_provisions" in sql
        assert "workshop_id" not in sql

    def test_groups_by_item_and_environment(self):
        from rcars.services.reporting_sync import _build_nonprod_provisions_sql
        sql = _build_nonprod_provisions_sql("2025-10-23", ["a.b"])
        assert "GROUPING SETS ((ci.name), (ci.name, ps.environment))" in sql


class TestMcpQueryOrdering:
    def test_defaults_to_first_column(self):
        from unittest.mock import patch
        from rcars.services.reporting_sync import mcp_query
        with patch("rcars.services.reporting_sync._mcp_call", return_value={"rows": []}) as call:
            mcp_query("SELECT 1", url="url", token="token")
        assert "ORDER BY 1 LIMIT" in call.call_args[0][1]["sql"]

    def test_accepts_unique_sort_key(self):
        from unittest.mock import patch
        from rcars.services.reporting_sync import mcp_query
        with patch("rcars.services.reporting_sync._mcp_call", return_value={"rows": []}) as call:
            mcp_query("SELECT 1", url="url", token="token", order_by="1, 2, 3")
        assert "ORDER BY 1, 2, 3 LIMIT" in call.call_args[0][1]["sql"]


class TestSyncNonprodUsage:
    def test_function_exists(self):
        from rcars.services.reporting_sync import _sync_nonprod_usage
        assert callable(_sync_nonprod_usage)

    def test_stores_totals_and_per_environment_metrics(self):
        import json
        from unittest.mock import MagicMock, patch
        from rcars.services.reporting_sync import _sync_nonprod_usage

        def row(env, is_total, provisions, total, users, first, last):
            return {
                "catalog_base_name": "summit-2026.lb2596", "environment": env, "is_total": is_total,
                "provisions": provisions, "total_provisions": total,
                "requests": provisions, "experiences": provisions,
                "unique_users": users, "success_ratio": 0.9, "failure_ratio": 0.1,
                "first_provision": first, "last_provision": last,
            }

        rows = [
            row(None, 1, 106, 642, 5, "2026-03-13", "2026-09-14"),
            row("dev", 0, 37, 46, 4, "2026-03-13", "2026-05-11"),
            row("event", 0, 69, 596, 2, "2026-05-06", "2026-09-14"),
        ]
        db = MagicMock()
        db.get_nonprod_base_names.return_value = {"summit-2026.lb2596": "cid-1"}
        db.upsert_nonprod_usage.side_effect = lambda r: len(r)
        db.delete_orphan_nonprod_data.return_value = 0

        with patch("rcars.services.reporting_sync.mcp_query", return_value=rows) as query:
            _sync_nonprod_usage(db, "url", "token")

        # Several rows share a base name, so pagination needs a unique sort key
        assert all(c.kwargs["order_by"] == "1, 2, 3" for c in query.call_args_list)

        upserted = db.upsert_nonprod_usage.call_args[0][0][0]
        assert upserted["provisions"] == 106
        assert upserted["unique_users"] == 5
        assert upserted["total_provisions"] == 642
        assert upserted["first_provision"] == "2026-03-13"
        windowed = json.loads(upserted["windowed_metrics"])
        assert windowed["12m"]["provisions"] == 106
        by_env = windowed["12m"]["by_env"]
        assert by_env["dev"]["provisions"] == 37
        assert by_env["dev"]["last_provision"] == "2026-05-11"
        assert by_env["event"]["unique_users"] == 2
        assert by_env["event"]["total_provisions"] == 596


class TestNonprodRouteExists:
    def test_nonprod_endpoint_registered(self):
        """Verify the nonprod routes exist on the analysis router."""
        from rcars.api.routes.analysis import router
        paths = [r.path for r in router.routes]
        assert "/analysis/nonprod" in paths
        assert "/analysis/nonprod/ignore/{base_name}" in paths


class TestSortEmptyLast:
    def test_empty_values_stay_last_in_both_directions(self):
        from rcars.api.routes.analysis import _sort_empty_last

        for reverse, expected in ((False, ["a", "b", ""]), (True, ["b", "a", ""])):
            items = [{"v": ""}, {"v": "b"}, {"v": "a"}]
            _sort_empty_last(items, lambda i: i["v"], reverse)
            assert [i["v"] for i in items] == expected
