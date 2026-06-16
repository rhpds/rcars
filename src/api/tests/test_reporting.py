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
        """No prod, zero usage, zero sales, high cost."""
        score = compute_retirement_score(
            provisions=0, experiences=0, touched_amount=0, closed_amount=0,
            total_cost=10000, has_prod=False, first_provision="",
        )
        assert score >= 85

    def test_healthy_asset(self):
        """Prod, high usage, high sales, reasonable cost."""
        score = compute_retirement_score(
            provisions=500, experiences=2000, touched_amount=100_000_000,
            closed_amount=20_000_000, total_cost=50000, has_prod=True,
            first_provision="2024-01-01",
        )
        assert score < 30

    def test_new_item_discount(self):
        """Recently published items get score reduction."""
        from datetime import datetime, timedelta
        recent = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        score = compute_retirement_score(
            provisions=5, experiences=5, touched_amount=0, closed_amount=0,
            total_cost=100, has_prod=True, first_provision=recent,
        )
        assert score <= 40

    def test_no_prod_adds_twenty(self):
        """Missing prod environment adds 20 points."""
        score_with = compute_retirement_score(
            provisions=200, experiences=1000, touched_amount=50_000_000,
            closed_amount=10_000_000, total_cost=30000, has_prod=True,
            first_provision="2024-01-01",
        )
        score_without = compute_retirement_score(
            provisions=200, experiences=1000, touched_amount=50_000_000,
            closed_amount=10_000_000, total_cost=30000, has_prod=False,
            first_provision="2024-01-01",
        )
        assert score_without == score_with + 20

    def test_high_cost_zero_sales(self):
        """High cost with zero closed sales adds 15 points."""
        score = compute_retirement_score(
            provisions=200, experiences=1000, touched_amount=50_000_000,
            closed_amount=0, total_cost=10000, has_prod=True,
            first_provision="2024-01-01",
        )
        assert score >= 15

    def test_score_capped_at_100(self):
        """Score should never exceed 100."""
        score = compute_retirement_score(
            provisions=0, experiences=0, touched_amount=0, closed_amount=0,
            total_cost=100000, has_prod=False, first_provision="2020-01-01",
        )
        assert score <= 100

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
