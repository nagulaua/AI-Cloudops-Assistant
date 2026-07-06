"""FastAPI server exposing the CloudOps assistant over HTTP."""

import tempfile
from typing import List, Dict, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.multicloud import full_status_snapshot
from app.aws_utils import get_cloudwatch_alarms
from app.gcp_utils import get_monitoring_alerts
from app.llm_client import LLMClient
from app.log_analyzer import analyze_log_file
from app.config import settings

app = FastAPI(
    title="AI CloudOps Assistant API",
    description="Chat with Claude about your cloud environment, check resource "
                "status, and analyze logs.",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def status():
    """Return a combined AWS + GCP snapshot (EC2/S3/CloudWatch and GCE/GCS/Monitoring).
    GCP is skipped automatically if GCP_PROJECT_ID isn't configured."""
    return full_status_snapshot()


@app.get("/alarms")
def alarms(state: str = "ALARM"):
    """AWS CloudWatch alarms filtered by state (default: currently firing)."""
    return get_cloudwatch_alarms(state_filter=state)


@app.get("/gcp-alerts")
def gcp_alerts():
    """GCP Cloud Monitoring enabled alert policies."""
    if not settings.gcp_configured():
        return {"skipped": True, "reason": "GCP_PROJECT_ID not set in .env"}
    return get_monitoring_alerts()


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    client = LLMClient()
    try:
        reply = client.chat(req.message, req.history)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ChatResponse(reply=reply)


@app.post("/analyze-logs")
async def analyze_logs(file: UploadFile = File(...), question: Optional[str] = None):
    contents = await file.read()
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".log", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        result = analyze_log_file(tmp_path, question)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"analysis": result}
