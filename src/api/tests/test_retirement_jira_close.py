from unittest.mock import Mock

import pytest

from rcars.services import jira


@pytest.mark.parametrize("transitions, expected", [([], False), ([{"id": "1", "to": {"name": "Done"}}], True)])
def test_jira_close_reports_whether_it_transitioned(monkeypatch, transitions, expected):
    monkeypatch.setattr(jira, "_jira_request", Mock(side_effect=[
        {"fields": {"status": {"name": "Open"}}}, {"transitions": transitions}, None,
        {"fields": {"status": {"name": "Done"}, "resolution": {"name": "Won't Do"}}},
    ]))
    assert jira.close_issue_wont_do(object(), "EXAMPLE-1") is expected
