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

    # LLM — LiteMaaS is the only provider (RHDPCD-2226).
    # The former Vertex/Anthropic fallback was removed on 2026-11-03: we lost
    # direct Vertex access and will not use it again. If a fallback provider
    # is ever needed, build it then.
    model: str = "claude-sonnet-5-5-a46b"
    litemaas_url: str = ""
    litemaas_api_key: str = ""

    # Scanning
    max_parallel: int = 5
    clone_dir: str = "/tmp/rcars-clones"

    # Embedding server (vLLM)
    embedding_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "nomic-ai/nomic-embed-text-v1.5"
    embedding_dim: int = 768

    # Recommender pipeline
    vector_cutoff: float = 0.55
    triage_model: str = "claude-haiku-5-5-a8b"
    triage_cutoff: int = 30
    rationale_model: str = "claude-sonnet-5-5-a46b"
    rationale_top_n: int = 5

    # Advisor chat (multi-intent)
    chat_router_model: str = ""          # empty → defaults to triage_model
    chat_answer_model: str = ""          # empty → defaults to rationale_model
    chat_intent_roles_str: str = ""
    chat_router_confidence_threshold: float = 0.6
    chat_context_turns: int = 5

    # CLI token exchange
    cli_token_expiry_hours: int = 24

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
    oauth_server_url: str = ""
    oauth_client_id: str = "rcars-api"
    oauth_client_secret: str = ""
    performance_public: bool = True

    # Controlled vocabulary (RHDPCD-507)
    # Empty → the file packaged in rcars/data/vocabulary.yaml. Ansible mounts a
    # ConfigMap at /opt/app-root/config/vocabulary.yaml and sets this so ops can
    # patch terms without an image rebuild. A change needs a rolling restart.
    vocabulary_path: str = ""

    # Content overlap
    overlap_min_products: int = 1
    overlap_min_topics: int = 2
    overlap_model: str = "claude-haiku-5-5-a8b"

    # Ops
    stale_days: int = 3
    workload_scan_enabled: bool = True
    workload_scan_interval_days: int = 1

    # Reporting MCP integration
    reporting_mcp_url: str = ""
    reporting_mcp_token: str = ""
    reporting_provisions_days: int = 90
    reporting_sales_days: int = 365

    # Jira integration (retirement tickets)
    jira_base_url: str = "https://redhat.atlassian.net"
    jira_api_email: str = ""
    jira_api_token: str = ""
    # Epic for new retirement tickets; applied only when the ticket's project matches.
    jira_retirement_parent: str = "RHDPCD-2191"

    # GitHub App (agv-retire PR creation — RHDPCD-2103)
    github_app_id: str = ""
    github_app_private_key: str = ""            # PEM contents; Ansible mounts as sealed secret
    github_app_installation_id: str = ""        # installation ID for rhpds org
    github_app_installation_id_zt_rhelbu: str = ""     # installation ID for zt-rhelbu org
    github_app_installation_id_zt_ansiblebu: str = ""  # installation ID for zt-ansiblebu org

    # Scheduled maintenance pipeline
    pipeline_enabled: bool = True
    pipeline_hour: int = 4
    pipeline_minute: int = 0

    # Portfolio Architecture ingest (RHDPCD-28)
    osspa_sync_enabled: bool = True
    osspa_palist_url: str = (
        "https://gitlab.com/osspa/osspa-site/-/raw/main/src/app/ArchitectureList/PAList.csv"
    )
    osspa_examples_repo_url: str = "https://gitlab.com/osspa/portfolio-architecture-examples.git"
    osspa_examples_ref: str = "main"
    osspa_clone_dir: str = ""             # empty → {clone_dir}/osspa-examples
    osspa_csv_fetch_timeout_s: int = 15
    osspa_clone_timeout_s: int = 60
    osspa_max_adoc_bytes: int = 200000
    osspa_retire_shrink_guard_pct: float = 0.5
    osspa_advisory_lock_id: int = 736372
    osspa_analysis_model: str = ""        # empty → falls back to settings.model

    def model_post_init(self, __context) -> None:
        if self.overlap_min_products < 0:
            raise ValueError(f"overlap_min_products must be >= 0, got {self.overlap_min_products}")
        if self.overlap_min_topics < 0:
            raise ValueError(f"overlap_min_topics must be >= 0, got {self.overlap_min_topics}")
        if self.overlap_min_products == 0 and self.overlap_min_topics == 0:
            raise ValueError("at least one overlap threshold must be greater than 0")
        if self.workload_scan_interval_days < 1:
            raise ValueError(f"workload_scan_interval_days must be positive, got {self.workload_scan_interval_days}")

        if not self.chat_router_model:
            self.chat_router_model = self.triage_model
        if not self.chat_answer_model:
            self.chat_answer_model = self.rationale_model
        if not (0 <= self.chat_router_confidence_threshold <= 1):
            raise ValueError(f"chat_router_confidence_threshold must be in [0, 1], got {self.chat_router_confidence_threshold}")
        if self.chat_context_turns < 1:
            raise ValueError(f"chat_context_turns must be >= 1, got {self.chat_context_turns}")
        for part in _parse_csv(self.chat_intent_roles_str):
            intent, sep, role = part.partition(":")
            if not sep or role.strip() not in ("any", "curator", "admin"):
                raise ValueError(f"chat_intent_roles entries must be 'intent:any|curator|admin', got {part!r}")
        if not self.osspa_analysis_model:
            self.osspa_analysis_model = self.model
        if not self.osspa_clone_dir:
            self.osspa_clone_dir = f"{self.clone_dir.rstrip('/')}/osspa-examples"
        if not 0 < self.osspa_retire_shrink_guard_pct <= 1:
            raise ValueError(
                f"osspa_retire_shrink_guard_pct must be in (0, 1], got {self.osspa_retire_shrink_guard_pct}")
        if self.osspa_max_adoc_bytes < 1024:
            raise ValueError(f"osspa_max_adoc_bytes must be >= 1024, got {self.osspa_max_adoc_bytes}")

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
    def chat_intent_roles(self) -> dict[str, str]:
        roles: dict[str, str] = {}
        for part in _parse_csv(self.chat_intent_roles_str):
            intent, _, role = part.partition(":")
            roles[intent.strip()] = role.strip()
        return roles

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
    """Single-provider LLM call: LiteMaaS only (RHDPCD-2226).

    The former Vertex/Anthropic fallback was removed on 2026-11-03 — we no
    longer have direct Vertex access and will not use it again. A model that
    is not served by LiteMaaS fails loudly instead of falling back, and
    LiteMaaS errors propagate to the caller. When system is provided, it is
    passed as an OpenAI-style system role message.
    """
    litemaas_models = fetch_litemaas_models(settings)

    if model not in litemaas_models:
        raise RuntimeError(
            f"Model {model} is not available on LiteMaaS (available: {sorted(litemaas_models)})"
        )
    return _call_litemaas(settings, model, messages, max_tokens, temperature, system)


# Models that reject the temperature parameter (Bedrock-backed Claude 5.5
# returns "temperature is deprecated for this model"). Seeded with the known
# 5.5 names so the first call is clean; any other model is added on first
# rejection.
_models_without_temperature: set[str] = {
    "claude-haiku-5-5-a8b",
    "claude-sonnet-5-5-a46b",
}


def _call_litemaas(settings, model, messages, max_tokens, temperature, system=None):
    client = settings.get_litemaas_client()
    llm_messages = messages
    if system:
        llm_messages = [{"role": "system", "content": system}] + messages
    kwargs = dict(model=model, messages=llm_messages, max_tokens=max_tokens)
    if model not in _models_without_temperature:
        kwargs["temperature"] = temperature
    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as e:
        if "temperature" not in str(e).lower() or "temperature" not in kwargs:
            raise
        # The model rejects temperature outright. Remember that and retry
        # once without it so later calls skip the parameter.
        _models_without_temperature.add(model)
        kwargs.pop("temperature")
        response = client.chat.completions.create(**kwargs)
    if not response.choices:
        raise RuntimeError(f"LiteMaaS returned empty choices for model {model}")
    return LLMResult(
        text=response.choices[0].message.content,
        input_tokens=response.usage.prompt_tokens if response.usage else 0,
        output_tokens=response.usage.completion_tokens if response.usage else 0,
        provider="litemaas",
    )
