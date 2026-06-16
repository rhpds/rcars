from __future__ import annotations

import os
from pydantic_settings import BaseSettings


def _parse_csv(val: str) -> list[str]:
    return [x.strip() for x in val.split(",") if x.strip()] if val else []


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
