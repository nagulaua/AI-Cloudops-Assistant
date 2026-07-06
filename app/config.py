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
        # Either explicit keys or a profile/default credential chain is fine;
        # we only warn, we never hard-fail, since boto3 can fall back to
        # instance roles, shared credentials file, etc.
        return True

    def gcp_configured(self) -> bool:
        # A project ID is the one thing we can't infer, so treat it as the
        # signal that GCP checks should be attempted. Credentials themselves
        # can come from ADC even without GOOGLE_APPLICATION_CREDENTIALS set.
        return bool(self.gcp_project_id)

    def gcp_zone_list(self) -> list:
        return [z.strip() for z in self.gcp_zones.split(",") if z.strip()]


settings = Settings()
