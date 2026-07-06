"""AWS resource inspection helpers, built on boto3.

All functions fail soft: if credentials are missing or a call errors out,
they return a dict with an "error" key instead of raising, so the CLI/API
can keep working and report partial status.
"""

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from app.config import settings


def _session():
    kwargs = {"region_name": settings.aws_region}
    if settings.aws_profile:
        kwargs["profile_name"] = settings.aws_profile
    elif settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.Session(**kwargs)


def list_ec2_instances() -> dict:
    try:
        ec2 = _session().client("ec2")
        paginator = ec2.get_paginator("describe_instances")
        instances = []
        for page in paginator.paginate():
            for reservation in page["Reservations"]:
                for inst in reservation["Instances"]:
                    name = next(
                        (t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"),
                        "(unnamed)",
                    )
                    instances.append({
                        "id": inst["InstanceId"],
                        "name": name,
                        "state": inst["State"]["Name"],
                        "type": inst["InstanceType"],
                        "az": inst.get("Placement", {}).get("AvailabilityZone"),
                    })
        return {"instances": instances, "count": len(instances)}
    except (NoCredentialsError, ClientError, BotoCoreError) as exc:
        return {"error": str(exc)}


def list_s3_buckets() -> dict:
    try:
        s3 = _session().client("s3")
        resp = s3.list_buckets()
        buckets = [b["Name"] for b in resp.get("Buckets", [])]
        return {"buckets": buckets, "count": len(buckets)}
    except (NoCredentialsError, ClientError, BotoCoreError) as exc:
        return {"error": str(exc)}


def get_cloudwatch_alarms(state_filter: str = "ALARM") -> dict:
    """Fetch CloudWatch alarms, defaulting to only those currently firing."""
    try:
        cw = _session().client("cloudwatch")
        paginator = cw.get_paginator("describe_alarms")
        alarms = []
        for page in paginator.paginate(StateValue=state_filter):
            for alarm in page.get("MetricAlarms", []):
                alarms.append({
                    "name": alarm["AlarmName"],
                    "state": alarm["StateValue"],
                    "reason": alarm.get("StateReason"),
                    "metric": alarm.get("MetricName"),
                })
        return {"alarms": alarms, "count": len(alarms)}
    except (NoCredentialsError, ClientError, BotoCoreError) as exc:
        return {"error": str(exc)}


def full_aws_status_snapshot() -> dict:
    """One-shot snapshot combining EC2, S3, and CloudWatch alarm state."""
    return {
        "ec2": list_ec2_instances(),
        "s3": list_s3_buckets(),
        "alarms": get_cloudwatch_alarms(),
    }
