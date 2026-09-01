import pytest
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


def test_osspa_defaults():
    s = Settings(database_url="postgresql://x/y")
    assert s.osspa_sync_enabled is True
    assert s.osspa_palist_url.endswith("PAList.csv")
    assert s.osspa_examples_repo_url.endswith("portfolio-architecture-examples.git")
    assert s.osspa_examples_ref == "main"
    assert s.osspa_csv_fetch_timeout_s == 15
    assert s.osspa_clone_timeout_s == 60
    assert s.osspa_max_adoc_bytes == 200000
    assert s.osspa_retire_shrink_guard_pct == 0.5
    assert s.osspa_advisory_lock_id == 736372


def test_osspa_analysis_model_inherits_default_model():
    s = Settings(database_url="postgresql://x/y")
    assert s.osspa_analysis_model == s.model

    s2 = Settings(database_url="postgresql://x/y", osspa_analysis_model="claude-haiku-4-5")
    assert s2.osspa_analysis_model == "claude-haiku-4-5"


def test_osspa_clone_dir_derives_from_clone_dir():
    s = Settings(database_url="postgresql://x/y", clone_dir="/tmp/rcars-clones")
    assert s.osspa_clone_dir == "/tmp/rcars-clones/osspa-examples"

    s2 = Settings(database_url="postgresql://x/y", osspa_clone_dir="/var/osspa")
    assert s2.osspa_clone_dir == "/var/osspa"


def test_osspa_shrink_guard_must_be_a_fraction():
    with pytest.raises(ValueError):
        Settings(database_url="postgresql://x/y", osspa_retire_shrink_guard_pct=1.5)
    with pytest.raises(ValueError):
        Settings(database_url="postgresql://x/y", osspa_retire_shrink_guard_pct=0)
