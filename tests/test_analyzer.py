"""Tests for Showroom analyzer."""

import json
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
