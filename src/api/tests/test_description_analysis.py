"""Description-based analysis: source resolution, setter, analyzer, pipeline."""

from rcars.services.showroom_source import effective_analysis_source


def test_effective_analysis_source_defaults_to_showroom():
    assert effective_analysis_source({}) == "showroom"
    assert effective_analysis_source({"analysis_source_override": None}) == "showroom"
    assert effective_analysis_source({"analysis_source_override": "bogus"}) == "showroom"


def test_effective_analysis_source_returns_override():
    assert effective_analysis_source(
        {"analysis_source_override": "agnosticv_description"}
    ) == "agnosticv_description"
    assert effective_analysis_source(
        {"analysis_source_override": "custom_description"}
    ) == "custom_description"
