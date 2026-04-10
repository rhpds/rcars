"""Tests for Babylon CRD catalog reader."""

import pytest
from rcars.catalog_reader import (
    extract_catalog_item,
    extract_showroom_url,
    extract_base_ci_refs,
    component_item_to_ci_name,
    CRD_FIELD_ALLOWLIST,
)


SAMPLE_CATALOG_ITEM = {
    "apiVersion": "babylon.gpte.redhat.com/v1",
    "kind": "CatalogItem",
    "metadata": {
        "name": "openshift-cnv.ocp4-lightspeed-cnv.prod",
        "namespace": "babylon-catalog-prod",
        "labels": {
            "babylon.gpte.redhat.com/Product": "Red_Hat_OpenShift_Container_Platform",
            "babylon.gpte.redhat.com/Product_Family": "Red_Hat_Cloud",
            "babylon.gpte.redhat.com/category": "Demos",
            "babylon.gpte.redhat.com/stage": "prod",
            "demo.redhat.com/primaryBU": "Hybrid_Platforms",
            "demo.redhat.com/secondaryBU": "Artificial_Intelligence",
        },
    },
    "spec": {
        "displayName": "OpenShift Lightspeed Demo (CNV)",
        "category": "Demos",
        "keywords": ["openshift", "ocp", "lightspeed", "ols"],
        "description": {
            "content": "This environment provides an OpenShift cluster with Lightspeed.",
            "format": "asciidoc",
        },
        "icon": {
            "url": "https://gpte-public.s3.amazonaws.com/catalog-icon-openshift.svg"
        },
        "owners": {
            "maintainer": [
                {"email": "testuser@example.com", "name": "Test User"},
            ]
        },
        "lastUpdate": {
            "git": {
                "when_committer": "2026-03-18T15:40:37Z",
                "hash": "e09ad80d",
            }
        },
    },
}


SAMPLE_AGNOSTICV_COMPONENT = {
    "spec": {
        "definition": {
            "ocp4_workload_showroom_content_git_repo": "https://github.com/dialvare/showroom-openshift-lightspeed.git",
            "ocp4_workload_showroom_content_git_repo_ref": "main",
            "ocp4_workload_ols_api_token": "$ANSIBLE_VAULT;1.2;AES256;secret_data",
            "ssh_authorized_keys": [{"key": "ssh-rsa AAAA..."}],
            "agnosticd_save_output_dir_s3_secret_access_key": "$ANSIBLE_VAULT;data",
        }
    }
}


SAMPLE_COMPONENT_SHOWROOM_GIT_REPO = {
    "spec": {
        "definition": {
            "showroom_git_repo": "https://github.com/example/showroom-alt.git",
            "showroom_git_repo_ref": "v2.0",
        }
    }
}


SAMPLE_COMPONENT_NO_SHOWROOM = {
    "spec": {
        "definition": {
            "cloud_provider": "aws",
            "env_type": "ocp4-workshop",
        }
    }
}


def test_extract_catalog_item_basic_fields():
    """Should extract display name, category, product from CatalogItem."""
    result = extract_catalog_item(SAMPLE_CATALOG_ITEM)
    assert result["ci_name"] == "openshift-cnv.ocp4-lightspeed-cnv.prod"
    assert result["display_name"] == "OpenShift Lightspeed Demo (CNV)"
    assert result["category"] == "Demos"
    assert result["product"] == "Red_Hat_OpenShift_Container_Platform"
    assert result["product_family"] == "Red_Hat_Cloud"
    assert result["primary_bu"] == "Hybrid_Platforms"
    assert result["secondary_bu"] == "Artificial_Intelligence"
    assert result["stage"] == "prod"
    assert result["is_prod"] is True


def test_extract_catalog_item_keywords():
    """Should extract keywords as a list."""
    result = extract_catalog_item(SAMPLE_CATALOG_ITEM)
    assert result["keywords"] == ["openshift", "ocp", "lightspeed", "ols"]


def test_extract_catalog_item_description():
    """Should extract description content."""
    result = extract_catalog_item(SAMPLE_CATALOG_ITEM)
    assert "OpenShift cluster with Lightspeed" in result["description"]


def test_extract_catalog_item_owners():
    """Should extract owners as JSON."""
    result = extract_catalog_item(SAMPLE_CATALOG_ITEM)
    assert result["owners_json"]["maintainer"][0]["name"] == "Test User"


def test_extract_catalog_item_namespace():
    """Should preserve the catalog namespace."""
    result = extract_catalog_item(SAMPLE_CATALOG_ITEM)
    assert result["catalog_namespace"] == "babylon-catalog-prod"


def test_extract_catalog_item_dev_stage():
    """Dev items should have is_prod=False."""
    item = {
        "metadata": {
            "name": "test.dev",
            "namespace": "babylon-catalog-dev",
            "labels": {"babylon.gpte.redhat.com/stage": "dev"},
        },
        "spec": {"displayName": "Dev Item"},
    }
    result = extract_catalog_item(item)
    assert result["stage"] == "dev"
    assert result["is_prod"] is False


def test_extract_showroom_url_primary_var():
    """Should extract Showroom URL from ocp4_workload_ variable."""
    url, ref = extract_showroom_url(SAMPLE_AGNOSTICV_COMPONENT)
    assert url == "https://github.com/dialvare/showroom-openshift-lightspeed.git"
    assert ref == "main"


def test_extract_showroom_url_alternate_var():
    """Should extract from showroom_git_repo variable name."""
    url, ref = extract_showroom_url(SAMPLE_COMPONENT_SHOWROOM_GIT_REPO)
    assert url == "https://github.com/example/showroom-alt.git"
    assert ref == "v2.0"


def test_extract_showroom_url_missing():
    """Should return None when no Showroom URL found."""
    url, ref = extract_showroom_url(SAMPLE_COMPONENT_NO_SHOWROOM)
    assert url is None
    assert ref is None


def test_extract_showroom_url_no_secrets_leaked():
    """Extraction must never return sensitive fields."""
    url, ref = extract_showroom_url(SAMPLE_AGNOSTICV_COMPONENT)
    assert "ANSIBLE_VAULT" not in str(url)
    assert "ANSIBLE_VAULT" not in str(ref)


def test_crd_field_allowlist_excludes_secrets():
    """The allowlist should only contain safe field names."""
    for field_name in CRD_FIELD_ALLOWLIST:
        assert "secret" not in field_name.lower()
        assert "password" not in field_name.lower()
        assert "token" not in field_name.lower()
        assert "vault" not in field_name.lower()
        assert "ssh" not in field_name.lower()


# --- Published VCI tests ---

SAMPLE_PUBLISHED_CATALOG_ITEM = {
    "metadata": {
        "name": "published.ocp4-lightspeed.prod",
        "namespace": "babylon-catalog-prod",
        "labels": {
            "babylon.gpte.redhat.com/stage": "prod",
            "babylon.gpte.redhat.com/Product": "Red_Hat_OpenShift_Container_Platform",
            "babylon.gpte.redhat.com/category": "Demos",
        },
    },
    "spec": {
        "displayName": "OpenShift Lightspeed Demo",
        "category": "Demos",
        "keywords": ["openshift", "lightspeed"],
    },
}


SAMPLE_PUBLISHED_COMPONENT = {
    "spec": {
        "definition": {
            "__meta__": {
                "components": [
                    {
                        "display_name": "OpenShift Lightspeed Demo (CNV)",
                        "item": "openshift_cnv/ocp4-lightspeed-cnv",
                        "name": "ocp4-lightspeed-cnv",
                    }
                ]
            }
        }
    }
}


SAMPLE_MULTI_COMPONENT = {
    "spec": {
        "definition": {
            "__meta__": {
                "components": [
                    {"item": "agd_v2/ocp-cluster-cnv", "name": "ocp-cluster-cnv"},
                    {"item": "agd_v2/ocp-cluster-aws", "name": "ocp-cluster-aws"},
                ]
            }
        }
    }
}


def test_extract_catalog_item_detects_published():
    """Published VCIs should have is_published=True."""
    result = extract_catalog_item(SAMPLE_PUBLISHED_CATALOG_ITEM)
    assert result["is_published"] is True
    assert result["ci_name"] == "published.ocp4-lightspeed.prod"


def test_extract_catalog_item_base_not_published():
    """Base CIs should have is_published=False."""
    result = extract_catalog_item(SAMPLE_CATALOG_ITEM)
    assert result["is_published"] is False


def test_extract_base_ci_refs():
    """Should extract component item paths from published VCI."""
    refs = extract_base_ci_refs(SAMPLE_PUBLISHED_COMPONENT)
    assert refs == ["openshift_cnv/ocp4-lightspeed-cnv"]


def test_extract_base_ci_refs_multi():
    """Should extract multiple component item paths."""
    refs = extract_base_ci_refs(SAMPLE_MULTI_COMPONENT)
    assert len(refs) == 2
    assert refs[0] == "agd_v2/ocp-cluster-cnv"
    assert refs[1] == "agd_v2/ocp-cluster-aws"


def test_extract_base_ci_refs_no_components():
    """Should return empty list when no components."""
    refs = extract_base_ci_refs(SAMPLE_AGNOSTICV_COMPONENT)
    assert refs == []


def test_component_item_to_ci_name():
    """Should convert component path to CI name format."""
    result = component_item_to_ci_name("openshift_cnv/ocp4-lightspeed-cnv", "prod")
    assert result == "openshift-cnv.ocp4-lightspeed-cnv.prod"


def test_component_item_to_ci_name_agd_v2():
    """Should handle agd_v2 paths."""
    result = component_item_to_ci_name("agd_v2/aap-multiinstance-workshop", "dev")
    assert result == "agd-v2.aap-multiinstance-workshop.dev"
