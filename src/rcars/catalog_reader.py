"""Babylon CRD catalog reader.

Reads CatalogItem and AgnosticVComponent CRDs from the Babylon K8s API
and extracts catalog metadata and Showroom URLs using a strict allowlist.
"""

import logging
from datetime import datetime
from typing import Any

from kubernetes import client, config as k8s_config

log = logging.getLogger(__name__)

# Only these fields are extracted from AgnosticVComponent spec.definition.
# Everything else (vault secrets, SSH keys, credentials) is discarded.
CRD_FIELD_ALLOWLIST = [
    "ocp4_workload_showroom_content_git_repo",
    "ocp4_workload_showroom_content_git_repo_ref",
    "showroom_git_repo",
    "showroom_git_repo_ref",
]

LABEL_PREFIX = "babylon.gpte.redhat.com/"
DEMO_LABEL_PREFIX = "demo.redhat.com/"


def _get_label(metadata: dict, key: str, prefix: str = LABEL_PREFIX) -> str:
    """Get a label value from CRD metadata, or empty string."""
    labels = metadata.get("labels", {}) or {}
    return labels.get(f"{prefix}{key}", "")


def extract_catalog_item(crd: dict[str, Any]) -> dict[str, Any]:
    """Extract catalog metadata from a CatalogItem CRD.

    Returns a dict suitable for db.upsert_catalog_item().
    """
    metadata = crd.get("metadata", {})
    spec = crd.get("spec", {})
    labels = metadata.get("labels", {}) or {}

    stage = _get_label(metadata, "stage")

    description = spec.get("description", "")
    if isinstance(description, dict):
        description = description.get("content", "")

    last_update = spec.get("lastUpdate", {})
    last_crd_update = None
    if last_update and "git" in last_update:
        when = last_update["git"].get("when_committer")
        if when:
            try:
                last_crd_update = datetime.fromisoformat(
                    when.replace("Z", "+00:00")
                )
            except ValueError:
                pass

    return {
        "ci_name": metadata.get("name", ""),
        "display_name": spec.get("displayName", ""),
        "category": spec.get("category", _get_label(metadata, "category")),
        "product": _get_label(metadata, "Product"),
        "product_family": _get_label(metadata, "Product_Family"),
        "primary_bu": labels.get(f"{DEMO_LABEL_PREFIX}primaryBU", ""),
        "secondary_bu": labels.get(f"{DEMO_LABEL_PREFIX}secondaryBU", ""),
        "stage": stage,
        "catalog_namespace": metadata.get("namespace", ""),
        "keywords": spec.get("keywords", []) or [],
        "description": description,
        "icon_url": (spec.get("icon") or {}).get("url", ""),
        "owners_json": spec.get("owners"),
        "last_crd_update": last_crd_update,
        "is_prod": stage == "prod",
    }


def extract_showroom_url(
    component_crd: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Extract Showroom URL and ref from an AgnosticVComponent CRD.

    Uses a strict allowlist — only Showroom URL/ref variables are read.
    All other fields in spec.definition (secrets, credentials, SSH keys)
    are ignored.

    Returns (url, ref) tuple. Both are None if no Showroom URL found.
    """
    definition = (
        component_crd.get("spec", {}).get("definition", {}) or {}
    )

    url_vars = [
        "ocp4_workload_showroom_content_git_repo",
        "showroom_git_repo",
    ]
    ref_vars = [
        "ocp4_workload_showroom_content_git_repo_ref",
        "showroom_git_repo_ref",
    ]

    url = None
    ref = None

    for var in url_vars:
        value = definition.get(var)
        if value and isinstance(value, str) and not value.startswith("{{"):
            url = value
            break

    for var in ref_vars:
        value = definition.get(var)
        if value and isinstance(value, str) and not value.startswith("{{"):
            ref = value
            break

    return url, ref


class CatalogReader:
    """Reads catalog data from Babylon K8s CRDs."""

    CATALOG_ITEM_GROUP = "babylon.gpte.redhat.com"
    CATALOG_ITEM_VERSION = "v1"
    CATALOG_ITEM_PLURAL = "catalogitems"

    COMPONENT_GROUP = "gpte.redhat.com"
    COMPONENT_VERSION = "v1"
    COMPONENT_PLURAL = "agnosticvcomponents"

    def __init__(self, kubeconfig_path: str = ""):
        if kubeconfig_path:
            k8s_config.load_kube_config(config_file=kubeconfig_path)
        else:
            try:
                k8s_config.load_incluster_config()
            except k8s_config.ConfigException:
                k8s_config.load_kube_config()

        self._custom_api = client.CustomObjectsApi()

    def list_catalog_items(self, namespace: str) -> list[dict[str, Any]]:
        result = self._custom_api.list_namespaced_custom_object(
            group=self.CATALOG_ITEM_GROUP,
            version=self.CATALOG_ITEM_VERSION,
            namespace=namespace,
            plural=self.CATALOG_ITEM_PLURAL,
        )
        return result.get("items", [])

    def get_agnosticv_component(
        self, name: str, namespace: str
    ) -> dict[str, Any] | None:
        try:
            return self._custom_api.get_namespaced_custom_object(
                group=self.COMPONENT_GROUP,
                version=self.COMPONENT_VERSION,
                namespace=namespace,
                plural=self.COMPONENT_PLURAL,
                name=name,
            )
        except client.ApiException as e:
            if e.status == 404:
                log.debug("AgnosticVComponent %s not found in %s", name, namespace)
                return None
            raise

    def refresh_catalog(
        self,
        namespaces: list[str],
        component_namespace: str = "babylon-config",
    ) -> list[dict[str, Any]]:
        items = []

        for ns in namespaces:
            log.info("Reading CatalogItems from %s", ns)
            try:
                crds = self.list_catalog_items(ns)
            except client.ApiException as e:
                log.error("Failed to list CatalogItems in %s: %s", ns, e.reason)
                continue

            for crd in crds:
                item = extract_catalog_item(crd)
                ci_name = item["ci_name"]

                component = self.get_agnosticv_component(
                    ci_name, component_namespace
                )
                if component:
                    url, ref = extract_showroom_url(component)
                    item["showroom_url"] = url
                    item["showroom_ref"] = ref

                items.append(item)

            log.info("Found %d CatalogItems in %s", len(crds), ns)

        return items
