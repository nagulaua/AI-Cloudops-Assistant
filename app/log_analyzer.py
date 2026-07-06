"""Extracts interesting lines from log files and hands them to the LLM."""

import re
from pathlib import Path
from typing import List

from app.llm_client import LLMClient

ERROR_PATTERNS = re.compile(
    r"\b(error|exception|fail(ed|ure)?|traceback|critical|panic|timeout|"
    r"refused|denied|5\d\d)\b",
    re.IGNORECASE,
)


def extract_notable_lines(file_path: str, max_lines: int = 200) -> List[str]:
    """Return lines that look like errors/warnings, capped at max_lines."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {file_path}")

    notable = []
    with path.open("r", errors="ignore") as f:
        for line in f:
            if ERROR_PATTERNS.search(line):
                notable.append(line.rstrip())
                if len(notable) >= max_lines:
                    break
    return notable


def analyze_log_file(file_path: str, question: str = None) -> str:
    """Extract notable lines from a log file and ask Claude to summarize
    the likely root cause and recommended next steps."""
    notable = extract_notable_lines(file_path)
    if not notable:
        return "No error/warning/exception patterns were found in this log file."

    data = "\n".join(notable)
    question = question or (
        "Summarize what's going wrong, identify the most likely root cause, "
        "and list concrete next steps an on-call engineer should take."
    )
    client = LLMClient()
    return client.analyze(
        context_label=f"{len(notable)} notable log lines extracted from {file_path}",
        data=data,
        question=question,
    )
