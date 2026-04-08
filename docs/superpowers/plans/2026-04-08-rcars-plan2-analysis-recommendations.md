# RCARS Plan 2: Analysis & Recommendations

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Showroom content analysis and recommendation capabilities — `rcars scan` clones Showroom repos, analyzes content via Sonnet, stores results + embeddings in PostgreSQL. `rcars recommend` searches by semantic similarity and ranks with Sonnet.

**Architecture:** Showroom repos are shallow-cloned to `/tmp`, `.adoc` files read and sent to Sonnet for structured analysis. Results stored in `showroom_analysis` table, embeddings generated via sentence-transformers and stored in `embeddings` table (pgvector). Recommendations use pgvector similarity search to find candidates, then Sonnet to rank and explain.

**Tech Stack:** Python 3.11+, anthropic[vertex] (Sonnet API), sentence-transformers (all-MiniLM-L6-v2), psycopg 3, Click, Rich, pytest.

**Prerequisites:** Plan 1 complete. PostgreSQL running with pgvector. `rcars refresh` has been run (catalog_items populated).

---

## File Structure (New/Modified)

```
src/rcars/
├── analyzer.py          # NEW: Showroom clone + Sonnet analysis + embedding generation
├── recommender.py       # NEW: pgvector search + Sonnet ranking
├── event_parser.py      # NEW: Event URL → structured profile
├── cli.py               # MODIFY: add scan, recommend commands
├── config.py            # MODIFY: add get_anthropic_client() factory
├── db.py                # MODIFY: add showroom_analysis CRUD, embedding ops

prompts/
├── analyze_showroom.txt # NEW: Showroom → structured JSON analysis prompt
├── recommend.txt        # NEW: Candidates + query → ranked recommendations
├── match_event.txt      # NEW: Event URL → structured profile

tests/
├── test_analyzer.py     # NEW: analysis parsing, boilerplate filtering tests
├── test_recommender.py  # NEW: embedding search, ranking tests
├── test_event_parser.py # NEW: event extraction tests
```

---

## Task 1: Anthropic Client Factory

**Files:**
- Modify: `src/rcars/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_get_anthropic_client_vertex(monkeypatch):
    """Should return AnthropicVertex when project ID is set."""
    monkeypatch.setenv("ANTHROPIC_VERTEX_PROJECT_ID", "test-project")
    monkeypatch.setenv("CLOUD_ML_REGION", "us-east5")
    settings = Settings()
    client = settings.get_anthropic_client()
    assert client is not None


def test_get_anthropic_client_direct(monkeypatch):
    """Should return Anthropic when API key is set."""
    monkeypatch.delenv("ANTHROPIC_VERTEX_PROJECT_ID", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    settings = Settings()
    client = settings.get_anthropic_client()
    assert client is not None


def test_get_anthropic_client_none(monkeypatch):
    """Should return None when no credentials."""
    monkeypatch.delenv("ANTHROPIC_VERTEX_PROJECT_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = Settings()
    client = settings.get_anthropic_client()
    assert client is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py::test_get_anthropic_client_vertex -v`
Expected: FAIL — `Settings` has no `get_anthropic_client` method

- [ ] **Step 3: Implement get_anthropic_client**

Add to `src/rcars/config.py` Settings class:

```python
    def get_anthropic_client(self):
        """Create an Anthropic client based on available credentials.

        Returns AnthropicVertex if project ID is set, Anthropic if API key
        is set, or None if no credentials are available.
        """
        if self.vertex_project_id:
            from anthropic import AnthropicVertex
            return AnthropicVertex(
                project_id=self.vertex_project_id,
                region=self.cloud_ml_region,
            )
        elif self.anthropic_api_key:
            from anthropic import Anthropic
            return Anthropic(api_key=self.anthropic_api_key)
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/rcars/config.py tests/test_config.py
git commit -m "rcars: Add Anthropic client factory to Settings"
```

---

## Task 2: Analysis Prompt Template

**Files:**
- Create: `prompts/analyze_showroom.txt`

- [ ] **Step 1: Create the prompt**

Create `prompts/analyze_showroom.txt`:

```
You are analyzing a Red Hat Demo Platform (RHDP) Showroom — a hands-on lab or demo guide built with AsciiDoc.

## Item Information
- CI Name: {ci_name}
- Display Name: {display_name}
- Category: {category}
- Product: {product}

## Instructions

Analyze the Showroom content below and produce a structured JSON assessment. Focus on what someone would LEARN or EXPERIENCE by completing this lab/demo.

### Pages to SKIP (do not analyze these — they are boilerplate):
- Login/credentials pages ("your username is...", "connect to bastion...", "SSH to your environment...")
- Environment setup pages ("your lab environment has been provisioned...", "wait for your environment...")
- Navigation/index pages (table of contents, module listings, "welcome to this lab")
- Author bios, revision history, "about this lab" boilerplate
- Generic "how to use Showroom" instructions

### Focus your analysis on:
- What Red Hat products and technologies are covered
- What the learner will actually DO (hands-on activities)
- What concepts and skills the learner will gain
- The difficulty level based on prerequisite knowledge needed
- How long it would realistically take to complete

### Learning Objectives
Extract TWO types of learning objectives:
1. **Stated objectives**: What the Showroom explicitly says you will learn (often in an intro/overview page)
2. **Inferred objectives**: What you determine the learner will actually learn by completing the exercises, even if not explicitly stated. For example, a lab that has you deploy with ArgoCD teaches "GitOps workflows" even if it never uses that phrase.

### Output Format

Return ONLY valid JSON (no markdown fences, no explanation):

{{
  "content_type": "workshop" or "demo",
  "summary": "2-3 sentence summary of what this lab/demo covers and who it's for",
  "products": ["list of official Red Hat product names covered"],
  "audience": ["target audience descriptors, e.g. 'platform engineers', 'developers', 'IT decision makers'"],
  "difficulty": "beginner" or "intermediate" or "advanced",
  "estimated_duration_min": 60,
  "topics": ["specific technical topics covered, e.g. 'Kubernetes operators', 'CI/CD pipelines'"],
  "learning_objectives": {{
    "stated": ["objectives explicitly mentioned in the content"],
    "inferred": ["objectives you determine from the hands-on activities"]
  }},
  "modules": [
    {{
      "title": "Module title from nav or heading",
      "topics": ["topics covered in this module"],
      "learning_objectives": ["what this specific module teaches"],
      "estimated_duration_min": 15
    }}
  ],
  "use_cases": ["business problems this content helps solve"],
  "event_fit": {{
    "booth_demo": {{"suitable": true/false, "notes": "why or why not"}},
    "hands_on_lab": {{"suitable": true/false, "notes": "why or why not"}},
    "presentation_support": {{"suitable": true/false, "notes": "why or why not"}}
  }}
}}

## Showroom Content

{content_files}
```

- [ ] **Step 2: Commit**

```bash
git add prompts/analyze_showroom.txt
git commit -m "rcars: Add Showroom analysis prompt with boilerplate filtering and learning objectives"
```

---

## Task 3: Showroom Analyzer

**Files:**
- Create: `src/rcars/analyzer.py`
- Create: `tests/test_analyzer.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_analyzer.py`:

```python
"""Tests for Showroom analyzer."""

import json
import pytest
from rcars.analyzer import (
    parse_analysis_response,
    filter_boilerplate_files,
    truncate_content,
)


SAMPLE_ANALYSIS_JSON = {
    "content_type": "workshop",
    "summary": "A hands-on workshop on OpenShift Lightspeed.",
    "products": ["Red Hat OpenShift Container Platform", "OpenShift Lightspeed"],
    "audience": ["platform engineers", "cluster administrators"],
    "difficulty": "intermediate",
    "estimated_duration_min": 90,
    "topics": ["AI assistants", "OpenShift web console", "troubleshooting"],
    "learning_objectives": {
        "stated": ["Use OpenShift Lightspeed to troubleshoot cluster issues"],
        "inferred": ["Understand how LLMs integrate with Kubernetes platforms"],
    },
    "modules": [
        {
            "title": "Introduction to Lightspeed",
            "topics": ["OpenShift Lightspeed", "AI"],
            "learning_objectives": ["Understand what Lightspeed does"],
            "estimated_duration_min": 15,
        },
        {
            "title": "Troubleshooting with Lightspeed",
            "topics": ["troubleshooting", "pod debugging"],
            "learning_objectives": ["Debug pod failures using Lightspeed"],
            "estimated_duration_min": 30,
        },
    ],
    "use_cases": ["Reduce MTTR for cluster issues"],
    "event_fit": {
        "booth_demo": {"suitable": True, "notes": "Quick to show"},
        "hands_on_lab": {"suitable": True, "notes": "Full workshop"},
        "presentation_support": {"suitable": True, "notes": "Good visuals"},
    },
}


def test_parse_analysis_response_valid_json():
    """Should parse valid JSON response."""
    result = parse_analysis_response(json.dumps(SAMPLE_ANALYSIS_JSON))
    assert result is not None
    assert result["content_type"] == "workshop"
    assert result["difficulty"] == "intermediate"
    assert result["estimated_duration_min"] == 90
    assert len(result["modules"]) == 2
    assert len(result["learning_objectives"]["stated"]) == 1
    assert len(result["learning_objectives"]["inferred"]) == 1


def test_parse_analysis_response_with_markdown_fences():
    """Should handle JSON wrapped in markdown code fences."""
    wrapped = f"```json\n{json.dumps(SAMPLE_ANALYSIS_JSON)}\n```"
    result = parse_analysis_response(wrapped)
    assert result is not None
    assert result["content_type"] == "workshop"


def test_parse_analysis_response_with_plain_fences():
    """Should handle JSON wrapped in plain code fences."""
    wrapped = f"```\n{json.dumps(SAMPLE_ANALYSIS_JSON)}\n```"
    result = parse_analysis_response(wrapped)
    assert result is not None


def test_parse_analysis_response_invalid():
    """Should return None for invalid JSON."""
    result = parse_analysis_response("This is not JSON at all")
    assert result is None


def test_parse_analysis_response_empty():
    """Should return None for empty string."""
    result = parse_analysis_response("")
    assert result is None


def test_filter_boilerplate_files():
    """Should filter out known boilerplate filenames."""
    files = {
        "01-introduction.adoc": "Welcome to this workshop...",
        "02-environment.adoc": "Your lab environment has been provisioned with...",
        "03-deploy-app.adoc": "In this module you will deploy an application...",
        "04-login.adoc": "Your username is user1 and your password is...",
        "index.adoc": "= Module List\n* Module 1\n* Module 2",
        "05-troubleshoot.adoc": "In this exercise, you will troubleshoot a failing pod...",
    }
    filtered = filter_boilerplate_files(files)
    # Should keep content files, remove boilerplate
    assert "03-deploy-app.adoc" in filtered
    assert "05-troubleshoot.adoc" in filtered
    # Should remove login/environment/index pages
    assert "04-login.adoc" not in filtered
    assert "02-environment.adoc" not in filtered
    assert "index.adoc" not in filtered


def test_filter_boilerplate_keeps_real_content():
    """Should keep files that discuss real technical content."""
    files = {
        "setup-operators.adoc": "Install the OpenShift Pipelines operator by navigating to...",
        "access-info.adoc": "Your credentials are user1/password123...",
    }
    filtered = filter_boilerplate_files(files)
    assert "setup-operators.adoc" in filtered
    assert "access-info.adoc" not in filtered


def test_truncate_content():
    """Should truncate content to max chars."""
    content = "x" * 200000
    result = truncate_content(content, max_chars=150000)
    assert len(result) <= 150000


def test_truncate_content_short():
    """Should not truncate content under the limit."""
    content = "Short content"
    result = truncate_content(content, max_chars=150000)
    assert result == content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_analyzer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement analyzer.py**

Create `src/rcars/analyzer.py`:

```python
"""Showroom content analyzer.

Clones Showroom repos, reads AsciiDoc content, sends to Sonnet for
structured analysis, generates embeddings, and stores results.
"""

import json
import logging
import re
import shutil
import subprocess
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
    Also reads nav.adoc and antora.yml if present.
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

    return template.format(
        ci_name=ci_name,
        display_name=display_name or ci_name,
        category=category or "Unknown",
        product=product or "Unknown",
        content_files=all_content,
    )


def generate_embedding(text: str, model_name: str = "all-MiniLM-L6-v2") -> list[float]:
    """Generate a 384-dim embedding for text using sentence-transformers."""
    from sentence_transformers import SentenceTransformer

    # Cache model instance on the function
    if not hasattr(generate_embedding, "_model") or generate_embedding._model_name != model_name:
        generate_embedding._model = SentenceTransformer(model_name)
        generate_embedding._model_name = model_name

    embedding = generate_embedding._model.encode(text, normalize_embeddings=True)
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

    parts.extend(analysis.get("topics", []))
    parts.extend(analysis.get("products", []))
    parts.extend(analysis.get("audience", []))
    parts.extend(analysis.get("use_cases", []))

    return " ".join(str(p) for p in parts if p)


def build_module_embedding_text(module: dict[str, Any]) -> str:
    """Build text for module-level embedding."""
    parts = [
        module.get("title", ""),
    ]
    parts.extend(module.get("topics", []))
    parts.extend(module.get("learning_objectives", []))
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_analyzer.py -v`
Expected: All tests PASS (tests only cover pure functions, not the full pipeline)

- [ ] **Step 5: Commit**

```bash
git add src/rcars/analyzer.py tests/test_analyzer.py
git commit -m "rcars: Add Showroom analyzer with boilerplate filtering and embedding generation"
```

---

## Task 4: Database — Analysis & Embedding CRUD

**Files:**
- Modify: `src/rcars/db.py`
- Modify: `tests/test_db.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_db.py`:

```python
def test_upsert_showroom_analysis(db):
    """Should store and retrieve analysis results."""
    # Need a catalog item first (FK constraint)
    db.upsert_catalog_item({
        "ci_name": "test.item.prod",
        "display_name": "Test",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
    })

    analysis = {
        "ci_name": "test.item.prod",
        "content_type": "workshop",
        "summary": "A test workshop",
        "products_json": ["OpenShift"],
        "audience_json": ["developers"],
        "topics_json": ["kubernetes"],
        "modules_json": [{"title": "Intro", "topics": ["k8s"]}],
        "learning_objectives_json": {
            "stated": ["Learn Kubernetes"],
            "inferred": ["Understand container orchestration"],
        },
        "difficulty": "beginner",
        "estimated_duration_min": 60,
        "last_repo_commit": "abc123",
        "last_repo_updated": "2026-01-01T00:00:00+00:00",
    }
    db.upsert_showroom_analysis(analysis)

    result = db.get_showroom_analysis("test.item.prod")
    assert result is not None
    assert result["content_type"] == "workshop"
    assert result["summary"] == "A test workshop"
    assert result["difficulty"] == "beginner"


def test_store_and_search_embeddings(db):
    """Should store embeddings and search by vector similarity."""
    db.upsert_catalog_item({
        "ci_name": "test.item.prod",
        "display_name": "Test",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
    })

    # Store a CI-level embedding (384 dims)
    embedding = [0.1] * 384
    db.store_embedding(
        ci_name="test.item.prod",
        embed_type="ci_summary",
        content_text="OpenShift Kubernetes workshop for developers",
        embedding=embedding,
    )

    # Search should find it
    results = db.search_embeddings(
        query_embedding=embedding,
        limit=5,
        prod_only=False,
    )
    assert len(results) >= 1
    assert results[0]["ci_name"] == "test.item.prod"


def test_get_items_needing_analysis(db):
    """Should return items with Showroom URLs but no analysis."""
    db.upsert_catalog_item({
        "ci_name": "analyzed.item",
        "display_name": "Analyzed",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
        "showroom_url": "https://github.com/example/repo1.git",
    })
    db.upsert_catalog_item({
        "ci_name": "pending.item",
        "display_name": "Pending",
        "stage": "prod",
        "catalog_namespace": "babylon-catalog-prod",
        "is_prod": True,
        "showroom_url": "https://github.com/example/repo2.git",
    })
    # Only analyze the first one
    db.upsert_showroom_analysis({
        "ci_name": "analyzed.item",
        "content_type": "demo",
        "summary": "Already analyzed",
    })

    pending = db.get_items_needing_analysis()
    ci_names = [p["ci_name"] for p in pending]
    assert "pending.item" in ci_names
    assert "analyzed.item" not in ci_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_db.py::test_upsert_showroom_analysis -v`
Expected: FAIL — `Database` has no `upsert_showroom_analysis` method

- [ ] **Step 3: Add analysis and embedding methods to db.py**

Add these methods to the `Database` class in `src/rcars/db.py`:

```python
    def upsert_showroom_analysis(self, analysis: dict[str, Any]):
        """Insert or update a showroom analysis result."""
        fields = [
            "ci_name", "content_type", "summary",
            "products_json", "audience_json", "topics_json",
            "modules_json", "learning_objectives_json",
            "difficulty", "estimated_duration_min",
            "event_fit_json", "use_cases_json",
            "last_repo_commit", "last_repo_updated",
            "last_analyzed", "is_stale", "stale_commit",
            "enrichment_review_needed",
        ]
        present = {k: analysis.get(k) for k in fields if k in analysis}
        if "last_analyzed" not in present:
            present["last_analyzed"] = datetime.now(timezone.utc)

        # Wrap JSONB fields
        jsonb_fields = [
            "products_json", "audience_json", "topics_json",
            "modules_json", "learning_objectives_json",
            "event_fit_json", "use_cases_json",
        ]
        for f in jsonb_fields:
            if f in present and present[f] is not None:
                present[f] = Jsonb(present[f])

        columns = list(present.keys())
        placeholders = [f"%({k})s" for k in columns]
        updates = [f"{k} = EXCLUDED.{k}" for k in columns if k != "ci_name"]

        sql = f"""
            INSERT INTO showroom_analysis ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT (ci_name) DO UPDATE SET {', '.join(updates)}
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, present)
        self._conn.commit()

    def get_showroom_analysis(self, ci_name: str) -> dict[str, Any] | None:
        """Get analysis for a catalog item."""
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM showroom_analysis WHERE ci_name = %(ci_name)s",
                {"ci_name": ci_name},
            )
            return cur.fetchone()

    def store_embedding(
        self,
        ci_name: str,
        embed_type: str,
        content_text: str,
        embedding: list[float],
        module_title: str | None = None,
    ):
        """Store an embedding vector."""
        with self._conn.cursor() as cur:
            # Delete existing embedding of same type for this CI
            if module_title:
                cur.execute(
                    """DELETE FROM embeddings
                       WHERE ci_name = %(ci_name)s AND embed_type = %(embed_type)s
                       AND module_title = %(module_title)s""",
                    {"ci_name": ci_name, "embed_type": embed_type, "module_title": module_title},
                )
            else:
                cur.execute(
                    """DELETE FROM embeddings
                       WHERE ci_name = %(ci_name)s AND embed_type = %(embed_type)s
                       AND module_title IS NULL""",
                    {"ci_name": ci_name, "embed_type": embed_type},
                )
            cur.execute(
                """INSERT INTO embeddings (ci_name, embed_type, module_title, content_text, embedding)
                   VALUES (%(ci_name)s, %(embed_type)s, %(module_title)s, %(content_text)s, %(embedding)s::vector)""",
                {
                    "ci_name": ci_name,
                    "embed_type": embed_type,
                    "module_title": module_title,
                    "content_text": content_text,
                    "embedding": str(embedding),
                },
            )
        self._conn.commit()

    def search_embeddings(
        self,
        query_embedding: list[float],
        limit: int = 15,
        prod_only: bool = True,
        embed_type: str = "ci_summary",
    ) -> list[dict[str, Any]]:
        """Search embeddings by cosine similarity."""
        prod_filter = ""
        if prod_only:
            prod_filter = "AND ci.is_prod = TRUE"

        sql = f"""
            SELECT e.ci_name, e.content_text, e.module_title,
                   e.embedding <=> %(query)s::vector AS distance,
                   ci.display_name, ci.category, ci.stage,
                   ci.is_published, ci.published_ci_name, ci.base_ci_name
            FROM embeddings e
            JOIN catalog_items ci ON e.ci_name = ci.ci_name
            WHERE e.embed_type = %(embed_type)s
            {prod_filter}
            ORDER BY distance ASC
            LIMIT %(limit)s
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, {
                "query": str(query_embedding),
                "embed_type": embed_type,
                "limit": limit,
            })
            return cur.fetchall()

    def get_items_needing_analysis(self) -> list[dict[str, Any]]:
        """Get catalog items with Showroom URLs but no analysis."""
        with self._conn.cursor() as cur:
            cur.execute("""
                SELECT ci.* FROM catalog_items ci
                LEFT JOIN showroom_analysis sa ON ci.ci_name = sa.ci_name
                WHERE ci.showroom_url IS NOT NULL
                AND ci.showroom_url != ''
                AND sa.ci_name IS NULL
                ORDER BY ci.ci_name
            """)
            return cur.fetchall()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_db.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/rcars/db.py tests/test_db.py
git commit -m "rcars: Add showroom analysis and embedding CRUD to database layer"
```

---

## Task 5: Recommendation Prompt & Engine

**Files:**
- Create: `prompts/recommend.txt`
- Create: `prompts/match_event.txt`
- Create: `src/rcars/recommender.py`
- Create: `src/rcars/event_parser.py`
- Create: `tests/test_recommender.py`

- [ ] **Step 1: Create recommendation prompt**

Create `prompts/recommend.txt`:

```
You are a Red Hat Demo Platform (RHDP) content advisor. Given a request and a list of candidate RHDP catalog items, rank them by fit and explain your reasoning.

## Request

{request_description}

## Candidates

{candidates}

## Instructions

Rank the candidates by how well they fit the request. Consider:
- Topic alignment (does the content match what's being asked for?)
- Audience fit (is the difficulty and target audience appropriate?)
- Duration fit (does the estimated time work for the context?)
- Content type (demo vs workshop — which fits better?)
- Event fit (if this is for an event, is it suitable for the format?)
- Freshness (prefer recently updated content)

Return ONLY valid JSON (no markdown fences):

{{
  "recommendations": [
    {{
      "rank": 1,
      "ci_name": "the-ci-name",
      "display_name": "Human readable name",
      "fit_score": 95,
      "rationale": "2-3 sentences explaining why this is a good fit",
      "suggested_format": "booth_demo" or "hands_on_lab" or "presentation",
      "duration_notes": "How to adapt timing if needed",
      "caveats": "Any concerns or things to watch for"
    }}
  ],
  "overall_assessment": "1-2 paragraph summary of the recommendations and any content gaps",
  "content_gaps": ["topics requested but not covered by any candidate"]
}}
```

- [ ] **Step 2: Create event parser prompt**

Create `prompts/match_event.txt`:

```
You are analyzing a conference or event page to extract a structured profile for matching RHDP demo content.

## Page Content

{page_content}

## Instructions

Extract a structured profile from this event page. Handle non-English content by translating key themes.

Return ONLY valid JSON (no markdown fences):

{{
  "event_name": "Name of the event",
  "event_dates": "Date range or null",
  "event_location": "Location or null",
  "event_type": "conference" or "meetup" or "workshop_series" or "hackathon" or "summit" or "other",
  "audience_profile": {{
    "primary_audience": "developers, architects, etc.",
    "experience_level": "beginner, intermediate, advanced, mixed",
    "industry_focus": "specific industry or general"
  }},
  "themes": ["major event themes"],
  "relevant_topics": ["technical topics relevant to Red Hat products"],
  "format_opportunities": {{
    "has_booth": true/false,
    "has_lab_slots": true/false,
    "has_talk_slots": true/false,
    "estimated_session_duration_min": 45,
    "notes": "Any relevant format details"
  }},
  "search_queries": ["3-5 natural language queries to find matching RHDP content"]
}}
```

- [ ] **Step 3: Implement recommender.py**

Create `src/rcars/recommender.py`:

```python
"""RCARS recommendation engine.

Combines pgvector semantic search with Sonnet ranking.
"""

import json
import logging
from pathlib import Path
from typing import Any

from rcars.analyzer import generate_embedding, parse_analysis_response
from rcars.db import Database

log = logging.getLogger(__name__)

RECOMMEND_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "recommend.txt"


def format_candidate(item: dict[str, Any], analysis: dict[str, Any] | None) -> str:
    """Format a candidate item for the ranking prompt."""
    parts = [
        f"CI Name: {item['ci_name']}",
        f"Display Name: {item.get('display_name', '')}",
        f"Category: {item.get('category', '')}",
        f"Product: {item.get('product', '')}",
        f"Stage: {item.get('stage', '')}",
    ]

    if item.get("is_published") and item.get("base_ci_name"):
        parts.append(f"Type: Virtual CI (orders via this name)")
    elif item.get("published_ci_name"):
        parts.append(f"Type: Base CI (order via {item['published_ci_name']})")

    if analysis:
        parts.append(f"Content Type: {analysis.get('content_type', '')}")
        parts.append(f"Summary: {analysis.get('summary', '')}")
        parts.append(f"Difficulty: {analysis.get('difficulty', '')}")
        parts.append(f"Duration: {analysis.get('estimated_duration_min', '?')} min")
        parts.append(f"Topics: {', '.join(analysis.get('topics_json', []) or [])}")
        parts.append(f"Products: {', '.join(analysis.get('products_json', []) or [])}")
        parts.append(f"Audience: {', '.join(analysis.get('audience_json', []) or [])}")

        objectives = analysis.get("learning_objectives_json", {})
        if isinstance(objectives, dict):
            stated = objectives.get("stated", [])
            inferred = objectives.get("inferred", [])
            if stated:
                parts.append(f"Stated Objectives: {'; '.join(stated)}")
            if inferred:
                parts.append(f"Inferred Objectives: {'; '.join(inferred)}")

    return "\n".join(parts)


def recommend(
    query: str,
    db: Database,
    anthropic_client,
    model: str = "claude-sonnet-4-6",
    limit: int = 15,
    prod_only: bool = True,
) -> dict[str, Any] | None:
    """Run a recommendation query.

    1. Generate embedding for query
    2. Search pgvector for top candidates
    3. Enrich with analysis data
    4. Send to Sonnet for ranking
    5. Return ranked results
    """
    # Generate query embedding
    query_embedding = generate_embedding(query)

    # Search for candidates
    candidates = db.search_embeddings(
        query_embedding=query_embedding,
        limit=limit,
        prod_only=prod_only,
    )

    if not candidates:
        log.warning("No candidates found for query: %s", query[:100])
        return None

    # Enrich with analysis data
    formatted_candidates = []
    for i, candidate in enumerate(candidates, 1):
        ci_name = candidate["ci_name"]
        analysis = db.get_showroom_analysis(ci_name)
        formatted = format_candidate(candidate, analysis)
        formatted_candidates.append(f"--- Candidate {i} ---\n{formatted}")

    candidates_text = "\n\n".join(formatted_candidates)

    # Build ranking prompt
    template = RECOMMEND_PROMPT_PATH.read_text()
    prompt = template.format(
        request_description=query,
        candidates=candidates_text,
    )

    # Call Sonnet for ranking
    response = anthropic_client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    result = parse_analysis_response(response.content[0].text)
    if not result:
        log.error("Failed to parse recommendation response")
        return None

    return result
```

- [ ] **Step 4: Implement event_parser.py**

Create `src/rcars/event_parser.py`:

```python
"""Event URL parser.

Fetches event web pages, extracts structured profiles via Sonnet.
"""

import logging
import re
from pathlib import Path
from typing import Any

import httpx

from rcars.analyzer import parse_analysis_response

log = logging.getLogger(__name__)

EVENT_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "match_event.txt"


def fetch_and_strip_html(url: str, max_chars: int = 50000) -> str | None:
    """Fetch a URL and strip HTML to plain text."""
    try:
        response = httpx.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()
    except httpx.HTTPError as e:
        log.error("Failed to fetch %s: %s", url, e)
        return None

    html = response.text

    # Strip HTML tags
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text[:max_chars]


def parse_event_url(
    url: str,
    anthropic_client,
    model: str = "claude-sonnet-4-6",
) -> dict[str, Any] | None:
    """Parse an event URL into a structured profile."""
    page_text = fetch_and_strip_html(url)
    if not page_text:
        return None

    template = EVENT_PROMPT_PATH.read_text()
    prompt = template.format(page_content=page_text)

    response = anthropic_client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    return parse_analysis_response(response.content[0].text)
```

- [ ] **Step 5: Write recommender tests**

Create `tests/test_recommender.py`:

```python
"""Tests for recommendation engine."""

import pytest
from rcars.recommender import format_candidate


def test_format_candidate_basic():
    """Should format a basic candidate."""
    item = {
        "ci_name": "test.item.prod",
        "display_name": "Test Item",
        "category": "Demos",
        "product": "OpenShift",
        "stage": "prod",
    }
    result = format_candidate(item, None)
    assert "test.item.prod" in result
    assert "Test Item" in result
    assert "Demos" in result


def test_format_candidate_with_analysis():
    """Should include analysis details."""
    item = {
        "ci_name": "test.item.prod",
        "display_name": "Test Item",
        "category": "Demos",
        "product": "OpenShift",
        "stage": "prod",
    }
    analysis = {
        "content_type": "workshop",
        "summary": "A great workshop",
        "difficulty": "beginner",
        "estimated_duration_min": 60,
        "topics_json": ["kubernetes", "operators"],
        "products_json": ["OpenShift"],
        "audience_json": ["developers"],
        "learning_objectives_json": {
            "stated": ["Learn K8s"],
            "inferred": ["Understand operators"],
        },
    }
    result = format_candidate(item, analysis)
    assert "workshop" in result
    assert "beginner" in result
    assert "60 min" in result
    assert "Learn K8s" in result
    assert "Understand operators" in result


def test_format_candidate_published_vci():
    """Should note published VCI type."""
    item = {
        "ci_name": "published.test.prod",
        "display_name": "Test",
        "category": "Demos",
        "product": "OpenShift",
        "stage": "prod",
        "is_published": True,
        "base_ci_name": "openshift-cnv.test.prod",
    }
    result = format_candidate(item, None)
    assert "Virtual CI" in result
```

- [ ] **Step 6: Run all tests**

Run: `python -m pytest tests/ -v -m "not integration"`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add prompts/recommend.txt prompts/match_event.txt src/rcars/recommender.py src/rcars/event_parser.py tests/test_recommender.py
git commit -m "rcars: Add recommendation engine with pgvector search and Sonnet ranking"
```

---

## Task 6: CLI — scan and recommend commands

**Files:**
- Modify: `src/rcars/cli.py`

- [ ] **Step 1: Add scan command**

Add to `src/rcars/cli.py`:

```python
@cli.command()
@click.option("--max", "max_analyze", type=int, default=None, help="Max items to analyze")
@click.option("--force", is_flag=True, default=False, help="Re-analyze everything")
def scan(max_analyze: int | None, force: bool):
    """Analyze Showroom content via Sonnet API."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from rcars.analyzer import analyze_showroom
    from rcars.db import Database

    settings = Settings()
    db = get_db()

    anthropic_client = settings.get_anthropic_client()
    if not anthropic_client:
        console.print("[red]Error:[/red] No Anthropic credentials (set ANTHROPIC_VERTEX_PROJECT_ID or ANTHROPIC_API_KEY)")
        db.close()
        sys.exit(1)

    if force:
        items = db.list_catalog_items()
        items = [i for i in items if i.get("showroom_url")]
    else:
        items = db.get_items_needing_analysis()

    # Filter to non-published items (analyze base CIs, not published VCIs)
    items = [i for i in items if not i.get("is_published")]

    if max_analyze:
        items = items[:max_analyze]

    if not items:
        console.print("[green]Nothing to analyze.[/green] All items are up to date.")
        db.close()
        return

    console.print(f"[bold]Analyzing {len(items)} Showroom(s)...[/bold]")

    completed = 0
    errors = 0

    def process_item(item):
        return analyze_showroom(
            ci_name=item["ci_name"],
            display_name=item.get("display_name", ""),
            category=item.get("category", ""),
            product=item.get("product", ""),
            showroom_url=item["showroom_url"],
            showroom_ref=item.get("showroom_ref"),
            anthropic_client=anthropic_client,
            model=settings.model,
            clone_dir=settings.clone_dir,
        )

    with ThreadPoolExecutor(max_workers=settings.max_parallel) as executor:
        futures = {executor.submit(process_item, item): item for item in items}

        for future in as_completed(futures):
            item = futures[future]
            try:
                result = future.result()
                if result:
                    analysis = result["analysis"]
                    db.upsert_showroom_analysis({
                        "ci_name": result["ci_name"],
                        "content_type": analysis.get("content_type"),
                        "summary": analysis.get("summary"),
                        "products_json": analysis.get("products"),
                        "audience_json": analysis.get("audience"),
                        "topics_json": analysis.get("topics"),
                        "modules_json": analysis.get("modules"),
                        "learning_objectives_json": analysis.get("learning_objectives"),
                        "difficulty": analysis.get("difficulty"),
                        "estimated_duration_min": analysis.get("estimated_duration_min"),
                        "event_fit_json": analysis.get("event_fit"),
                        "use_cases_json": analysis.get("use_cases"),
                        "last_repo_commit": result.get("last_repo_commit"),
                        "last_repo_updated": result.get("last_repo_updated"),
                    })

                    # Store embeddings
                    db.store_embedding(
                        ci_name=result["ci_name"],
                        embed_type="ci_summary",
                        content_text=result["ci_embedding_text"],
                        embedding=result["ci_embedding"],
                    )
                    for mod_emb in result.get("module_embeddings", []):
                        db.store_embedding(
                            ci_name=result["ci_name"],
                            embed_type="module",
                            module_title=mod_emb["module_title"],
                            content_text=mod_emb["content_text"],
                            embedding=mod_emb["embedding"],
                        )

                    db.log_action(result["ci_name"], "analyze")
                    completed += 1
                    console.print(f"  [green]✓[/green] {item['ci_name']}")
                else:
                    errors += 1
                    db.log_action(item["ci_name"], "error", details="Analysis returned None")
                    console.print(f"  [red]✗[/red] {item['ci_name']}")
            except Exception as e:
                errors += 1
                db.log_action(item["ci_name"], "error", details=str(e)[:200])
                console.print(f"  [red]✗[/red] {item['ci_name']}: {e}")

    console.print(f"\n[bold]Done.[/bold] {completed} analyzed, {errors} errors")
    db.close()


@cli.command()
@click.argument("query")
@click.option("--url", "event_url", type=str, default=None, help="Event URL to analyze")
@click.option("--include-dev", is_flag=True, default=False, help="Include dev items")
@click.option("--limit", type=int, default=15, help="Max candidates to consider")
@click.option("--json-output", is_flag=True, default=False, help="Output raw JSON")
def recommend(query: str, event_url: str | None, include_dev: bool, limit: int, json_output: bool):
    """Get content recommendations for an event or use case."""
    import json as json_mod
    from rcars.recommender import recommend as run_recommend
    from rcars.event_parser import parse_event_url

    settings = Settings()
    db = get_db()

    anthropic_client = settings.get_anthropic_client()
    if not anthropic_client:
        console.print("[red]Error:[/red] No Anthropic credentials")
        db.close()
        sys.exit(1)

    # If event URL provided, parse it and enhance query
    if event_url:
        console.print(f"[bold]Parsing event URL...[/bold]")
        event_profile = parse_event_url(event_url, anthropic_client, settings.model)
        if event_profile:
            queries = event_profile.get("search_queries", [])
            themes = event_profile.get("themes", [])
            query = f"{query}. Event themes: {', '.join(themes)}. {' '.join(queries)}"
            console.print(f"  Event: {event_profile.get('event_name', 'Unknown')}")

    console.print(f"[bold]Searching for recommendations...[/bold]")

    result = run_recommend(
        query=query,
        db=db,
        anthropic_client=anthropic_client,
        model=settings.model,
        limit=limit,
        prod_only=not include_dev,
    )

    if not result:
        console.print("[yellow]No recommendations found.[/yellow]")
        db.close()
        return

    if json_output:
        console.print(json_mod.dumps(result, indent=2))
    else:
        console.print(f"\n[bold]Recommendations[/bold]\n")
        for rec in result.get("recommendations", []):
            score = rec.get("fit_score", 0)
            color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
            console.print(f"  [{color}]{score}%[/{color}] [bold]{rec.get('display_name', rec.get('ci_name'))}[/bold]")
            console.print(f"       {rec.get('rationale', '')}")
            console.print(f"       Format: {rec.get('suggested_format', '-')} | {rec.get('duration_notes', '')}")
            if rec.get("caveats"):
                console.print(f"       [dim]Caveat: {rec['caveats']}[/dim]")
            console.print()

        if result.get("content_gaps"):
            console.print("[bold]Content Gaps[/bold]")
            for gap in result["content_gaps"]:
                console.print(f"  • {gap}")

        if result.get("overall_assessment"):
            console.print(f"\n[dim]{result['overall_assessment']}[/dim]")

    db.close()
```

- [ ] **Step 2: Run all tests to verify nothing broke**

Run: `python -m pytest tests/ -v -m "not integration"`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/rcars/cli.py
git commit -m "rcars: Add scan and recommend CLI commands"
```

---

## Task 7: End-to-End Verification

**Files:**
- No new files — manual testing

- [ ] **Step 1: Run a small scan**

```bash
rcars scan --max 3
```

Verify: 3 items analyzed, embeddings stored, no errors.

- [ ] **Step 2: Check status**

```bash
rcars status
```

Verify: "Analyzed" count is 3.

- [ ] **Step 3: Run a recommendation**

```bash
rcars recommend "OpenShift demos for a developer audience at a Kubernetes conference"
```

Verify: Returns ranked results with scores, rationale, and content gaps.

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/ -v -m "not integration"
```

Expected: All tests PASS.

- [ ] **Step 5: Commit any fixes from testing**

---

## Summary

After completing Plan 2, you will have:

- **Anthropic client factory** — Vertex AI or direct API, from Settings
- **Analysis prompt** — boilerplate filtering, learning objectives (stated + inferred), module-level detail
- **Showroom analyzer** — clone, read, filter, analyze via Sonnet, generate embeddings
- **Recommendation engine** — pgvector similarity search → Sonnet ranking with rationale
- **Event parser** — URL → structured event profile for enhanced queries
- **Database CRUD** — showroom_analysis upsert, embedding storage/search
- **CLI** — `rcars scan` (threaded analysis) and `rcars recommend` (query + ranking)

**What comes next in Plan 3:**
- FastAPI web app with HTMX
- Red Hat SSO authentication
- Enrichment tag management UI
- APScheduler for daily rescans
- Helm charts for OpenShift deployment
