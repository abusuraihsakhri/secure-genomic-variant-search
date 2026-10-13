"""
FastAPI REST API Server for Secure Genomic Variant Search.
"""
import hmac
import os
from typing import Dict, Any, List
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard, SecurityException
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """Fail closed unless an API_ACCESS_TOKEN is supplied at startup."""
    expected = os.environ.get("API_ACCESS_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="API authentication is not configured")
    if not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

app = FastAPI(
    title="Secure Genomic Variant Search API",
    description="Synthetic metric auditing demonstration; no clinical or ORAM validation",
    version="3.0.1-DEMO",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "secure-genomic-variant-search", "domain": "Clinical & Biomedical AI", "standard": "Unvalidated demo rules", "version": "3.0.1-DEMO"}


@app.get("/metrics", dependencies=[Depends(require_api_key)])
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit", dependencies=[Depends(require_api_key)])
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
    except SecurityException:
        raise HTTPException(status_code=422, detail="Potential sensitive identifier in request")
    return dossier.to_dict()


@app.post("/api/chat", dependencies=[Depends(require_api_key)])
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException:
        raise HTTPException(status_code=422, detail="Potential sensitive identifier in request")


@app.get("/api/audit/logs", dependencies=[Depends(require_api_key)])
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
