#!/usr/bin/env python3
"""Sync the vocabulary.yaml products section from Red Hat's Official Product List (OPL).

Requires VPN access to the OPL API. This is a user-run script, not part of
the nightly pipeline — run it periodically when you want to refresh the
product list against OPL's authoritative source.

WORKFLOW
--------
1. Connect to the Red Hat VPN.

2. Generate a candidate vocabulary file:

    python tools/sync_opl_vocabulary.py \\
        --api-url https://opl-ui.apps.int.gpc.ocp-hub.prod.psi.redhat.com/api/v1 \\
        --api-key YOUR_OPL_API_KEY \\
        --output /tmp/vocabulary.yaml

3. Review the diff against the current file:

    diff src/api/rcars/data/vocabulary.yaml /tmp/vocabulary.yaml

4. If satisfied, replace the source file:

    cp /tmp/vocabulary.yaml src/api/rcars/data/vocabulary.yaml

5. Commit, open a PR, and deploy. The vocabulary takes effect on the next
   rolling restart of the API, scan-worker, and recommend-worker.

FILTERING STRATEGY
------------------
Three layers, designed to be self-maintaining as OPL adds new products:

  1. Portfolio allowlist — only products in Cloud, AI, Application services,
     Automation and management, Data services, Edge, Virtualization, Linux
     platforms. New products landing in these portfolios appear automatically.

  2. Type filter — within allowed portfolios, keep Market product + Family.
     This covers the core sellable products and product families.

  3. Named includes — products OPL types as Operator/Component/Feature/Tool
     that are real products with RHDP content (GitOps, Pipelines, etc.).
     Aliases still come from OPL — only the name is hardcoded here.

Products that pass all three filters but are SKU variants, partner bundles,
or otherwise not relevant to RHDP content are excluded via SKIP_EXACT.

Products NOT in OPL at all (deprecated, community, or not yet listed) are
appended as manual entries in a clearly marked section of the output file.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import yaml


# ── Strategic filters ──

ALLOW_PORTFOLIOS = {
    "Cloud",
    "AI",
    "Application services",
    "Automation and management",
    "Data services",
    "Edge",
    "Virtualization",
    "Linux platforms",
}

ALLOW_TYPES = {"Market product", "Family"}

# Products OPL types as Operator/Component/Feature/Tool/Collection/Portal
# but that are real products with RHDP content. They get their aliases from
# OPL automatically — only the name needs to be listed here.
INCLUDE_BY_NAME = {
    "Red Hat OpenShift GitOps",
    "Red Hat OpenShift Pipelines",
    "Red Hat OpenShift Virtualization",
    "Red Hat OpenShift Service Mesh",
    "Red Hat OpenShift Serverless",
    "Red Hat build of Keycloak",
    "Red Hat OpenShift Lightspeed",
    "Event-Driven Ansible",
    "Red Hat Hardened Images",
    "Red Hat OpenShift Logging",
    "Red Hat OpenShift Builds",
    "Identity Management",
}

# ── Tactical skip rules (within allowed portfolios/types) ──

SKIP_PREFIXES = [
    "Red Hat Consulting:",
    "Red Hat Learning Subscription",
    "Dell ",
    "HPE ",
    "Nokia ",
    "Celonis ",
    "Cloudera ",
    "Microsoft SQL",
]

SKIP_CONTAINS = [
    "on IBM Cloud",
    "on Microsoft Azure",
    "from AWS",
    "from Google Cloud",
    "for Microsoft Azure",
    "for AWS",
    "for Google Cloud",
    "on Azure",
    "Managed Service",
    "Cloud Service",
    "for IBM Power",
    "for IBM Z",
    "for SAP ",
    "for ARM",
    "for NVIDIA",
    "for Real Time",
    "for Workstations",
    "for Virtual Datacenters",
    "for Business Developers",
    "for Distributed Computing",
    "for Third Party Linux Migration",
    "High Availability Add-On",
    "Load Balancer Add-On",
    "Extended Life Cycle",
    "Extended Update Support",
    "Long-Life Add-On",
    "(classic architecture)",
    "GovCloud",
    "Self-Managed",
]

SKIP_EXACT = {
    "Red Hat Desktop",
    "Red Hat Certificate System",
    "Red Hat Directory Server",
    "Red Hat Enterprise Linux Desktop",
    "Red Hat Enterprise Linux Server",
    "Red Hat Enterprise Linux Server for High-Performance Computing",
    "Red Hat Enterprise Linux CoreOS",
    "Red Hat Runtimes",
    "Red Hat Update Infrastructure",
    "Red Hat JBoss Web Server",
    "Red Hat JBoss Enterprise Application Platform for OpenShift Container Platform",
    "Red Hat Quay.io",
    "Red Hat Data Grid for OpenShift Container Platform",
    "Red Hat Trusted Artifact Signer Client",
    "Red Hat Developer Hub Local",
    "Red Hat OpenShift Data Foundation Advanced",
    "Red Hat OpenShift Data Foundation Essentials",
    "Red Hat OpenShift Virtualization Engine",
    "Red Hat OpenShift Kubernetes Engine",
    "Red Hat OpenShift AI Cloud Service",
    "Red Hat OpenShift AI Self-Managed",
    "Red Hat OpenShift API Designer",
    "Red Hat OpenShift API Management",
    "Red Hat OpenShift Container Platform Extended Life Cycle Support Add-On",
    "Red Hat OpenShift Service on AWS (classic architecture)",
    "Red Hat Satellite Server",
    "Red Hat Satellite Extended Update Support Add-On",
    "Red Hat AI Enterprise",
    "Red Hat Ansible Inside",
    "Red Hat Bare-Metal-as-a-Service for OpenShift",
    "Red Hat Device Edge Essentials",
    "Lightwell Clearinghouse Premier",
    "Red Hat AI Accelerator",
    "Red Hat AI Factory with NVIDIA",
    "Red Hat Ansible Automation Platform Service on AWS",
    "Red Hat Ansible Developer",
    "Red Hat Application Foundations",
    "Red Hat Developer Toolset",
    "Red Hat OpenShift Local",
    "Red Hat OpenShift Platform Plus",
}

# Products OPL lists separately but should merge into one vocabulary entry.
# Key = OPL name to absorb, value = canonical name to merge into.
MERGE_INTO = {
    "Lightwell Network": "Lightwell",
    "Red Hat AMQ": "Red Hat AMQ Streams",
}

# Explicit renames: OPL official name → our current (incorrect) name.
RENAME_EXACT = {
    "Microsoft Azure Red Hat OpenShift": "Azure Red Hat OpenShift",
    "Lightwell": "Red Hat Lightwell",
}

RENAME_SUFFIXES = [
    " for Kubernetes",
    " for Virtualization",
]

# Products NOT in OPL that we maintain manually. These have active RHDP
# content but OPL either doesn't list them or lists them as Deprecated.
MANUAL_ENTRIES = [
    {"name": "Migration Toolkit for Virtualization", "aliases": ["MTV"]},
    {"name": "Red Hat Insights", "aliases": ["Insights"]},
    {"name": "Red Hat Build of Apache Camel", "aliases": ["Camel", "Red Hat Fuse", "Fuse"]},
    {"name": "Red Hat Trusted Application Pipeline", "aliases": ["TAP", "Trusted Application Pipeline"]},
    {"name": "Red Hat Enterprise Linux CoreOS", "aliases": ["RHCOS", "CoreOS"]},
]


# ── API helpers ──

def _fetch(api_url: str, api_key: str, path: str) -> Any:
    url = f"{api_url.rstrip('/')}/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def _should_skip(name: str) -> bool:
    if name in SKIP_EXACT:
        return True
    for prefix in SKIP_PREFIXES:
        if name.startswith(prefix):
            return True
    for fragment in SKIP_CONTAINS:
        if fragment in name:
            return True
    return False


def _find_current_match(opl_name: str, current_by_name: dict[str, dict], matched: set[str]) -> str | None:
    if opl_name in current_by_name and opl_name not in matched:
        return opl_name
    if opl_name in RENAME_EXACT:
        old_name = RENAME_EXACT[opl_name]
        if old_name in current_by_name and old_name not in matched:
            return old_name
    for suffix in RENAME_SUFFIXES:
        if opl_name.endswith(suffix):
            shorter = opl_name[: -len(suffix)]
            if shorter in current_by_name and shorter not in matched:
                return shorter
    return None


def fetch_all_products(api_url: str, api_key: str, log) -> list[dict[str, Any]]:
    """Fetch all Available products from OPL (no type_id filter)."""
    products: dict[str, dict] = {}
    page = 1
    while True:
        data = _fetch(api_url, api_key, f"products?status=Available&per_page=100&page={page}")
        for p in data["products"]:
            products[p["product_id"]] = p
        total_pages = data["pagination"]["pages"]
        log(f"  Page {page}/{total_pages} ({len(products)} products)")
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.1)
    return list(products.values())


def fetch_product_detail(api_url: str, api_key: str, product_id: str) -> dict[str, Any]:
    return _fetch(api_url, api_key, f"products/{product_id}")


def build_product_entry(detail: dict[str, Any]) -> dict[str, Any]:
    name = detail["product_name"].strip()
    aliases = []
    for a in detail.get("aliases", []):
        alias_name = a["alias_name"].strip()
        if not alias_name or alias_name == name or a.get("previous_name"):
            continue
        if ", " in alias_name and a.get("alias_type") != "Acronym":
            for part in alias_name.split(", "):
                part = part.strip()
                if part and part != name and part not in aliases:
                    aliases.append(part)
        elif alias_name not in aliases:
            aliases.append(alias_name)
    return {"name": name, "aliases": aliases}


def should_include(name: str, portfolios: set[str], types: set[str]) -> bool:
    """Three-layer filter: portfolio → type → named include."""
    if not portfolios & ALLOW_PORTFOLIOS:
        return False
    if name in INCLUDE_BY_NAME:
        return True
    if types & ALLOW_TYPES:
        return True
    return False


def load_current_vocabulary(vocab_path: Path) -> dict[str, Any]:
    return yaml.safe_load(vocab_path.read_text()) or {}


HEADER = """\
# vocabulary.yaml — controlled vocabulary shared by all content analyzers
#
# Product names sourced from the Red Hat Official Product List (OPL).
# Regenerated by tools/sync_opl_vocabulary.py (requires VPN).
#
# How it is used:
#   1. Loaded once per process by rcars/services/vocabulary.py (@lru_cache).
#   2. ONLY products are injected into the analysis prompt. The model is told
#      to PREFER a listed product name and only coin a new one when nothing
#      matches. All other dimensions stay OUT of the prompt.
#   3. A post-analysis normalization pass snaps aliases to canonical forms.
#
# Aliases vs search_terms:
#   aliases      — alternate names that normalize to the canonical name in BOTH
#                  directions: the analysis normalizer rewrites them, AND Advisor
#                  query expansion includes them. Use for acronyms, short names,
#                  and official alternate spellings.
#   search_terms — widen Advisor query expansion ONLY. The normalizer ignores
#                  them entirely. Use for concepts, technologies, or generic
#                  terms that should pull up a product in search but are not
#                  alternate names for it (e.g. "container registry" -> Red Hat
#                  Quay, "Istio" -> Red Hat OpenShift Service Mesh).
#
# To update products: run tools/sync_opl_vocabulary.py (requires VPN).
# To update other sections: edit this file directly, open a PR, merge.
# Ops can override per-environment via the mounted ConfigMap.

"""


def main():
    parser = argparse.ArgumentParser(
        description="Sync vocabulary.yaml products from the Red Hat Official Product List (OPL).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--api-url", required=True, help="OPL API base URL")
    parser.add_argument("--api-key", required=True, help="OPL API bearer token")
    parser.add_argument(
        "--vocab",
        default=str(Path(__file__).resolve().parent.parent / "src" / "api" / "rcars" / "data" / "vocabulary.yaml"),
        help="Path to current vocabulary.yaml (default: src/api/rcars/data/vocabulary.yaml)",
    )
    parser.add_argument("--output", required=True, help="Where to write the merged vocabulary.yaml")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    args = parser.parse_args()

    def log(msg: str):
        if not args.quiet:
            print(msg, file=sys.stderr)

    vocab_path = Path(args.vocab)
    if not vocab_path.exists():
        print(f"Error: vocabulary file not found: {vocab_path}", file=sys.stderr)
        sys.exit(1)

    current = load_current_vocabulary(vocab_path)
    current_products = current.get("products", [])
    current_by_name = {p["name"]: dict(p) for p in current_products}
    log(f"Current vocabulary: {len(current_products)} products")

    # Fetch all products from OPL
    log("Fetching all products from OPL...")
    all_products = fetch_all_products(args.api_url, args.api_key, log)
    log(f"OPL total: {len(all_products)}")

    # Fetch detail for each, apply 3-layer filter
    opl_entries = []
    absorbed_names: set[str] = set(MERGE_INTO.keys())
    merge_aliases: dict[str, list[str]] = {}

    for i, p in enumerate(all_products):
        pid = p["product_id"]
        name = p["product_name"].strip()
        if (i + 1) % 50 == 0:
            log(f"  Fetching details... {i + 1}/{len(all_products)}")
        try:
            detail = fetch_product_detail(args.api_url, args.api_key, pid)
            portfolios = {c["category_name"] for c in detail.get("portfolios", [])}
            types = {t["product_type"] for t in detail.get("types", [])}

            if not should_include(name, portfolios, types):
                continue
            if _should_skip(name):
                continue

            entry = build_product_entry(detail)

            # Handle merges
            if name in MERGE_INTO:
                target = MERGE_INTO[name]
                merge_aliases.setdefault(target, []).append(name)
                merge_aliases[target].extend(entry.get("aliases", []))
                continue

            opl_entries.append(entry)
        except Exception as e:
            log(f"  Warning: failed to fetch detail for {name}: {e}")
        time.sleep(0.03)

    log(f"OPL products after filtering: {len(opl_entries)}")

    # Build merged product list: OPL first, then manual
    merged = []
    matched_current: set[str] = set()
    renamed = []

    for op in opl_entries:
        name = op["name"]
        entry: dict[str, Any] = {"name": name}
        aliases = list(op.get("aliases", []))

        # Add aliases from merged products
        if name in merge_aliases:
            for extra in merge_aliases[name]:
                if extra not in aliases and extra != name:
                    aliases.append(extra)

        # Match against current vocabulary for overlays
        cur_match = _find_current_match(name, current_by_name, matched_current)
        if cur_match:
            cur = current_by_name[cur_match]
            matched_current.add(cur_match)
            if cur_match != name:
                if cur_match not in aliases:
                    aliases.append(cur_match)
                renamed.append(f"{cur_match} → {name}")
            # Keep manual aliases from current that OPL doesn't have
            for a in cur.get("aliases", []):
                if a not in aliases and a != name:
                    aliases.append(a)
            if cur.get("search_terms"):
                entry["search_terms"] = cur["search_terms"]
            if cur.get("is_tdp"):
                entry["is_tdp"] = True

        entry["aliases"] = aliases
        merged.append(entry)

    # Handle merge targets that are manual (e.g. Red Hat AMQ Streams)
    for target, extra_aliases in merge_aliases.items():
        if target not in {e["name"] for e in merged} and target in current_by_name:
            cur = current_by_name[target]
            matched_current.add(target)
            entry = dict(cur)
            cur_aliases = list(entry.get("aliases", []))
            for a in extra_aliases:
                if a not in cur_aliases and a != target:
                    cur_aliases.append(a)
            entry["aliases"] = cur_aliases
            merged.append(entry)

    # Manual entries — clearly separated
    manual_added = []
    for me in MANUAL_ENTRIES:
        if me["name"] not in {e["name"] for e in merged}:
            merged.append(dict(me))
            manual_added.append(me["name"])

    # Build output
    output = dict(current)
    output["products"] = merged

    body = yaml.safe_dump(output, sort_keys=False, default_flow_style=False, allow_unicode=True)

    # Insert a comment before the manual entries in the YAML output
    if manual_added:
        first_manual = manual_added[0]
        body = body.replace(
            f"- name: {first_manual}",
            f"# ── Manual entries — not in OPL, maintained by hand ──\n- name: {first_manual}",
        )

    Path(args.output).write_text(HEADER + body)

    # Report
    log("")
    log(f"Output written to: {args.output}")
    log(f"  Products: {len(opl_entries)} from OPL + {len(manual_added)} manual = {len(merged)} total")

    if renamed:
        log(f"\n  RENAMED ({len(renamed)}):")
        for r in renamed:
            log(f"    {r}")

    new_from_opl = [e["name"] for e in opl_entries if e["name"] not in current_by_name and e["name"] not in [r.split(" → ")[1] for r in renamed]]
    if new_from_opl:
        log(f"\n  NEW from OPL ({len(new_from_opl)}):")
        for name in new_from_opl:
            log(f"    + {name}")

    if manual_added:
        log(f"\n  MANUAL ({len(manual_added)}):")
        for name in manual_added:
            log(f"    # {name}")

    log("")
    log("Next steps:")
    log(f"  1. Review: diff {args.vocab} {args.output}")
    log(f"  2. If satisfied: cp {args.output} {args.vocab}")
    log("  3. Commit, PR, deploy.")


if __name__ == "__main__":
    main()
