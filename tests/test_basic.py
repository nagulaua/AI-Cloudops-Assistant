"""Basic tests that run without AWS credentials or an Anthropic API key."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.log_analyzer import extract_notable_lines
from app.config import settings


SAMPLE_LOG = os.path.join(os.path.dirname(__file__), "..", "logs_sample", "app.log")


def test_extract_notable_lines_finds_errors():
    lines = extract_notable_lines(SAMPLE_LOG)
    assert len(lines) > 0
    assert any("ERROR" in line or "CRITICAL" in line for line in lines)


def test_extract_notable_lines_missing_file():
    try:
        extract_notable_lines("/nonexistent/path.log")
        assert False, "should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_settings_load_without_crashing():
    # Should not raise even if no .env / API keys are configured.
    assert settings.aws_region  # has a default
    assert isinstance(settings.anthropic_configured(), bool)


def test_require_at_least_one_cloud_raises_when_none_configured():
    # Temporarily clear cloud config to verify the validation error fires
    # with a clear, actionable message when NEITHER cloud is configured.
    original_aws_profile = settings.aws_profile
    original_aws_key = settings.aws_access_key_id
    original_gcp_project = settings.gcp_project_id
    settings.aws_profile = ""
    settings.aws_access_key_id = ""
    settings.gcp_project_id = ""
    try:
        try:
            settings.require_at_least_one_cloud()
            assert False, "should have raised RuntimeError"
        except RuntimeError as exc:
            assert "AWS" in str(exc)
            assert "GCP" in str(exc)
    finally:
        settings.aws_profile = original_aws_profile
        settings.aws_access_key_id = original_aws_key
        settings.gcp_project_id = original_gcp_project


def test_require_at_least_one_cloud_passes_with_only_one_configured():
    # Only AWS configured, GCP not - should NOT raise (at least one is enough).
    original_aws_profile = settings.aws_profile
    original_gcp_project = settings.gcp_project_id
    settings.aws_profile = "some-profile"
    settings.gcp_project_id = ""
    try:
        settings.require_at_least_one_cloud()  # should not raise
    finally:
        settings.aws_profile = original_aws_profile
        settings.gcp_project_id = original_gcp_project
