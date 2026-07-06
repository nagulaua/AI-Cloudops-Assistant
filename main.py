#!/usr/bin/env python3
"""Entry point for the AI CloudOps Assistant CLI.

Usage:
    python main.py status
    python main.py chat
    python main.py analyze-logs path/to/file.log
    python main.py check-alarms
    python main.py serve
"""

from app.cli import cli

if __name__ == "__main__":
    cli()
