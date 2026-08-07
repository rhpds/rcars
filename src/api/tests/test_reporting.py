"""Tests for reporting sync utilities."""

import json
from unittest.mock import patch, MagicMock

from rcars.services.reporting_sync import (
    extract_base_name, compute_performance_score, compute_performance_score_breakdown, mcp_query,
    _window_start, _build_windowed_metrics, WINDOW_DAYS,
)


class TestExtractBaseName:
    def test_prod_suffix(self):
        assert extract_base_name("sandboxes-gpte.sandbox-open.prod") == "sandboxes-gpte.sandbox-open"

    def test_dev_suffix(self):
        assert extract_base_name("openshift-cnv.ocp-virt-advanced.dev") == "openshift-cnv.ocp-virt-advanced"

    def test_event_suffix(self):
        assert extract_base_name("partner.ocp-virt-roadshow.event") == "partner.ocp-virt-roadshow"

    def test_test_suffix(self):
        assert extract_base_name("agd-v2.something.test") == "agd-v2.something"

    def test_no_suffix(self):
        assert extract_base_name("some-name-without-stage") == "some-name-without-stage"

    def test_dotted_name_with_suffix(self):
        assert extract_base_name("a.b.c.prod") == "a.b.c"


class TestComputePerformanceScore:
    def test_zero_activity_scores_zero(self):
        score = compute_performance_score(
            provisions_zero=True, provisions_pct=0,
            touched_zero=True, touched_pct=0,
            closed_zero=True, closed_pct=0,
            total_cost=0, closed_amount=0,
        )
        assert score == 0

    def test_top_performer_scores_high(self):
        score = compute_performance_score(
            provisions_zero=False, provisions_pct=90, provisions_raw=612,
            touched_zero=False, touched_pct=90, touched_raw=3_800_000,
            closed_zero=False, closed_pct=90,
            total_cost=50_000, closed_amount=4_200_000,
            roi_zero=False, roi_pct=90,
        )
        # 25 (usage) + 15 (pipeline) + 25 (closed) + round(15*0.90)=14 → 79
        assert score >= 75

    def test_high_cost_zero_sales_gets_zero_roi_points(self):
        breakdown = compute_performance_score_breakdown(
            provisions_zero=False, provisions_pct=80, provisions_raw=100,
            touched_zero=True, touched_pct=0,
            closed_zero=True, closed_pct=0,
            total_cost=50_000, closed_amount=0,
            roi_zero=True, roi_pct=0,
        )
        roi = next(f for f in breakdown["factors"] if f["factor"] == "roi")
        assert roi["points"] == 0
        assert roi["level"] == "none"

    def test_median_item_moderate_score(self):
        score = compute_performance_score(
            provisions_zero=False, provisions_pct=45, provisions_raw=28,
            touched_zero=False, touched_pct=45, touched_raw=120_000,
            closed_zero=False, closed_pct=45,
            total_cost=8_000, closed_amount=90_000,
            roi_zero=False, roi_pct=45,
        )
        # 15 + 5 + 10 + round(15*0.45)=7 → 37: moderate band
        assert 35 <= score < 55

    def test_no_age_discount_parameter(self):
        import inspect
        from rcars.services.reporting_sync import _compute_performance_score_with_breakdown
        params = inspect.signature(_compute_performance_score_with_breakdown).parameters
        assert "first_provision" not in params

    def test_breakdown_has_no_age_discount_key(self):
        breakdown = compute_performance_score_breakdown(
            provisions_zero=True, provisions_pct=0,
            touched_zero=True, touched_pct=0,
            closed_zero=True, closed_pct=0,
            total_cost=0, closed_amount=0,
        )
        assert "age_discount" not in breakdown
        assert breakdown["score"] == 0

    def test_sales_impact_high(self):
        from rcars.services.reporting_sync import compute_sales_impact
        assert compute_sales_impact(1_500_000) == "high"

    def test_sales_impact_moderate(self):
        from rcars.services.reporting_sync import compute_sales_impact
        assert compute_sales_impact(500_000) == "moderate"

    def test_sales_impact_low(self):
        from rcars.services.reporting_sync import compute_sales_impact
        assert compute_sales_impact(50_000) == "low"


class TestWindowStart:
    def test_3m_returns_91_days_back(self):
        from datetime import datetime, timedelta
        result = _window_start("3m")
        expected = (datetime.now() - timedelta(days=91)).strftime("%Y-%m-%d")
        assert result == expected

    def test_6m_returns_182_days_back(self):
        from datetime import datetime, timedelta
        result = _window_start("6m")
        expected = (datetime.now() - timedelta(days=182)).strftime("%Y-%m-%d")
        assert result == expected

    def test_12m_returns_365_days_back(self):
        from datetime import datetime, timedelta
        result = _window_start("12m")
        expected = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        assert result == expected

    def test_all_window_keys_covered(self):
        assert set(WINDOW_DAYS.keys()) == {"3m", "6m", "9m", "12m"}


class TestBuildWindowedMetrics:
    def test_basic_structure(self):
        """Windowed metrics should have entries for all four windows."""
        names = {"item-a", "item-b"}
        w_provisions = {
            wk: {"item-a": {"provisions": 10, "experiences": 5, "requests": 3,
                            "unique_users": 4, "success_ratio": 0.9, "failure_ratio": 0.1}}
            for wk in WINDOW_DAYS
        }
        w_touched = {wk: {"item-a": 50000.0} for wk in WINDOW_DAYS}
        w_closed = {wk: {"item-a": 20000.0} for wk in WINDOW_DAYS}
        w_cost = {wk: {"item-a": 5000.0} for wk in WINDOW_DAYS}
        w_uu = {wk: {"item-a": 7} for wk in WINDOW_DAYS}

        result = _build_windowed_metrics(
            names, w_provisions, w_touched, w_closed, w_cost, w_uu,
        )

        assert "item-a" in result
        assert "item-b" in result
        for wk in WINDOW_DAYS:
            assert wk in result["item-a"]
            entry = result["item-a"][wk]
            assert entry["provisions"] == 10
            assert entry["unique_users"] == 7
            assert entry["pipeline_touched"] == 50000.0
            assert entry["closed_amount"] == 20000.0
            assert entry["total_cost"] == 5000.0
            assert "performance_score" in entry
            assert "sales_impact" in entry
            assert entry["avg_cost_per_provision"] == 500.0

    def test_zero_item_gets_min_performance_score(self):
        """An item with zero provisions/sales in a window should score 0."""
        names = {"zero-item"}
        empty = {wk: {} for wk in WINDOW_DAYS}
        result = _build_windowed_metrics(
            names, empty, empty, empty, empty, empty,
        )
        for wk in WINDOW_DAYS:
            assert result["zero-item"][wk]["provisions"] == 0
            assert result["zero-item"][wk]["performance_score"] == 0

    def test_percentile_ranking_varies_across_items(self):
        """Items with different provision counts should get different scores."""
        names = {"high", "low"}
        w_provisions = {
            wk: {
                "high": {"provisions": 100, "experiences": 0, "requests": 0,
                         "success_ratio": 1.0, "failure_ratio": 0.0},
                "low": {"provisions": 1, "experiences": 0, "requests": 0,
                         "success_ratio": 1.0, "failure_ratio": 0.0},
            }
            for wk in WINDOW_DAYS
        }
        w_touched = {wk: {"high": 500000.0, "low": 1000.0} for wk in WINDOW_DAYS}
        w_closed = {wk: {"high": 200000.0, "low": 500.0} for wk in WINDOW_DAYS}
        w_cost = {wk: {"high": 10000.0, "low": 100.0} for wk in WINDOW_DAYS}
        w_uu = {wk: {} for wk in WINDOW_DAYS}

        result = _build_windowed_metrics(
            names, w_provisions, w_touched, w_closed, w_cost, w_uu,
        )
        for wk in WINDOW_DAYS:
            assert result["high"][wk]["performance_score"] > result["low"][wk]["performance_score"]


class TestMcpPagination:
    def _mock_response(self, rows: list[dict], row_count: int | None = None):
        """Build a mock urllib response for an MCP query result."""
        text = json.dumps({
            "columns": list(rows[0].keys()) if rows else [],
            "rows": rows,
            "row_count": row_count or len(rows),
            "truncated": len(rows) >= 500,
        })
        body = json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "result": {"content": [{"type": "text", "text": text}]},
        }).encode()
        resp = MagicMock()
        resp.read.return_value = body
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    @patch("rcars.services.reporting_sync.urllib.request.urlopen")
    def test_single_page(self, mock_urlopen):
        rows = [{"name": f"item-{i}"} for i in range(100)]
        mock_urlopen.return_value = self._mock_response(rows)
        result = mcp_query("SELECT 1", url="https://test", token="tok")
        assert len(result) == 100

    @patch("rcars.services.reporting_sync.urllib.request.urlopen")
    def test_auto_pagination(self, mock_urlopen):
        page1 = [{"name": f"item-{i}"} for i in range(500)]
        page2 = [{"name": f"item-{i}"} for i in range(500, 623)]
        mock_urlopen.side_effect = [
            self._mock_response(page1),
            self._mock_response(page2),
        ]
        result = mcp_query("SELECT 1", url="https://test", token="tok")
        assert len(result) == 623
