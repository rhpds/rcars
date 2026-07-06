"""Pydantic response schemas for OpenAPI documentation.

These models describe API response shapes so FastAPI can generate
accurate Swagger/ReDoc documentation and validate responses at runtime.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Common ──────────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    status: str = Field(examples=["ok"])


class JobResponse(BaseModel):
    job_id: str = Field(description="Async job identifier for tracking progress")


class ErrorDetail(BaseModel):
    detail: str


# ── Health ──────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])


class HealthChecks(BaseModel):
    database: bool
    redis: bool


class ReadinessResponse(BaseModel):
    status: str = Field(examples=["ok", "degraded"])
    checks: HealthChecks


# ── Auth ────────────────────────────────────────────────────────────

class AuthMeResponse(BaseModel):
    email: str = Field(description="Authenticated user's email address")
    roles: list[str] = Field(description="Granted roles: user, curator, admin")


# ── Advisor ─────────────────────────────────────────────────────────

class QuerySubmitResponse(BaseModel):
    job_id: str = Field(description="Job ID; poll via /advisor/query/{job_id}/result or stream via /advisor/query/{job_id}/stream")


class QueryResultResponse(BaseModel):
    status: str = Field(description="Job status: queued, running, complete, failed")
    result: dict | None = Field(default=None, description="Recommendation results when status=complete")
    error: str | None = Field(default=None, description="Error message when status=failed")


class SessionSummary(BaseModel):
    session_id: str
    started_at: str
    turns: int


class SessionListResponse(BaseModel):
    items: list[SessionSummary]
    total: int


class SessionTurn(BaseModel):
    turn_index: int
    query: str
    result_json: dict | None = None
    chosen_ci_name: str | None = None
    created_at: str


class SessionDetailResponse(BaseModel):
    session_id: str
    turns: list[dict]


# ── Catalog ─────────────────────────────────────────────────────────

class CatalogListResponse(BaseModel):
    items: list[dict] = Field(description="Catalog items matching filters")
    total: int
    has_more: bool = False


class CatalogItemWorkload(BaseModel):
    role: str
    product_name: str | None = None
    mapped: bool


class CatalogItemResponse(BaseModel):
    """Full catalog item with analysis, tags, workloads, and reporting metrics."""
    ci_name: str
    display_name: str | None = None
    stage: str | None = None
    cloud_provider: str | None = None
    showroom_url: str | None = None
    analysis: dict | None = None
    tags: list[dict] = []
    workloads: list[dict] = []
    acl_groups: list[dict] = []
    reporting: dict | None = None

    model_config = {"extra": "allow"}


class CatalogStatsResponse(BaseModel):
    total: int = 0
    analyzed: int = 0
    with_showroom: int = 0
    stale: int = 0
    last_refreshed: str | None = None

    model_config = {"extra": "allow"}


class SimilarItem(BaseModel):
    ci_name: str
    display_name: str | None = None
    similarity: float


class SimilarItemsResponse(BaseModel):
    ci_name: str
    similar: list[dict]
    count: int


class InfraSearchResponse(BaseModel):
    items: list[dict]
    total: int


class FacetsResponse(BaseModel):
    workloads: list[str] = []
    agd_configs: list[str] = []
    cloud_providers: list[str] = []
    os_images: list[str] = []

    model_config = {"extra": "allow"}


class WorkloadMappingsResponse(BaseModel):
    mappings: list[dict]
    aliases: list[dict]


class UnmappedWorkloadsResponse(BaseModel):
    unmapped: list[dict]


class InfraStatsResponse(BaseModel):
    model_config = {"extra": "allow"}


class ContentPathResponse(BaseModel):
    status: str = Field(examples=["ok"])
    content_path: str | None = None
    job_id: str | None = None


# ── Analysis ────────────────────────────────────────────────────────

class RetirementDashboardResponse(BaseModel):
    items: list[dict] = Field(description="Retirement-scored catalog items with reporting metrics")
    total: int
    synced_at: str | None = None
    summary: dict | None = None
    window: str


class WorkflowResponse(BaseModel):
    status: str = Field(examples=["ok"])
    workflow: dict | None = None


class WorkflowGetResponse(BaseModel):
    workflow: dict | None = None


class StartRetirementResponse(BaseModel):
    status: str = Field(examples=["ok"])
    workflow: dict | None = None
    jira_key: str | None = None


class CancelWorkflowResponse(BaseModel):
    status: str = Field(examples=["ok"])
    deleted: bool


class ScanResponse(BaseModel):
    job_id: str
    enqueued: int = Field(description="Number of analysis jobs enqueued")
    unique_items: int = 0
    dedup_groups: int = 0
    ref_groups: int = 0
    sha_groups: int = 0
    sha_merged: int = 0

    model_config = {"extra": "allow"}


class RescanResponse(ScanResponse):
    marked_stale: int = 0


# ── Admin ───────────────────────────────────────────────────────────

class TokenUsageResponse(BaseModel):
    stats: dict
    recent_queries: list[dict]
    days: int


class JobListResponse(BaseModel):
    items: list[dict]
    total: int


class QueueDepths(BaseModel):
    recommend: int = 0
    analyze: int = 0
    ops: int = 0


class RunningJob(BaseModel):
    id: str
    job_type: str
    ci_name: str | None = None
    created_at: str


class WorkerHealthResponse(BaseModel):
    queue_depths: QueueDepths
    active_jobs: int
    running_jobs: list[RunningJob]
    failed_jobs_recent: int


class ScanProgressResponse(BaseModel):
    queued: int
    running: int
    complete: int
    failed: int
    total: int
    total_propagated: int = 0
    recent_complete: list[str]
    recent_failures: list[str]


class QueryHistorySession(BaseModel):
    session_id: str
    started_at: str
    turn_count: int
    turns: list[dict]


class QueryHistoryResponse(BaseModel):
    items: list[QueryHistorySession]
    total: int


class OverlapPair(BaseModel):
    ci_name_a: str
    ci_name_b: str
    similarity: float

    model_config = {"extra": "allow"}


class SimilarityThresholds(BaseModel):
    related: float
    high_overlap: float


class OverlapResponse(BaseModel):
    pairs: list[dict]
    total: int
    stats: dict | None = None
    thresholds: SimilarityThresholds


class ScheduleResponse(BaseModel):
    pipeline_enabled: bool
    pipeline_schedule: str
    last_pipeline: dict | None = None


class LlmProviderResponse(BaseModel):
    litemaas_enabled: bool
    litemaas_url: str | None = None
    litemaas_models: list[str] = []
    vertex_enabled: bool
    vertex_region: str | None = None
    vertex_models: list[str] = []
    analysis_model: str
    triage_model: str
    rationale_model: str
    scanning_model: str


class ReportingStatusResponse(BaseModel):
    configured: bool
    total: int = 0
    with_provisions: int = 0
    with_cost: int = 0
    with_sales: int = 0
    last_synced: str | None = None


# ── API Keys ───────────────────────────────────────────────────────

class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200, description="Human-readable label for the key")
    role: str = Field(default="user", pattern="^(user|curator|admin)$", description="Maximum role: user, curator, or admin")
    expires_in_days: int | None = Field(default=None, ge=1, le=365, description="Days until expiry. Null = never expires.")


class CreateApiKeyResponse(BaseModel):
    api_key: str = Field(description="Raw API key — shown exactly once, never retrievable again")
    id: int
    name: str
    role: str
    expires_at: str | None


class ApiKeyInfo(BaseModel):
    id: int
    key_prefix: str
    name: str
    created_by: str
    role: str
    created_at: str
    expires_at: str | None
    last_used_at: str | None
    is_active: bool


class ApiKeyListResponse(BaseModel):
    keys: list[ApiKeyInfo]


class RevokeApiKeyResponse(BaseModel):
    id: int
    revoked_at: str
