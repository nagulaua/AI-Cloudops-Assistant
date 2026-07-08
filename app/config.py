"""Centralized configuration loaded from environment variables / .env file."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env file if present (does not override real environment variables)
load_dotenv()


@dataclass
class Settings:
    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # AWS
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_profile: str = os.getenv("AWS_PROFILE", "")

    # GCP
    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "")
    google_application_credentials: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    gcp_zones: str = os.getenv("GCP_ZONES", "us-central1-a")

    # Alerting
    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")

    # API server
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    def anthropic_configured(self) -> bool:
        return bool(self.anthropic_api_key)

    def aws_configured(self) -> bool:
        # AWS is a required cloud for this project. We consider it configured
        # if an explicit profile or access-key pair is set, OR the user has
        # signaled instance-role auth by setting AWS_USE_INSTANCE_ROLE=1.
        # (We can't detect an attached IAM role directly without making a
        # call, so this is an explicit opt-in for that case.)
        if self.aws_profile:
            return True
        if self.aws_access_key_id and self.aws_secret_access_key:
            return True
        if os.getenv("AWS_USE_INSTANCE_ROLE", "").lower() in ("1", "true", "yes"):
            return True
        return False

    def gcp_configured(self) -> bool:
        # GCP is a required cloud for this project. A project ID is the one
        # thing we can't infer, so it's the signal that GCP is set up.
        # Credentials themselves can come from ADC even without
        # GOOGLE_APPLICATION_CREDENTIALS set.
        return bool(self.gcp_project_id)

    def gcp_zone_list(self) -> list:
        return [z.strip() for z in self.gcp_zones.split(",") if z.strip()]

    def require_at_least_one_cloud(self) -> None:
        """Raise a clear, actionable error if NEITHER AWS nor GCP is configured.

        At least one cloud is required for this project's status/alarm
        features - you don't need both, but you need at least one.
        """
        if not self.aws_configured() and not self.gcp_configured():
            raise RuntimeError(
                "This project requires at least one cloud to be configured "
                "(AWS, GCP, or both). Set one of:\n"
                "  - AWS: AWS_PROFILE, or AWS_ACCESS_KEY_ID + "
                "AWS_SECRET_ACCESS_KEY, or AWS_USE_INSTANCE_ROLE=1 in .env\n"
                "  - GCP: GCP_PROJECT_ID in .env"
            )


settings = Settings()
