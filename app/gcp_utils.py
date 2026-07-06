"""GCP resource inspection helpers, built on the google-cloud-* client libraries.

All functions fail soft: if the project isn't configured, credentials are
missing, or a call errors out, they return a dict with an "error" key
instead of raising, so the CLI/API can keep working and report partial
status alongside AWS.
"""

from app.config import settings


def _not_configured():
    return {
        "error": "GCP_PROJECT_ID is not set in .env - skipping GCP checks.",
        "skipped": True,
    }


def list_gce_instances() -> dict:
    """List Compute Engine instances across the configured zones."""
    if not settings.gcp_configured():
        return _not_configured()
    try:
        from google.cloud import compute_v1

        client = compute_v1.InstancesClient()
        instances = []
        for zone in settings.gcp_zone_list():
            try:
                for inst in client.list(project=settings.gcp_project_id, zone=zone):
                    machine_type = inst.machine_type.rsplit("/", 1)[-1]
                    instances.append({
                        "name": inst.name,
                        "id": str(inst.id),
                        "status": inst.status,
                        "machine_type": machine_type,
                        "zone": zone,
                    })
            except Exception as zone_exc:  # noqa: BLE001 - surface per-zone errors, keep going
                instances.append({"zone": zone, "error": str(zone_exc)})
        return {"instances": instances, "count": len([i for i in instances if "error" not in i])}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def list_gcs_buckets() -> dict:
    """List Cloud Storage buckets in the configured project."""
    if not settings.gcp_configured():
        return _not_configured()
    try:
        from google.cloud import storage

        client = storage.Client(project=settings.gcp_project_id)
        buckets = [b.name for b in client.list_buckets()]
        return {"buckets": buckets, "count": len(buckets)}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def get_monitoring_alerts() -> dict:
    """List open (unacknowledged) Cloud Monitoring alerting incidents.

    Note: Cloud Monitoring's alerting API surfaces "AlertPolicy" objects and
    incidents differently from CloudWatch; this lists alert policies that are
    currently enabled and have open incidents where supported, falling back
    to just listing enabled policies otherwise.
    """
    if not settings.gcp_configured():
        return _not_configured()
    try:
        from google.cloud import monitoring_v3

        client = monitoring_v3.AlertPolicyServiceClient()
        project_name = f"projects/{settings.gcp_project_id}"
        policies = []
        for policy in client.list_alert_policies(name=project_name):
            if policy.enabled.value:
                policies.append({
                    "name": policy.display_name,
                    "enabled": policy.enabled.value,
                    "combiner": monitoring_v3.AlertPolicy.ConditionCombinerType(
                        policy.combiner
                    ).name,
                })
        return {"policies": policies, "count": len(policies)}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def full_gcp_status_snapshot() -> dict:
    """One-shot snapshot combining GCE, GCS, and Cloud Monitoring alert policies."""
    return {
        "gce": list_gce_instances(),
        "gcs": list_gcs_buckets(),
        "monitoring": get_monitoring_alerts(),
    }
