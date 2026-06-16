"""Workload repo scanner — clone agDv2 collection repos, read role code, LLM-analyze."""

import json
import shutil
import structlog
from pathlib import Path
from typing import Any

from rcars.services.analyzer import clone_showroom, ls_remote_sha
from rcars.db import Database

log = structlog.get_logger()

AGDV2_COLLECTIONS = [
    {"name": "agnosticd.core_workloads", "url": "https://github.com/agnosticd/core_workloads.git"},
    {"name": "agnosticd.ai_workloads", "url": "https://github.com/agnosticd/ai_workloads.git"},
    {"name": "agnosticd.cloud_vm_workloads", "url": "https://github.com/agnosticd/cloud_vm_workloads.git"},
    {"name": "agnosticd.namespaced_workloads", "url": "https://github.com/agnosticd/namespaced_workloads.git"},
    {"name": "agnosticd.cnv_workloads", "url": "https://github.com/agnosticd/cnv_workloads.git"},
    {"name": "agnosticd.showroom", "url": "https://github.com/agnosticd/showroom.git"},
]

WORKLOAD_ANALYSIS_PROMPT = """You are analyzing an Ansible role from the AgnosticD v2 automation framework.
Your job is to determine what Red Hat product, operator, or service this role installs or configures on an OpenShift cluster or RHEL system.

Role name: {role_name}
Collection: {collection_name}

Below is the actual code from this role. Use ONLY the code to determine what this role does — do not guess from the name.

{code_content}

Respond with a JSON object:
{{
  "product_name": "Human-readable product name (e.g. 'OpenShift AI', 'Advanced Cluster Security')",
  "description": "One sentence describing what this role installs/configures",
  "category": "One of: ai_ml, cicd, security, storage, virtualization, networking, runtime, developer_tools, registry, management, automation, messaging, auth, platform, monitoring, other",
  "is_infrastructure_plumbing": true/false
}}

Set is_infrastructure_plumbing to true if this role is internal setup (authentication, showroom deployment, bastion configuration, namespace creation, certificate management) rather than a user-facing product that someone would search for.

Return ONLY the JSON object, no other text."""


def read_role_code(role_path: Path, max_chars: int = 12000) -> str:
    """Read key files from an Ansible role for LLM analysis."""
    sections = []
    files_to_read = [
        ("defaults/main.yml", "DEFAULTS"),
        ("defaults/main.yaml", "DEFAULTS"),
        ("tasks/main.yml", "TASKS"),
        ("tasks/main.yaml", "TASKS"),
        ("meta/main.yml", "META"),
        ("meta/main.yaml", "META"),
    ]
    for rel_path, label in files_to_read:
        fp = role_path / rel_path
        if fp.exists():
            content = fp.read_text(errors="replace")[:4000]
            sections.append(f"=== {label} ({rel_path}) ===\n{content}")

    template_dir = role_path / "templates"
    if template_dir.is_dir():
        for tf in sorted(template_dir.iterdir())[:5]:
            if tf.suffix in (".yml", ".yaml", ".j2") and tf.is_file():
                content = tf.read_text(errors="replace")[:2000]
                sections.append(f"=== TEMPLATE ({tf.name}) ===\n{content}")

    combined = "\n\n".join(sections)
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "\n... (truncated)"
    return combined


def discover_roles(clone_path: Path) -> list[str]:
    """Find all role directories in a cloned collection repo."""
    roles_dir = clone_path / "roles"
    if roles_dir.is_dir():
        return sorted([
            d.name for d in roles_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ])
    return sorted([
        d.name for d in clone_path.iterdir()
        if d.is_dir()
        and not d.name.startswith(".")
        and d.name not in ("meta", "plugins", "tests", "docs", ".github")
        and ((d / "tasks").is_dir() or (d / "defaults").is_dir())
    ])


def analyze_role(
    role_name: str,
    role_path: Path,
    collection_name: str,
    settings,
    model: str,
    db: Database | None = None,
) -> dict | None:
    """Analyze a single role via LLM and return the mapping dict."""
    code_content = read_role_code(role_path)
    if not code_content.strip():
        log.info("workload_scan_skip", component="workload_scan", action="skipping",
                 collection=collection_name, role=role_name, reason="no readable code")
        return None

    prompt = WORKLOAD_ANALYSIS_PROMPT.format(
        role_name=role_name,
        collection_name=collection_name,
        code_content=code_content,
    )

    try:
        from rcars.config import call_llm
        llm_result = call_llm(settings, model=model, messages=[{"role": "user", "content": prompt}], max_tokens=1024)

        input_tokens = llm_result.input_tokens
        output_tokens = llm_result.output_tokens

        if db is not None:
            db.log_token_usage(
                operation="workload_scan",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                ci_name=f"{collection_name}.{role_name}",
                provider=llm_result.provider,
            )

        text = llm_result.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]

        result = json.loads(text)
        log.info("workload_scan_analyzed", component="workload_scan", action="analyzed",
                 collection=collection_name, role=role_name,
                 product_name=result.get("product_name"), category=result.get("category"))
        return result

    except (json.JSONDecodeError, IndexError, KeyError) as e:
        log.warning("workload_scan_parse_error", component="workload_scan", action="failed_to_parse",
                    collection=collection_name, role=role_name, error=str(e))
        return None
    except Exception as e:
        log.error("workload_scan_llm_error", component="workload_scan", action="llm_error",
                  collection=collection_name, role=role_name, error=str(e))
        return None


def scan_collection(
    collection_name: str,
    collection_url: str,
    clone_dir: str,
    settings,
    model: str,
    db: Database,
    force: bool = False,
) -> dict:
    """Scan a single collection repo. Returns stats dict."""
    rlog = log.bind(collection=collection_name)

    if not force:
        remote_sha = ls_remote_sha(collection_url, "main")
        if remote_sha:
            state = db.get_scan_state(collection_name)
            if state and state.get("last_sha") == remote_sha:
                rlog.info("workload_scan: unchanged (SHA %s), skipping", remote_sha[:12])
                return {"collection": collection_name, "status": "unchanged", "roles_scanned": 0}

    clone_path = clone_showroom(collection_url, "main", clone_dir)
    if not clone_path:
        rlog.error("workload_scan: clone failed")
        return {"collection": collection_name, "status": "clone_failed", "roles_scanned": 0}

    try:
        import subprocess
        local_sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(clone_path),
            capture_output=True, text=True,
        )
        local_sha = local_sha_result.stdout.strip() if local_sha_result.returncode == 0 else None

        roles = discover_roles(clone_path)
        rlog.info("workload_scan: found %d roles", len(roles))

        scanned = 0
        mapped = 0
        skipped_plumbing = 0

        for role_name in roles:
            role_path = clone_path / "roles" / role_name
            if not role_path.is_dir():
                role_path = clone_path / role_name
            if not role_path.is_dir():
                continue

            result = analyze_role(role_name, role_path, collection_name, settings, model, db)
            scanned += 1

            if result and result.get("product_name"):
                if result.get("is_infrastructure_plumbing"):
                    skipped_plumbing += 1
                    rlog.info("workload_scan: %s → plumbing, not mapping", role_name)
                else:
                    db.upsert_workload_mapping(
                        workload_role=role_name,
                        product_name=result["product_name"],
                        description=result.get("description"),
                        category=result.get("category"),
                        source_collection=collection_name,
                        verified=True,
                        added_by="workload_scanner",
                    )
                    mapped += 1

        if local_sha:
            db.upsert_scan_state(collection_name, local_sha)

        stats = {
            "collection": collection_name,
            "status": "scanned",
            "roles_found": len(roles),
            "roles_scanned": scanned,
            "roles_mapped": mapped,
            "roles_plumbing": skipped_plumbing,
        }
        rlog.info("workload_scan: complete", **stats)
        return stats

    finally:
        shutil.rmtree(clone_path, ignore_errors=True)


def scan_all_collections(
    clone_dir: str,
    settings,
    model: str,
    db: Database,
    force: bool = False,
    collection_filter: str | None = None,
) -> list[dict]:
    """Scan all (or filtered) agDv2 collection repos."""
    collections = AGDV2_COLLECTIONS
    if collection_filter:
        collections = [c for c in collections if c["name"] == collection_filter]
        if not collections:
            log.warning("workload_scan: unknown collection %s", collection_filter)
            return []

    results = []
    for coll in collections:
        result = scan_collection(
            collection_name=coll["name"],
            collection_url=coll["url"],
            clone_dir=clone_dir,
            settings=settings,
            model=model,
            db=db,
            force=force,
        )
        results.append(result)

    return results
