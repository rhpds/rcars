from __future__ import annotations

import os
from dataclasses import dataclass
from pydantic_settings import BaseSettings

import structlog


def _parse_csv(val: str) -> list[str]:
    return [x.strip() for x in val.split(",") if x.strip()] if val else []


# Canonical stage ordering used for deduplication and priority across
# the codebase (database, workers, recommender).
STAGE_PRIORITY: dict[str, int] = {"prod": 0, "event": 1, "dev": 2}


class Settings(BaseSettings):
    model_config = {"env_prefix": "RCARS_", "case_sensitive": False}

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # LLM
    model: str = "claude-sonnet-4-6"
    vertex_project_id: str = ""
    cloud_ml_region: str = "us-east5"
    anthropic_api_key: str = ""
    litemaas_url: str = ""
    litemaas_api_key: str = ""

    # Scanning
    max_parallel: int = 5
    clone_dir: str = "/tmp/rcars-clones"

    # Recommender pipeline
    vector_cutoff: float = 0.55
    triage_model: str = "claude-haiku-4-5"
    triage_cutoff: int = 30
    rationale_model: str = "claude-sonnet-4-6"
    rationale_top_n: int = 5

    # Babylon K8s
    kubeconfig_path: str = ""
    agnosticv_component_namespace: str = "babylon-config"
    catalog_namespaces: list[str] = [
        "babylon-catalog-prod",
        "babylon-catalog-dev",
        "babylon-catalog-event",
    ]

    # Showroom URL variable names (OCP Helm/Operator, RHEL/VM bastion, legacy bookbag)
    showroom_url_vars: list[str] = [
        "ocp4_workload_showroom_content_git_repo",
        "showroom_git_repo",
        "bookbag_git_repo",
    ]
    showroom_ref_vars: list[str] = [
        "ocp4_workload_showroom_content_git_repo_ref",
        "ocp4_workload_showroom_content_git_ref",
        "showroom_git_ref",
    ]

    # Auth / roles
    curator_emails_str: str = ""
    admin_emails_str: str = ""
    dev_user: str = ""
    sa_allowlist_str: str = ""
    proxy_verification_secret: str = ""
    advisor_rate_limit_per_user_per_hour: int = 50

    # Content overlap
    similarity_threshold: float = 0.75
    similarity_high_threshold: float = 0.85

    # Ops
    stale_days: int = 3
    workload_scan_enabled: bool = True
    workload_scan_interval_days: int = 1

    # Reporting MCP integration
    reporting_mcp_url: str = ""
    reporting_mcp_token: str = ""
    reporting_provisions_days: int = 90
    reporting_sales_days: int = 365

    # Scheduled maintenance pipeline
    pipeline_enabled: bool = True
    pipeline_hour: int = 4
    pipeline_minute: int = 0

    def model_post_init(self, __context) -> None:
        if not self.vertex_project_id:
            self.vertex_project_id = os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID", "")
        if not self.cloud_ml_region or self.cloud_ml_region == "us-east5":
            self.cloud_ml_region = os.environ.get("CLOUD_ML_REGION", self.cloud_ml_region)
        if not self.anthropic_api_key:
            self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        if not (0 <= self.similarity_threshold <= 1):
            raise ValueError(f"similarity_threshold must be in [0, 1], got {self.similarity_threshold}")
        if not (0 <= self.similarity_high_threshold <= 1):
            raise ValueError(f"similarity_high_threshold must be in [0, 1], got {self.similarity_high_threshold}")
        if self.similarity_high_threshold < self.similarity_threshold:
            raise ValueError(f"similarity_high_threshold ({self.similarity_high_threshold}) must be >= similarity_threshold ({self.similarity_threshold})")
        if self.workload_scan_interval_days < 1:
            raise ValueError(f"workload_scan_interval_days must be positive, got {self.workload_scan_interval_days}")

    @property
    def curator_emails(self) -> list[str]:
        return _parse_csv(self.curator_emails_str)

    @property
    def admin_emails(self) -> list[str]:
        return _parse_csv(self.admin_emails_str)

    @property
    def sa_allowlist(self) -> list[str]:
        return _parse_csv(self.sa_allowlist_str)

    @property
    def use_vertex(self) -> bool:
        return bool(self.vertex_project_id)

    @property
    def use_litemaas(self) -> bool:
        return bool(self.litemaas_url and self.litemaas_api_key)

    def get_litemaas_client(self):
        if not self.use_litemaas:
            return None
        from openai import OpenAI
        return OpenAI(base_url=self.litemaas_url, api_key=self.litemaas_api_key)

    def is_curator(self, email: str) -> bool:
        return email.lower() in [e.lower() for e in self.curator_emails]

    def is_admin(self, email: str) -> bool:
        return email.lower() in [e.lower() for e in self.admin_emails]

    def get_anthropic_client(self):
        if self.vertex_project_id:
            from anthropic import AnthropicVertex
            return AnthropicVertex(project_id=self.vertex_project_id, region=self.cloud_ml_region)
        if self.anthropic_api_key:
            from anthropic import Anthropic
            return Anthropic(api_key=self.anthropic_api_key)
        return None


# ── LLM provider routing ──

_litemaas_models: set[str] | None = None
logger = structlog.get_logger(component="llm")


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    provider: str


def fetch_litemaas_models(settings: Settings) -> set[str]:
    """Query LiteMaaS /v1/models endpoint once and cache the result."""
    global _litemaas_models
    if _litemaas_models is not None:
        return _litemaas_models
    if not settings.use_litemaas:
        _litemaas_models = set()
        return _litemaas_models
    try:
        client = settings.get_litemaas_client()
        models_response = client.models.list()
        _litemaas_models = {m.id for m in models_response.data}
        logger.info("litemaas_models_loaded", models=sorted(_litemaas_models))
    except Exception as e:
        logger.warning("litemaas_models_fetch_failed", error=str(e))
        _litemaas_models = set()
    return _litemaas_models


def call_llm(
    settings: Settings,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float = 0,
    system: str | None = None,
) -> LLMResult:
    """Unified LLM call with automatic provider routing.

    LiteMaaS preferred if configured and has the model; Vertex/Anthropic as fallback.
    When system is provided, it is passed as the system prompt (Anthropic API system
    parameter, or OpenAI-style system role message for LiteMaaS).
    """
    litemaas_models = fetch_litemaas_models(settings)

    if model in litemaas_models:
        try:
            return _call_litemaas(settings, model, messages, max_tokens, temperature, system)
        except Exception as e:
            logger.warning("litemaas_call_failed, falling back to anthropic/vertex", model=model, error=str(e))

    return _call_anthropic(settings, model, messages, max_tokens, temperature, system)


def _call_litemaas(settings, model, messages, max_tokens, temperature, system=None):
    client = settings.get_litemaas_client()
    llm_messages = messages
    if system:
        llm_messages = [{"role": "system", "content": system}] + messages
    response = client.chat.completions.create(
        model=model,
        messages=llm_messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if not response.choices:
        raise RuntimeError(f"LiteMaaS returned empty choices for model {model}")
    return LLMResult(
        text=response.choices[0].message.content,
        input_tokens=response.usage.prompt_tokens if response.usage else 0,
        output_tokens=response.usage.completion_tokens if response.usage else 0,
        provider="litemaas",
    )


def _call_anthropic(settings, model, messages, max_tokens, temperature, system=None):
    client = settings.get_anthropic_client()
    if client is None:
        raise RuntimeError("No LLM provider configured (set RCARS_LITEMAAS_URL or ANTHROPIC_VERTEX_PROJECT_ID or ANTHROPIC_API_KEY)")
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=messages,
    )
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    if not response.content:
        raise RuntimeError(f"Anthropic returned empty content for model {model}")
    provider = "vertex" if settings.use_vertex else "anthropic"
    return LLMResult(
        text=response.content[0].text,
        input_tokens=getattr(response.usage, "input_tokens", 0),
        output_tokens=getattr(response.usage, "output_tokens", 0),
        provider=provider,
    )
