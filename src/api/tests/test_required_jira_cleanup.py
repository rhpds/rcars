from unittest.mock import Mock

import pytest

from rcars.services import jira


@pytest.mark.parametrize("helper,resolution", [("close_issue_wont_do", "Won't Do"), ("close_issue_done", "Done")])
def test_required_closure_selects_resolution_and_verifies_result(monkeypatch, helper, resolution):
    calls = []
    def request(settings, path, method="POST", body=None):
        calls.append((path, method, body))
        if path.endswith("?fields=status,resolution"):
            return {"fields": {"status": {"name": "Done" if len(calls) > 2 else "Open", "statusCategory": {"key": "done" if len(calls) > 2 else "new"}}, "resolution": {"name": resolution} if len(calls) > 2 else None}}
        if method == "GET":
            return {"transitions": [{"id": "31", "to": {"name": "Done"}}]}
        return None
    monkeypatch.setattr(jira, "_jira_request", request)
    close = getattr(jira, helper, lambda *args: False)
    assert close(object(), "EXAMPLE-1") is True
    posted = [body for _, method, body in calls if method == "POST"]
    assert posted == [{"transition": {"id": "31"}, "fields": {"resolution": {"name": resolution}}}]
    assert calls[-1][1] == "GET"


def test_already_closed_issue_needs_no_transition(monkeypatch):
    calls = []
    def request(*args, **kwargs):
        calls.append(kwargs.get("method"))
        return {"fields": {"status": {"name": "Archived", "statusCategory": {"key": "done"}}, "resolution": {"name": "Done"}}}
    monkeypatch.setattr(jira, "_jira_request", request)
    assert jira.close_issue_wont_do(object(), "EXAMPLE-1") is True
    assert calls == ["GET"]


def test_closure_requires_a_terminal_result(monkeypatch):
    monkeypatch.setattr(jira, "_jira_request", Mock(side_effect=[
        {"fields": {"status": {"name": "Open"}, "resolution": None}},
        {"transitions": [{"id": "31", "to": {"name": "Done"}}]},
        None,
        {"fields": {"status": {"name": "Open"}, "resolution": None}},
    ]))
    with pytest.raises(RuntimeError):
        jira.close_issue_wont_do(object(), "EXAMPLE-1")


def test_new_closure_requires_the_requested_resolution(monkeypatch):
    monkeypatch.setattr(jira, "_jira_request", Mock(side_effect=[
        {"fields": {"status": {"name": "Open"}}},
        {"transitions": [{"id": "31", "to": {"name": "Done"}}]},
        None,
        {"fields": {"status": {"name": "Done"}, "resolution": {"name": "Duplicate"}}},
    ]))
    with pytest.raises(RuntimeError):
        jira.close_issue_done(object(), "EXAMPLE-1")
