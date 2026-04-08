"""Showroom content analyzer.

Clones Showroom repos, reads AsciiDoc content, sends to Sonnet for
structured analysis, generates embeddings, and stores results.
"""

import json
import logging
import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

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

PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "prompts" / "analyze_showroom.txt"


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
        # Try to find JSON object in the response
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start : brace_end + 1])
            except json.JSONDecodeError:
                pass

        log.warning("Failed to parse analysis response as JSON")
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


def truncate_content(content: str, max_chars: int = 150000) -> str:
    """Truncate content to max characters."""
    if len(content) <= max_chars:
        return content
    return content[:max_chars]


def clone_showroom(
    url: str, ref: str | None, clone_dir: str = "/tmp"
) -> Path | None:
    """Shallow clone a Showroom repo. Returns clone path or None on failure."""
    # Derive a safe directory name from the URL
    repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
    clone_path = Path(clone_dir) / f"rcars-showroom-{repo_name}"

    # Clean up any previous clone
    if clone_path.exists():
        shutil.rmtree(clone_path)

    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd.extend(["--branch", ref])
    cmd.extend([url, str(clone_path)])

    try:
        subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=120
        )
        return clone_path
    except subprocess.CalledProcessError as e:
        # If branch not found, retry without --branch (use default)
        if ref and ("not found" in e.stderr or "could not find" in e.stderr.lower()):
            log.warning("Ref %s not found for %s, trying default branch", ref, url)
            cmd_fallback = ["git", "clone", "--depth", "1", url, str(clone_path)]
            try:
                subprocess.run(
                    cmd_fallback, capture_output=True, text=True, check=True, timeout=120
                )
                return clone_path
            except subprocess.CalledProcessError as e2:
                log.error("Failed to clone %s: %s", url, e2.stderr)
                return None
        log.error("Failed to clone %s (ref=%s): %s", url, ref, e.stderr)
        return None
    except subprocess.TimeoutExpired:
        log.error("Clone timed out for %s", url)
        return None


def read_showroom_content(clone_path: Path) -> dict[str, str]:
    """Read .adoc files from a cloned Showroom repo.

    Reads from content/modules/ROOT/pages/ (standard Antora layout).
    Also reads nav.adoc if present, for structure context.
    """
    files = {}
    pages_dir = clone_path / "content" / "modules" / "ROOT" / "pages"

    if pages_dir.exists():
        for adoc_file in sorted(pages_dir.glob("*.adoc")):
            try:
                files[adoc_file.name] = adoc_file.read_text(errors="replace")
            except OSError as e:
                log.warning("Could not read %s: %s", adoc_file, e)

    # Also read nav.adoc for structure context
    nav_file = clone_path / "content" / "modules" / "ROOT" / "nav.adoc"
    if nav_file.exists():
        try:
            files["_nav.adoc"] = nav_file.read_text(errors="replace")
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
) -> str:
    """Build the analysis prompt from template and content."""
    template = PROMPT_TEMPLATE_PATH.read_text()

    # Concatenate file contents with headers
    content_parts = []
    for filename, content in sorted(content_files.items()):
        content_parts.append(f"=== File: {filename} ===\n{content}")
    all_content = "\n\n".join(content_parts)
    all_content = truncate_content(all_content)

    # Use simple string replacement instead of str.format() to avoid KeyErrors
    # from AsciiDoc {attribute} syntax in both the template (JSON examples)
    # and the content files.
    substitutions = {
        "{ci_name}": ci_name,
        "{display_name}": display_name or ci_name,
        "{category}": category or "Unknown",
        "{product}": product or "Unknown",
        "{content_files}": all_content,
    }
    result = template
    for placeholder, value in substitutions.items():
        result = result.replace(placeholder, value)
    return result


_embedding_lock = threading.Lock()
_embedding_models: dict[str, Any] = {}


def generate_embedding(text: str, model_name: str = "all-MiniLM-L6-v2") -> list[float]:
    """Generate a 384-dim embedding for text using sentence-transformers."""
    if model_name not in _embedding_models:
        with _embedding_lock:
            if model_name not in _embedding_models:
                from sentence_transformers import SentenceTransformer
                _embedding_models[model_name] = SentenceTransformer(model_name)

    embedding = _embedding_models[model_name].encode(text, normalize_embeddings=True)
    return embedding.tolist()


def build_embedding_text(analysis: dict[str, Any]) -> str:
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
    anthropic_client,
    model: str = "claude-sonnet-4-6",
    clone_dir: str = "/tmp",
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
    clone_path = None
    try:
        # Clone
        clone_path = clone_showroom(showroom_url, showroom_ref, clone_dir)
        if not clone_path:
            return None

        # Get repo HEAD info
        head_sha, head_date = get_repo_head(clone_path)

        # Read content
        raw_files = read_showroom_content(clone_path)
        if not raw_files:
            log.warning("No .adoc files found in %s", showroom_url)
            return None

        # Filter boilerplate
        content_files = filter_boilerplate_files(raw_files)
        if not content_files:
            log.warning("All files filtered as boilerplate in %s", showroom_url)
            content_files = raw_files  # Fall back to unfiltered

        # Build prompt and call Sonnet
        prompt = build_analysis_prompt(
            ci_name, display_name, category, product, content_files
        )

        response = anthropic_client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text
        analysis = parse_analysis_response(response_text)
        if not analysis:
            log.error("Failed to parse analysis for %s", ci_name)
            return None

        # Generate embeddings
        ci_embedding_text = build_embedding_text(analysis)
        ci_embedding = generate_embedding(ci_embedding_text)

        module_embeddings = []
        for module in analysis.get("modules", []):
            mod_text = build_module_embedding_text(module)
            if mod_text.strip():
                mod_embedding = generate_embedding(mod_text)
                module_embeddings.append({
                    "module_title": module.get("title", ""),
                    "content_text": mod_text,
                    "embedding": mod_embedding,
                })

        # Assemble result
        return {
            "ci_name": ci_name,
            "analysis": analysis,
            "ci_embedding_text": ci_embedding_text,
            "ci_embedding": ci_embedding,
            "module_embeddings": module_embeddings,
            "last_repo_commit": head_sha,
            "last_repo_updated": head_date,
        }

    finally:
        # Always clean up clone
        if clone_path and clone_path.exists():
            shutil.rmtree(clone_path, ignore_errors=True)
