"""Showroom content analyzer.

Clones Showroom repos, reads AsciiDoc content, sends to Sonnet for
structured analysis, generates embeddings, and stores results.
"""

import hashlib
import json
import re
import shutil
import subprocess
import threading
import uuid
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rcars.services.showroom_source import (
    AnalysisSignature, ResolvedShowroom, SHOWROOM_ANALYSIS_POLICY_VERSION,
    effective_showroom_source, signature_matches_source,
)

import structlog

log = structlog.get_logger()

# Content signals that indicate boilerplate (case-insensitive)
BOILERPLATE_SIGNALS = [
    "your username is",
    "your password is",
    "connect to bastion",
    "ssh to your",
    "your lab environment has been provisioned",
    "your environment is now available",
    "access your environment",
    "credentials for your",
    "your credentials are",
    "login information",
    "log into your",
]

BOILERPLATE_FILENAMES = [
    "_nav.adoc",
    "nav.adoc",
    "_attributes.adoc",
]

PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent / "prompts" / "analyze_showroom.txt"


def parse_analysis_response(response_text: str) -> dict[str, Any] | list | None:
    """Parse Sonnet's JSON response, handling markdown fences."""
    if not response_text or not response_text.strip():
        return None

    text = response_text.strip()

    # Strip markdown code fences if present
    fence_pattern = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", re.DOTALL)
    match = fence_pattern.match(text)
    if match:
        text = match.group(1).strip()

    try:
        parsed = json.loads(text)
        if not isinstance(parsed, (dict, list)):
            log.warning("parse_unexpected_json_type", json_type=type(parsed).__name__)
            return None
        return parsed
    except json.JSONDecodeError:
        # Try to find JSON array in the response
        bracket_start = text.find("[")
        bracket_end = text.rfind("]")
        if bracket_start >= 0 and bracket_end > bracket_start:
            try:
                return json.loads(text[bracket_start : bracket_end + 1])
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in the response
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start : brace_end + 1])
            except json.JSONDecodeError:
                pass

        # Truncated JSON array recovery — extract complete objects from
        # a response that was cut off by max_tokens before the array closed
        if bracket_start >= 0:
            array_text = text[bracket_start:]
            recovered = []
            for obj_match in re.finditer(r'\{[^{}]*\}', array_text):
                try:
                    recovered.append(json.loads(obj_match.group()))
                except json.JSONDecodeError:
                    continue
            if recovered:
                log.warning("parse_truncated_recovery", entries=len(recovered))
                return recovered

        log.warning("parse_analysis_failed", text_preview=text[:200])
        return None


def filter_boilerplate_files(files: dict[str, str]) -> dict[str, str]:
    """Filter out boilerplate Showroom pages.

    Removes login/credentials pages, environment setup pages,
    index/navigation pages, and other non-content pages.
    """
    filtered = {}
    for filename, content in files.items():
        # Skip known boilerplate filenames
        if filename.lower() in BOILERPLATE_FILENAMES:
            continue

        # Check content for boilerplate signals
        content_lower = content.lower()[:500]  # Check first 500 chars
        is_boilerplate = any(signal in content_lower for signal in BOILERPLATE_SIGNALS)

        # Publishing House starter pages and pure navigation have no lab evidence.
        if "publishing house" in content_lower and any(
            marker in content_lower for marker in ("placeholder", "welcome", "template", "your content")
        ):
            is_boilerplate = True
        substantive = [line for line in content.splitlines() if line.strip() and not re.match(
            r"^\s*(?:=+\s|//|:[\w-]+:|\*?\s*xref:|include::|ifdef::|endif::)", line)]
        if not substantive:
            is_boilerplate = True

        if not is_boilerplate:
            filtered[filename] = content

    return filtered


def hash_showroom_content(files: dict[str, str]) -> str:
    """Produce a deterministic SHA-256 hash of showroom content files.

    Normalizes whitespace so that trailing spaces, blank line differences,
    and line ending changes don't produce a different hash. Files are
    sorted by name for stable ordering.
    """
    h = hashlib.sha256()
    for filename in sorted(files.keys()):
        normalized = _canonical_content(files[filename])
        h.update(filename.encode())
        h.update(b"\x00")
        h.update(normalized.encode())
        h.update(b"\x00")
    return h.hexdigest()


def _canonical_content(content: str) -> str:
    """The exact text hashed is also the text sent to the analysis model."""
    text = "\n".join(line.rstrip() for line in content.splitlines())
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def check_showroom_stale(
    clone_path: Path,
    old_content_hash: str | None,
    content_path: str | None = None,
) -> dict[str, Any]:
    """Check if a cloned showroom has materially changed since last analysis.

    Returns dict with:
        is_stale: bool — True if content hash differs from old_content_hash
        content_hash: str — current content hash
        head_sha: str | None — current HEAD commit
        content_chars: int — total characters in filtered content
    """
    head_sha, _ = get_repo_head(clone_path)

    raw_files = read_showroom_content(clone_path, content_path=content_path)
    if not raw_files:
        return {"is_stale": True, "content_hash": None, "head_sha": head_sha, "content_chars": 0}

    content_files = filter_boilerplate_files(raw_files)
    if not content_files:
        return {"is_stale": True, "content_hash": None, "head_sha": head_sha, "content_chars": 0}

    content_hash = hash_showroom_content(content_files)
    content_chars = sum(len(v) for v in content_files.values())

    is_stale = old_content_hash is None or content_hash != old_content_hash

    return {
        "is_stale": is_stale,
        "content_hash": content_hash,
        "head_sha": head_sha,
        "content_chars": content_chars,
    }


def truncate_content(content: str, max_chars: int = 150000) -> str:
    """Truncate content to max characters."""
    if len(content) <= max_chars:
        return content
    return content[:max_chars]


def classify_scan_error(
    exc: Exception, url: str | None = None, ref: str | None = None,
    content_path: str | None = None,
) -> tuple[str, str]:
    """Classify a scan error and return (error_class, human_message)."""
    msg = str(exc)
    if isinstance(exc, InvalidShowroomRef):
        return "invalid_ref", msg
    stderr = getattr(exc, "stderr", "") or ""
    suffix = ""
    if ref:
        suffix += f" (ref={ref})"
    if content_path:
        suffix += f", content_path={content_path}" if suffix else f" (content_path={content_path})"

    if url and ("{{" in url or "{%" in url):
        return "jinja_url", f"Showroom URL contains unresolved template variables: {url}{suffix}"

    if isinstance(exc, subprocess.TimeoutExpired):
        return "timeout", f"Clone timed out after {exc.timeout}s for {url}{suffix}"

    if isinstance(exc, subprocess.CalledProcessError):
        stderr_lower = stderr.lower()
        if "permission denied" in stderr_lower or "403" in stderr_lower:
            return "private_repo", f"Permission denied cloning {url}{suffix}: {stderr.strip()}"
        if "not found" in stderr_lower or "404" in stderr_lower:
            return "http_404", f"Repository not found: {url}{suffix}: {stderr.strip()}"
        return "clone_failed", f"Git clone failed for {url}{suffix}: {stderr.strip()}"

    msg_lower = msg.lower()
    if "no .adoc" in msg_lower or isinstance(exc, FileNotFoundError):
        return "missing_antora", f"No .adoc files found in Showroom layout for {url}{suffix}"
    if "boilerplate" in msg_lower:
        return "no_content", f"All content filtered as boilerplate for {url}{suffix}"
    if "parse" in msg_lower or "json" in msg_lower:
        return "parse_error", f"Failed to parse analysis response for {url}: {msg}"

    return "unknown", f"Unexpected error scanning {url}: {msg}"


def _is_github_throttle(stderr: str) -> bool:
    indicators = ["rate limit", "too many requests", "403", "secondary rate"]
    return any(ind in stderr.lower() for ind in indicators)


def _run_git_with_retry(cmd: list[str], timeout: int = 120, max_retries: int = 3) -> subprocess.CompletedProcess:
    """Run a git command with retry and exponential backoff for GitHub throttling."""
    import time
    for attempt in range(max_retries):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=timeout)
        except subprocess.CalledProcessError as e:
            if _is_github_throttle(e.stderr) and attempt < max_retries - 1:
                wait = 10 * (2 ** attempt)
                log.warning("github_throttle_retry", attempt=attempt + 1,
                            max_retries=max_retries, wait_seconds=wait)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("unreachable")


class InvalidShowroomRef(ValueError):
    """Requested source cannot be resolved to exactly one commit."""


def ls_remote_sha(url: str, ref: str | None) -> str:
    """Resolve exact heads/tags (peeling annotated tags), not Git glob matches."""
    result = _run_git_with_retry(["git", "ls-remote", "--", url], timeout=30)
    lookup = dict(line.split()[::-1] for line in result.stdout.splitlines() if len(line.split()) == 2)
    head = lookup.get("HEAD")
    for name, commit in list(lookup.items()):
        if name.endswith("^{}"):
            lookup[name[:-3]] = commit
    if ref and re.fullmatch(r"[0-9a-fA-F]{40}", ref):
        return ref.lower()  # reachability/type verified by detached fetch before use
    commit = _resolve_ref_from_lookup(ref, lookup, head)
    if not commit:
        raise InvalidShowroomRef(f"Missing or ambiguous Showroom ref: {ref or 'HEAD'}")
    return commit


def _resolve_ref_from_lookup(
    ref: str | None,
    ref_lookup: dict[str, str],
    head_sha: str | None,
) -> str | None:
    """Resolve a single ref against the parsed ls-remote output."""
    if ref is None or ref == "HEAD":
        return head_sha

    if ref.startswith("refs/"):
        return ref_lookup.get(ref)
    candidates = [name for name in (f"refs/heads/{ref}", f"refs/tags/{ref}") if name in ref_lookup]
    return ref_lookup[candidates[0]] if len(candidates) == 1 else None


def clone_showroom(
    url: str, ref: str | None, clone_dir: str = "/tmp", *, expected_commit: str | None = None,
) -> Path | None:
    """Fetch and verify an exact detached commit. Never fall back to default HEAD."""
    repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
    suffix = uuid.uuid4().hex[:8]
    clone_path = Path(clone_dir) / f"rcars-showroom-{repo_name}-{suffix}"

    commit = expected_commit or ls_remote_sha(url, ref)
    try:
        _run_git_with_retry(["git", "init", str(clone_path)])
        _run_git_with_retry(["git", "-C", str(clone_path), "remote", "add", "origin", url])
        _run_git_with_retry(["git", "-C", str(clone_path), "fetch", "--depth", "1", "origin", commit])
        _run_git_with_retry(["git", "-C", str(clone_path), "checkout", "--detach", "FETCH_HEAD"])
        actual, _ = get_repo_head(clone_path)
        if actual != commit:
            raise InvalidShowroomRef("Fetched Showroom commit does not match resolved ref")
        return clone_path
    except Exception:
        shutil.rmtree(clone_path, ignore_errors=True)
        raise


def _parse_nav_includes(nav_text: str) -> set[str]:
    """Extract active page filenames from nav.adoc.

    Parses xref: references on uncommented lines. Returns a set of
    filenames (basename only, no subdirectories) that nav.adoc includes.
    """
    included = set()
    for line in nav_text.splitlines():
        stripped = line.lstrip(" *")
        if stripped.startswith("//"):
            continue
        match = re.search(r'xref:([^\[]+)', stripped)
        if match:
            ref_path = match.group(1).strip().split("#")[0]
            included.add(ref_path)
    return included


def read_showroom_content(clone_path: Path, content_path: str | None = None, ci_name: str | None = None) -> dict[str, str]:
    """Read .adoc files from a cloned Showroom repo.

    Uses nav.adoc as the source of truth for which pages to include.
    Only pages referenced in active (uncommented) nav entries are read.
    Falls back to reading all pages if nav.adoc doesn't exist or
    contains no xref entries.
    """
    label = ci_name or clone_path.name
    files = {}
    if content_path:
        if Path(content_path).is_absolute() or ".." in Path(content_path).parts:
            raise ValueError("content_path must remain inside the clone")
        pages_dir = clone_path / content_path
    else:
        pages_dir = clone_path / "content" / "modules" / "ROOT" / "pages"

    def contained(path):
        if not path.resolve().is_relative_to(clone_path.resolve()):
            raise ValueError("content_path symlink leaves the clone")
        return path

    contained(pages_dir)

    # Parse nav.adoc to determine which pages are active
    nav_file = contained(pages_dir.parent / "nav.adoc")
    nav_includes: set[str] | None = None
    if nav_file.exists():
        try:
            nav_text = nav_file.read_text(errors="replace")
            files["_nav.adoc"] = nav_text
            nav_includes = _parse_nav_includes(nav_text)
            if nav_includes:
                log.info("nav_active_pages", ci_name=label, count=len(nav_includes), pages=sorted(nav_includes))
            else:
                nav_includes = None
        except OSError:
            pass

    if pages_dir.exists():
        for adoc_file in sorted(pages_dir.glob("*.adoc")):
            contained(adoc_file)
            if nav_includes and adoc_file.name not in nav_includes:
                log.info("nav_skip_file", ci_name=label, file=adoc_file.name)
                continue
            try:
                files[adoc_file.name] = adoc_file.read_text(errors="replace")
            except OSError as e:
                log.warning("adoc_read_error", file=str(adoc_file), error=str(e))

    # For nav.adoc with subdirectory xrefs (e.g. 200-ops/lab_1.adoc),
    # also check those paths relative to ROOT/pages/
    if nav_includes:
        root_dir = pages_dir
        for inc in nav_includes:
            if "/" in inc:
                subpath = contained(root_dir / inc)
                if subpath.exists() and inc not in files:
                    try:
                        files[inc] = subpath.read_text(errors="replace")
                    except OSError:
                        pass

    return files


def get_repo_head(clone_path: Path) -> tuple[str | None, str | None]:
    """Get HEAD commit SHA and date from a cloned repo."""
    try:
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
            cwd=clone_path,
        )
        date_result = subprocess.run(
            ["git", "log", "-1", "--format=%aI"],
            capture_output=True, text=True, check=True,
            cwd=clone_path,
        )
        return sha_result.stdout.strip(), date_result.stdout.strip()
    except subprocess.CalledProcessError:
        return None, None


def build_analysis_prompt(
    ci_name: str,
    display_name: str,
    category: str,
    product: str,
    content_files: dict[str, str],
    entity_content_type: str = "lab",
) -> tuple[str, str]:
    """Build analysis prompt split into system instructions and user data.

    entity_content_type is content_entities.content_type — NOT the LLM's
    self-reported content_type, which does not exist yet at this point. It
    selects the action-verb hints in the injected vocabulary block.

    Returns (system_prompt, user_message) for system/user separation (M-1/M-4).
    """
    from rcars.services.vocabulary import (
        VOCABULARY_SENTINEL,
        load_vocabulary,
        render_vocabulary_block,
    )

    template = PROMPT_TEMPLATE_PATH.read_text()

    # The template contains literal { } from its JSON example, so str.format()
    # cannot be used — replace an explicit sentinel instead.
    vocabulary_block = render_vocabulary_block(load_vocabulary(), entity_content_type)
    template = template.replace(VOCABULARY_SENTINEL, vocabulary_block)

    # Concatenate file contents with headers
    content_parts = []
    for filename, content in sorted(content_files.items()):
        content_parts.append(f"=== File: {filename} ===\n{_canonical_content(content)}")
    all_content = "\n\n".join(content_parts)
    all_content = truncate_content(all_content)

    # Split template: system gets role + instructions, user gets item info + content
    item_info_start = template.index("\n## Item Information\n")
    instructions_start = template.index("\n## Instructions\n")
    content_start = template.index("\n## Showroom Content\n")

    system_prompt = template[:item_info_start].strip() + "\n\n" + template[instructions_start:content_start].strip()

    user_message = (
        f"## Item Information\n"
        f"- CI Name: {ci_name}\n"
        f"- Display Name: {display_name or ci_name}\n"
        f"- Category: {category or 'Unknown'}\n"
        f"- Product: {product or 'Unknown'}\n\n"
        f"## Showroom Content\n\n{all_content}"
    )

    return system_prompt, user_message


_embedding_client: Any = None
_embedding_lock = threading.Lock()


def _get_embedding_client():
    """Lazy-init a shared httpx client for the vLLM embedding server."""
    global _embedding_client
    if _embedding_client is None:
        with _embedding_lock:
            if _embedding_client is None:
                import httpx
                from rcars.config import Settings
                settings = Settings()
                if not settings.embedding_url:
                    raise RuntimeError(
                        "RCARS_EMBEDDING_URL is not set. "
                        "A vLLM embedding server is required — see deployment docs."
                    )
                headers = {}
                if settings.embedding_api_key:
                    headers["Authorization"] = f"Bearer {settings.embedding_api_key}"
                _embedding_client = httpx.Client(
                    base_url=settings.embedding_url,
                    headers=headers,
                    timeout=30.0,
                )
    return _embedding_client


EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"
EMBEDDING_DIM = 768


def generate_embedding(text: str, prefix: str = "search_document", *, model: str | None = None) -> list[float]:
    """Generate a 768-dim embedding via the vLLM embedding server.

    Nomic requires task prefixes: 'search_query' for advisor queries,
    'search_document' for content being indexed. The prefix is prepended
    client-side before sending to the vLLM /v1/embeddings API.
    """
    from rcars.config import Settings
    client = _get_embedding_client()
    prefixed_text = f"{prefix}: {text}" if prefix else text

    resp = client.post("/embeddings", json={
        "model": model or Settings().embedding_model,
        "input": prefixed_text,
    })
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def build_embedding_text(analysis: dict[str, Any], keywords: list[str] | None = None, display_name: str | None = None) -> str:
    """Build text for CI-level embedding from analysis results."""
    parts = [
        analysis.get("summary", ""),
    ]

    # Learning objectives
    objectives = analysis.get("learning_objectives", {})
    if isinstance(objectives, dict):
        parts.extend(objectives.get("stated", []))
        parts.extend(objectives.get("inferred", []))

    for field in ("topics", "products", "audience", "use_cases"):
        val = analysis.get(field, [])
        if isinstance(val, list):
            parts.extend(val)

    if display_name:
        parts.append(display_name)

    if keywords:
        parts.extend(keywords)

    return " ".join(str(p) for p in parts if p)


def build_module_embedding_text(module: dict[str, Any]) -> str:
    """Build text for module-level embedding."""
    parts = [
        module.get("title", ""),
    ]
    for field in ("topics", "learning_objectives"):
        val = module.get(field, [])
        if isinstance(val, list):
            parts.extend(val)
    return " ".join(str(p) for p in parts if p)


def _fingerprint(*values) -> str:
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def compute_analysis_input_hash(system_prompt: str, user_message: str, model: str) -> str:
    return _fingerprint(system_prompt, user_message, model, SHOWROOM_ANALYSIS_POLICY_VERSION)


def compute_analysis_context_hash(system_prompt: str, canonical_item_info: str, model: str) -> str:
    return _fingerprint(system_prompt, canonical_item_info, model, SHOWROOM_ANALYSIS_POLICY_VERSION)


def compute_embedding_fingerprint(text: str, model: str, configuration: dict) -> str:
    return _fingerprint(text, model, configuration)


def analysis_from_row(row: dict) -> dict:
    result = {key: row.get(key) for key in ("summary", "content_type", "difficulty", "estimated_duration_min")}
    for key in ("products", "topics", "audience", "modules", "learning_objectives", "format_suitability", "use_cases", "recommender_audience"):
        result[key] = row.get(key + "_json")
    return result


def _embedding_specs(analysis, keywords, display_name, settings):
    configuration = {"prefix": "search_document", "dimensions": settings.embedding_dim}
    specs = [("summary", None, build_embedding_text(analysis, keywords=keywords, display_name=display_name))]
    for index, module in enumerate(analysis.get("modules") or []):
        text = build_module_embedding_text(module)
        if text.strip():
            specs.append((f"{index}:{module.get('title', '')}", module.get("title", ""), text))
    return [(key, title, text, compute_embedding_fingerprint(text, settings.embedding_model, configuration))
            for key, title, text in specs]


def _valid_embedding(spec, embeddings, fingerprints):
    key, title, text, fingerprint = spec
    prior = fingerprints.get("summary") if key == "summary" else (fingerprints.get("modules") or {}).get(key)
    if prior != fingerprint:
        return None
    for row in embeddings:
        if (row["embed_type"] == ("summary" if key == "summary" else "module")
                and row.get("module_title") == title and row.get("content_text") == text
                and row.get("embedding_text")):
            return row
    return None


def _own_analysis_current(row, source, context_hash, *, allow_stale=False):
    provenance = (row or {}).get("analysis_provenance_json") or {}
    signature = provenance.get("signature") or {}
    return bool(row and row.get("summary") and isinstance(row.get("modules_json"), list)
                and (allow_stale or not row.get("is_stale"))
                and signature_matches_source(signature, source)
                and row.get("content_hash") == signature.get("content_hash")
                and signature.get("context_hash") == context_hash
                and provenance.get("source") == source.to_dict())


def analysis_context_hash(scope_key: str, display_name: str, category: str, product: str,
                          entity_content_type: str, model: str) -> str:
    system, info = build_analysis_prompt(scope_key, display_name, category, product, {},
                                         entity_content_type=entity_content_type)
    return compute_analysis_context_hash(system, info, model)


def _item_context_hash(item: dict, scope_key: str, model: str) -> str:
    return analysis_context_hash(scope_key, item.get("display_name", ""), item.get("category", ""),
                                 item.get("product", ""), item.get("content_type") or "lab", model)


def reuse_key_from_signature(signature: dict) -> str:
    return _fingerprint(*(signature.get(key) for key in ("scope_key", "repo", "ref", "content_path", "context_hash")))


def showroom_reuse_key(item: dict, settings) -> str | None:
    """Pre-clone part of the AnalysisSignature. Stages sharing it share one generation
    unless the commit or selected content differs; None when no source resolves."""
    source = effective_showroom_source(item)
    if source.status != "resolved" or not source.repo or not source.scope_key:
        return None
    return reuse_key_from_signature({"scope_key": source.scope_key, "repo": source.repo, "ref": source.ref,
        "content_path": source.content_path, "context_hash": _item_context_hash(item, source.scope_key, settings.model)})


def order_for_reuse(items: list[dict], settings) -> list[dict]:
    """Queue one donor candidate per reuse key first (prod preferred, matching donor
    lookup), then its siblings, so siblings find a finished donor instead of racing it."""
    rank = {"prod": 0, "event": 1}
    leaders, followers, seen = [], [], set()
    for item in sorted(items, key=lambda i: (rank.get(i.get("stage"), 2), i["ci_name"])):
        key = showroom_reuse_key(item, settings)
        if key is not None and key in seen:
            followers.append(item)
        else:
            seen.add(key)
            leaders.append(item)
    return leaders + followers


def showroom_analysis_current(item: dict, row: dict, settings) -> bool:
    """Current source AND actual non-content prompt inputs, not just Git SHA."""
    source = effective_showroom_source(item)
    context = _item_context_hash(item, source.scope_key or item["ci_name"], settings.model)
    return item.get("scan_status") == "success" and _own_analysis_current(row, source, context)


def showroom_work_needed(item: dict, row: dict, embeddings: list[dict], settings) -> bool:
    """Read-only selection predicate: no Git, LLM, or embedding requests."""
    if not showroom_analysis_current(item, row, settings):
        return True
    fingerprints = (row.get("analysis_provenance_json") or {}).get("embedding_fingerprints") or {}
    return any(not _valid_embedding(spec, embeddings, fingerprints) for spec in _embedding_specs(
        analysis_from_row(row), item.get("keywords"), item.get("display_name"), settings))


def _finish_showroom_result(ci_name, display_name, keywords, settings, analysis, signature,
                            source, *, origin=None, prior_embeddings=(), force=False,
                            outcome="analyzed", head_date=None, input_tokens=0, output_tokens=0,
                            content_file_count=0, reused_from=None, fresh_generation=False):
    provenance = deepcopy((origin or {}).get("analysis_provenance_json") or {})
    prior_fingerprints = provenance.get("embedding_fingerprints") or {}
    fingerprints = {"modules": {}}
    summary = None
    modules = []
    changed = []
    for spec in _embedding_specs(analysis, keywords, display_name, settings):
        key, title, text, fingerprint = spec
        existing = None if force else _valid_embedding(spec, prior_embeddings, prior_fingerprints)
        vector = json.loads(existing["embedding_text"]) if existing else generate_embedding(text, model=settings.embedding_model)
        if existing is None:
            changed.append(key)
        if key == "summary":
            fingerprints["summary"] = fingerprint
            summary = (text, vector)
        else:
            fingerprints["modules"][key] = fingerprint
            modules.append({"module_title": title, "content_text": text, "embedding": vector})
    if outcome == "unchanged" and changed:
        outcome = "embeddings_repaired"
    if fresh_generation:
        provenance = {}
    provenance.update(signature=signature.to_dict(), source=source.to_dict(),
        generated_for=provenance.get("generated_for") or f"babylon:{ci_name}",
        generated_commit=provenance.get("generated_commit") or signature.commit,
        reused_from=reused_from if reused_from is not None else provenance.get("reused_from"),
        embedding_fingerprints=fingerprints)
    return {"ci_name": ci_name, "analysis": analysis, "analysis_provenance": provenance,
        "outcome": outcome, "reused_from": provenance["reused_from"],
        "ci_embedding_text": summary[0], "ci_embedding": summary[1], "module_embeddings": modules,
        "embedding_changes": changed, "last_repo_commit": signature.commit,
        "last_repo_updated": head_date or (origin or {}).get("last_repo_updated"),
        "last_analyzed": (origin or {}).get("last_analyzed") if origin and not fresh_generation else datetime.now(timezone.utc),
        "content_hash": signature.content_hash, "input_tokens": input_tokens, "output_tokens": output_tokens,
        "content_file_count": content_file_count}


def regenerate_embeddings(
    db,
    content_id: str,
    content_type: str,
    source: str,
    summary_text: str,
    summary_embedding: list[float],
    module_embeddings: list[dict] | None = None,
    conn=None,
) -> int:
    """Clear old embeddings and store fresh ones for a content_id atomically.

    Returns the number of embeddings stored.
    """
    rows = [{"content_id": content_id, "content_type": content_type, "source": source,
             "embed_type": "summary", "content_text": summary_text, "embedding": summary_embedding}]
    for mod in module_embeddings or []:
        rows.append({"content_id": content_id, "content_type": content_type, "source": source,
                     "embed_type": "module", "module_title": mod["module_title"],
                     "content_text": mod["content_text"], "embedding": mod["embedding"]})
    db.replace_embeddings(content_id, rows, conn=conn)
    return len(rows)


def build_infrastructure_embedding_text(row: dict[str, Any]) -> str:
    """Build text for infrastructure embedding from an infrastructure table row."""
    parts = []
    if row.get("description"):
        parts.append(row["description"])
    for field in ("products", "capabilities"):
        val = row.get(field, [])
        if isinstance(val, list):
            parts.extend(val)
    if row.get("category"):
        parts.append(row["category"])
    parts.append(row["role_name"])
    return " ".join(str(p) for p in parts if p)


def analyze_showroom(
    ci_name: str,
    display_name: str,
    category: str,
    product: str,
    showroom_url: str,
    showroom_ref: str | None,
    settings,
    model: str = "claude-sonnet-4-6",
    clone_dir: str = "/tmp",
    db=None,
    content_path: str | None = None,
    keywords: list[str] | None = None,
    entity_content_type: str = "lab",
    *,
    source: ResolvedShowroom,
    force: bool = False,
) -> dict[str, Any] | None:
    """Full analysis pipeline for a single Showroom.

    1. Clone repo
    2. Read .adoc files
    3. Filter boilerplate
    4. Send to Sonnet for analysis
    5. Generate embeddings
    6. Clean up clone
    7. Return results dict

    Returns None on failure.
    """
    import time
    t0 = time.monotonic()
    clone_path = None
    try:
        content_id = f"babylon:{ci_name}"
        item = db.get_babylon_item(content_id) if db is not None else None
        if item:
            source = effective_showroom_source(item)
        if source.status != "resolved" or not source.repo or not source.scope_key:
            return {"error": f"{source.status}_source", "message": source.error or "No resolved Showroom source"}
        showroom_url, showroom_ref, content_path = source.repo, source.ref, source.content_path
        if any(value and ("{{" in value or "{%" in value) for value in (showroom_url, showroom_ref, content_path)):
            return {"error": "invalid_source", "message": "Unresolved Showroom variables"}
        context_hash = analysis_context_hash(source.scope_key, display_name, category, product,
                                             entity_content_type, model)
        revision = ls_remote_sha(showroom_url, showroom_ref)
        own = db.get_showroom_analysis(content_id) if db is not None else None
        own_embeddings = db.get_embeddings_for_content(content_id) if own and db is not None else []
        own_current = not force and _own_analysis_current(own, source, context_hash, allow_stale=True)
        if item and item.get("scan_status") not in (None, "success"):
            own_current = False
        if own_current:
            own_signature = AnalysisSignature(**own["analysis_provenance_json"]["signature"])
            if own_signature.commit == revision and not own.get("is_stale"):
                return _finish_showroom_result(ci_name, display_name, keywords, settings, analysis_from_row(own),
                    own_signature, source, origin=own, prior_embeddings=own_embeddings, outcome="unchanged")

        # Clone
        log.info("analyze_cloning", ci_name=ci_name, url=showroom_url, ref=showroom_ref or "HEAD")
        Path(clone_dir).mkdir(parents=True, exist_ok=True)
        clone_path = clone_showroom(showroom_url, showroom_ref, clone_dir, expected_commit=revision)
        if not clone_path:
            log.error("analyze_clone_failed", ci_name=ci_name)
            return {"error": "clone_failed", "message": f"Failed to clone {showroom_url}"}

        # Get repo HEAD info
        head_sha, head_date = get_repo_head(clone_path)
        if head_sha != revision:
            raise InvalidShowroomRef("Checkout differs from the verified Showroom revision")
        log.info("analyze_cloned", ci_name=ci_name, head_sha=head_sha[:8] if head_sha else "?")

        # Read content
        raw_files = read_showroom_content(clone_path, content_path=content_path, ci_name=ci_name)
        if not raw_files:
            ref_info = f" (ref={showroom_ref})" if showroom_ref else " (ref=HEAD)"
            path_info = f", content_path={content_path}" if content_path else ""
            log.warning("analyze_no_adoc", ci_name=ci_name, url=showroom_url, ref=showroom_ref, content_path=content_path)
            return {"error": "no_content", "message": f"No .adoc files found in {showroom_url}{ref_info}{path_info}"}

        # Filter boilerplate
        content_files = filter_boilerplate_files(raw_files)
        if not content_files:
            log.warning("analyze_all_boilerplate", ci_name=ci_name)
            return {"error": "no_content", "message": "Only navigation or template content found"}

        total_chars = sum(len(v) for v in content_files.values())
        log.info("analyze_content", ci_name=ci_name, files=len(content_files),
                 chars=total_chars, boilerplate=len(raw_files) - len(content_files))

        content_hash = hash_showroom_content(content_files)
        system_prompt, user_message = build_analysis_prompt(
            source.scope_key, display_name, category, product, content_files,
            entity_content_type=entity_content_type,
        )
        signature = AnalysisSignature(source.scope_key, source.repo, source.ref, source.content_path,
            head_sha, content_hash, context_hash, compute_analysis_input_hash(system_prompt, user_message, model),
            SHOWROOM_ANALYSIS_POLICY_VERSION)
        if own_current and own_signature.content_hash == content_hash and own_signature.input_hash == signature.input_hash:
            return _finish_showroom_result(ci_name, display_name, keywords, settings, analysis_from_row(own),
                signature, source, origin=own, prior_embeddings=own_embeddings, outcome="revision_verified", head_date=head_date)

        # Only the full authorized signature may identify a donor, after validation.
        if db is not None and not force:
            donor = db.find_showroom_donor(signature, exclude_content_id=content_id)
            if donor:
                return _finish_showroom_result(ci_name, display_name, keywords, settings, analysis_from_row(donor),
                    signature, source, origin=donor, prior_embeddings=db.get_embeddings_for_content(donor["content_id"]),
                    outcome="reused", head_date=head_date, content_file_count=len(content_files), reused_from=donor["content_id"])

        # Build prompt and call Sonnet
        log.info("analyze_sending", ci_name=ci_name, model=model, prompt_chars=len(system_prompt) + len(user_message))

        from rcars.config import call_llm
        result = call_llm(settings, model=model, messages=[{"role": "user", "content": user_message}], max_tokens=8192, system=system_prompt)

        input_tokens = result.input_tokens
        output_tokens = result.output_tokens
        log.info("analyze_response", ci_name=ci_name, input_tokens=input_tokens,
                 output_tokens=output_tokens, provider=result.provider)

        if db is not None:
            db.log_token_usage(
                operation="scan",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                ci_name=ci_name,
                provider=result.provider,
            )

        response_text = result.text
        analysis = parse_analysis_response(response_text)
        if not isinstance(analysis, dict) or not analysis.get("summary"):
            log.error("analyze_parse_failed", ci_name=ci_name)
            return {"error": "parse_failed", "message": f"Failed to parse LLM response for {ci_name}"}

        # Normalize ONCE, here — never at the individual write sites.
        from rcars.services.vocabulary import normalize_analysis
        analysis = normalize_analysis(
            analysis, entity_content_type, db=db, content_id=f"babylon:{ci_name}"
        )

        analysis.setdefault("modules", [])
        result = _finish_showroom_result(ci_name, display_name, keywords, settings, analysis, signature, source,
            origin=own, prior_embeddings=own_embeddings, fresh_generation=True,
            force=force, head_date=head_date, input_tokens=input_tokens, output_tokens=output_tokens,
            content_file_count=len(content_files))
        result["elapsed_seconds"] = round(time.monotonic() - t0, 1)
        log.info("analyze_complete", ci_name=ci_name, outcome=result["outcome"], signature=signature.to_dict())
        return result

    except InvalidShowroomRef as exc:
        return {"error": "invalid_ref", "message": str(exc)}
    except Exception:
        elapsed = time.monotonic() - t0
        log.exception("analyze_failed", ci_name=ci_name, elapsed=round(elapsed, 1))
        raise

    finally:
        # Always clean up clone
        if clone_path and clone_path.exists():
            shutil.rmtree(clone_path, ignore_errors=True)
