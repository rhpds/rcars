"""Workload repo scanner — clone agDv2 collection repos, read role code, LLM-analyze."""

import json
import re
import shutil
import structlog
from pathlib import Path
from typing import Any

from rcars.services.analyzer import (
    clone_showroom, ls_remote_sha,
    build_infrastructure_embedding_text, generate_embedding, regenerate_embeddings,
)
from rcars.db import Database

log = structlog.get_logger()

AGDV2_COLLECTIONS = [
    {"name": "agnosticd.core_workloads", "url": "https://github.com/rhpds/core_workloads.git"},
    {"name": "agnosticd.ai_workloads", "url": "https://github.com/rhpds/ai_workloads.git"},
    {"name": "agnosticd.cloud_vm_workloads", "url": "https://github.com/rhpds/cloud_vm_workloads.git"},
    {"name": "agnosticd.namespaced_workloads", "url": "https://github.com/rhpds/namespaced_workloads.git"},
    {"name": "agnosticd.cnv_workloads", "url": "https://github.com/rhpds/cnv_workloads.git"},
    {"name": "agnosticd.showroom", "url": "https://github.com/rhpds/showroom.git"},
]

WORKLOAD_SYSTEM_PROMPT = """\
You are analyzing an Ansible role from the AgnosticD v2 automation framework.
Your job is to determine what this role installs, configures, or enables on an OpenShift cluster or RHEL system.

Use ONLY the code provided to determine what the role does — do not guess from the name.

Respond with a JSON object:
{
  "product_name": "Human-readable product name (e.g. 'OpenShift AI', 'Advanced Cluster Security')",
  "description": "Multi-sentence narrative covering what this role installs, configures, and enables, including default configuration choices discovered from the code (e.g. 'default authentication provider is KeyCloak')",
  "products": ["Array of products/operators/services this installs"],
  "capabilities": ["Array of capabilities this enables (e.g. 'model-serving', 'notebook-hosting')"],
  "category": "One of: ai_ml, cicd, security, storage, virtualization, networking, runtime, developer_tools, registry, management, automation, messaging, auth, platform, monitoring, other",
  "requires": ["Array of prerequisites (e.g. 'openshift 4.14+', 'gpu-nodes')"],
}

Return ONLY the JSON object, no other text."""

WORKLOAD_USER_TEMPLATE = """\
Role name: {role_name}
Collection: {collection_name}

{code_content}"""


_INCLUDE_RE = re.compile(r'(?:include_tasks|import_tasks):\s*["\']?([^\s"\']+\.ya?ml)', re.MULTILINE)


def _follow_task_includes(tasks_content: str, tasks_dir: Path, sections: list[str]) -> None:
    """Read files referenced by include_tasks/import_tasks in tasks/main — one level only."""
    for match in _INCLUDE_RE.findall(tasks_content):
        fp = tasks_dir / match
        if fp.exists() and fp.is_file():
            content = fp.read_text(errors="replace")[:4000]
            sections.append(f"=== TASKS ({match}) ===\n{content}")


def read_role_code(role_path: Path, max_chars: int = 40000) -> str:
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
            if label == "TASKS":
                _follow_task_includes(content, fp.parent, sections)

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

    user_message = WORKLOAD_USER_TEMPLATE.format(
        role_name=role_name,
        collection_name=collection_name,
        code_content=code_content,
    )

    try:
        from rcars.config import call_llm
        llm_result = call_llm(settings, model=model, messages=[{"role": "user", "content": user_message}], max_tokens=1024, system=WORKLOAD_SYSTEM_PROMPT)

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

        if result.get("product_name"):
            emb_text = build_infrastructure_embedding_text({
                "role_name": role_name,
                "description": result.get("description"),
                "products": result.get("products", [result["product_name"]]),
                "capabilities": result.get("capabilities", []),
                "category": result.get("category"),
            })
            if emb_text.strip():
                result["embedding_text"] = emb_text
                result["embedding"] = generate_embedding(emb_text, prefix="search_document")

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
            existing = db.get_infrastructure_scan_sha(collection_name)
            if existing == remote_sha:
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

        for role_name in roles:
            role_path = clone_path / "roles" / role_name
            if not role_path.is_dir():
                role_path = clone_path / role_name
            if not role_path.is_dir():
                continue

            result = analyze_role(role_name, role_path, collection_name, settings, model, db)
            scanned += 1

            if result and result.get("product_name"):
                fqcn = f"{collection_name}.{role_name}"
                db.upsert_infrastructure(
                    role_name=role_name,
                    fqcn=fqcn,
                    collection=collection_name,
                    type="workload",
                    description=result.get("description"),
                    products=result.get("products", [result["product_name"]]),
                    capabilities=result.get("capabilities", []),
                    category=result.get("category"),
                    requires=result.get("requires", []),
                    source_sha=local_sha,
                )
                if result.get("embedding"):
                    regenerate_embeddings(
                        db, role_name, "infrastructure", "agnosticd",
                        result["embedding_text"], result["embedding"],
                    )
                mapped += 1

        stats = {
            "collection": collection_name,
            "status": "scanned",
            "roles_found": len(roles),
            "roles_scanned": scanned,
            "roles_mapped": mapped,
        }
        rlog.info("workload_scan: complete", **stats)
        return stats

    finally:
        shutil.rmtree(clone_path, ignore_errors=True)


AGDV2_CONFIGS_REPO = {
    "name": "agnosticd-v2-configs",
    "url": "https://github.com/rhpds/agnosticd-v2.git",
    "configs_path": "ansible/configs",
}

EXCLUDE_CONFIGS = {"test-empty-config"}

CONFIG_SYSTEM_PROMPT = """\
You are analyzing a base infrastructure configuration from the AgnosticD v2 automation framework.
This is NOT an Ansible role — it is a full environment configuration that provisions cloud infrastructure
and installs a base platform (e.g. an OpenShift cluster, a set of cloud VMs, a namespace).

Use ONLY the code provided to determine what this config provisions and what it provides.

Respond with a JSON object:
{
  "description": "Multi-sentence narrative covering what this config provisions, what platform it provides, what cloud providers it supports, and key configuration options",
  "products": ["Array of products/platforms this provides (e.g. 'OpenShift', 'RHEL')"],
  "capabilities": ["Array of capabilities (e.g. 'cluster-provisioning', 'gpu-support', 'multi-node')"],
  "category": "One of: platform, virtualization, cloud, namespace, other",
  "requires": ["Array of prerequisites (e.g. 'AWS account', 'Azure subscription')"]
}

Return ONLY the JSON object, no other text."""

CONFIG_USER_TEMPLATE = """\
Config name: {config_name}

{code_content}"""


def read_config_code(config_path: Path, max_chars: int = 40000) -> str:
    """Read key files from a config directory for LLM analysis."""
    sections = []
    files_to_read = [
        ("default_vars.yml", "DEFAULT VARS"),
        ("default_vars.yaml", "DEFAULT VARS"),
        ("README.adoc", "README"),
        ("README.md", "README"),
        ("software.yml", "SOFTWARE PLAYBOOK"),
        ("software.yaml", "SOFTWARE PLAYBOOK"),
        ("post_software.yml", "POST SOFTWARE"),
        ("post_software.yaml", "POST SOFTWARE"),
    ]
    for rel_path, label in files_to_read:
        fp = config_path / rel_path
        if fp.exists() and fp.is_file():
            content = fp.read_text(errors="replace")[:4000]
            sections.append(f"=== {label} ({rel_path}) ===\n{content}")
            if "PLAYBOOK" in label:
                _follow_task_includes(content, fp.parent, sections)

    # Provider-specific default_vars in subdirectories
    for subdir in sorted(config_path.iterdir()) if config_path.is_dir() else []:
        if subdir.is_dir() and subdir.name not in (".", ".."):
            for name in ("default_vars.yml", "default_vars.yaml"):
                fp = subdir / name
                if fp.exists() and fp.is_file():
                    content = fp.read_text(errors="replace")[:3000]
                    sections.append(f"=== PROVIDER VARS ({subdir.name}/{name}) ===\n{content}")

    combined = "\n\n".join(sections)
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "\n... (truncated)"
    return combined


def analyze_config(
    config_name: str,
    config_path: Path,
    settings,
    model: str,
    db: Database | None = None,
) -> dict | None:
    """Analyze a single config via LLM and return structured data."""
    code_content = read_config_code(config_path)
    if not code_content.strip():
        log.info("config_scan_skip", component="config_scan", action="skipping",
                 config=config_name, reason="no readable code")
        return None

    user_message = CONFIG_USER_TEMPLATE.format(
        config_name=config_name, code_content=code_content,
    )

    try:
        from rcars.config import call_llm
        llm_result = call_llm(settings, model=model,
                              messages=[{"role": "user", "content": user_message}],
                              max_tokens=1024, system=CONFIG_SYSTEM_PROMPT)

        if db is not None:
            db.log_token_usage(
                operation="config_scan", model=model,
                input_tokens=llm_result.input_tokens,
                output_tokens=llm_result.output_tokens,
                ci_name=config_name, provider=llm_result.provider,
            )

        text = llm_result.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]

        result = json.loads(text)
        emb_text = build_infrastructure_embedding_text({
            "role_name": config_name,
            "description": result.get("description"),
            "products": result.get("products", []),
            "capabilities": result.get("capabilities", []),
            "category": result.get("category"),
        })
        if emb_text.strip():
            result["embedding_text"] = emb_text
            result["embedding"] = generate_embedding(emb_text, prefix="search_document")

        log.info("config_scan_analyzed", component="config_scan", action="analyzed",
                 config=config_name, category=result.get("category"))
        return result

    except (json.JSONDecodeError, IndexError, KeyError) as e:
        log.warning("config_scan_parse_error", component="config_scan", action="failed_to_parse",
                    config=config_name, error=str(e))
        return None
    except Exception as e:
        log.error("config_scan_llm_error", component="config_scan", action="llm_error",
                  config=config_name, error=str(e))
        return None


def scan_configs(
    clone_dir: str,
    settings,
    model: str,
    db: Database,
    force: bool = False,
) -> dict:
    """Scan AgnosticD v2 configs directory."""
    repo = AGDV2_CONFIGS_REPO
    rlog = log.bind(component="config_scan")

    if not force:
        remote_sha = ls_remote_sha(repo["url"], "main")
        if remote_sha:
            existing = db.get_infrastructure_scan_sha(repo["name"])
            if existing == remote_sha:
                rlog.info("config_scan: unchanged, skipping")
                return {"status": "unchanged", "configs_scanned": 0}

    clone_path = clone_showroom(repo["url"], "main", clone_dir)
    if not clone_path:
        rlog.error("config_scan: clone failed")
        return {"status": "clone_failed", "configs_scanned": 0}

    try:
        import subprocess
        local_sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(clone_path),
            capture_output=True, text=True,
        )
        local_sha = local_sha_result.stdout.strip() if local_sha_result.returncode == 0 else None

        configs_dir = clone_path / Path(repo["configs_path"])
        if not configs_dir.is_dir():
            rlog.error("config_scan: configs path not found: %s", configs_dir)
            return {"status": "no_configs_dir", "configs_scanned": 0}

        config_dirs = sorted([
            d for d in configs_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".") and d.name not in EXCLUDE_CONFIGS
        ])
        rlog.info("config_scan: found %d configs", len(config_dirs))

        scanned = 0
        for config_dir in config_dirs:
            config_name = config_dir.name
            result = analyze_config(config_name, config_dir, settings, model, db)
            scanned += 1

            if result:
                db.upsert_infrastructure(
                    role_name=config_name,
                    fqcn=None,
                    collection=repo["name"],
                    type="config",
                    description=result.get("description"),
                    products=result.get("products", []),
                    capabilities=result.get("capabilities", []),
                    category=result.get("category"),
                    requires=result.get("requires", []),
                    source_sha=local_sha,
                )
                if result.get("embedding"):
                    regenerate_embeddings(
                        db, config_name, "infrastructure", "agnosticd",
                        result["embedding_text"], result["embedding"],
                    )

        return {"status": "scanned", "configs_found": len(config_dirs), "configs_scanned": scanned}

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
