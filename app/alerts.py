"""Optional Slack webhook alerting."""

import requests
from app.config import settings


def send_slack_alert(message: str) -> bool:
    """Post a message to the configured Slack webhook. Returns True on success."""
    if not settings.slack_webhook_url:
        return False
    try:
        resp = requests.post(
            settings.slack_webhook_url,
            json={"text": message},
            timeout=10,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False
