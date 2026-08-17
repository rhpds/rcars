import asyncio
import os
from rcars.services.chat import handlers
from rcars.services.chat.models import RouterOutput
from rcars.services.chat.router import Resolution
from rcars.config import Settings
from tests.chat_fixtures import seed_chat_fixtures
import pytest
from tests.test_db import db  # Import the db fixture

TEST_DB_URL = os.environ.get(
    "RCARS_TEST_DATABASE_URL",
    "postgresql://rcars:dev@localhost:5432/rcars_test",
)


async def _noop(data):
    pass


def _res(intent, ids=None, items=None, args=None):
    return Resolution(kind="execute",
                      output=RouterOutput(intent=intent, confidence=1.0, args=args or {}),
                      scope_ids=ids or [], items=items or [])


def _settings():
    return Settings(database_url=TEST_DB_URL, redis_url="redis://localhost:6379")


def test_overlap_handler(db):
    ids = seed_chat_fixtures(db)
    anchor = db.get_babylon_item(ids["lb2144-ansible-eda"])
    r = asyncio.run(handlers.handle_overlap(
        _res("overlap", items=[anchor]), db, _settings(), ["prod"], True, _noop))
    types = [b.type for b in r.blocks]
    assert types == ["item_card", "overlap_table"]
    neighbors = r.blocks[1].data["neighbors"]
    assert neighbors[0]["display_name"] == "LB2145 Ansible Automation Basics"
    assert neighbors[0]["shared_products"] == 2
    assert neighbors[0]["recommendation"] is None  # no llm_assessment seeded
    assert r.anchor_ids == [ids["lb2144-ansible-eda"]]
    assert r.session_results[0]["content_id"] == ids["lb2145-ansible-basics"]


def test_performance_handler_rows_match_scope(db):
    ids = seed_chat_fixtures(db)
    scope = [ids["lb2144-ansible-eda"], ids["lb2145-ansible-basics"]]
    r = asyncio.run(handlers.handle_performance(
        _res("performance", ids=scope, args={"window": "3m"}), db, _settings(), ["prod"], True, _noop))
    rows = r.blocks[0].data["rows"]
    assert [row["content_id"] for row in rows] == scope
    assert rows[0]["provisions"] == 40
    assert r.blocks[0].data["window"] == "3m"
    assert rows[0]["score"] is None               # no performance_scores seeded


def test_item_facts_handler(db):
    ids = seed_chat_fixtures(db)
    item = db.get_babylon_item(ids["ocpvirt-migration"])
    r = asyncio.run(handlers.handle_item_facts(
        _res("item_facts", items=[item]), db, _settings(), ["prod"], True, _noop))
    card = r.blocks[0].data
    assert r.blocks[0].type == "item_card"
    assert card["display_name"] == "OpenShift Virtualization Migration"
    assert "setup_virt" in card["workloads"]
    assert card["neighbors"][0]["display_name"] == "OpenShift Virtualization Roadshow"


def test_infrastructure_handler_uses_embedding_search():
    """Verify handler uses embedding search, not list_infrastructure."""
    from unittest.mock import MagicMock, patch

    fake_vec = [0.0] * 768
    mock_db = MagicMock()
    mock_db.search_infrastructure_embeddings.return_value = [
        {"role_name": "ocp4_workload_openshift_ai", "similarity": 0.92}
    ]
    mock_db.get_infrastructure.return_value = {
        "role_name": "ocp4_workload_openshift_ai",
        "type": "workload",
        "description": "Installs OpenShift AI.",
        "products": ["OpenShift AI"],
        "capabilities": [],
        "category": "ai_ml",
        "requires": [],
        "collection": "ocp4",
    }
    mock_db.get_infrastructure_linked_items.return_value = []

    with patch("rcars.services.chat.handlers.generate_embedding", return_value=fake_vec):
        result = asyncio.run(handlers.handle_infrastructure(
            _res("infrastructure", args={"search_query": "what deploys RHOAI?"}),
            mock_db, _settings(), ["prod"], True, _noop,
        ))

    mock_db.list_infrastructure.assert_not_called()
    mock_db.search_infrastructure_embeddings.assert_called_once_with(fake_vec, limit=10)
    assert result.blocks[0].type == "infra_detail"
    assert result.blocks[0].data["role_name"] == "ocp4_workload_openshift_ai"


def test_infrastructure_handler_no_match_returns_notice():
    """Verify handler returns notice when no embeddings match."""
    from unittest.mock import MagicMock, patch

    mock_db = MagicMock()
    mock_db.search_infrastructure_embeddings.return_value = []

    with patch("rcars.services.chat.handlers.generate_embedding", return_value=[0.0] * 768):
        result = asyncio.run(handlers.handle_infrastructure(
            _res("infrastructure", args={"search_query": "xyzzy nonsense"}),
            mock_db, _settings(), ["prod"], True, _noop,
        ))

    assert result.blocks[0].type == "notice"
    assert result.blocks[0].data["kind"] == "no_items"
