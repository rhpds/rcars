"""Tests for reporting sync utilities."""

import json
from unittest.mock import patch, MagicMock

from rcars.services.reporting_sync import extract_base_name, compute_retirement_score, mcp_query


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


class TestRetirementScore:
    def test_perfect_retirement_candidate(self):
        """Bottom percentile on everything, zero sales, high cost."""
        score = compute_retirement_score(
            provisions_zero=True, provisions_pct=0,
            touched_zero=True, touched_pct=0,
            closed_zero=True, closed_pct=0,
            total_cost=10000, closed_amount=0, first_provision="",
        )
        assert score >= 70

    def test_healthy_asset(self):
        """Top percentile on everything."""
        score = compute_retirement_score(
            provisions_zero=False, provisions_pct=90,
            touched_zero=False, touched_pct=90,
            closed_zero=False, closed_pct=90,
            total_cost=50000, closed_amount=5_000_000, first_provision="2024-01-01",
        )
        assert score < 10

    def test_new_item_discount(self):
        """Recently published items get score reduction."""
        from datetime import datetime, timedelta
        recent = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        score = compute_retirement_score(
            provisions_zero=True, provisions_pct=0,
            touched_zero=True, touched_pct=0,
            closed_zero=True, closed_pct=0,
            total_cost=100, closed_amount=0, first_provision=recent,
        )
        assert score <= 50

    def test_high_cost_zero_sales(self):
        """High cost with zero closed sales adds 15 points."""
        score = compute_retirement_score(
            provisions_zero=False, provisions_pct=60,
            touched_zero=False, touched_pct=60,
            closed_zero=True, closed_pct=0,
            total_cost=10000, closed_amount=0, first_provision="2024-01-01",
        )
        assert score >= 15

    def test_score_capped_at_100(self):
        """Score should never exceed 100."""
        score = compute_retirement_score(
            provisions_zero=True, provisions_pct=0,
            touched_zero=True, touched_pct=0,
            closed_zero=True, closed_pct=0,
            total_cost=100000, closed_amount=0, first_provision="2020-01-01",
        )
        assert score <= 100

    def test_median_item_moderate_score(self):
        """Item at p50 on everything should score moderately."""
        score = compute_retirement_score(
            provisions_zero=False, provisions_pct=50,
            touched_zero=False, touched_pct=50,
            closed_zero=False, closed_pct=50,
            total_cost=5000, closed_amount=500_000, first_provision="2024-01-01",
        )
        assert 5 <= score <= 30

    def test_zero_touched_always_penalized(self):
        """Zero touched gets full pipeline penalty regardless of percentile."""
        score_zero = compute_retirement_score(
            provisions_zero=False, provisions_pct=50,
            touched_zero=True, touched_pct=0,
            closed_zero=False, closed_pct=80,
            total_cost=0, closed_amount=1_000_000, first_provision="2024-01-01",
        )
        score_nonzero = compute_retirement_score(
            provisions_zero=False, provisions_pct=50,
            touched_zero=False, touched_pct=30,
            closed_zero=False, closed_pct=80,
            total_cost=0, closed_amount=1_000_000, first_provision="2024-01-01",
        )
        assert score_zero > score_nonzero

    def test_sales_impact_high(self):
        from rcars.services.reporting_sync import compute_sales_impact
        assert compute_sales_impact(1_500_000) == "high"

    def test_sales_impact_moderate(self):
        from rcars.services.reporting_sync import compute_sales_impact
        assert compute_sales_impact(500_000) == "moderate"

    def test_sales_impact_low(self):
        from rcars.services.reporting_sync import compute_sales_impact
        assert compute_sales_impact(50_000) == "low"


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
