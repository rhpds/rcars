"""Retirement routes must not act while another worker holds the workflow lock."""

from datetime import date, timedelta

import pytest

from rcars.services.retirement_cleanup import workflow_lock_id
from tests.test_retirement_pr_status import BASE_NAME, CONTENT_ID, client, db  # noqa: F401

URL = f"/api/v1/analysis/retirement/workflow/{BASE_NAME}"
FUTURE = (date.today() + timedelta(days=90)).isoformat()

# (method, path suffix, json body, workflow state the route needs)
ROUTES = [
    ("put", "/review", None, "approved"),
    ("put", "/approve", {"reason": "Low usage"}, "approved"),
    ("put", "/notify", None, "approved"),
    ("put", "/link-jira", {"jira_key": "EXAMPLE-9"}, "approved"),
    ("put", "/edit", {"retirement_target_date": FUTURE}, "started"),
    ("put", "/notes", {"notes": "changed"}, "started"),
    ("delete", "", None, "started"),
]


def _prepare(db, state):
    if state == "approved":
        db.delete_retirement_workflow(CONTENT_ID)
        db.upsert_retirement_workflow(CONTENT_ID, {"status": "approved", "step_approved_at": "NOW()"})
    else:
        db.upsert_retirement_workflow(CONTENT_ID, {"jira_key": "EXAMPLE-1", "agv_retire_pr_url": None})


@pytest.mark.parametrize("method,suffix,body,state", ROUTES, ids=[r[1] or "cancel" for r in ROUTES])
def test_route_rejects_when_workflow_lock_held(client, db, method, suffix, body, state):
    # Another API worker holds the lock: this request is a duplicate and must change nothing.
    _prepare(db, state)
    before = db.get_retirement_workflow(CONTENT_ID)
    with db.advisory_lock(workflow_lock_id(CONTENT_ID)) as acquired:
        assert acquired
        response = getattr(client, method)(URL + suffix, **({"json": body} if body is not None else {}))
    assert response.status_code == 409
    after = db.get_retirement_workflow(CONTENT_ID)
    if method == "delete":
        # Cancel records its intent before the lock so the running cleanup finishes it.
        assert after is not None and after["jira_key"] == before["jira_key"]
        assert after["step_retired_at"] is None
    else:
        assert after == before


@pytest.mark.parametrize("method,suffix,body,state", ROUTES, ids=[r[1] or "cancel" for r in ROUTES])
def test_route_releases_lock_after_request(client, db, method, suffix, body, state):
    _prepare(db, state)
    response = getattr(client, method)(URL + suffix, **({"json": body} if body is not None else {}))
    assert response.status_code != 409, response.text
    with db.advisory_lock(workflow_lock_id(CONTENT_ID)) as acquired:
        assert acquired
