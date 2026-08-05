from rcars.config import Settings


def test_defaults():
    s = Settings(database_url="postgresql://test:test@localhost/test", redis_url="redis://localhost:6379")
    assert s.model == "claude-sonnet-4-6"
    assert s.triage_model == "claude-haiku-4-5"
    assert s.vector_cutoff == 0.55
    assert s.rationale_top_n == 5
    assert s.triage_cutoff == 30


def test_curator_check():
    s = Settings(
        database_url="postgresql://test:test@localhost/test",
        redis_url="redis://localhost:6379",
        curator_emails_str="alice@redhat.com,Bob@REDHAT.COM",
    )
    assert s.is_curator("alice@redhat.com")
    assert s.is_curator("bob@redhat.com")
    assert not s.is_curator("charlie@redhat.com")


def test_admin_check():
    s = Settings(
        database_url="postgresql://test:test@localhost/test",
        redis_url="redis://localhost:6379",
        admin_emails_str="admin@redhat.com",
    )
    assert s.is_admin("admin@redhat.com")
    assert not s.is_admin("user@redhat.com")


def test_use_vertex():
    s = Settings(
        database_url="postgresql://test:test@localhost/test",
        redis_url="redis://localhost:6379",
        vertex_project_id="my-project",
    )
    assert s.use_vertex is True

    s2 = Settings(
        database_url="postgresql://test:test@localhost/test",
        redis_url="redis://localhost:6379",
    )
    assert s2.use_vertex is False


def test_chat_model_defaults_follow_triage_and_rationale():
    s = Settings(database_url="postgresql://x/x",
                 triage_model="m-triage", rationale_model="m-rationale")
    assert s.chat_router_model == "m-triage"
    assert s.chat_answer_model == "m-rationale"


def test_chat_models_explicit_override():
    s = Settings(database_url="postgresql://x/x",
                 chat_router_model="open-model", chat_answer_model="other")
    assert s.chat_router_model == "open-model"
    assert s.chat_answer_model == "other"


def test_chat_intent_roles_parse():
    s = Settings(database_url="postgresql://x/x",
                 chat_intent_roles_str="performance:curator, item_facts:any")
    assert s.chat_intent_roles == {"performance": "curator", "item_facts": "any"}
    assert Settings(database_url="postgresql://x/x").chat_intent_roles == {}


def test_chat_intent_roles_invalid_role_rejected():
    import pytest
    with pytest.raises(ValueError):
        Settings(database_url="postgresql://x/x", chat_intent_roles_str="performance:sudo")


def test_chat_router_threshold_validated():
    import pytest
    with pytest.raises(ValueError):
        Settings(database_url="postgresql://x/x", chat_router_confidence_threshold=1.5)
