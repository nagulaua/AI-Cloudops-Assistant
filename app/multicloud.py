"""Combines AWS and GCP status snapshots into one multi-cloud view.

At least one of AWS or GCP is required for this project - see
Settings.require_at_least_one_cloud() for the validation that enforces this.
Whichever cloud isn't configured is skipped with a clear message rather
than causing an error, as long as the other one is set up.
"""

from app.aws_utils import full_aws_status_snapshot
from app.gcp_utils import full_gcp_status_snapshot
from app.config import settings


def full_status_snapshot() -> dict:
    """Return a combined AWS + GCP status snapshot.

    Raises RuntimeError if NEITHER cloud is configured. If only one is
    configured, the other is included as a "skipped" entry rather than
    causing an error.
    """
    settings.require_at_least_one_cloud()

    snapshot = {}
    if settings.aws_configured():
        snapshot["aws"] = full_aws_status_snapshot()
    else:
        snapshot["aws"] = {"skipped": True, "reason": "AWS not configured in .env"}

    if settings.gcp_configured():
        snapshot["gcp"] = full_gcp_status_snapshot()
    else:
        snapshot["gcp"] = {"skipped": True, "reason": "GCP_PROJECT_ID not set in .env"}

    return snapshot
