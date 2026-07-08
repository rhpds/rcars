"""Showroom content analyzer.

Clones Showroom repos, reads AsciiDoc content, sends to Sonnet for
structured analysis, generates embeddings, and stores results.
"""

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import uuid
import warnings
from pathlib import Path
from typing import Any

# Silence HuggingFace/sentence-transformers noise before any library imports.
# These env vars are read at library import time — setting them here at module
# load ensures they're in place before sentence_transformers is imported lazily
# inside generate_embedding().
#
# TQDM_DISABLE=1            — suppresses the "Loading weights" progress bar
# TRANSFORMERS_VERBOSITY    — suppresses BertModel LOAD REPORT and similar
# HF_HUB_DISABLE_PROGRESS_BARS — suppresses HuggingFace download progress
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

log = logging.getLogger(__name__)

# Suppress low-level HTTP and HuggingFace loggers. Set at module load time
# so they take effect before any CLI basicConfig call cascades DEBUG to root.
for _noisy_logger in ("httpcore", "httpx", "huggingface_hub", "transformers", "urllib3"):
    logging.getLogger(_noisy_logger).setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

# Suppress the "unauthenticated HF Hub" UserWarning — goes through Python's
# warnings module, not logging, so setLevel alone doesn't catch it.
warnings.filterwarnings("ignore", message=".*unauthenticated.*")
warnings.filterwarnings("ignore", message=".*HF_TOKEN.*")

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
    "index.adoc",
    "index-no-nav.adoc",
    "_attributes.adoc",
]

PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent / "prompts" / "analyze_showroom.txt"


def parse_analysis_response(response_text: str) -> dict[str, Any] | None:
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
        return json.loads(text)
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
                log.warning("Recovered %d entries from truncated JSON array", len(recovered))
                return recovered

        log.warning("Failed to parse analysis response as JSON: %s", text[:200])
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
        content = files[filename]
        # Normalize: strip trailing whitespace per line, collapse blank lines
        lines = [line.rstrip() for line in content.splitlines()]
        normalized = "\n".join(line for line in lines if line or (lines and lines[-1]))
        normalized = re.sub(r'\n{3,}', '\n\n', normalized).strip()
        h.update(filename.encode())
        h.update(b"\x00")
        h.update(normalized.encode())
        h.update(b"\x00")
    return h.hexdigest()


def check_showroom_stale(
    clone_path: Path,
    old_content_hash: str | None,
) -> dict[str, Any]:
    """Check if a cloned showroom has materially changed since last analysis.

    Returns dict with:
        is_stale: bool — True if content hash differs from old_content_hash
        content_hash: str — current content hash
        head_sha: str | None — current HEAD commit
        content_chars: int — total characters in filtered content
    """
    head_sha, _ = get_repo_head(clone_path)

    raw_files = read_showroom_content(clone_path)
    if not raw_files:
        return {"is_stale": False, "content_hash": None, "head_sha": head_sha, "content_chars": 0}

    content_files = filter_boilerplate_files(raw_files)
    if not content_files:
        content_files = raw_files

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
                log.warning("GitHub throttle on attempt %d/%d, waiting %ds: %s",
                            attempt + 1, max_retries, wait, cmd[:3])
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("unreachable")


def ls_remote_sha(url: str, ref: str | None) -> str | None:
    """Get the current SHA for a ref without cloning. Returns None on failure."""
    cmd = ["git", "ls-remote", url]
    if ref:
        cmd.append(ref)
    else:
        cmd.append("HEAD")
    try:
        result = _run_git_with_retry(cmd, timeout=30)
        for line in result.stdout.strip().splitlines():
            sha = line.split()[0]
            return sha
        return None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        stderr = getattr(e, "stderr", "") or ""
        log.warning("ls-remote failed for %s (ref=%s): %s", url, ref, stderr.strip()[:200])
        return None


def resolve_refs_to_shas(
    url_ref_pairs: list[tuple[str, str | None]],
) -> dict[tuple[str, str | None], str | None]:
    """Batch-resolve git refs to commit SHAs via ls-remote.

    Groups pairs by URL so each unique URL needs only one ls-remote call.
    Falls back to individual ls_remote_sha() on failure.

    Returns {(url, ref): sha_or_none}.
    """
    import time

    by_url: dict[str, list[str | None]] = {}
    for url, ref in url_ref_pairs:
        by_url.setdefault(url, []).append(ref)

    result: dict[tuple[str, str | None], str | None] = {}
    t0 = time.monotonic()

    for url, refs in by_url.items():
        ref_lookup: dict[str, str] | None = None
        head_sha: str | None = None

        try:
            proc = _run_git_with_retry(["git", "ls-remote", url], timeout=30)
            ref_lookup = {}
            for line in proc.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) < 2:
                    continue
                sha, refname = parts[0], parts[1]
                if refname == "HEAD":
                    head_sha = sha
                elif refname.endswith("^{}"):
                    base = refname[:-3]
                    ref_lookup[base] = sha
                else:
                    ref_lookup.setdefault(refname, sha)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            stderr = getattr(e, "stderr", "") or ""
            log.warning("ls-remote batch failed for %s: %s", url, stderr.strip()[:200])

        for ref in refs:
            if ref_lookup is not None:
                sha = _resolve_ref_from_lookup(ref, ref_lookup, head_sha)
                result[(url, ref)] = sha
            else:
                result[(url, ref)] = ls_remote_sha(url, ref)

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    resolved = sum(1 for v in result.values() if v is not None)
    log.info("resolve_refs_to_shas complete: %d pairs, %d resolved, %d failed, %dms",
             len(result), resolved, len(result) - resolved, elapsed_ms)
    return result


def _resolve_ref_from_lookup(
    ref: str | None,
    ref_lookup: dict[str, str],
    head_sha: str | None,
) -> str | None:
    """Resolve a single ref against the parsed ls-remote output."""
    if ref is None:
        return head_sha

    candidates = [
        f"refs/heads/{ref}",
        f"refs/tags/{ref}",
        ref,
    ]
    for candidate in candidates:
        if candidate in ref_lookup:
            return ref_lookup[candidate]
    return None


def clone_showroom(
    url: str, ref: str | None, clone_dir: str = "/tmp"
) -> Path | None:
    """Shallow clone a Showroom repo. Returns clone path or None on failure."""
    repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
    suffix = uuid.uuid4().hex[:8]
    clone_path = Path(clone_dir) / f"rcars-showroom-{repo_name}-{suffix}"

    if clone_path.exists():
        shutil.rmtree(clone_path)

    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd.extend(["--branch", ref])
    cmd.extend([url, str(clone_path)])

    try:
        _run_git_with_retry(cmd, timeout=120)
        return clone_path
    except subprocess.CalledProcessError as e:
        if ref and ("not found" in e.stderr or "could not find" in e.stderr.lower()):
            log.warning("Ref %s not found for %s, trying default branch", ref, url)
            cmd_fallback = ["git", "clone", "--depth", "1", url, str(clone_path)]
            try:
                _run_git_with_retry(cmd_fallback, timeout=120)
                return clone_path
            except subprocess.CalledProcessError as e2:
                log.error("Failed to clone %s: %s", url, e2.stderr.strip()[:200])
                return None
        log.error("Failed to clone %s (ref=%s): %s", url, ref, e.stderr.strip()[:200])
        return None
    except subprocess.TimeoutExpired:
        log.error("Clone timed out for %s", url)
        return None


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
            included.add(Path(ref_path).name)
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
        pages_dir = clone_path / content_path
    else:
        pages_dir = clone_path / "content" / "modules" / "ROOT" / "pages"

    # Parse nav.adoc to determine which pages are active
    nav_file = clone_path / "content" / "modules" / "ROOT" / "nav.adoc"
    nav_includes: set[str] | None = None
    if nav_file.exists():
        try:
            nav_text = nav_file.read_text(errors="replace")
            files["_nav.adoc"] = nav_text
            nav_includes = _parse_nav_includes(nav_text)
            if nav_includes:
                log.info("%s nav.adoc: %d active pages: %s", label, len(nav_includes), sorted(nav_includes))
            else:
                nav_includes = None
        except OSError:
            pass

    if pages_dir.exists():
        for adoc_file in sorted(pages_dir.glob("*.adoc")):
            if nav_includes and adoc_file.name not in nav_includes:
                log.info("%s skipping %s — not in nav.adoc", label, adoc_file.name)
                continue
            try:
                files[adoc_file.name] = adoc_file.read_text(errors="replace")
            except OSError as e:
                log.warning("Could not read %s: %s", adoc_file, e)

    # For nav.adoc with subdirectory xrefs (e.g. 200-ops/lab_1.adoc),
    # also check those paths relative to ROOT/pages/
    if nav_includes:
        root_dir = clone_path / "content" / "modules" / "ROOT" / "pages"
        for inc in nav_includes:
            if "/" in inc:
                subpath = root_dir / inc
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
) -> tuple[str, str]:
    """Build analysis prompt split into system instructions and user data.

    Returns (system_prompt, user_message) for system/user separation (M-1/M-4).
    """
    template = PROMPT_TEMPLATE_PATH.read_text()

    # Concatenate file contents with headers
    content_parts = []
    for filename, content in sorted(content_files.items()):
        content_parts.append(f"=== File: {filename} ===\n{content}")
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


_embedding_lock = threading.Lock()
_embedding_models: dict[str, Any] = {}


def generate_embedding(text: str, model_name: str = "all-MiniLM-L6-v2") -> list[float]:
    """Generate a 384-dim embedding for text using sentence-transformers."""
    if model_name not in _embedding_models:
        with _embedding_lock:
            if model_name not in _embedding_models:
                from sentence_transformers import SentenceTransformer
                # Try loading from local cache first (no network check, no tqdm bar).
                # Falls back to downloading if not yet cached (first install).
                try:
                    _embedding_models[model_name] = SentenceTransformer(
                        model_name, local_files_only=True
                    )
                except Exception:
                    _embedding_models[model_name] = SentenceTransformer(model_name)

    embedding = _embedding_models[model_name].encode(text, normalize_embeddings=True)
    return embedding.tolist()


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
        # Clone
        log.info("analyze %s: cloning %s (ref=%s)", ci_name, showroom_url, showroom_ref or "HEAD")
        clone_path = clone_showroom(showroom_url, showroom_ref, clone_dir)
        if not clone_path:
            log.error("analyze %s: clone failed", ci_name)
            return {"error": "clone_failed", "message": f"Failed to clone {showroom_url}"}

        # Get repo HEAD info
        head_sha, head_date = get_repo_head(clone_path)
        log.info("analyze %s: cloned (HEAD=%s)", ci_name, head_sha[:8] if head_sha else "?")

        # Read content
        raw_files = read_showroom_content(clone_path, content_path=content_path, ci_name=ci_name)
        if not raw_files:
            ref_info = f" (ref={showroom_ref})" if showroom_ref else " (ref=HEAD)"
            path_info = f", content_path={content_path}" if content_path else ""
            log.warning("analyze %s: no .adoc files found in %s%s%s", ci_name, showroom_url, ref_info, path_info)
            return {"error": "no_content", "message": f"No .adoc files found in {showroom_url}{ref_info}{path_info}"}

        # Filter boilerplate
        content_files = filter_boilerplate_files(raw_files)
        if not content_files:
            log.warning("analyze %s: all files filtered as boilerplate, using unfiltered", ci_name)
            content_files = raw_files

        total_chars = sum(len(v) for v in content_files.values())
        log.info("analyze %s: %d content files (%d chars), %d filtered as boilerplate",
                 ci_name, len(content_files), total_chars, len(raw_files) - len(content_files))

        content_hash = hash_showroom_content(content_files)

        # Check if another CI already has analysis + embeddings for this content.
        # If so, reuse them instead of calling the LLM again — identical content
        # must produce identical analysis and embeddings.
        if db is not None:
            donor = db.find_donor_by_content_hash(content_hash, exclude_ci=ci_name)
            if donor:
                donor_name = donor["ci_name"]
                log.info("analyze %s: reusing analysis from %s (same content_hash %s)",
                         ci_name, donor_name, content_hash[:12])
                donor_analysis = {
                    "content_type": donor.get("content_type"),
                    "summary": donor.get("summary"),
                    "products": donor.get("products_json"),
                    "audience": donor.get("audience_json"),
                    "topics": donor.get("topics_json"),
                    "modules": donor.get("modules_json"),
                    "learning_objectives": donor.get("learning_objectives_json"),
                    "difficulty": donor.get("difficulty"),
                    "estimated_duration_min": donor.get("estimated_duration_min"),
                    "format_suitability": donor.get("format_suitability_json"),
                    "use_cases": donor.get("use_cases_json"),
                }

                # Rebuild CI embedding with this CI's own keywords
                ci_embedding_text = build_embedding_text(donor_analysis, keywords=keywords, display_name=display_name)
                ci_embedding = generate_embedding(ci_embedding_text)

                # Module embeddings don't include keywords, safe to copy
                donor_embeddings = db.get_embeddings_for_ci(donor_name)
                module_embeddings = []
                for e in donor_embeddings:
                    if e["embed_type"] == "module":
                        raw_vec = e["embedding_text"]
                        module_embeddings.append({
                            "module_title": e.get("module_title", ""),
                            "content_text": e["content_text"],
                            "embedding": [float(x) for x in raw_vec.strip("[]").split(",")],
                        })

                return {
                    "ci_name": ci_name,
                    "analysis": donor_analysis,
                    "ci_embedding_text": ci_embedding_text,
                    "ci_embedding": ci_embedding,
                    "module_embeddings": module_embeddings,
                    "last_repo_commit": head_sha,
                    "last_repo_updated": head_date,
                    "content_hash": content_hash,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "content_file_count": len(content_files),
                    "elapsed_seconds": round(time.monotonic() - t0, 1),
                    "reused_from": donor_name,
                    }

        # Build prompt and call Sonnet
        system_prompt, user_message = build_analysis_prompt(
            ci_name, display_name, category, product, content_files
        )
        log.info("analyze %s: sending to %s (prompt ~%d chars)", ci_name, model, len(system_prompt) + len(user_message))

        from rcars.config import call_llm
        result = call_llm(settings, model=model, messages=[{"role": "user", "content": user_message}], max_tokens=8192, system=system_prompt)

        input_tokens = result.input_tokens
        output_tokens = result.output_tokens
        log.info("analyze %s: response received (in=%d out=%d tokens, provider=%s)",
                 ci_name, input_tokens, output_tokens, result.provider)

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
        if not analysis:
            log.error("analyze %s: failed to parse Sonnet response", ci_name)
            return {"error": "parse_failed", "message": f"Failed to parse LLM response for {ci_name}"}

        # Generate embeddings (include catalog keywords for event/metadata signal)
        ci_embedding_text = build_embedding_text(analysis, keywords=keywords, display_name=display_name)
        ci_embedding = generate_embedding(ci_embedding_text)

        module_embeddings = []
        modules = analysis.get("modules", [])
        for module in modules:
            mod_text = build_module_embedding_text(module)
            if mod_text.strip():
                mod_embedding = generate_embedding(mod_text)
                module_embeddings.append({
                    "module_title": module.get("title", ""),
                    "content_text": mod_text,
                    "embedding": mod_embedding,
                })

        elapsed = time.monotonic() - t0
        log.info("analyze %s: complete (%.1fs, %d modules, %d embeddings)",
                 ci_name, elapsed, len(modules), 1 + len(module_embeddings))

        # Assemble result
        return {
            "ci_name": ci_name,
            "analysis": analysis,
            "ci_embedding_text": ci_embedding_text,
            "ci_embedding": ci_embedding,
            "module_embeddings": module_embeddings,
            "last_repo_commit": head_sha,
            "last_repo_updated": head_date,
            "content_hash": content_hash,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "content_file_count": len(content_files),
            "elapsed_seconds": round(elapsed, 1),
        }

    except Exception:
        elapsed = time.monotonic() - t0
        log.exception("analyze %s: failed after %.1fs", ci_name, elapsed)
        raise

    finally:
        # Always clean up clone
        if clone_path and clone_path.exists():
            shutil.rmtree(clone_path, ignore_errors=True)
