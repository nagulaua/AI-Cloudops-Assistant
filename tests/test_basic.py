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
