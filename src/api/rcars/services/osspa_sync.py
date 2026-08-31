"""OSSPA portfolio architecture ingest.

Fetches the Architecture Center inventory (PAList.csv), scopes it to the three
architecture asset types, upserts entity + extension rows, retires what
disappeared, and re-analyzes only the items whose content actually changed.

Terminology: these are portfolio architectures, validated patterns, and
solution patterns — never "reference architectures". A reference architecture
is a prescriptive Red Hat artifact; these are curated examples.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

import structlog

logger = structlog.get_logger(component="osspa_sync")


class OsspaSyncError(Exception):
    """Fatal, sync-aborting condition — bad CSV, failed clone, unusable input."""


# The three architecture asset types. The CSV column is called ProductType but
# its values are Architecture Center artifact kinds, not Red Hat products.
ARCHITECTURE_ASSET_TYPES = frozenset({"PA", "VP", "SP"})
EXCLUDED_ASSET_TYPE = "IE"          # deferred: needs a different analysis approach

REQUIRED_CSV_COLUMNS = (
    "ppid", "PAName", "Heading", "islive", "showInCatalog", "ProductType", "DetailPage",
)

_TRUE_VALUES = frozenset({"true", "t", "yes", "y", "1"})

DEFAULT_AUDIENCE = ["architect", "developer"]


def content_id_for(ppid: int | str) -> str:
    return f"pa:{int(ppid)}"


def _as_bool(value: Any) -> bool:
    return str(value or "").strip().casefold() in _TRUE_VALUES


def _split_list(value: Any) -> list[str]:
    """Comma-split a CSV cell into a deduped, order-preserving list."""
    out: list[str] = []
    for part in str(value or "").split(","):
        item = part.strip()
        if item and item not in out:
            out.append(item)
    return out


def parse_palist_csv(text: str) -> list[dict[str, str]]:
    """Parse PAList.csv. Raises OsspaSyncError if the header is not usable."""
    reader = csv.DictReader(io.StringIO(text))
    header = reader.fieldnames or []
    missing = [c for c in REQUIRED_CSV_COLUMNS if c not in header]
    if missing:
        raise OsspaSyncError(f"PAList.csv header missing columns: {', '.join(missing)}")
    return [
        {(key or "").strip(): (value or "").strip() for key, value in row.items() if key is not None}
        for row in reader
    ]


def fetch_palist_csv(settings) -> list[dict[str, str]]:
    """HTTP GET PAList.csv under a bounded timeout, then parse it."""
    import httpx

    try:
        resp = httpx.get(
            settings.osspa_palist_url,
            timeout=settings.osspa_csv_fetch_timeout_s,
            follow_redirects=True,
        )
    except httpx.HTTPError as exc:
        raise OsspaSyncError(f"PAList.csv fetch failed: {exc}") from exc

    if resp.status_code != 200:
        raise OsspaSyncError(f"PAList.csv fetch returned HTTP {resp.status_code}")

    rows = parse_palist_csv(resp.text)
    logger.info("osspa_csv_fetched", action="fetch_csv",
                url=settings.osspa_palist_url, rows=len(rows), bytes=len(resp.text))
    return rows


def asset_type_tokens(product_type: str) -> list[str]:
    return [t.strip().upper() for t in str(product_type or "").split(",") if t.strip()]


def scope_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Apply the ingestion gate.

    Keep a row when it carries at least one of PA/VP/SP, carries no IE token,
    and points at a .adoc DetailPage. Live/catalog status is NOT a gate — it
    only drives the status tag (see derive_osspa_status).
    """
    scoped: list[dict[str, str]] = []
    index_by_ppid: dict[int, int] = {}

    for row in rows:
        tokens = asset_type_tokens(row.get("ProductType", ""))
        if EXCLUDED_ASSET_TYPE in tokens:
            continue
        if not ARCHITECTURE_ASSET_TYPES.intersection(tokens):
            continue

        detail = (row.get("DetailPage") or "").strip()
        if not detail or not detail.lower().endswith(".adoc"):
            continue

        raw_ppid = (row.get("ppid") or "").strip()
        if not raw_ppid.isdigit():
            logger.warning("osspa_row_skipped", action="scope_rows",
                           reason="non_numeric_ppid", ppid=raw_ppid,
                           pa_name=row.get("PAName"))
            continue
        ppid = int(raw_ppid)

        if ppid in index_by_ppid:
            logger.warning("osspa_duplicate_ppid", action="scope_rows",
                           ppid=ppid, resolution="last_row_wins")
            scoped[index_by_ppid[ppid]] = row
            continue

        index_by_ppid[ppid] = len(scoped)
        scoped.append(row)

    logger.info("osspa_rows_scoped", action="scope_rows",
                input_rows=len(rows), scoped_rows=len(scoped))
    return scoped


def derive_osspa_status(row: dict[str, str]) -> str:
    """Map the raw CSV booleans into Babylon's status vocabulary."""
    if _as_bool(row.get("islive")) and _as_bool(row.get("showInCatalog")):
        return "prod"
    return "dev"


def normalize_row(row: dict[str, str]) -> dict[str, Any]:
    """CSV row → the payload upsert_osspa_item takes."""
    solutions = _split_list(row.get("Solutions"))
    verticals = _split_list(row.get("Vertical"))
    topics: list[str] = []
    for term in (*solutions, *verticals):
        if term not in topics:
            topics.append(term)

    ppid = int(row["ppid"])
    return {
        "content_id": content_id_for(ppid),
        "ppid": ppid,
        "pa_name": row.get("PAName") or "",
        "display_name": row.get("Heading") or row.get("PAName") or f"Architecture {ppid}",
        "status": derive_osspa_status(row),
        "summary": row.get("Summary") or None,
        "products": _split_list(row.get("Product")),
        "topics": topics,
        "audience": list(DEFAULT_AUDIENCE),
        "solutions": solutions,
        "verticals": verticals,
        "detail_page": row.get("DetailPage") or "",
        "image_url": row.get("Image1Url") or None,
        "is_live": _as_bool(row.get("islive")),
        "show_in_catalog": _as_bool(row.get("showInCatalog")),
        "asset_type": (row.get("ProductType") or "").strip(),
        "meta_desc": row.get("metaDesc") or "",
        "meta_keyword": row.get("metaKeyword") or "",
    }


# ── Examples repo ──

def _run_git(args: list[str], timeout: int, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd) if cwd else None,
        capture_output=True, text=True, check=True, timeout=timeout,
    )


def clone_examples_repo(settings) -> Path:
    """Shallow, sparse checkout of the examples repo — .adoc files only."""
    clone_path = Path(settings.osspa_clone_dir)
    timeout = settings.osspa_clone_timeout_s
    ref = settings.osspa_examples_ref

    try:
        if (clone_path / ".git").is_dir():
            _run_git(["fetch", "--depth", "1", "origin", ref], timeout, cwd=clone_path)
            _run_git(["reset", "--hard", "FETCH_HEAD"], timeout, cwd=clone_path)
            _run_git(["clean", "-fdx"], timeout, cwd=clone_path)
        else:
            if clone_path.exists():
                import shutil
                shutil.rmtree(clone_path, ignore_errors=True)
            clone_path.parent.mkdir(parents=True, exist_ok=True)
            _run_git([
                "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                "--branch", ref, settings.osspa_examples_repo_url, str(clone_path),
            ], timeout)
            _run_git(["sparse-checkout", "set", "--no-cone", "*.adoc"], timeout, cwd=clone_path)
    except subprocess.TimeoutExpired as exc:
        raise OsspaSyncError(
            f"examples repo clone/fetch timed out after {timeout}s") from exc
    except subprocess.CalledProcessError as exc:
        raise OsspaSyncError(
            f"examples repo clone/fetch failed: {(exc.stderr or '').strip()[:300]}") from exc

    logger.info("osspa_clone_ready", action="clone_examples_repo",
                path=str(clone_path), ref=ref, head=get_head_sha(clone_path))
    return clone_path


def get_head_sha(clone_path: Path) -> str | None:
    try:
        return _run_git(["rev-parse", "HEAD"], timeout=30, cwd=clone_path).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None


def file_commit_sha(clone_path: Path, rel_path: str) -> str | None:
    """Commit SHA of the DetailPage file itself."""
    try:
        out = _run_git(["log", "-1", "--format=%H", "--", rel_path],
                       timeout=30, cwd=clone_path).stdout.strip()
        return out or None
    except (subprocess.SubprocessError, OSError):
        return None


def resolve_repo_path(clone_root: Path, rel_path: str) -> Path | None:
    """Safe join with canonical containment. None means reject the row."""
    candidate_rel = str(rel_path or "").strip().replace("\\", "/")
    if not candidate_rel or candidate_rel.startswith("/"):
        return None
    if ".." in Path(candidate_rel).parts:
        return None

    try:
        root_real = clone_root.resolve()
        real = (clone_root / candidate_rel).resolve()
    except OSError:
        return None

    if not real.is_relative_to(root_real):
        logger.warning("osspa_path_escape", action="resolve_repo_path", path=candidate_rel)
        return None
    return real


def is_tracked_at_head(clone_root: Path, path: Path) -> bool:
    """True only if the file exists in the HEAD tree — not merely on disk."""
    try:
        rel = path.resolve().relative_to(clone_root.resolve()).as_posix()
    except (OSError, ValueError):
        return False
    try:
        out = _run_git(["ls-tree", "-r", "--name-only", "HEAD", "--", rel],
                       timeout=30, cwd=clone_root).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return False
    return out == rel


# ── adoc reader ──

MAX_INCLUDE_DEPTH = 3

_INCLUDE_RE = re.compile(r"^\s*include::([^\[\]]+)\[([^\]]*)\]\s*$")
_PASSTHROUGH_DELIM_RE = re.compile(r"^\+{4,}\s*$")
_ARCADE_COMMENT_RE = re.compile(r"<!--\s*ARCADE EMBED.*?-->", re.DOTALL | re.IGNORECASE)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


class AdocRead(NamedTuple):
    full_text: str      # fully expanded, untruncated — the hash input
    prompt_text: str    # passthrough stripped and capped — the LLM input
    truncated: bool


def strip_passthrough(text: str) -> str:
    """Drop ++++ passthrough blocks and HTML/Arcade comments — no text signal."""
    out: list[str] = []
    inside = False
    for line in text.splitlines():
        if _PASSTHROUGH_DELIM_RE.match(line):
            inside = not inside
            continue
        if not inside:
            out.append(line)
    cleaned = "\n".join(out)
    cleaned = _ARCADE_COMMENT_RE.sub("", cleaned)
    return _HTML_COMMENT_RE.sub("", cleaned)


def expand_includes(clone_root: Path, path: Path, max_bytes: int) -> str:
    """Inline repo-internal include:: directives."""
    def _expand(current: Path, depth: int, visited: set[Path], budget: list[int]) -> list[str]:
        try:
            source = current.read_text(errors="replace")
        except OSError as exc:
            logger.warning("osspa_include_unreadable", action="expand_includes",
                           path=str(current), error=str(exc))
            return []

        lines: list[str] = []
        for line in source.splitlines():
            match = _INCLUDE_RE.match(line)
            if not match:
                lines.append(line)
                budget[0] += len(line) + 1
                continue

            target, selectors = match.group(1).strip(), match.group(2).strip()
            if selectors:
                logger.info("osspa_include_selectors_ignored", action="expand_includes",
                            target=target, selectors=selectors)

            if target.startswith(("http://", "https://")) or "{" in target:
                logger.warning("osspa_include_rejected", action="expand_includes",
                               target=target, reason="url_or_unresolved_attribute")
                continue
            if depth >= MAX_INCLUDE_DEPTH:
                logger.warning("osspa_include_rejected", action="expand_includes",
                               target=target, reason="max_depth")
                continue
            if budget[0] >= max_bytes:
                logger.warning("osspa_include_rejected", action="expand_includes",
                               target=target, reason="byte_budget_exhausted")
                continue

            try:
                candidate_rel = (current.parent / target).relative_to(clone_root).as_posix()
            except ValueError:
                candidate_rel = target
            resolved = resolve_repo_path(clone_root, candidate_rel)

            if resolved is None or not resolved.is_file():
                logger.warning("osspa_include_rejected", action="expand_includes",
                               target=target, reason="outside_root_or_missing")
                continue
            if resolved in visited:
                logger.warning("osspa_include_rejected", action="expand_includes",
                               target=target, reason="cycle")
                continue
            if not is_tracked_at_head(clone_root, resolved):
                logger.warning("osspa_include_rejected", action="expand_includes",
                               target=target, reason="untracked_at_head")
                continue

            visited.add(resolved)
            lines.extend(_expand(resolved, depth + 1, visited, budget))

        return lines

    return "\n".join(_expand(path, 0, {path.resolve()}, [0]))


def read_detail_adoc(clone_root: Path, detail_page: str, max_bytes: int) -> AdocRead | None:
    """Read one DetailPage. None means skip the row (unsafe, missing, untracked)."""
    target = resolve_repo_path(clone_root, detail_page)
    if target is None or not target.is_file():
        return None
    if not is_tracked_at_head(clone_root, target):
        logger.warning("osspa_detail_page_untracked", action="read_detail_adoc",
                       detail_page=detail_page)
        return None

    full_text = expand_includes(clone_root, target, max_bytes)
    prompt_source = strip_passthrough(full_text)
    encoded = prompt_source.encode("utf-8")

    if len(encoded) > max_bytes:
        return AdocRead(full_text, encoded[:max_bytes].decode("utf-8", errors="ignore"), True)
    return AdocRead(full_text, prompt_source, False)


# Ordered on purpose — the hash must be stable across runs.
_HASH_FIELDS = ("summary", "products", "solutions", "verticals", "meta_keyword")


def compute_content_hash(full_text: str, payload: dict[str, Any]) -> str:
    """SHA-256 of the FULL adoc body plus the CSV fields that feed the prompt."""
    digest = hashlib.sha256()
    digest.update(full_text.encode("utf-8", errors="replace"))
    for field in _HASH_FIELDS:
        value = payload.get(field)
        if isinstance(value, (list, tuple)):
            value = "|".join(str(v) for v in value)
        digest.update(b"\x00")
        digest.update(str(value or "").encode("utf-8", errors="replace"))
    return digest.hexdigest()


# ── Analysis ──

from rcars.config import call_llm
from rcars.services.analyzer import generate_embedding, parse_analysis_response

ARCHITECTURE_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "architecture_analyze.txt"

EMBEDDING_PREFIX = "Portfolio architecture: "


def build_architecture_prompt(payload: dict[str, Any], adoc_text: str) -> tuple[str, str]:
    """Split the template into (system_prompt, user_message)."""
    from rcars.services.vocabulary import (
        VOCABULARY_SENTINEL,
        load_vocabulary,
        render_vocabulary_block,
    )

    template = ARCHITECTURE_PROMPT_PATH.read_text()
    template = template.replace(
        VOCABULARY_SENTINEL, render_vocabulary_block(load_vocabulary(), "architecture"))

    item_info_start = template.index("\n## Item Information\n")
    instructions_start = template.index("\n## Instructions\n")
    content_start = template.index("\n## Architecture Content\n")

    system_prompt = (
        template[:item_info_start].strip() + "\n\n" +
        template[instructions_start:content_start].strip()
    )

    user_message = (
        "## Item Information\n"
        f"- Name: {payload.get('display_name') or ''}\n"
        f"- Asset type: {payload.get('asset_type') or 'PA'}\n"
        f"- Summary (from the Architecture Center inventory): {payload.get('summary') or 'None'}\n"
        f"- Products listed in the inventory: {', '.join(payload.get('products') or []) or 'None'}\n"
        f"- Solution areas listed in the inventory: {', '.join(payload.get('solutions') or []) or 'None'}\n"
        f"- Industry verticals listed in the inventory: {', '.join(payload.get('verticals') or []) or 'None'}\n"
        f"- Inventory keywords: {payload.get('meta_keyword') or 'None'}\n\n"
        f"## Architecture Content\n\n{adoc_text}"
    )
    return system_prompt, user_message


def build_architecture_embedding_text(analysis: dict[str, Any]) -> str:
    """One embedding per item — summary plus all extracted signal fields."""
    parts = [EMBEDDING_PREFIX + (analysis.get("summary") or "").strip()]

    def _join(key: str, label: str) -> None:
        vals = analysis.get(key) or []
        if vals:
            parts.append(f"{label}: {', '.join(str(v) for v in vals if v)}")

    _join("products", "Products")
    _join("detailed_topics", "Topics")
    _join("solution_areas", "Solution areas")
    _join("use_cases", "Use cases")
    _join("key_components", "Key components")
    _join("audience", "Audience")
    return "\n".join(parts)


def analyze_architecture_item(
    db,
    content_id: str,
    payload: dict[str, Any],
    adoc_text: str,
    content_hash: str,
    settings,
    stale_commit: str | None = None,
    truncated: bool = False,
) -> dict[str, Any]:
    """LLM analysis → vocabulary normalization → analysis row → card → embedding."""
    from rcars.services.vocabulary import normalize_analysis

    log = logger.bind(content_id=content_id)
    db.mark_architecture_stale(content_id, stale_commit)

    system_prompt, user_message = build_architecture_prompt(payload, adoc_text)
    model = settings.osspa_analysis_model
    log.info("osspa_analysis_started", action="analyze",
             display_name=payload.get("display_name"), asset_type=payload.get("asset_type"),
             model=model, prompt_chars=len(system_prompt) + len(user_message))

    result = call_llm(
        settings, model=model,
        messages=[{"role": "user", "content": user_message}],
        max_tokens=8192, system=system_prompt,
    )
    db.log_token_usage(
        operation="osspa_scan", model=model,
        input_tokens=result.input_tokens, output_tokens=result.output_tokens,
        ci_name=content_id, provider=result.provider,
    )

    analysis = parse_analysis_response(result.text)
    if not isinstance(analysis, dict):
        raise OsspaSyncError(f"Could not parse architecture analysis for {content_id}")

    analysis = normalize_analysis(analysis, "architecture", db=db, content_id=content_id)

    review_reasons = ["adoc_truncated"] if truncated else []
    db.upsert_architecture_analysis({
        "content_id": content_id,
        "summary": analysis.get("summary"),
        "products_json": analysis.get("products"),
        "topics_json": analysis.get("topics"),
        "audience_json": analysis.get("audience"),
        "recommender_audience_json": analysis.get("recommender_audience"),
        "difficulty": analysis.get("difficulty"),
        "content_hash": content_hash,
        "solution_areas_json": analysis.get("solution_areas"),
        "use_cases_json": analysis.get("use_cases"),
        "key_components_json": analysis.get("key_components"),
        "detailed_topics_json": analysis.get("detailed_topics"),
        "enrichment_review_needed": bool(review_reasons),
        "review_reasons": review_reasons,
    })

    db.update_content_entity_card(
        content_id,
        summary=analysis.get("summary"),
        products_json=analysis.get("products"),
        topics_json=analysis.get("topics"),
        audience_json=analysis.get("audience"),
        difficulty=analysis.get("difficulty"),
    )

    embedding_text = build_architecture_embedding_text(analysis)
    embedding = generate_embedding(embedding_text)
    db.replace_embeddings(content_id, [{
        "content_id": content_id,
        "content_type": "architecture",
        "source": "portfolio_arch",
        "embed_type": "summary",
        "content_text": embedding_text,
        "embedding": embedding,
    }])

    db.clear_architecture_stale(content_id)

    log.info("osspa_analysis_complete", action="analyze",
             display_name=payload.get("display_name"), asset_type=payload.get("asset_type"),
             input_tokens=result.input_tokens, output_tokens=result.output_tokens,
             truncated=truncated)
    return {
        "status": "analyzed",
        "content_id": content_id,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }


# ── Orchestrator ──

def _noop_progress(phase: str, message: str) -> None:
    return None


def run_osspa_sync(
    db,
    settings,
    *,
    force: bool = False,
    confirm_empty_inventory: bool = False,
    on_progress: Callable[[str, str], None] | None = None,
) -> dict[str, Any]:
    """Full OSSPA sync. Synchronous by design — the worker wraps it in one
    asyncio.to_thread() call so nothing blocks the shared scan worker loop.
    """
    progress = on_progress or _noop_progress
    stats: dict[str, Any] = {
        "status": "complete", "scoped_rows": 0, "upserted": 0, "retired": 0,
        "analyzed": 0, "skipped": 0, "failed": 0,
        "head_sha": None, "retire_skipped_reason": None,
    }

    with db.advisory_lock(settings.osspa_advisory_lock_id) as acquired:
        if not acquired:
            logger.info("osspa_sync_already_running", action="run_osspa_sync")
            stats["status"] = "locked"
            return stats

        # 1. Inventory
        progress("pipeline:osspa:csv_fetch", "Fetching the Architecture Center inventory...")
        rows = fetch_palist_csv(settings)
        active_rows = [normalize_row(r) for r in scope_rows(rows)]
        stats["scoped_rows"] = len(active_rows)

        # 2. Empty-inventory guard
        if not active_rows and not confirm_empty_inventory:
            logger.warning("osspa_sync_aborted_empty_inventory", action="run_osspa_sync",
                           csv_rows=len(rows))
            progress("pipeline:osspa:csv_fetch",
                     "No in-scope rows in PAList.csv — aborting without retiring anything")
            stats["status"] = "aborted_empty_inventory"
            return stats

        # 3. Clone BEFORE any DB write
        progress("pipeline:osspa:clone", "Cloning the portfolio architecture examples repo...")
        clone_path = clone_examples_repo(settings)
        stats["head_sha"] = get_head_sha(clone_path)

        # 4. Upsert
        progress("pipeline:osspa:upsert", f"Upserting {len(active_rows)} architecture items...")
        active_ids: set[str] = set()
        for payload in active_rows:
            db.upsert_osspa_item(payload)
            active_ids.add(payload["content_id"])
            stats["upserted"] += 1

        # 5. Retire, behind the shrink guard
        current_active = db.count_active_osspa()
        floor = current_active * settings.osspa_retire_shrink_guard_pct
        if not active_rows and confirm_empty_inventory:
            allowed, reason = True, None
        elif current_active and len(active_rows) < floor:
            allowed, reason = False, "shrink_guard"
        else:
            allowed, reason = True, None

        if allowed:
            progress("pipeline:osspa:retire", "Retiring items no longer in the inventory...")
            stats["retired"] = len(db.retire_missing_osspa(active_ids))
        else:
            stats["retire_skipped_reason"] = reason
            logger.warning("osspa_retire_skipped", action="run_osspa_sync", reason=reason,
                           active_rows=len(active_rows), db_active=current_active)
            progress("pipeline:osspa:retire",
                     f"Retirement skipped ({reason}): {len(active_rows)} in-scope rows vs "
                     f"{current_active} active in the database — possible truncated CSV")

        # 6. Analyze what actually changed
        progress("pipeline:osspa:analyze", f"Checking {len(active_rows)} items for content changes...")
        for payload in active_rows:
            content_id = payload["content_id"]
            try:
                adoc = read_detail_adoc(clone_path, payload["detail_page"], settings.osspa_max_adoc_bytes)
                if adoc is None:
                    db.ensure_architecture_analysis_row(content_id, payload.get("asset_type"))
                    logger.error("osspa_detail_page_unavailable", action="run_osspa_sync",
                                 content_id=content_id, detail_page=payload["detail_page"])
                    stats["failed"] += 1
                    db.set_scan_status(content_id, "failed", error_class="adoc_unavailable",
                                       error_message=f"detail page not found: {payload['detail_page']}")
                    continue

                content_hash = compute_content_hash(adoc.full_text, payload)
                existing = db.get_architecture_analysis(content_id) or {}
                has_embedding = bool(db.get_embeddings_for_content(content_id))
                unchanged = (
                    not force
                    and not existing.get("is_stale")
                    and existing.get("content_hash") == content_hash
                    and has_embedding
                )
                if unchanged:
                    stats["skipped"] += 1
                    continue

                stale_commit = file_commit_sha(clone_path, payload["detail_page"])
                analyze_architecture_item(
                    db, content_id, payload, adoc.prompt_text, content_hash, settings,
                    stale_commit=stale_commit, truncated=adoc.truncated,
                )
                stats["analyzed"] += 1
                db.set_scan_status(content_id, "success")
            except Exception as exc:      # one bad item must not abort the sync
                stats["failed"] += 1
                logger.error("osspa_item_failed", action="run_osspa_sync",
                             content_id=content_id, error=str(exc), exc_info=True)
                db.set_scan_status(content_id, "failed", error_class="sync_error",
                                   error_message=str(exc))

    logger.info("osspa_sync_complete", action="run_osspa_sync", **stats)
    progress("pipeline:osspa:complete",
             f"OSSPA sync complete: {stats['upserted']} upserted, {stats['analyzed']} analyzed, "
             f"{stats['skipped']} unchanged, {stats['retired']} retired, {stats['failed']} failed")
    return stats
