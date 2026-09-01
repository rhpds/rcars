from rcars.services.catalog import _apply_component_inheritance
from rcars.services.recommender.models import Candidate, QueryState


def test_candidate_similarity_pct():
    assert Candidate.similarity_pct(0.0) == 100
    assert Candidate.similarity_pct(0.5) == 75
    assert Candidate.similarity_pct(1.0) == 50


def test_query_state_defaults():
    state = QueryState(phase="SUBMITTED", candidates=[])
    assert state.query == ""
    assert state.overall_assessment is None
    assert state.content_gaps is None


def test_candidate_tier_defaults():
    c = Candidate(
        content_id="babylon:test.item",
        display_name="Test",
        category="Workshops",
        summary="A test item",
        topics=["openshift"],
        products=["OpenShift"],
        difficulty="beginner",
        duration_min=60,
        content_type="workshop",
        ci_name="test.item",
    )
    assert c.tier == "white"
    assert c.relevance_score is None
    assert c.rationale is None


def test_imports():
    from rcars.services.recommender import run_query, Candidate, QueryState
    from rcars.services.analyzer import generate_embedding, parse_analysis_response, analyze_showroom
    from rcars.services.catalog import CatalogReader
    assert run_query is not None
    assert Candidate is not None
    assert generate_embedding is not None
    assert CatalogReader is not None


def _run_catalog_second_pass(items):
    """Run the production second pass and return items keyed by ci_name."""
    _apply_component_inheritance(items)
    return {i["ci_name"]: i for i in items}


def test_three_layer_workload_propagation():
    """Workloads merge up the full chain: bottom → middle → published."""
    bottom_workloads = [
        {"fqcn": "agnosticd.core_workloads.ocp4_workload_cert_manager", "role": "ocp4_workload_cert_manager", "collection": "agnosticd.core_workloads"},
        {"fqcn": "agnosticd.core_workloads.ocp4_workload_external_odf", "role": "ocp4_workload_external_odf", "collection": "agnosticd.core_workloads"},
    ]
    middle_workloads = [
        {"fqcn": "agnosticd.core_workloads.ocp4_workload_kafka", "role": "ocp4_workload_kafka", "collection": "agnosticd.core_workloads"},
    ]
    items = [
        {
            "ci_name": "agd-v2.ocp-cluster-cnv-pools.prod",
            "is_published": False,
            "published_ci_name": None,
            "base_ci_name": None,
            "is_agd_v2": True,
            "agd_config": "openshift-cluster",
            "cloud_provider": "ec2",
            "ocp_version": "4.20",
            "_workloads": bottom_workloads,
        },
        {
            "ci_name": "openshift-cnv.kafka-developer-workshop-cnv",
            "is_published": False,
            "published_ci_name": None,
            "base_ci_name": "agd-v2.ocp-cluster-cnv-pools.prod",
            "is_agd_v2": True,
            "agd_config": "openshift-cluster",
            "cloud_provider": "ec2",
            "ocp_version": "4.20",
            "showroom_url": "https://github.com/example/showroom.git",
            "showroom_ref": "main",
            "_workloads": middle_workloads,
        },
        {
            "ci_name": "published.kafka-developer-workshop",
            "is_published": True,
            "published_ci_name": None,
            "base_ci_name": "openshift-cnv.kafka-developer-workshop-cnv",
            "showroom_url": None,
            "showroom_ref": None,
            "_workloads": [],
        },
    ]

    result = _run_catalog_second_pass(items)

    # Published CI gets all three workloads
    published = result["published.kafka-developer-workshop"]
    fqcns = {w["fqcn"] for w in published["_workloads"]}
    assert fqcns == {
        "agnosticd.core_workloads.ocp4_workload_kafka",
        "agnosticd.core_workloads.ocp4_workload_cert_manager",
        "agnosticd.core_workloads.ocp4_workload_external_odf",
    }

    # Middle layer also gets bottom's workloads
    middle = result["openshift-cnv.kafka-developer-workshop-cnv"]
    middle_fqcns = {w["fqcn"] for w in middle["_workloads"]}
    assert middle_fqcns == fqcns

    # published_ci_name only set by published items, not by middle
    assert result["openshift-cnv.kafka-developer-workshop-cnv"]["published_ci_name"] == "published.kafka-developer-workshop"
    assert result["agd-v2.ocp-cluster-cnv-pools.prod"]["published_ci_name"] is None

    # Showroom URL inherited
    assert published["showroom_url"] == "https://github.com/example/showroom.git"

    # Infrastructure metadata inherited
    assert published.get("is_agd_v2") is True
    assert published.get("agd_config") == "openshift-cluster"
    assert published.get("cloud_provider") == "ec2"
    assert published.get("ocp_version") == "4.20"


def test_workload_dedup_across_layers():
    """If middle and bottom share a workload, it appears only once."""
    shared = {"fqcn": "agnosticd.core_workloads.ocp4_workload_cert_manager", "role": "ocp4_workload_cert_manager", "collection": "agnosticd.core_workloads"}
    items = [
        {"ci_name": "bottom", "is_published": False, "published_ci_name": None, "base_ci_name": None, "_workloads": [shared]},
        {"ci_name": "middle", "is_published": False, "published_ci_name": None, "base_ci_name": "bottom", "_workloads": [shared]},
        {"ci_name": "published.top", "is_published": True, "published_ci_name": None, "base_ci_name": "middle", "_workloads": []},
    ]
    result = _run_catalog_second_pass(items)
    assert len(result["published.top"]["_workloads"]) == 1


def test_published_ci_name_not_set_by_non_published():
    """Non-published items with base_ci_name must not set published_ci_name on their base."""
    items = [
        {"ci_name": "bottom", "is_published": False, "published_ci_name": None, "base_ci_name": None, "_workloads": []},
        {"ci_name": "middle", "is_published": False, "published_ci_name": None, "base_ci_name": "bottom", "_workloads": []},
    ]
    result = _run_catalog_second_pass(items)
    assert result["bottom"]["published_ci_name"] is None


def test_multi_base_published_ci():
    """Published CI with multiple bases gets union of workloads and combined infra fields."""
    aws_workloads = [{"fqcn": "agnosticd.core_workloads.ocp4_workload_cert_manager", "role": "ocp4_workload_cert_manager", "collection": "agnosticd.core_workloads"}]
    azure_workloads = [
        {"fqcn": "agnosticd.core_workloads.ocp4_workload_cert_manager", "role": "ocp4_workload_cert_manager", "collection": "agnosticd.core_workloads"},
        {"fqcn": "agnosticd.core_workloads.ocp4_workload_azure_files", "role": "ocp4_workload_azure_files", "collection": "agnosticd.core_workloads"},
    ]
    items = [
        {
            "ci_name": "agd-v2.ocp-cluster-aws.prod",
            "is_published": False, "published_ci_name": None, "base_ci_name": None,
            "is_agd_v2": True, "agd_config": "openshift-cluster", "cloud_provider": "ec2", "ocp_version": "4.20",
            "_workloads": aws_workloads,
        },
        {
            "ci_name": "agd-v2.ocp-cluster-azure.prod",
            "is_published": False, "published_ci_name": None, "base_ci_name": None,
            "is_agd_v2": True, "agd_config": "openshift-cluster", "cloud_provider": "azure", "ocp_version": "4.20",
            "_workloads": azure_workloads,
        },
        {
            "ci_name": "published.ocp4-cluster",
            "is_published": True, "published_ci_name": None,
            "base_ci_name": "agd-v2.ocp-cluster-aws.prod",
            "_base_ci_names": ["agd-v2.ocp-cluster-aws.prod", "agd-v2.ocp-cluster-azure.prod"],
            "_workloads": [],
        },
    ]
    result = _run_catalog_second_pass(items)
    published = result["published.ocp4-cluster"]

    # Workloads: union of both bases (cert_manager shared, azure_files unique)
    fqcns = {w["fqcn"] for w in published["_workloads"]}
    assert fqcns == {
        "agnosticd.core_workloads.ocp4_workload_cert_manager",
        "agnosticd.core_workloads.ocp4_workload_azure_files",
    }

    # is_agd_v2: true (both bases are v2)
    assert published.get("is_agd_v2") is True

    # cloud_provider: combined since they differ
    assert "ec2" in published.get("cloud_provider", "")
    assert "azure" in published.get("cloud_provider", "")

    # ocp_version: same on both bases, single value
    assert published.get("ocp_version") == "4.20"

    # agd_config: same on both bases, single value
    assert published.get("agd_config") == "openshift-cluster"


def test_format_single_candidate_handles_architecture():
    from rcars.services.recommender.models import Candidate
    from rcars.services.recommender.rationale import _format_single_candidate

    candidate = Candidate(
        content_id="pa:275",
        display_name="Multitenant Setup for RHACS",
        content_type="architecture",
        summary="An architecture for multi-tenant RHACS.",
        topics=["security"],
        products=["Red Hat Advanced Cluster Security"],
        difficulty="intermediate",
        duration_min=None,
        category="architecture",
        source="portfolio_arch",
        is_hands_on=False,
        relevance_score=88,
    )
    analysis = {
        "audience_json": ["security architects"],
        "solution_areas_json": ["Application Platform"],
        "use_cases_json": ["Isolate tenants in a shared cluster"],
        "key_components_json": ["RHACS", "OpenShift"],
        "asset_type": "PA",
    }

    text = _format_single_candidate(candidate, analysis)

    assert "Asset Type: Portfolio Architecture" in text
    assert "Solution Areas: Application Platform" in text
    assert "Use Cases: Isolate tenants in a shared cluster" in text
    assert "Key Components: RHACS; OpenShift" in text
    assert "Audience: security architects" in text
    assert "Duration" not in text
    assert "reference architecture" not in text.lower()
