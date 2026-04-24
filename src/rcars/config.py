"""RCARS configuration from environment variables."""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application settings, all from environment variables."""

    # Database
    database_url: str = field(
        default_factory=lambda: os.environ.get("RCARS_DATABASE_URL", "")
    )

    # LLM
    model: str = field(
        default_factory=lambda: os.environ.get("RCARS_MODEL", "claude-sonnet-4-6")
    )
    vertex_project_id: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID", "")
    )
    cloud_ml_region: str = field(
        default_factory=lambda: os.environ.get("CLOUD_ML_REGION", "us-east5")
    )
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )

    # Scanning
    max_parallel: int = field(
        default_factory=lambda: int(os.environ.get("RCARS_MAX_PARALLEL", "5"))
    )
    clone_dir: str = field(
        default_factory=lambda: os.environ.get("RCARS_CLONE_DIR", "/tmp/rcars-clones")
    )

    # Recommender pipeline
    vector_cutoff: float = field(
        default_factory=lambda: float(os.environ.get("RCARS_VECTOR_CUTOFF", "0.55"))
    )
    triage_model: str = field(
        default_factory=lambda: os.environ.get("RCARS_TRIAGE_MODEL", "claude-haiku-4-5")
    )
    triage_cutoff: int = field(
        default_factory=lambda: int(os.environ.get("RCARS_TRIAGE_CUTOFF", "30"))
    )
    rationale_model: str = field(
        default_factory=lambda: os.environ.get("RCARS_RATIONALE_MODEL", "claude-sonnet-4-6")
    )
    rationale_top_n: int = field(
        default_factory=lambda: int(os.environ.get("RCARS_RATIONALE_TOP_N", "5"))
    )

    # Babylon K8s
    kubeconfig_path: str = field(
        default_factory=lambda: os.environ.get("RCARS_KUBECONFIG", "")
    )
    agnosticv_component_namespace: str = field(
        default_factory=lambda: os.environ.get(
            "RCARS_AGNOSTICV_NAMESPACE", "babylon-config"
        )
    )

    # Catalog namespaces (always sync all stages)
    catalog_namespaces: list[str] = field(
        default_factory=lambda: [
            "babylon-catalog-prod",
            "babylon-catalog-dev",
            "babylon-catalog-event",
        ]
    )

    # Showroom URL variable names to extract from AgnosticVComponent
    showroom_url_vars: list[str] = field(
        default_factory=lambda: [
            "ocp4_workload_showroom_content_git_repo",
            "showroom_git_repo",
        ]
    )
    showroom_ref_vars: list[str] = field(
        default_factory=lambda: [
            "ocp4_workload_showroom_content_git_repo_ref",
            "showroom_git_repo_ref",
        ]
    )

    # Web UI settings
    curator_emails: list[str] = field(
        default_factory=lambda: [
            e.strip() for e in os.environ.get("RCARS_CURATOR_EMAILS", "").split(",") if e.strip()
        ]
    )
    admin_emails: list[str] = field(
        default_factory=lambda: [
            e.strip() for e in os.environ.get("RCARS_ADMIN_EMAILS", "").split(",") if e.strip()
        ]
    )
    dev_user: str = field(
        default_factory=lambda: os.environ.get("RCARS_DEV_USER", "")
    )
    stale_days: int = field(
        default_factory=lambda: int(os.environ.get("RCARS_STALE_DAYS", "3"))
    )

    @property
    def use_vertex(self) -> bool:
        """Whether to use Vertex AI (preferred) or direct Anthropic API."""
        return bool(self.vertex_project_id)

    def is_curator(self, email: str) -> bool:
        """Return True if email is in the curator list (case-insensitive)."""
        return email.lower() in {e.lower() for e in self.curator_emails}

    def is_admin(self, email: str) -> bool:
        """Return True if email is in the admin list (case-insensitive)."""
        return email.lower() in {e.lower() for e in self.admin_emails}

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
