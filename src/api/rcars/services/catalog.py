"""Babylon CRD catalog reader.

Reads CatalogItem and AgnosticVComponent CRDs from the Babylon K8s API
and extracts catalog metadata and Showroom URLs using a strict allowlist.
"""

import logging
import urllib3
from datetime import datetime
from typing import Any

from kubernetes import client, config as k8s_config

# Suppress SSL warnings for clusters with self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)

# Only these fields are extracted from AgnosticVComponent spec.definition.
# Everything else (vault secrets, SSH keys, credentials) is discarded.
# Covers OCP (Helm/Operator), RHEL/VM (bastion container), and legacy bookbag.
CRD_FIELD_ALLOWLIST = [
    "ocp4_workload_showroom_content_git_repo",
    "ocp4_workload_showroom_content_git_repo_ref",
    "ocp4_workload_showroom_content_git_ref",
    "showroom_git_repo",
    "showroom_git_ref",
    "bookbag_git_repo",
]

LABEL_PREFIX = "babylon.gpte.redhat.com/"
DEMO_LABEL_PREFIX = "demo.redhat.com/"


def _get_label(metadata: dict, key: str, prefix: str = LABEL_PREFIX) -> str:
    """Get a label value from CRD metadata, or empty string."""
    labels = metadata.get("labels", {}) or {}
    return labels.get(f"{prefix}{key}", "")


def extract_catalog_item(crd: dict[str, Any]) -> dict[str, Any]:
    """Extract catalog metadata from a CatalogItem CRD.

    Returns a dict suitable for db.upsert_babylon_catalog_item().
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
        "is_published": metadata.get("name", "").startswith("published."),
        "published_ci_name": None,
        "base_ci_name": None,
    }


def extract_base_ci_refs(
    component_crd: dict[str, Any],
) -> list[str]:
    """Extract base CI component item paths from a published VCI's AgnosticVComponent.

    Returns list of component item paths (e.g., ['openshift_cnv/ocp4-lightspeed-cnv']).
    Only reads from __meta__.components[].item — nothing else.
    """
    definition = component_crd.get("spec", {}).get("definition", {}) or {}
    meta = definition.get("__meta__", {})
    components = meta.get("components", [])
    return [c["item"] for c in components if "item" in c]


def component_item_to_ci_name(component_item: str, stage: str) -> str:
    """Convert a component item path to a CI name.

    e.g., 'openshift_cnv/ocp4-lightspeed-cnv' + 'prod'
       -> 'openshift-cnv.ocp4-lightspeed-cnv.prod'
    """
    return component_item.replace("/", ".").replace("_", "-") + "." + stage


def _resolve_template_var(
    value: str, definition: dict, catalog_params: list[dict],
) -> str | None:
    """Resolve a Jinja2 template variable like '{{ showroom_repo_revision }}'.

    Resolution order:
    1. Check catalog parameters for a default (user-facing override, e.g. dev.yaml)
    2. Fall back to the variable's value in spec.definition (e.g. from common.yaml)
    """
    import re
    match = re.match(r"\{\{\s*(\w+)\s*\}\}", value.strip())
    if not match:
        return None
    var_name = match.group(1)

    for param in catalog_params:
        if param.get("name") == var_name:
            default = (param.get("openAPIV3Schema") or {}).get("default")
            if default and isinstance(default, str):
                return default.split(" #")[0].strip()

    resolved = definition.get(var_name)
    if resolved and isinstance(resolved, str) and not resolved.startswith("{{"):
        return resolved.split(" #")[0].strip()

    return None


URL_VARS = [
    "ocp4_workload_showroom_content_git_repo",
    "showroom_git_repo",
    "bookbag_git_repo",
]
REF_VARS = [
    "ocp4_workload_showroom_content_git_repo_ref",
    "ocp4_workload_showroom_content_git_ref",
    "showroom_git_ref",
]


TEMPLATE_REPOS = [
    "showroom_template_default",
    "showroom_template_nookbag",
    "showroom_template_zero",
]


def _is_template_repo(url: str) -> bool:
    return any(t in url for t in TEMPLATE_REPOS)


def _extract_from_dict(
    d: dict, catalog_params: list[dict], definition: dict,
) -> tuple[str | None, str | None]:
    """Extract showroom URL and ref from a flat dict of variables."""
    url = None
    ref = None

    for var in URL_VARS:
        value = d.get(var)
        if value and isinstance(value, str) and not value.startswith("{{"):
            candidate = value.split(" #")[0].strip()
            if _is_template_repo(candidate):
                continue
            url = candidate
            break

    for var in REF_VARS:
        value = d.get(var)
        if not value or not isinstance(value, str):
            continue
        if value.startswith("{{"):
            resolved = _resolve_template_var(value, definition, catalog_params)
            if resolved:
                ref = resolved
                break
        else:
            ref = value.split(" #")[0].strip()
            break

    return url, ref


def extract_showroom_url(
    component_crd: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Extract Showroom URL and ref from an AgnosticVComponent CRD.

    Checks three locations in priority order:
    1. Top-level spec.definition (direct showroom vars — standard CIs)
    2. __meta__.components[].parameter_values (ZT Virtual CIs that pass
       the showroom URL as a parameter override to a base component)

    When a ref value is a Jinja2 template (e.g. '{{ showroom_repo_revision }}'),
    resolves it by looking up the variable in spec.definition, with catalog
    parameter defaults taking precedence per stage.

    Returns (url, ref) tuple. Both are None if no Showroom URL found.
    """
    definition = (
        component_crd.get("spec", {}).get("definition", {}) or {}
    )
    meta = definition.get("__meta__", {})
    catalog_params = (meta.get("catalog") or {}).get("parameters") or []

    # 1. Check top-level definition
    url, ref = _extract_from_dict(definition, catalog_params, definition)
    if url:
        return url, ref

    # 2. Fall back to component parameter_values (ZT Virtual CI pattern)
    for comp in meta.get("components", []):
        pv = comp.get("parameter_values", {})
        if pv:
            url, ref = _extract_from_dict(pv, catalog_params, definition)
            if url:
                return url, ref

    return None, None


AGD_V2_SCM_URL = "https://github.com/rhpds/agnosticd-v2"

VM_WORKLOAD_FIELDS = [
    "software_workloads",
    "pre_software_workloads",
    "post_software_workloads",
    "post_software_final_workloads",
]


def is_agnosticd_v2(component_crd: dict[str, Any]) -> bool:
    """Check if a component uses the canonical AgnosticD v2 deployer."""
    definition = component_crd.get("spec", {}).get("definition", {}) or {}
    scm_url = definition.get("__meta__", {}).get("deployer", {}).get("scm_url", "")
    return scm_url == AGD_V2_SCM_URL


def parse_workload_fqcn(fqcn: str) -> tuple[str, str, str | None]:
    """Parse an Ansible FQCN workload reference into (fqcn, role, collection).

    'agnosticd.core_workloads.ocp4_workload_openshift_ai'
        → ('agnosticd.core_workloads.ocp4_workload_openshift_ai',
           'ocp4_workload_openshift_ai', 'agnosticd.core_workloads')
    'ocp4_workload_showroom'
        → ('ocp4_workload_showroom', 'ocp4_workload_showroom', None)
    """
    parts = fqcn.rsplit(".", 1)
    if len(parts) == 2 and "." in parts[0]:
        return fqcn, parts[1], parts[0]
    elif len(parts) == 2:
        return fqcn, parts[1], parts[0]
    else:
        return fqcn, fqcn, None


def extract_infrastructure_metadata(
    component_crd: dict[str, Any],
) -> dict[str, Any] | None:
    """Extract infrastructure metadata from an AgnosticD v2 component CRD.

    Returns None if the component is not AgnosticD v2.
    """
    if not is_agnosticd_v2(component_crd):
        return None

    definition = component_crd.get("spec", {}).get("definition", {}) or {}
    result: dict[str, Any] = {"is_agd_v2": True}

    field_mapping = {
        "config": "agd_config",
        "cloud_provider": "cloud_provider",
        "host_ocp4_installer_version": "ocp_version",
        "worker_instance_count": "worker_instance_count",
        "control_plane_instance_count": "control_plane_instance_count",
    }
    for crd_field, col_name in field_mapping.items():
        value = definition.get(crd_field)
        if value is not None:
            result[col_name] = str(value) if not isinstance(value, str) else value

    config = definition.get("config", "")

    if config == "cloud-vms-base":
        os_image = (
            definition.get("bastion_instance_image")
            or definition.get("default_instance_image")
        )
        if os_image and isinstance(os_image, str):
            result["os_image"] = os_image

        instances = definition.get("instances")
        if isinstance(instances, list):
            result["instances_json"] = [
                {k: v for k, v in inst.items()
                 if k in ("name", "cores", "memory", "image", "image_size", "count")}
                for inst in instances if isinstance(inst, dict)
            ]

    workloads: list[dict[str, Any]] = []
    seen_fqcns: set[str] = set()

    if config == "cloud-vms-base":
        for field in VM_WORKLOAD_FIELDS:
            raw = definition.get(field)
            if not isinstance(raw, dict):
                continue
            for _host_group, wl_list in raw.items():
                if not isinstance(wl_list, list):
                    continue
                for entry in wl_list:
                    if isinstance(entry, str) and entry not in seen_fqcns:
                        seen_fqcns.add(entry)
                        fqcn, role, collection = parse_workload_fqcn(entry)
                        workloads.append({"fqcn": fqcn, "role": role, "collection": collection})

        owd = definition.get("openshift_workload_deployer_workloads")
        if isinstance(owd, list):
            for entry in owd:
                name = entry.get("name") if isinstance(entry, dict) else None
                if name and isinstance(name, str) and name not in seen_fqcns:
                    seen_fqcns.add(name)
                    fqcn, role, collection = parse_workload_fqcn(name)
                    workloads.append({"fqcn": fqcn, "role": role, "collection": collection})
    else:
        raw = definition.get("workloads")
        if isinstance(raw, list):
            for entry in raw:
                if isinstance(entry, str) and entry not in seen_fqcns:
                    seen_fqcns.add(entry)
                    fqcn, role, collection = parse_workload_fqcn(entry)
                    workloads.append({"fqcn": fqcn, "role": role, "collection": collection})

    result["workloads"] = workloads

    meta = definition.get("__meta__", {})
    access_control = meta.get("access_control", {}) or {}
    acl_groups = access_control.get("allow_groups", []) or []
    result["acl_groups"] = [g for g in acl_groups if isinstance(g, str)]

    return result


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

        for ns_idx, ns in enumerate(namespaces, 1):
            log.info("Reading CatalogItems from namespace %d/%d: %s", ns_idx, len(namespaces), ns)
            try:
                crds = self.list_catalog_items(ns)
            except client.ApiException as e:
                log.error("Failed to list CatalogItems in %s: %s", ns, e.reason)
                continue

            log.info("Found %d CatalogItems in %s, processing...", len(crds), ns)
            for i, crd in enumerate(crds, 1):
                item = extract_catalog_item(crd)
                ci_name = item["ci_name"]

                component = self.get_agnosticv_component(
                    ci_name, component_namespace
                )
                if component:
                    url, ref = extract_showroom_url(component)
                    item["showroom_url"] = url
                    item["showroom_ref"] = ref
                    if url:
                        log.debug("  %s: showroom=%s ref=%s", ci_name, url, ref)

                    infra = extract_infrastructure_metadata(component)
                    if infra:
                        item["is_agd_v2"] = True
                        item["agd_config"] = infra.get("agd_config")
                        item["cloud_provider"] = infra.get("cloud_provider")
                        item["ocp_version"] = infra.get("ocp_version")
                        item["os_image"] = infra.get("os_image")
                        item["worker_instance_count"] = infra.get("worker_instance_count")
                        item["control_plane_instance_count"] = infra.get("control_plane_instance_count")
                        item["instances_json"] = infra.get("instances_json")
                        item["_workloads"] = infra.get("workloads", [])
                        item["_acl_groups"] = infra.get("acl_groups", [])

                    if item["is_published"]:
                        base_refs = extract_base_ci_refs(component)
                        if base_refs:
                            stage = item.get("stage", "prod")
                            item["base_ci_name"] = component_item_to_ci_name(
                                base_refs[0], stage
                            )

                items.append(item)

                if i % 50 == 0:
                    log.info("  processed %d/%d items in %s", i, len(crds), ns)

            log.info("Completed %s: %d items", ns, len(crds))

        # Second pass: set published_ci_name on base CIs
        items_by_name = {i["ci_name"]: i for i in items}
        for item in items:
            if item.get("base_ci_name") and item["base_ci_name"] in items_by_name:
                base = items_by_name[item["base_ci_name"]]
                base["published_ci_name"] = item["ci_name"]
                # Inherit Showroom URL from base CI if published VCI doesn't have one
                if not item.get("showroom_url") and base.get("showroom_url"):
                    item["showroom_url"] = base["showroom_url"]
                    item["showroom_ref"] = base.get("showroom_ref")

        return items
