"""Thin wrapper around the Anthropic API for CloudOps-flavored prompts."""

from typing import List, Dict, Optional
from anthropic import Anthropic
from app.config import settings

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer and Cloud
Operations assistant. You help engineers understand the health of their
cloud infrastructure, triage incidents, interpret logs and metrics, and
recommend safe, specific remediation steps. When you are given structured
data (resource lists, log excerpts, alarm states), ground your answer in
that data rather than speculating. Be concise, use bullet points for
action items, and call out anything that looks urgent or risky at the
top of your answer."""


class LLMClient:
    def __init__(self):
        if not settings.anthropic_configured():
            self.client: Optional[Anthropic] = None
        else:
            self.client = Anthropic(api_key=settings.anthropic_api_key)

    def _require_client(self):
        if self.client is None:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file "
                "to enable chat and log-analysis features."
            )

    def chat(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """Send a single-turn or multi-turn chat message to Claude."""
        self._require_client()
        messages = list(history or [])
        messages.append({"role": "user", "content": message})

        response = self.client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return "".join(block.text for block in response.content if block.type == "text")

    def analyze(self, context_label: str, data: str, question: str) -> str:
        """Ask Claude to analyze a labeled chunk of structured/log data."""
        self._require_client()
        prompt = (
            f"Here is {context_label}:\n\n"
            f"```\n{data}\n```\n\n"
            f"{question}"
        )
        response = self.client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")
