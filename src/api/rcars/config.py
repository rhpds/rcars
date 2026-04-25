from __future__ import annotations

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

    # Auth / roles — stored as comma-separated strings, parsed via methods
    curator_emails_str: str = ""
    admin_emails_str: str = ""
    dev_user: str = ""
    sa_allowlist_str: str = ""

    # Ops
    stale_days: int = 3

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
