from types import SimpleNamespace

import pytest

from tests.showroom_helpers import db
from rcars.api.routes.catalog import get_catalog_item, get_analysis
from rcars.config import Settings

URL = "https://github.com/example/content"


def add_item(db, name, *, owner_ci_name=None):
    owner = owner_ci_name or name
    from rcars.services.showroom_source import ResolvedShowroom
    source = ResolvedShowroom("resolved", owner, name.rsplit(".", 1)[0], URL, "main",
                              paths=((name, owner) if owner_ci_name else (name,),))
    return db.upsert_babylon_catalog_item({
        "ci_name": name, "stage": name.rsplit(".", 1)[-1], "display_name": name,
        "category": "Workshop", "showroom_url": URL, "showroom_ref": "main",
        "showroom_source": source.to_dict()})


def request(db):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        db=db, settings=Settings(database_url=db._url))))


@pytest.mark.asyncio
async def test_stub_detail_returns_the_owner_analysis_and_names_the_owner(db):
    owner = add_item(db, "isolation-test.owner.prod")
    stub = add_item(db, "isolation-test.virtual.prod", owner_ci_name="isolation-test.owner.prod")
    db.upsert_showroom_analysis({"content_id": owner, "summary": "Owner analysis",
                                 "modules_json": [], "content_hash": "content"})
    detail = await get_catalog_item("isolation-test.virtual.prod", request(db), user="test@example.com")
    assert detail["content_owner"] == "isolation-test.owner.prod"
    assert detail["analysis"]["summary"] == "Owner analysis"
    analysis = await get_analysis("isolation-test.virtual.prod", request(db), user="test@example.com")
    assert analysis["summary"] == "Owner analysis"


@pytest.mark.asyncio
async def test_owner_detail_has_no_content_owner(db):
    owner = add_item(db, "isolation-test.owner.prod")
    detail = await get_catalog_item("isolation-test.owner.prod", request(db), user="test@example.com")
    assert detail["content_owner"] is None
