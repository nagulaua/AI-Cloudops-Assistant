"""Combines AWS and GCP status snapshots into one multi-cloud view."""

from app.aws_utils import full_aws_status_snapshot
from app.gcp_utils import full_gcp_status_snapshot
from app.config import settings


def full_status_snapshot() -> dict:
    """Return a combined AWS + GCP status snapshot.

    GCP checks are automatically skipped (with an explanatory message,
    not an error) if GCP_PROJECT_ID isn't set in .env, so this works fine
    for AWS-only or GCP-only setups too.
    """
    snapshot = {"aws": full_aws_status_snapshot()}
    if settings.gcp_configured():
        snapshot["gcp"] = full_gcp_status_snapshot()
    else:
        snapshot["gcp"] = {"skipped": True, "reason": "GCP_PROJECT_ID not set in .env"}
    return snapshot
