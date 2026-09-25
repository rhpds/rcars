# Content-Type Drivers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bolt-on content-type branching with a driver/strategy pattern so adding a new content type requires one Python file and zero pipeline/frontend changes.

**Architecture:** Per-type driver objects provide 7 hooks. The orchestrator groups requested types by driver and runs parallel pipeline instances via `asyncio.gather`. Results stream to the frontend with category labels; `RecCard` renders generically from backend-provided display config.

**Tech Stack:** Python 3.11 (dataclasses, ABC, asyncio), React 19 + TypeScript, PatternFly 6 CSS vars.

**Spec:** `docs/superpowers/specs/2026-09-25-advisor-v2-content-type-drivers-design.md`

## Global Constraints

- Python 3.11+, no new dependencies
- All LLM responses must be structured JSON — use `parse_analysis_response()` for safe extraction
- structlog JSON logging with `component`, `job_id`, `action` fields on every line
- `content_id` is the universal candidate key (not `ci_name`)
- SSE transport unchanged — Redis pub/sub → EventSource
- Tests run via `cd src/api && python -m pytest tests/ -v`

## Review Focus

1. **Architecture candidate with missing display fields** — `RecCard` renders `display.header_right` but architecture omits it. Card must render without error when `header_right` is absent. → Task 8, architecture card rendering assertion.
2. **Single content_type skips gather** — orchestrator runs one `run_category()` directly when only one driver is needed, no unnecessary `asyncio.gather` overhead. → Task 6, orchestrator single-driver test.
3. **Empty results for one category** — if architectures return 0 candidates but labs return 15, the architecture category emits `complete` with 0 results without crashing. → Task 6, orchestrator mixed-results test.
4. **Performance data for architectures** — architectures have no provisions. `driver.serialize(include_performance=True)` must return `None` for performance fields, not crash. → Task 4, serialize test.
5. **Triage guidance injection placement** — driver guidance text must appear before `## Instructions` in the triage prompt, not after. Otherwise the LLM may ignore it. → Task 5, prompt assembly test.

---

## File Map

### Create
| File | Responsibility |
|------|---------------|
| `src/api/rcars/services/recommender/drivers/__init__.py` | Registry: `get_driver(type)`, `get_drivers_for_types(types)` |
| `src/api/rcars/services/recommender/drivers/base.py` | `ContentTypeDriver` ABC — 7 abstract hooks |
| `src/api/rcars/services/recommender/drivers/hands_on.py` | Driver for `lab`, `demo`, `sandbox` |
| `src/api/rcars/services/recommender/drivers/architecture.py` | Driver for `architecture` |
| `src/api/tests/test_drivers.py` | Unit tests for drivers, orchestrator, serialization |

### Modify
| File | What changes |
|------|-------------|
| `models.py` | Candidate: flat type-specific fields → `type_data` dict. Rename `stage` → `status`. Delete `grouped_results` from QueryState. |
| `vector_search.py:218-303` | Build new Candidate with universal fields + `type_data` |
| `triage.py:16-44` | Accept `guidance` param, inject into prompt. Adapt `format_triage_candidates` for `type_data`. |
| `rationale.py:37-105,228-251` | Replace `_format_single_candidate` and analysis fetch branching with driver hooks |
| `pipeline.py:114-329` | Delete `_apply_duration_penalty`, `_apply_usage_boost`, `serialize_candidates`. New `run_category()` + orchestrator `run_query()`. |
| `handlers.py:51-97` | Accept `content_types`, use driver serialize |
| `recommend.py:6-39` | Accept `content_types`, use driver serialize |
| `useJobStream.ts` | `StreamCandidate` with `type_data` + `display`. Candidates → `Map<string, StreamCandidate[]>` by category. |
| `RecCard.tsx` | Generic renderer from `display` config |
| `RecCardList.tsx:25,37,50,82` | Key on `content_id` instead of `ci_name` |
| `RecCardsBlock.tsx` | Tab-based rendering from pre-categorized data |
| `ProgressStream.tsx` | Nested per-category progress display |

### Delete
| File | Replacement |
|------|------------|
| `serialize.py` | `driver.serialize()` methods |

All paths relative to `src/api/rcars/services/recommender/` unless otherwise noted.

---

### Task 1: Candidate Model Refactor

**Files:**
- Modify: `src/api/rcars/services/recommender/models.py`
- Test: `src/api/tests/test_drivers.py`

**Interfaces:**
- Consumes: nothing (foundational)
- Produces: `Candidate(content_id, display_name, content_type, source, summary, products, topics, status, difficulty, is_hands_on, tier, vector_distance, vector_similarity_pct, relevance_score, one_line_reason, why_it_fits, how_to_use, caveats, type_data)`, `QueryState(phase, candidates, query, overall_assessment, content_gaps, timings, token_usage)`

- [ ] **Step 1: Write failing test for new Candidate**

```python
# src/api/tests/test_drivers.py
"""Tests for content-type drivers and refactored models."""

from rcars.services.recommender.models import Candidate, QueryState


def test_candidate_universal_fields():
    c = Candidate(
        content_id="babylon:test-ci",
        display_name="Test Lab",
        content_type="lab",
        source="babylon",
        summary="A test lab",
        products=["OpenShift"],
        topics=["containers"],
    )
    assert c.status == "prod"
    assert c.is_hands_on is True
    assert c.tier == "white"
    assert c.type_data == {}


def test_candidate_with_type_data():
    c = Candidate(
        content_id="babylon:test-ci",
        display_name="Test Lab",
        content_type="lab",
        source="babylon",
        summary="A test lab",
        products=["OpenShift"],
        topics=["containers"],
        type_data={"ci_name": "test-ci", "duration_min": 120, "duration_source": "curated"},
    )
    assert c.type_data["ci_name"] == "test-ci"
    assert c.type_data["duration_min"] == 120


def test_query_state_no_grouped_results():
    qs = QueryState(phase="COMPLETE", candidates=[])
    assert not hasattr(qs, "grouped_results") or "grouped_results" not in qs.__dataclass_fields__
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd src/api && python -m pytest tests/test_drivers.py -v
```
Expected: FAIL — `Candidate` still has the old signature.

- [ ] **Step 3: Rewrite Candidate and QueryState**

Replace the entire `models.py` with:

```python
"""Data models for the recommendation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Candidate:
    """A content entity moving through the recommendation pipeline."""

    # Universal — present in content_entities for all types
    content_id: str
    display_name: str
    content_type: str
    source: str
    summary: str
    products: list[str]
    topics: list[str]
    status: str = "prod"
    difficulty: str | None = None
    is_hands_on: bool = True

    # Pipeline state — set by pipeline phases, universal
    tier: str = "white"
    vector_distance: float = 0.0
    vector_similarity_pct: int = 0
    relevance_score: int | None = None
    one_line_reason: str | None = None

    # Rationale — set by Phase 3, same structure for all types
    why_it_fits: str | None = None
    how_to_use: str | None = None
    caveats: str | None = None

    # Type-specific — populated by vector_search and driver hooks
    type_data: dict = field(default_factory=dict)

    @staticmethod
    def from_similarity(similarity: float) -> int:
        """Convert similarity score (0.0-1.0) to percentage."""
        return round(similarity * 100)


@dataclass
class QueryState:
    """State of a recommendation query at a pipeline phase boundary."""

    phase: str  # SUBMITTED | VECTOR_DONE | TRIAGE_DONE | COMPLETE | NO_MATCHES
    candidates: list[Candidate]
    query: str = ""
    overall_assessment: str | None = None
    content_gaps: list[str] | None = None
    timings: dict[str, float] = field(default_factory=dict)
    token_usage: list[dict] = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd src/api && python -m pytest tests/test_drivers.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/services/recommender/models.py src/api/tests/test_drivers.py
git commit -m "[RHDPCD-1953] Refactor Candidate model: flat fields to type_data dict"
```

---

### Task 2: Driver Base Class + Registry

**Files:**
- Create: `src/api/rcars/services/recommender/drivers/__init__.py`
- Create: `src/api/rcars/services/recommender/drivers/base.py`
- Test: `src/api/tests/test_drivers.py`

**Interfaces:**
- Consumes: `Candidate` from Task 1
- Produces: `ContentTypeDriver` ABC, `get_driver(content_type: str) -> ContentTypeDriver`, `get_drivers_for_types(types: list[str]) -> dict[str, ContentTypeDriver]`

- [ ] **Step 1: Write failing test for registry**

Append to `src/api/tests/test_drivers.py`:

```python
from rcars.services.recommender.drivers import get_driver, get_drivers_for_types
from rcars.services.recommender.drivers.base import ContentTypeDriver


def test_get_driver_lab():
    driver = get_driver("lab")
    assert isinstance(driver, ContentTypeDriver)
    assert "lab" in driver.content_types


def test_get_driver_architecture():
    driver = get_driver("architecture")
    assert isinstance(driver, ContentTypeDriver)
    assert "architecture" in driver.content_types


def test_get_drivers_for_types_groups():
    drivers = get_drivers_for_types(["lab", "demo", "architecture"])
    # lab and demo share one driver, architecture is separate
    assert len(drivers) == 2


def test_get_driver_unknown_raises():
    import pytest
    with pytest.raises(KeyError):
        get_driver("unknown_type")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd src/api && python -m pytest tests/test_drivers.py::test_get_driver_lab -v
```
Expected: FAIL — `drivers` package does not exist.

- [ ] **Step 3: Create the driver base class**

```python
# src/api/rcars/services/recommender/drivers/base.py
"""Abstract base class for content-type drivers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from rcars.services.recommender.models import Candidate


class ContentTypeDriver(ABC):
    """Strategy interface for content-type-specific pipeline behavior.

    Each driver handles one or more content_type strings and provides
    hooks that the pipeline calls at defined extension points.
    """

    @property
    @abstractmethod
    def content_types(self) -> list[str]:
        """Content type strings this driver handles (e.g. ["lab", "demo"])."""

    @property
    @abstractmethod
    def category_key(self) -> str:
        """Short key for SSE category labels and frontend tab grouping."""

    @abstractmethod
    def fetch_analysis(self, db: Any, candidate: Candidate) -> dict:
        """Fetch full analysis data for the rationale prompt."""

    @abstractmethod
    def triage_guidance(self) -> str:
        """Extra text injected into the triage prompt for this type.

        Return empty string if no special guidance needed.
        """

    @abstractmethod
    def format_for_rationale(self, candidate: Candidate, analysis: dict) -> str:
        """Format one candidate with analysis data for the per-candidate rationale LLM call."""

    @abstractmethod
    def post_triage(self, candidates: list[Candidate], query: str, db: Any) -> list[Candidate]:
        """Type-specific adjustments after triage (e.g. usage boost, duration penalty).

        Return the (possibly reordered) candidate list.
        """

    @abstractmethod
    def serialize(self, candidate: Candidate, include_performance: bool = False, db: Any | None = None) -> dict:
        """Convert candidate to JSON for frontend. Includes display config.

        Two modes: streaming (basic) and final (with performance metrics).
        """

    @abstractmethod
    def display_config(self) -> dict:
        """Static display configuration for the frontend card renderer."""
```

- [ ] **Step 4: Create the registry**

```python
# src/api/rcars/services/recommender/drivers/__init__.py
"""Content-type driver registry."""

from __future__ import annotations

from rcars.services.recommender.drivers.base import ContentTypeDriver

_REGISTRY: dict[str, ContentTypeDriver] = {}


def _register(driver: ContentTypeDriver) -> None:
    for ct in driver.content_types:
        _REGISTRY[ct] = driver


def get_driver(content_type: str) -> ContentTypeDriver:
    """Get the driver for a content type. Raises KeyError if unknown."""
    return _REGISTRY[content_type]


def get_drivers_for_types(content_types: list[str]) -> dict[str, ContentTypeDriver]:
    """Group content types by driver. Returns {category_key: driver}."""
    result: dict[str, ContentTypeDriver] = {}
    for ct in content_types:
        driver = get_driver(ct)
        result[driver.category_key] = driver
    return result


def registered_content_types() -> list[str]:
    """All content types with registered drivers."""
    return list(_REGISTRY.keys())


def _init_drivers() -> None:
    from rcars.services.recommender.drivers.hands_on import HandsOnDriver
    from rcars.services.recommender.drivers.architecture import ArchitectureDriver
    _register(HandsOnDriver())
    _register(ArchitectureDriver())


_init_drivers()
```

- [ ] **Step 5: Create stub drivers so the registry import works**

Stub `hands_on.py` (full implementation in Task 3):

```python
# src/api/rcars/services/recommender/drivers/hands_on.py
"""Driver for hands-on content: labs, demos, sandboxes."""

from __future__ import annotations
from typing import Any
from rcars.services.recommender.drivers.base import ContentTypeDriver
from rcars.services.recommender.models import Candidate


class HandsOnDriver(ContentTypeDriver):

    @property
    def content_types(self) -> list[str]:
        return ["lab", "demo", "sandbox"]

    @property
    def category_key(self) -> str:
        return "hands_on"

    def fetch_analysis(self, db: Any, candidate: Candidate) -> dict:
        raise NotImplementedError

    def triage_guidance(self) -> str:
        return ""

    def format_for_rationale(self, candidate: Candidate, analysis: dict) -> str:
        raise NotImplementedError

    def post_triage(self, candidates: list[Candidate], query: str, db: Any) -> list[Candidate]:
        return candidates

    def serialize(self, candidate: Candidate, include_performance: bool = False, db: Any | None = None) -> dict:
        raise NotImplementedError

    def display_config(self) -> dict:
        raise NotImplementedError
```

Stub `architecture.py` (full implementation in Task 4):

```python
# src/api/rcars/services/recommender/drivers/architecture.py
"""Driver for portfolio architecture content."""

from __future__ import annotations
from typing import Any
from rcars.services.recommender.drivers.base import ContentTypeDriver
from rcars.services.recommender.models import Candidate


class ArchitectureDriver(ContentTypeDriver):

    @property
    def content_types(self) -> list[str]:
        return ["architecture"]

    @property
    def category_key(self) -> str:
        return "architecture"

    def fetch_analysis(self, db: Any, candidate: Candidate) -> dict:
        raise NotImplementedError

    def triage_guidance(self) -> str:
        return ""

    def format_for_rationale(self, candidate: Candidate, analysis: dict) -> str:
        raise NotImplementedError

    def post_triage(self, candidates: list[Candidate], query: str, db: Any) -> list[Candidate]:
        return candidates

    def serialize(self, candidate: Candidate, include_performance: bool = False, db: Any | None = None) -> dict:
        raise NotImplementedError

    def display_config(self) -> dict:
        raise NotImplementedError
```

- [ ] **Step 6: Run tests to verify registry works**

```bash
cd src/api && python -m pytest tests/test_drivers.py -v -k "registry or get_driver"
```
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/api/rcars/services/recommender/drivers/
git commit -m "[RHDPCD-1953] Add ContentTypeDriver ABC and driver registry"
```

---

### Task 3: Hands-on Driver

**Files:**
- Modify: `src/api/rcars/services/recommender/drivers/hands_on.py`
- Test: `src/api/tests/test_drivers.py`

**Interfaces:**
- Consumes: `Candidate` from Task 1, `ContentTypeDriver` from Task 2
- Produces: `HandsOnDriver` with all 7 hooks implemented. Used by Task 5 (triage_guidance), Task 6 (rationale fetch_analysis + format_for_rationale, orchestrator post_triage + serialize).

- [ ] **Step 1: Write failing tests for hands-on driver hooks**

Append to `src/api/tests/test_drivers.py`:

```python
from rcars.services.recommender.drivers.hands_on import HandsOnDriver


def _make_hands_on_candidate(**overrides) -> Candidate:
    defaults = dict(
        content_id="babylon:test-lab",
        display_name="Test Lab",
        content_type="lab",
        source="babylon",
        summary="A test lab about OpenShift",
        products=["OpenShift"],
        topics=["containers"],
        type_data={
            "ci_name": "test-lab",
            "stage": "prod",
            "catalog_namespace": "babylon-catalog-prod",
            "base_ci_name": None,
            "duration_min": 120,
            "duration_source": "curated",
            "learning_objectives": ["Deploy an app"],
            "category": "Hands-on Lab",
        },
    )
    defaults.update(overrides)
    return Candidate(**defaults)


def test_hands_on_triage_guidance():
    driver = HandsOnDriver()
    guidance = driver.triage_guidance()
    assert "duration" in guidance.lower() or guidance == ""


def test_hands_on_format_for_rationale():
    driver = HandsOnDriver()
    c = _make_hands_on_candidate()
    analysis = {
        "audience_json": ["developers"],
        "learning_objectives_json": {"stated": ["Deploy an app"], "inferred": []},
        "modules_json": [{"title": "Setup"}, {"title": "Deploy"}],
    }
    text = driver.format_for_rationale(c, analysis)
    assert "Test Lab" in text
    assert "Duration: 120 min" in text
    assert "Deploy an app" in text


def test_hands_on_serialize_streaming():
    driver = HandsOnDriver()
    c = _make_hands_on_candidate(relevance_score=85, tier="yellow")
    result = driver.serialize(c)
    assert result["content_id"] == "babylon:test-lab"
    assert result["content_type"] == "lab"
    assert "display" in result
    assert result["display"]["format_badge"]["key"] in ("hands_on_lab", "lab")


def test_hands_on_serialize_with_performance(mocker):
    driver = HandsOnDriver()
    c = _make_hands_on_candidate(relevance_score=85, tier="green")
    mock_db = mocker.MagicMock()
    mock_db.get_performance_channels.return_value = [{
        "channel": "rhdp",
        "windowed_metrics": {"3m": {"provisions": 42}},
        "avg_cost_per_provision": "15.50",
        "closed_amount": "50000",
    }]
    result = driver.serialize(c, include_performance=True, db=mock_db)
    assert result["provisions_quarter"] == 42
    assert result["sales_impact"] is not None


def test_hands_on_display_config():
    driver = HandsOnDriver()
    config = driver.display_config()
    assert "format_badge" in config
    assert "detail_rows" in config
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd src/api && python -m pytest tests/test_drivers.py -v -k "hands_on"
```
Expected: FAIL — methods raise `NotImplementedError`.

- [ ] **Step 3: Implement HandsOnDriver**

Replace the stub in `src/api/rcars/services/recommender/drivers/hands_on.py` with the full implementation. Key code for each hook:

**fetch_analysis** — moves logic from `rationale.py:228-246`:
```python
def fetch_analysis(self, db, candidate):
    if candidate.content_type in ("lab", "demo"):
        base = candidate.type_data.get("base_ci_name")
        analysis_cid = f"babylon:{base}" if base else candidate.content_id
        return db.get_showroom_analysis(analysis_cid) or {}
    # sandbox
    item = db.get_babylon_item(candidate.content_id) or {}
    workloads = db.get_workload_classifications(candidate.content_id)
    if workloads:
        item["workload_classifications"] = workloads
    return item
```

**triage_guidance** — currently no special guidance for hands_on:
```python
def triage_guidance(self):
    return ""
```

**format_for_rationale** — moves logic from `rationale.py:37-105` (lab/demo/sandbox branches):
```python
def format_for_rationale(self, candidate, analysis):
    td = candidate.type_data
    lines = [
        f"Content ID: {candidate.content_id}",
        f"Display Name: {candidate.display_name}",
        f"Category: {td.get('category', '')}",
        f"Content Type: {candidate.content_type}",
        f"Relevance Score: {candidate.relevance_score or 0}%",
        f"Summary: {candidate.summary}",
        f"Difficulty: {candidate.difficulty}",
        f"Duration: {td.get('duration_min') or '?'} min",
        f"Topics: {', '.join(candidate.topics)}",
        f"Products: {', '.join(candidate.products)}",
    ]
    if candidate.content_type in ("lab", "demo"):
        audience = analysis.get("audience_json", [])
        if audience:
            lines.append(f"Audience: {', '.join(audience)}")
        objectives = analysis.get("learning_objectives_json", {})
        if isinstance(objectives, dict):
            stated = objectives.get("stated", [])
            inferred = objectives.get("inferred", [])
            if stated:
                lines.append(f"Stated Objectives: {'; '.join(stated)}")
            if inferred:
                lines.append(f"Inferred Objectives: {'; '.join(inferred)}")
        modules = analysis.get("modules_json", [])
        if modules:
            mod_titles = [m.get("title", "") for m in modules if m.get("title")]
            if mod_titles:
                lines.append(f"Modules: {'; '.join(mod_titles)}")
    elif candidate.content_type == "sandbox":
        cloud = analysis.get("cloud_provider", "")
        if cloud:
            lines.append(f"Cloud Provider: {cloud}")
        ocp = analysis.get("ocp_version", "")
        if ocp:
            lines.append(f"OpenShift Version: {ocp}")
        workloads = analysis.get("workload_classifications", [])
        if workloads:
            wl_names = [w.get("product_name", "") for w in workloads if w.get("product_name")]
            if wl_names:
                lines.append(f"Workloads: {'; '.join(wl_names)}")
    return "\n".join(lines)
```

**post_triage** — moves `_apply_usage_boost` (pipeline.py:142-183) and `_apply_duration_penalty` (pipeline.py:114-139):
```python
def post_triage(self, candidates, query, db):
    self._apply_usage_boost(candidates, db)
    duration_target, is_hard = self._extract_duration_target(query)
    if duration_target:
        self._apply_duration_penalty(candidates, duration_target, is_hard)
    return candidates
```

Include `_apply_usage_boost`, `_apply_duration_penalty`, and `_extract_duration_target` as private methods — copy directly from `pipeline.py:94-183`. Import `_extract_duration_target` from pipeline (it stays there as a utility) or move it into the driver. Since it's only used by HandsOnDriver, move it here.

**serialize** — merges `pipeline.py:231-246` (streaming) and `serialize.py:9-54` (with performance):
```python
def serialize(self, candidate, include_performance=False, db=None):
    td = candidate.type_data
    result = {
        "content_id": candidate.content_id,
        "content_type": candidate.content_type,
        "display_name": candidate.display_name,
        "tier": candidate.tier,
        "relevance_score": candidate.relevance_score,
        "vector_similarity_pct": candidate.vector_similarity_pct,
        "status": candidate.status,
        "why_it_fits": candidate.why_it_fits,
        "how_to_use": candidate.how_to_use,
        "caveats": candidate.caveats,
        # Type-specific
        "ci_name": td.get("ci_name"),
        "stage": td.get("stage", candidate.status),
        "catalog_namespace": td.get("catalog_namespace", ""),
        "duration_min": td.get("duration_min"),
        "duration_source": td.get("duration_source"),
        "learning_objectives": td.get("learning_objectives", []),
        "suggested_format": candidate.type_data.get("suggested_format"),
        "duration_notes": candidate.type_data.get("duration_notes"),
        "provisions_quarter": td.get("provisions_quarter"),
        "display": self._build_display(candidate),
    }
    if include_performance and db:
        self._attach_performance(result, candidate.content_id, db)
    return result
```

**_build_display** — constructs the display config dict:
```python
def _build_display(self, candidate):
    td = candidate.type_data
    fmt = td.get("suggested_format", "hands_on_lab" if candidate.content_type == "lab" else candidate.content_type)
    config = self.display_config()
    config["format_badge"] = {"label": _FORMAT_LABELS.get(fmt, fmt.replace("_", " ").title()), "key": fmt}
    if td.get("duration_min"):
        source = "Curated duration" if td.get("duration_source") == "curated" else "AI duration estimate"
        config["header_right"] = {"value": f"~{td['duration_min']} min", "tooltip": source}
    return config
```

**_attach_performance** — moves logic from `serialize.py:37-53`:
```python
def _attach_performance(self, result, content_id, db):
    import json
    from rcars.services.reporting_sync import compute_sales_impact
    channels = db.get_performance_channels(content_id)
    rhdp = next((ch for ch in (channels or []) if ch.get("channel") == "rhdp"), None)
    if rhdp:
        wm = rhdp.get("windowed_metrics") or {}
        if isinstance(wm, str):
            wm = json.loads(wm)
        q = wm.get("3m", {})
        result["provisions_quarter"] = q.get("provisions", 0)
        result["avg_cost_per_provision"] = float(rhdp.get("avg_cost_per_provision") or 0)
        result["sales_impact"] = compute_sales_impact(float(rhdp.get("closed_amount") or 0))
    else:
        result["avg_cost_per_provision"] = None
        result["sales_impact"] = None
```

**display_config:**
```python
def display_config(self):
    return {
        "detail_rows": [
            {"label": "Why it fits", "field": "why_it_fits"},
            {"label": "Objectives", "field": "learning_objectives", "type": "list", "max": 5},
            {"label": "How to use", "field": "how_to_use"},
        ],
        "footer_metrics": [
            {"label": "deployments (last 90d)", "field": "provisions_quarter"},
            {"label": "sales_impact", "field": "sales_impact", "type": "badge"},
        ],
        "links": [
            {"label": "View in RHDP Catalog", "url_template": "catalog"},
            {"label": "View in RCARS", "url_template": "browse"},
        ],
    }
```

Constants at module top:
```python
_FORMAT_LABELS = {
    "hands_on_lab": "Hands-on Lab",
    "demo": "Demo",
    "sandbox": "Sandbox",
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd src/api && python -m pytest tests/test_drivers.py -v -k "hands_on"
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/services/recommender/drivers/hands_on.py src/api/tests/test_drivers.py
git commit -m "[RHDPCD-1953] Implement HandsOnDriver with all 7 hooks"
```

---

### Task 4: Architecture Driver

**Files:**
- Modify: `src/api/rcars/services/recommender/drivers/architecture.py`
- Test: `src/api/tests/test_drivers.py`

**Interfaces:**
- Consumes: `Candidate` from Task 1, `ContentTypeDriver` from Task 2
- Produces: `ArchitectureDriver` with all 7 hooks implemented. Used by Task 5, Task 6.

- [ ] **Step 1: Write failing tests for architecture driver hooks**

Append to `src/api/tests/test_drivers.py`:

```python
from rcars.services.recommender.drivers.architecture import ArchitectureDriver


def _make_arch_candidate(**overrides) -> Candidate:
    defaults = dict(
        content_id="pa:25",
        display_name="Edge Computing Architecture",
        content_type="architecture",
        source="portfolio_arch",
        summary="Edge computing with OpenShift",
        products=["OpenShift"],
        topics=["edge"],
        is_hands_on=False,
        type_data={},
    )
    defaults.update(overrides)
    return Candidate(**defaults)


def test_arch_triage_guidance():
    driver = ArchitectureDriver()
    guidance = driver.triage_guidance()
    assert "duration" in guidance.lower()
    assert "architecture" in guidance.lower()


def test_arch_format_for_rationale():
    driver = ArchitectureDriver()
    c = _make_arch_candidate()
    analysis = {
        "asset_type": "VP",
        "audience_json": ["architects"],
        "solution_areas_json": ["Edge Computing"],
        "use_cases_json": ["Remote monitoring"],
        "key_components_json": ["MicroShift"],
    }
    text = driver.format_for_rationale(c, analysis)
    assert "Edge Computing Architecture" in text
    assert "Validated Pattern" in text
    assert "Duration" not in text


def test_arch_post_triage_is_passthrough():
    driver = ArchitectureDriver()
    c = _make_arch_candidate(relevance_score=80, tier="yellow")
    result = driver.post_triage([c], "edge computing", None)
    assert result == [c]
    assert c.relevance_score == 80


def test_arch_serialize_no_performance():
    driver = ArchitectureDriver()
    c = _make_arch_candidate(relevance_score=75, tier="yellow")
    result = driver.serialize(c)
    assert result["content_id"] == "pa:25"
    assert "display" in result
    assert "header_right" not in result["display"]
    assert result.get("provisions_quarter") is None


def test_arch_serialize_with_performance_no_crash(mocker):
    driver = ArchitectureDriver()
    c = _make_arch_candidate(relevance_score=75, tier="green")
    mock_db = mocker.MagicMock()
    mock_db.get_performance_channels.return_value = []
    result = driver.serialize(c, include_performance=True, db=mock_db)
    assert result.get("provisions_quarter") is None
    assert result.get("sales_impact") is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd src/api && python -m pytest tests/test_drivers.py -v -k "arch"
```
Expected: FAIL — methods raise `NotImplementedError`.

- [ ] **Step 3: Implement ArchitectureDriver**

Replace the stub in `src/api/rcars/services/recommender/drivers/architecture.py`:

```python
"""Driver for portfolio architecture content."""

from __future__ import annotations

from typing import Any

import structlog

from rcars.services.recommender.drivers.base import ContentTypeDriver
from rcars.services.recommender.models import Candidate

log = structlog.get_logger()

ASSET_TYPE_LABELS = {
    "VP": "Validated Pattern",
    "SP": "Solution Pattern",
    "PA": "Portfolio Architecture",
}


def _primary_asset_type(raw: str | None) -> str:
    tokens = [t.strip().upper() for t in str(raw or "").split(",") if t.strip()]
    for candidate in ("VP", "SP", "PA"):
        if candidate in tokens:
            return candidate
    return ""


class ArchitectureDriver(ContentTypeDriver):

    @property
    def content_types(self) -> list[str]:
        return ["architecture"]

    @property
    def category_key(self) -> str:
        return "architecture"

    def fetch_analysis(self, db: Any, candidate: Candidate) -> dict:
        return db.get_architecture_analysis(candidate.content_id) or {}

    def triage_guidance(self) -> str:
        return (
            "Architecture content (Validated Patterns, Solution Patterns, Portfolio Architectures) "
            "has no duration and cannot be provisioned. Ignore the Duration field for architecture "
            "candidates. Evaluate based on topic relevance, solution areas, and use cases."
        )

    def format_for_rationale(self, candidate: Candidate, analysis: dict) -> str:
        lines = [
            f"Content ID: {candidate.content_id}",
            f"Display Name: {candidate.display_name}",
            f"Content Type: {candidate.content_type}",
            f"Relevance Score: {candidate.relevance_score or 0}%",
            f"Summary: {candidate.summary}",
            f"Difficulty: {candidate.difficulty}",
            f"Topics: {', '.join(candidate.topics)}",
            f"Products: {', '.join(candidate.products)}",
        ]
        asset = _primary_asset_type(analysis.get("asset_type"))
        lines.append(f"Asset Type: {ASSET_TYPE_LABELS.get(asset, 'Architecture')}")
        audience = analysis.get("audience_json", [])
        if audience:
            lines.append(f"Audience: {', '.join(audience)}")
        for key, label in (("solution_areas_json", "Solution Areas"),
                           ("use_cases_json", "Use Cases"),
                           ("key_components_json", "Key Components")):
            values = analysis.get(key) or []
            if values:
                lines.append(f"{label}: {'; '.join(str(v) for v in values)}")
        return "\n".join(lines)

    def post_triage(self, candidates: list[Candidate], query: str, db: Any) -> list[Candidate]:
        return candidates

    def serialize(self, candidate: Candidate, include_performance: bool = False, db: Any | None = None) -> dict:
        result: dict = {
            "content_id": candidate.content_id,
            "content_type": candidate.content_type,
            "display_name": candidate.display_name,
            "tier": candidate.tier,
            "relevance_score": candidate.relevance_score,
            "vector_similarity_pct": candidate.vector_similarity_pct,
            "status": candidate.status,
            "why_it_fits": candidate.why_it_fits,
            "how_to_use": candidate.how_to_use,
            "caveats": candidate.caveats,
            "provisions_quarter": None,
            "sales_impact": None,
            "display": self._build_display(candidate),
        }
        return result

    def _build_display(self, candidate: Candidate) -> dict:
        config = self.display_config()
        asset = candidate.type_data.get("asset_type", "")
        primary = _primary_asset_type(asset)
        config["format_badge"] = {
            "label": ASSET_TYPE_LABELS.get(primary, "Architecture"),
            "key": f"architecture_{primary.lower()}" if primary else "architecture",
        }
        return config

    def display_config(self) -> dict:
        return {
            "detail_rows": [
                {"label": "Why it fits", "field": "why_it_fits"},
                {"label": "How to use", "field": "how_to_use"},
            ],
            "links": [
                {"label": "View in RCARS", "url_template": "browse"},
            ],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd src/api && python -m pytest tests/test_drivers.py -v -k "arch"
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/services/recommender/drivers/architecture.py src/api/tests/test_drivers.py
git commit -m "[RHDPCD-1953] Implement ArchitectureDriver with all 7 hooks"
```

---

### Task 5: Triage + Rationale Driver Hooks

**Files:**
- Modify: `src/api/rcars/services/recommender/triage.py`
- Modify: `src/api/rcars/services/recommender/rationale.py`
- Test: `src/api/tests/test_drivers.py`

**Interfaces:**
- Consumes: `ContentTypeDriver` from Task 2, `HandsOnDriver` from Task 3, `ArchitectureDriver` from Task 4, `Candidate` from Task 1
- Produces: `triage(state, settings, model, triage_cutoff, guidance="")`, `generate_rationale(state, db, settings, driver, model, top_n)`

- [ ] **Step 1: Write test for triage guidance injection**

Append to `src/api/tests/test_drivers.py`:

```python
from rcars.services.recommender.triage import format_triage_candidates


def test_format_triage_candidates_with_type_data():
    c = _make_hands_on_candidate()
    text = format_triage_candidates([c])
    assert "Content ID: babylon:test-lab" in text
    assert "Display Name: Test Lab" in text
    assert "Duration: 120 min" in text


def test_format_triage_candidates_architecture():
    c = _make_arch_candidate()
    text = format_triage_candidates([c])
    assert "Content ID: pa:25" in text
    assert "Duration" not in text or "?" in text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd src/api && python -m pytest tests/test_drivers.py -v -k "format_triage"
```
Expected: FAIL — `format_triage_candidates` accesses old flat fields like `c.category`, `c.ci_name`, `c.duration_min`.

- [ ] **Step 3: Update format_triage_candidates for new Candidate model**

In `src/api/rcars/services/recommender/triage.py`, replace `format_triage_candidates` (lines 16-36):

```python
def format_triage_candidates(candidates: list[Candidate]) -> str:
    """Format candidates compactly for the triage prompt."""
    parts = []
    for i, c in enumerate(candidates, 1):
        td = c.type_data
        block = (
            f"--- Candidate {i} ---\n"
            f"Content ID: {c.content_id}\n"
            f"Content Type: {c.content_type}\n"
        )
        ci_name = td.get("ci_name")
        if ci_name:
            block += f"CI Name: {ci_name}\n"
        block += (
            f"Display Name: {c.display_name}\n"
            f"Summary: {c.summary}\n"
            f"Topics: {', '.join(c.topics)}\n"
            f"Products: {', '.join(c.products)}\n"
        )
        category = td.get("category")
        if category:
            block += f"Category: {category}\n"
        if c.is_hands_on:
            duration = td.get("duration_min")
            block += f"Duration: {duration or '?'} min"
        parts.append(block)
    return "\n\n".join(parts)
```

- [ ] **Step 4: Add guidance parameter to triage()**

In `triage.py`, change the `triage` function signature (line 39) to accept `guidance`:

```python
def triage(
    state: QueryState,
    settings,
    model: str = "claude-haiku-4-5",
    triage_cutoff: int = 30,
    guidance: str = "",
) -> QueryState:
```

After line 60 (where `user_message` is built), inject guidance before the Instructions section:

```python
    if guidance:
        # Inject driver-specific guidance before the Instructions section
        instructions_marker = "\n## Instructions\n"
        if instructions_marker in system_prompt:
            system_prompt = system_prompt.replace(
                instructions_marker,
                f"\n## Content-Type Guidance\n\n{guidance}{instructions_marker}",
            )
```

- [ ] **Step 5: Update generate_rationale to use driver hooks**

In `src/api/rcars/services/recommender/rationale.py`:

Add `driver` parameter to `generate_rationale` (line 206):

```python
def generate_rationale(
    state: QueryState,
    db: Database,
    settings,
    driver=None,
    model: str = "claude-sonnet-4-6",
    top_n: int = 5,
) -> QueryState:
```

Replace the analysis fetch loop (lines 228-251) with:

```python
    analyses = {}
    for c in top_candidates:
        if driver:
            analysis = driver.fetch_analysis(db, c)
            if analysis:
                analyses[c.content_id] = analysis
        else:
            # Fallback for backward compatibility
            if c.content_type in ("lab", "demo"):
                base = c.type_data.get("base_ci_name")
                analysis_cid = f"babylon:{base}" if base else c.content_id
                analysis = db.get_showroom_analysis(analysis_cid)
                if analysis:
                    analyses[c.content_id] = analysis
            elif c.content_type == "architecture":
                analysis = db.get_architecture_analysis(c.content_id)
                if analysis:
                    analyses[c.content_id] = analysis
```

Replace the `_format_single_candidate` call in `_call_rationale_single` (line 115) to use the driver when available. Add a module-level variable:

```python
_active_driver = None  # Set by generate_rationale for use by _call_rationale_single
```

In `generate_rationale`, before the ThreadPoolExecutor block:

```python
    global _active_driver
    _active_driver = driver
```

In `_call_rationale_single` (line 115), replace:
```python
    candidate_text = _format_single_candidate(c, analysis)
```
with:
```python
    if _active_driver:
        candidate_text = _active_driver.format_for_rationale(c, analysis)
    else:
        candidate_text = _format_single_candidate(c, analysis)
```

Delete `ASSET_TYPE_LABELS` and `_primary_asset_type` from rationale.py (lines 21-34) — they're now in `architecture.py`. Keep `_format_single_candidate` as fallback until all callers are migrated.

- [ ] **Step 6: Run all tests**

```bash
cd src/api && python -m pytest tests/test_drivers.py -v
```
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/api/rcars/services/recommender/triage.py src/api/rcars/services/recommender/rationale.py src/api/tests/test_drivers.py
git commit -m "[RHDPCD-1953] Wire triage guidance and rationale hooks to drivers"
```

---

### Task 6: Orchestrator + Pipeline Refactor

**Files:**
- Modify: `src/api/rcars/services/recommender/pipeline.py`
- Modify: `src/api/rcars/services/recommender/vector_search.py:218-303`
- Test: `src/api/tests/test_drivers.py`

**Interfaces:**
- Consumes: `ContentTypeDriver` from Task 2, drivers from Task 3-4, triage/rationale hooks from Task 5, `Candidate` from Task 1
- Produces: `run_query(query, db, settings, ..., content_types=None) -> dict[str, QueryState]` (orchestrator), `run_category(query, db, settings, driver, ...) -> QueryState` (single-driver pipeline)

- [ ] **Step 1: Write orchestrator tests**

Append to `src/api/tests/test_drivers.py`:

```python
import pytest
import asyncio


@pytest.fixture
def mock_driver(mocker):
    driver = mocker.MagicMock()
    driver.content_types = ["lab", "demo"]
    driver.category_key = "hands_on"
    driver.triage_guidance.return_value = ""
    driver.post_triage.side_effect = lambda c, q, db: c
    driver.serialize.side_effect = lambda c, **kw: {"content_id": c.content_id, "display": {}}
    return driver


def test_orchestrator_single_category(mocker, mock_driver):
    """Single driver should run directly, not through asyncio.gather."""
    from rcars.services.recommender.drivers import get_drivers_for_types
    drivers = get_drivers_for_types(["lab", "demo"])
    assert len(drivers) == 1  # Both map to hands_on driver
```

- [ ] **Step 2: Update vector_search candidate construction**

In `src/api/rcars/services/recommender/vector_search.py`, replace lines 218-303 (candidate construction loop). The new version builds `Candidate` with universal fields + `type_data`:

```python
    candidates = []
    for row in rows:
        content_id = row["content_id"]
        content_type = row.get("content_type", "")
        ci_name = row.get("ci_name")

        # Fetch card data — source depends on content type
        type_data = {}
        if content_type in ("lab", "demo"):
            if row.get("is_published") and row.get("base_ci_name"):
                analysis_content_id = f"babylon:{row['base_ci_name']}"
            else:
                analysis_content_id = content_id
            analysis = db.get_showroom_analysis(analysis_content_id)

            lo = (analysis or {}).get("learning_objectives_json") or {}
            learning_objs = (lo.get("stated", []) if isinstance(lo, dict) else []) or []

            summary = (analysis or {}).get("summary", "")
            topics = (analysis or {}).get("topics_json", []) or []
            products = (analysis or {}).get("products_json", []) or []
            difficulty = (analysis or {}).get("difficulty", "")
            duration_min = (
                (analysis or {}).get("curated_duration_min")
                if (analysis or {}).get("curated_duration_min") is not None
                else (analysis or {}).get("estimated_duration_min")
            )
            duration_source = "curated" if (analysis or {}).get("curated_duration_min") is not None else "ai"

            type_data = {
                "ci_name": ci_name,
                "stage": row.get("stage", "prod"),
                "catalog_namespace": row.get("catalog_namespace", ""),
                "base_ci_name": row.get("base_ci_name"),
                "category": row.get("category", ""),
                "duration_min": duration_min,
                "duration_source": duration_source,
                "learning_objectives": learning_objs,
            }
        elif content_type == "sandbox":
            entity = db.get_content_entity(content_id)
            summary = (entity or {}).get("summary", "")
            topics = (entity or {}).get("topics_json", []) or []
            products = (entity or {}).get("products_json", []) or []
            difficulty = (entity or {}).get("difficulty", "")

            type_data = {
                "ci_name": ci_name,
                "stage": row.get("stage", "prod"),
                "catalog_namespace": row.get("catalog_namespace", ""),
                "base_ci_name": row.get("base_ci_name"),
                "category": row.get("category", ""),
            }
        elif content_type == "architecture":
            entity = db.get_content_entity(content_id)
            summary = (entity or {}).get("summary", "")
            topics = (entity or {}).get("topics_json", []) or []
            products = (entity or {}).get("products_json", []) or []
            difficulty = (entity or {}).get("difficulty", "")
        else:
            summary = row.get("summary", "")
            topics = []
            products = []
            difficulty = ""

        best_similarity = row["best_similarity"]
        vector_distance = 1.0 - best_similarity

        candidates.append(Candidate(
            content_id=content_id,
            display_name=row.get("display_name", content_id),
            content_type=content_type,
            source=row.get("source", "babylon"),
            summary=summary,
            products=products,
            topics=topics,
            status=row.get("stage", "prod"),
            difficulty=difficulty,
            is_hands_on=row.get("is_hands_on", True),
            vector_distance=vector_distance,
            vector_similarity_pct=Candidate.from_similarity(best_similarity),
            type_data=type_data,
        ))
```

- [ ] **Step 3: Refactor pipeline.py — extract run_category from run_query**

The current `run_query` (pipeline.py:186-329) becomes `run_category`. The new `run_query` is the orchestrator.

Key changes to pipeline.py:
1. Delete `_apply_duration_penalty` (lines 114-139) — moved to HandsOnDriver.post_triage
2. Delete `_apply_usage_boost` (lines 142-183) — moved to HandsOnDriver.post_triage
3. Delete `_extract_duration_target` (lines 94-111) — moved to HandsOnDriver
4. Rename current `run_query` → `run_category`, add `driver` parameter
5. New `run_query` orchestrator at the top

New `run_category` signature:
```python
async def run_category(
    query: str,
    db: Database,
    settings: Settings,
    driver: ContentTypeDriver,
    category: str = "",
    stages: list[str] | None = None,
    include_zt: bool = True,
    on_progress: Callable[[dict], Awaitable[None]] | None = None,
    depth: str = "high",
    scope_content_ids: list[str] | None = None,
) -> QueryState:
```

Inside `run_category`, replace hardcoded `content_types=["lab", "demo"]` (line 255) with:
```python
    content_types=driver.content_types
```

Replace `serialize_candidates` nested function (lines 231-246) with:
```python
    def serialize_candidates(candidates):
        return [driver.serialize(c) for c in candidates]
```

Add `category` to all `emit()` calls when category is set:
```python
    async def emit(data: dict):
        if category:
            data["category"] = category
        if on_progress:
            await on_progress(data)
```

Replace the usage boost + duration penalty block (lines 293-307) with:
```python
    # Driver-specific post-triage adjustments
    state.candidates = driver.post_triage(state.candidates, query, db)
    state.candidates.sort(key=lambda c: (
        0 if c.tier == "yellow" else 1,
        -(c.relevance_score or 0) if c.tier == "yellow" else -(c.vector_similarity_pct or 0),
    ))
```

Pass the driver to `generate_rationale`:
```python
    state = await asyncio.to_thread(generate_rationale, state, db, settings=settings,
                                     driver=driver, model=settings.rationale_model, top_n=top_n)
```

Pass the driver's guidance to `triage`:
```python
    state = await asyncio.to_thread(triage, state, settings=settings,
                                     model=settings.triage_model,
                                     triage_cutoff=settings.triage_cutoff,
                                     guidance=driver.triage_guidance())
```

New orchestrator:
```python
async def run_query(
    query: str,
    db: Database,
    settings: Settings,
    stages: list[str] | None = None,
    include_zt: bool = True,
    on_progress: Callable[[dict], Awaitable[None]] | None = None,
    depth: str = "high",
    scope_content_ids: list[str] | None = None,
    content_types: list[str] | None = None,
) -> dict[str, QueryState]:
    """Orchestrate parallel pipeline runs, one per content-type driver.

    Returns {category_key: QueryState}.
    """
    from rcars.services.recommender.drivers import get_drivers_for_types, registered_content_types

    types = content_types or registered_content_types()
    drivers = get_drivers_for_types(types)

    if len(drivers) == 1:
        cat, driver = next(iter(drivers.items()))
        state = await run_category(
            query, db, settings, driver=driver, category="" if len(drivers) == 1 else cat,
            stages=stages, include_zt=include_zt, on_progress=on_progress,
            depth=depth, scope_content_ids=scope_content_ids,
        )
        return {cat: state}

    async def _run_one(cat: str, driver):
        return cat, await run_category(
            query, db, settings, driver=driver, category=cat,
            stages=stages, include_zt=include_zt, on_progress=on_progress,
            depth=depth, scope_content_ids=scope_content_ids,
        )

    results = await asyncio.gather(*[_run_one(cat, drv) for cat, drv in drivers.items()])
    return dict(results)
```

- [ ] **Step 4: Run tests**

```bash
cd src/api && python -m pytest tests/test_drivers.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/rcars/services/recommender/pipeline.py src/api/rcars/services/recommender/vector_search.py src/api/tests/test_drivers.py
git commit -m "[RHDPCD-1953] Split pipeline into orchestrator + per-driver run_category"
```

---

### Task 7: Caller Integration + Cleanup

**Files:**
- Modify: `src/api/rcars/services/chat/handlers.py:51-97`
- Modify: `src/api/rcars/workers/recommend.py`
- Delete: `src/api/rcars/services/recommender/serialize.py`
- Modify: `src/api/rcars/services/recommender/rationale.py` (cleanup)

**Interfaces:**
- Consumes: orchestrator `run_query() -> dict[str, QueryState]` from Task 6, `driver.serialize()` from Tasks 3-4
- Produces: Updated callers that work with the new multi-category return type

- [ ] **Step 1: Update handle_recommend in handlers.py**

`run_query` now returns `dict[str, QueryState]` instead of `QueryState`. Update `handle_recommend`:

```python
from rcars.services.recommender.drivers import get_driver

async def handle_recommend(res, db, settings, stages, include_zt, on_progress):
    args = RecommendArgs.model_validate(res.output.args)
    query = res.message or args.search_query or " ".join(str(v) for v in args.constraints.values())
    if not query and res.scope_ids:
        query = " ".join(i.get("display_name", "") for i in (res.items or []) if i.get("display_name")) or "recommend similar content"
    depth = "medium" if res.scope_ids else "high"

    async def _relay(data):
        if data.get("phase") == "complete":
            return
        await on_progress(data)

    category_states = await run_query(query, db, settings, stages=stages, include_zt=include_zt,
                                       on_progress=_relay, depth=depth,
                                       scope_content_ids=res.scope_ids or None)

    # Serialize all candidates across categories with performance data
    all_cards = []
    combined_state = None
    for cat, state in category_states.items():
        driver = get_driver(state.candidates[0].content_type) if state.candidates else None
        if driver:
            cards = [driver.serialize(c, include_performance=True, db=db) for c in state.candidates]
        else:
            cards = []
        all_cards.extend(cards)
        if combined_state is None:
            combined_state = state
        else:
            combined_state.candidates.extend(state.candidates)
            if state.content_gaps:
                combined_state.content_gaps = (combined_state.content_gaps or []) + state.content_gaps

    if combined_state is None:
        combined_state = QueryState(phase="NO_MATCHES", candidates=[], query=query)

    green = [c for c in all_cards if c["tier"] == "green"]

    blocks = []
    scoped = bool(res.scope_ids)
    if scoped and not green:
        category_states = await run_query(query, db, settings, stages=stages, include_zt=include_zt,
                                           on_progress=_relay, depth="high", scope_content_ids=None)
        all_cards = []
        for cat, state in category_states.items():
            driver = get_driver(state.candidates[0].content_type) if state.candidates else None
            if driver:
                all_cards.extend([driver.serialize(c, include_performance=True, db=db) for c in state.candidates])
            combined_state = state
        green = [c for c in all_cards if c["tier"] == "green"]
        scoped = False
        blocks.append(Block(type="notice", data={
            "kind": "scope_expanded",
            "message": "No strong matches in your prior results. Expanded to the full catalog."}))

    blocks.append(Block(type="rec_cards", data={"candidates": all_cards,
                                                "content_gaps": combined_state.content_gaps}))
    return HandlerResult(
        blocks=blocks,
        scaffold_facts={"result_count": len(all_cards), "green_count": len(green),
                        "assessment": combined_state.overall_assessment,
                        "top": [c["display_name"] for c in (green or all_cards)[:3]],
                        "durations": [{"content_id": c["content_id"], "display_name": c["display_name"],
                                       "duration_min": c.get("duration_min")} for c in (green or all_cards)[:5]
                                      if c.get("duration_min") is not None],
                        "scoped": scoped},
        anchor_ids=[c["content_id"] for c in (green or all_cards)[:5]],
        session_results=all_cards)
```

- [ ] **Step 2: Update recommend worker**

In `src/api/rcars/workers/recommend.py`, replace the imports and result handling:

```python
from rcars.services.recommender.pipeline import run_query
from rcars.services.recommender.drivers import get_driver

# Remove: from rcars.services.recommender.serialize import candidates_with_performance
```

Replace lines 29-39:
```python
        category_states = await run_query(
            query=query, db=wctx.db, settings=wctx.settings,
            stages=stages or (["prod"] if prod_only else ["prod", "dev", "event"]),
            include_zt=include_zt, on_progress=on_progress, depth=depth,
        )

        # Serialize with performance data
        candidates_json = []
        combined_assessment = None
        combined_gaps = None
        for cat, state in category_states.items():
            driver = get_driver(state.candidates[0].content_type) if state.candidates else None
            if driver:
                candidates_json.extend([driver.serialize(c, include_performance=True, db=wctx.db)
                                        for c in state.candidates])
            if state.overall_assessment:
                combined_assessment = state.overall_assessment
            if state.content_gaps:
                combined_gaps = (combined_gaps or []) + state.content_gaps
```

Update the results dict:
```python
        results = {
            "phase": "COMPLETE" if candidates_json else "NO_MATCHES",
            "candidates": candidates_json,
            "overall_assessment": combined_assessment,
            "content_gaps": combined_gaps,
        }
```

- [ ] **Step 3: Delete serialize.py**

```bash
git rm src/api/rcars/services/recommender/serialize.py
```

- [ ] **Step 4: Clean up rationale.py**

Delete `ASSET_TYPE_LABELS` (lines 21-25), `_primary_asset_type` (lines 28-34) — now in architecture.py. Keep `_format_single_candidate` as dead code for now (delete after all callers are verified working). Or delete it if you're confident — the driver hooks replace it completely.

Also delete the `global _active_driver` pattern added in Task 5 — cleaner approach: pass the driver through to `_call_rationale_single` via the closure in `generate_rationale`:

```python
    # In generate_rationale, inside the ThreadPoolExecutor block:
    for c in top_candidates:
        analysis = analyses.get(c.content_id, {})
        future = executor.submit(_call_rationale_single, c, analysis, state.query, settings, model, driver)
        futures[future] = c.content_id
```

Update `_call_rationale_single` signature:
```python
def _call_rationale_single(c, analysis, query, settings, model, driver=None):
    ...
    if driver:
        candidate_text = driver.format_for_rationale(c, analysis)
    else:
        candidate_text = _format_single_candidate(c, analysis)
```

- [ ] **Step 5: Run full test suite**

```bash
cd src/api && python -m pytest tests/ -v -m "not integration"
```
Expected: PASS — existing tests should still work with the refactored pipeline.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "[RHDPCD-1953] Wire callers to orchestrator, delete serialize.py"
```

---

### Task 8: Frontend Refactor

**Files:**
- Modify: `src/frontend/src/hooks/useJobStream.ts`
- Modify: `src/frontend/src/components/advisor/RecCard.tsx`
- Modify: `src/frontend/src/components/advisor/RecCardList.tsx`
- Modify: `src/frontend/src/components/advisor/blocks/RecCardsBlock.tsx`
- Modify: `src/frontend/src/components/advisor/ProgressStream.tsx`

**Interfaces:**
- Consumes: Serialized candidate JSON from driver.serialize() (Tasks 3-4) with `display` config and optional `category` on SSE events
- Produces: Generic card rendering, category-tabbed results, nested progress display

- [ ] **Step 1: Update StreamCandidate type in useJobStream.ts**

Replace the `StreamCandidate` interface (lines 9-31):

```typescript
export interface DisplayConfig {
  format_badge?: { label: string; key: string }
  header_right?: { value: string; tooltip: string }
  detail_rows?: Array<{ label: string; field: string; type?: string; max?: number }>
  footer_metrics?: Array<{ label: string; field: string; type?: string }>
  links?: Array<{ label: string; url_template: string }>
}

export interface StreamCandidate {
  content_id: string
  content_type?: string
  display_name: string
  tier: string
  relevance_score: number | null
  vector_similarity_pct: number | null
  status?: string
  why_it_fits: string | null
  how_to_use: string | null
  caveats: string | null
  display?: DisplayConfig
  // Hands-on specific (via type_data serialization)
  ci_name?: string
  stage?: string
  catalog_namespace?: string
  learning_objectives?: string[]
  duration_min?: number | null
  duration_source?: string | null
  suggested_format?: string | null
  duration_notes?: string | null
  provisions_quarter?: number | null
  sales_impact?: string | null
  avg_cost_per_provision?: number | null
  // Allow additional fields from any driver
  [key: string]: unknown
}
```

Update `StreamState` — `candidates` becomes a `Record<string, StreamCandidate[]>` keyed by category:

```typescript
interface StreamState {
  phase: string
  progress: { current?: number; total?: number } | null
  userMessage: string
  results: unknown | null
  isComplete: boolean
  error: string | null
  messages: ProgressMessage[]
  candidates: Record<string, StreamCandidate[]>
}

const initialState: StreamState = {
  phase: '', progress: null, userMessage: '', results: null,
  isComplete: false, error: null, messages: [], candidates: {},
}
```

Update the `onmessage` handler (line 76):
```typescript
candidates: data.candidate_data
  ? data.category
    ? { ...prev.candidates, [data.category]: data.candidate_data }
    : { ...prev.candidates, _default: data.candidate_data }
  : prev.candidates,
```

- [ ] **Step 2: Update RecCard to render from display config**

Replace `RecCard.tsx`. The new version reads `candidate.display` for what to render:

Key changes:
- Format badge: `candidate.display?.format_badge` instead of `FORMAT_LABELS[suggested_format]`
- Header right (duration): `candidate.display?.header_right` instead of hardcoded `duration_min`
- Detail rows: iterate `candidate.display?.detail_rows`, read field value from `candidate[field]`
- Footer metrics: iterate `candidate.display?.footer_metrics`
- Links: iterate `candidate.display?.links`, build URLs from templates
- Stage badge: read from `candidate.stage` or `candidate.status`
- Key/selection: use `candidate.content_id` instead of `candidate.ci_name`

For the `handleSelect` function:
```typescript
const handleSelect = async () => {
  if (!sessionId || turnIndex == null) return
  await api.selectRecommendation(sessionId, turnIndex, candidate.content_id)
  setSelected(true)
}
```

For link URL building:
```typescript
function buildUrl(template: string, candidate: StreamCandidate): string {
  if (template === 'catalog' && candidate.ci_name) {
    const ns = candidate.catalog_namespace || 'babylon-catalog-prod'
    return `https://demo.redhat.com/catalog?item=${ns}/${candidate.ci_name}`
  }
  if (template === 'browse') {
    return '/browse?search=' + encodeURIComponent(candidate.display_name)
  }
  return '#'
}
```

Fallback: if `candidate.display` is missing (old data), render with the old hardcoded layout. This ensures backward compatibility with cached/historical sessions.

- [ ] **Step 3: Update RecCardList — key on content_id**

In `RecCardList.tsx`, change all `key={c.ci_name}` to `key={c.content_id}`:
- Line 25: `{candidates.map(c => <RecCard key={c.content_id} ...`
- Line 37: same
- Line 50: same
- Line 82: same

- [ ] **Step 4: Update RecCardsBlock — tab-based rendering**

Replace `RecCardsBlock.tsx`. The new version receives pre-categorized candidates:

```typescript
import { useState } from 'react'
import { RecCardList } from '../RecCardList'
import type { ChatBlock } from '../chatTypes'
import type { StreamCandidate } from '../../../hooks/useJobStream'

interface RecCardsBlockProps {
  block: ChatBlock
  sessionId?: string
  turnIndex: number
}

const CATEGORY_LABELS: Record<string, string> = {
  hands_on: 'Hands-on Labs & Demos',
  architecture: 'Architectures',
  _default: 'Results',
}

export function RecCardsBlock({ block, sessionId, turnIndex }: RecCardsBlockProps) {
  const candidates = (block.data.candidates || []) as StreamCandidate[]
  const contentGaps = (block.data.content_gaps || []) as string[]

  // Group by content type category for tabbed display
  const categories = new Map<string, StreamCandidate[]>()
  for (const c of candidates) {
    const key = c.content_type === 'architecture' ? 'architecture'
      : (c.content_type === 'lab' || c.content_type === 'demo' || c.content_type === 'sandbox') ? 'hands_on'
      : '_default'
    const list = categories.get(key) || []
    list.push(c)
    categories.set(key, list)
  }

  const categoryKeys = Array.from(categories.keys())
  const [activeTab, setActiveTab] = useState(categoryKeys[0] || '_default')
  const showTabs = categoryKeys.length > 1

  return (
    <div>
      {showTabs && (
        <div style={{ display: 'flex', gap: '0', borderBottom: '2px solid var(--border-subtle)', marginBottom: '12px' }}>
          {categoryKeys.map(key => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              style={{
                background: 'transparent', border: 'none', cursor: 'pointer',
                padding: '8px 16px', fontSize: '13px', fontWeight: 600,
                color: activeTab === key ? 'var(--text-primary)' : 'var(--text-muted)',
                borderBottom: activeTab === key ? '2px solid var(--score-green)' : '2px solid transparent',
                marginBottom: '-2px',
              }}
            >
              {CATEGORY_LABELS[key] || key} ({(categories.get(key) || []).length})
            </button>
          ))}
        </div>
      )}

      <RecCardList
        candidates={categories.get(activeTab) || []}
        isComplete
        sessionId={sessionId}
        turnIndex={turnIndex}
      />

      {contentGaps.length > 0 && (
        <div style={{
          marginTop: '16px', padding: '12px', background: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)',
          fontSize: '13px', color: 'var(--text-muted)',
        }}>
          <div style={{ fontWeight: 600, marginBottom: '6px' }}>Content gaps identified:</div>
          <ul style={{ margin: 0, paddingLeft: '20px' }}>
            {contentGaps.map((gap, i) => <li key={i}>{gap}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Update ProgressStream for nested categories**

Replace `ProgressStream.tsx` to show per-category progress when `category` is present on messages:

```typescript
interface ProgressMessage {
  phase: string
  message: string
  done: boolean
  category?: string
}

interface ProgressStreamProps {
  messages: ProgressMessage[]
}

export function ProgressStream({ messages }: ProgressStreamProps) {
  if (messages.length === 0) return null

  // Group by category if categories exist
  const hasCategories = messages.some(m => m.category)

  if (!hasCategories) {
    return (
      <div style={{ fontSize: '14px', lineHeight: '1.8' }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ color: msg.done ? 'var(--score-green)' : 'var(--score-amber)' }}>
            {msg.done ? '✓' : '●'} {msg.message}
          </div>
        ))}
      </div>
    )
  }

  const byCategory = new Map<string, ProgressMessage[]>()
  for (const msg of messages) {
    const key = msg.category || '_default'
    const list = byCategory.get(key) || []
    list.push(msg)
    byCategory.set(key, list)
  }

  const allDone = messages.every(m => m.done)

  return (
    <div style={{ fontSize: '14px', lineHeight: '1.8' }}>
      <div style={{ color: allDone ? 'var(--score-green)' : 'var(--score-amber)' }}>
        {allDone ? '✓' : '●'} Searching {byCategory.size} content types...
      </div>
      {Array.from(byCategory.entries()).map(([cat, msgs]) => {
        const latest = msgs[msgs.length - 1]
        return (
          <div key={cat} style={{ paddingLeft: '20px', color: latest?.done ? 'var(--score-green)' : 'var(--score-amber)' }}>
            {latest?.done ? '✓' : '●'} {cat}: {latest?.message}
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 6: Update useJobStream to pass category to ProgressMessage**

In `useJobStream.ts`, update the `newMessage` construction (around line 63):

```typescript
const newMessage: ProgressMessage = {
  phase: data.phase,
  message: data.user_message,
  done: data.status === 'complete' || data.phase === 'complete',
  category: data.category,
}
```

- [ ] **Step 7: Start dev server and test manually**

```bash
./dev-services.sh start
```

Test cases:
1. Ask a recommendation query that should return labs → verify cards render with display config
2. Check that the progress stream works during a query
3. Check that historical sessions still render (backward compat)
4. Check that RecCard expanded view shows detail_rows, footer_metrics, links

- [ ] **Step 8: Commit**

```bash
git add src/frontend/
git commit -m "[RHDPCD-1953] Frontend: generic RecCard from display config, category tabs"
```

---

## Execution Notes

- **Backend tasks (1-7) must be sequential** — each builds on the previous.
- **Frontend task (8) depends on backend** — driver.serialize() must produce `display` config before the frontend can consume it.
- After all tasks, run the full test suite: `cd src/api && python -m pytest tests/ -v -m "not integration"`
- Deploy to dev and test end-to-end before considering complete.
- The `_format_single_candidate` function in rationale.py and any remaining content-type branches can be deleted in a cleanup commit after verifying everything works.
