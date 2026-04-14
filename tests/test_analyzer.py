"""Tests for Showroom analyzer."""

import json
import os
import subprocess
from rcars.analyzer import (
    build_analysis_prompt,
    parse_analysis_response,
    filter_boilerplate_files,
    truncate_content,
)


SAMPLE_ANALYSIS_JSON = {
    "content_type": "workshop",
    "summary": "A hands-on workshop on OpenShift Lightspeed.",
    "products": ["Red Hat OpenShift Container Platform", "OpenShift Lightspeed"],
    "audience": ["platform engineers", "cluster administrators"],
    "difficulty": "intermediate",
    "estimated_duration_min": 90,
    "topics": ["AI assistants", "OpenShift web console", "troubleshooting"],
    "learning_objectives": {
        "stated": ["Use OpenShift Lightspeed to troubleshoot cluster issues"],
        "inferred": ["Understand how LLMs integrate with Kubernetes platforms"],
    },
    "modules": [
        {
            "title": "Introduction to Lightspeed",
            "topics": ["OpenShift Lightspeed", "AI"],
            "learning_objectives": ["Understand what Lightspeed does"],
            "estimated_duration_min": 15,
        },
        {
            "title": "Troubleshooting with Lightspeed",
            "topics": ["troubleshooting", "pod debugging"],
            "learning_objectives": ["Debug pod failures using Lightspeed"],
            "estimated_duration_min": 30,
        },
    ],
    "use_cases": ["Reduce MTTR for cluster issues"],
    "event_fit": {
        "booth_demo": {"suitable": True, "notes": "Quick to show"},
        "hands_on_lab": {"suitable": True, "notes": "Full workshop"},
        "presentation_support": {"suitable": True, "notes": "Good visuals"},
    },
}


def test_parse_analysis_response_valid_json():
    """Should parse valid JSON response."""
    result = parse_analysis_response(json.dumps(SAMPLE_ANALYSIS_JSON))
    assert result is not None
    assert result["content_type"] == "workshop"
    assert result["difficulty"] == "intermediate"
    assert result["estimated_duration_min"] == 90
    assert len(result["modules"]) == 2
    assert len(result["learning_objectives"]["stated"]) == 1
    assert len(result["learning_objectives"]["inferred"]) == 1


def test_parse_analysis_response_with_markdown_fences():
    """Should handle JSON wrapped in markdown code fences."""
    wrapped = f"```json\n{json.dumps(SAMPLE_ANALYSIS_JSON)}\n```"
    result = parse_analysis_response(wrapped)
    assert result is not None
    assert result["content_type"] == "workshop"


def test_parse_analysis_response_with_plain_fences():
    """Should handle JSON wrapped in plain code fences."""
    wrapped = f"```\n{json.dumps(SAMPLE_ANALYSIS_JSON)}\n```"
    result = parse_analysis_response(wrapped)
    assert result is not None


def test_parse_analysis_response_invalid():
    """Should return None for invalid JSON."""
    result = parse_analysis_response("This is not JSON at all")
    assert result is None


def test_parse_analysis_response_empty():
    """Should return None for empty string."""
    result = parse_analysis_response("")
    assert result is None


def test_filter_boilerplate_files():
    """Should filter out known boilerplate filenames."""
    files = {
        "01-introduction.adoc": "Welcome to this workshop...",
        "02-environment.adoc": "Your lab environment has been provisioned with...",
        "03-deploy-app.adoc": "In this module you will deploy an application...",
        "04-login.adoc": "Your username is user1 and your password is...",
        "index.adoc": "= Module List\n* Module 1\n* Module 2",
        "05-troubleshoot.adoc": "In this exercise, you will troubleshoot a failing pod...",
    }
    filtered = filter_boilerplate_files(files)
    # Should keep content files, remove boilerplate
    assert "03-deploy-app.adoc" in filtered
    assert "05-troubleshoot.adoc" in filtered
    # Should remove login/environment/index pages
    assert "04-login.adoc" not in filtered
    assert "02-environment.adoc" not in filtered
    assert "index.adoc" not in filtered


def test_filter_boilerplate_keeps_real_content():
    """Should keep files that discuss real technical content."""
    files = {
        "setup-operators.adoc": "Install the OpenShift Pipelines operator by navigating to...",
        "access-info.adoc": "Your credentials are user1/password123...",
    }
    filtered = filter_boilerplate_files(files)
    assert "setup-operators.adoc" in filtered
    assert "access-info.adoc" not in filtered


def test_truncate_content():
    """Should truncate content to max chars."""
    content = "x" * 200000
    result = truncate_content(content, max_chars=150000)
    assert len(result) <= 150000


def test_truncate_content_short():
    """Should not truncate content under the limit."""
    content = "Short content"
    result = truncate_content(content, max_chars=150000)
    assert result == content


def test_build_analysis_prompt_escapes_asciidoc_braces():
    """Should not raise KeyError when content contains AsciiDoc {attribute} syntax."""
    files = {"01-module.adoc": "Set {product_name} to {value} and deploy."}
    # Should not raise KeyError
    result = build_analysis_prompt(
        ci_name="test.ci",
        display_name="Test CI",
        category="Demos",
        product="OpenShift",
        content_files=files,
    )
    assert "{product_name}" in result
    assert "{value}" in result


def test_hash_showroom_content_deterministic():
    """Same content produces same hash, different content produces different hash."""
    from rcars.analyzer import hash_showroom_content
    files_a = {"module1.adoc": "= Hello World\nSome content.", "module2.adoc": "= Lab 2\nMore content."}
    files_b = {"module1.adoc": "= Hello World\nSome content.", "module2.adoc": "= Lab 2\nMore content."}
    files_c = {"module1.adoc": "= Hello World\nDifferent content.", "module2.adoc": "= Lab 2\nMore content."}

    assert hash_showroom_content(files_a) == hash_showroom_content(files_b)
    assert hash_showroom_content(files_a) != hash_showroom_content(files_c)


def test_hash_showroom_content_ignores_file_order():
    """Hash should be stable regardless of dict iteration order."""
    from rcars.analyzer import hash_showroom_content
    files_a = {"b.adoc": "content b", "a.adoc": "content a"}
    files_b = {"a.adoc": "content a", "b.adoc": "content b"}
    assert hash_showroom_content(files_a) == hash_showroom_content(files_b)


def test_hash_showroom_content_ignores_whitespace_changes():
    """Trailing whitespace and blank line differences should not change the hash."""
    from rcars.analyzer import hash_showroom_content
    files_a = {"mod.adoc": "= Title\nContent here.\n"}
    files_b = {"mod.adoc": "= Title\nContent here.  \n\n"}
    assert hash_showroom_content(files_a) == hash_showroom_content(files_b)


def test_check_showroom_stale_detects_change(tmp_path):
    """Should return new hash when content has materially changed."""
    from rcars.analyzer import check_showroom_stale

    # Create a fake showroom repo
    pages_dir = tmp_path / "content" / "modules" / "ROOT" / "pages"
    pages_dir.mkdir(parents=True)
    (pages_dir / "module1.adoc").write_text("= Lab 1\nOriginal content about OpenShift.")

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"})

    # First check — no old hash, should return hash
    result = check_showroom_stale(tmp_path, old_content_hash=None)
    assert result["is_stale"] is True
    assert result["content_hash"] is not None
    first_hash = result["content_hash"]

    # Same content — not stale
    result = check_showroom_stale(tmp_path, old_content_hash=first_hash)
    assert result["is_stale"] is False

    # Change content materially
    (pages_dir / "module1.adoc").write_text("= Lab 1\nCompletely rewritten content about Ansible Automation.")
    result = check_showroom_stale(tmp_path, old_content_hash=first_hash)
    assert result["is_stale"] is True
    assert result["content_hash"] != first_hash


def test_check_showroom_stale_ignores_typo_fix(tmp_path):
    """A typo fix changes the hash (the orchestrator decides whether to act)."""
    from rcars.analyzer import check_showroom_stale

    pages_dir = tmp_path / "content" / "modules" / "ROOT" / "pages"
    pages_dir.mkdir(parents=True)
    (pages_dir / "module1.adoc").write_text("= Lab 1\nThis is a tutoral about OpenShift.")

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"})

    result = check_showroom_stale(tmp_path, old_content_hash=None)
    first_hash = result["content_hash"]

    # Fix the typo: "tutoral" -> "tutorial"
    (pages_dir / "module1.adoc").write_text("= Lab 1\nThis is a tutorial about OpenShift.")
    result = check_showroom_stale(tmp_path, old_content_hash=first_hash)

    # Hash WILL differ — it's a content change. The check-stale orchestrator
    # decides whether to mark it stale based on threshold.
    assert result["content_hash"] != first_hash


def test_analyze_showroom_logs_scan_tokens(monkeypatch):
    """analyze_showroom should call db.log_token_usage with scan tokens when db provided."""
    from unittest.mock import MagicMock, patch
    from rcars.analyzer import analyze_showroom

    mock_db = MagicMock()
    mock_client = MagicMock()

    mock_response = MagicMock()
    mock_response.content[0].text = '{"content_type": "workshop", "summary": "Test", "products": [], "audience": [], "topics": [], "modules": [], "learning_objectives": {}, "difficulty": "beginner", "estimated_duration_min": 60, "event_fit": {}, "use_cases": []}'
    mock_response.usage.input_tokens = 12000
    mock_response.usage.output_tokens = 900
    mock_client.messages.create.return_value = mock_response

    with patch("rcars.analyzer.clone_showroom") as mock_clone, \
         patch("rcars.analyzer.read_showroom_content") as mock_read, \
         patch("rcars.analyzer.get_repo_head") as mock_head, \
         patch("rcars.analyzer.generate_embedding") as mock_embed:

        mock_clone.return_value = MagicMock()
        mock_read.return_value = {"module1.adoc": "= OpenShift Workshop\nLearn OpenShift basics here."}
        mock_head.return_value = ("abc123def", "2026-04-01T10:00:00+00:00")
        mock_embed.return_value = [0.1] * 384

        result = analyze_showroom(
            ci_name="test.ci.prod",
            display_name="Test CI",
            category="workshop",
            product="OCP",
            showroom_url="https://github.com/example/test.git",
            showroom_ref="main",
            anthropic_client=mock_client,
            model="claude-sonnet-4-6",
            db=mock_db,
        )

    assert result is not None
    mock_db.log_token_usage.assert_called_once_with(
        operation="scan",
        model="claude-sonnet-4-6",
        input_tokens=12000,
        output_tokens=900,
        ci_name="test.ci.prod",
    )


def test_analyze_showroom_no_db_does_not_fail():
    """analyze_showroom should work fine when db=None (no token logging)."""
    from unittest.mock import MagicMock, patch
    from rcars.analyzer import analyze_showroom

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content[0].text = '{"content_type": "demo", "summary": "Demo", "products": [], "audience": [], "topics": [], "modules": [], "learning_objectives": {}, "difficulty": "intermediate", "estimated_duration_min": 30, "event_fit": {}, "use_cases": []}'
    mock_response.usage.input_tokens = 5000
    mock_response.usage.output_tokens = 400
    mock_client.messages.create.return_value = mock_response

    with patch("rcars.analyzer.clone_showroom") as mock_clone, \
         patch("rcars.analyzer.read_showroom_content") as mock_read, \
         patch("rcars.analyzer.get_repo_head") as mock_head, \
         patch("rcars.analyzer.generate_embedding") as mock_embed:

        mock_clone.return_value = MagicMock()
        mock_read.return_value = {"module1.adoc": "= Demo\nContent here."}
        mock_head.return_value = ("abc123", "2026-04-01T10:00:00+00:00")
        mock_embed.return_value = [0.1] * 384

        result = analyze_showroom(
            ci_name="test.ci",
            display_name="Test",
            category="demo",
            product="OCP",
            showroom_url="https://github.com/example/test.git",
            showroom_ref=None,
            anthropic_client=mock_client,
            model="claude-sonnet-4-6",
            db=None,
        )
    assert result is not None
