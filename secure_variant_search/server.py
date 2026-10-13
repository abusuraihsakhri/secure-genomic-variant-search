"""
FastAPI REST API Server for SecureVariant-Search: Oblivious RAM (ORAM) Path Search over VCF Files.
"""
import hmac
import os
from typing import Dict, Any
from .models import FrontierPayload
from .agents import SecureVariantSearchCoordinator

coordinator = SecureVariantSearchCoordinator()


def create_app():
    try:
        from fastapi import Depends, FastAPI, Header, HTTPException
        from pydantic import BaseModel, Field

        from agents.base import PHIGuard, SecurityException

        def require_api_key(x_api_key: str = Header(default="")):
            expected = os.getenv("API_ACCESS_TOKEN", "")
            if not expected:
                raise HTTPException(status_code=503, detail="API authentication is not configured")
            if not hmac.compare_digest(x_api_key, expected):
                raise HTTPException(status_code=401, detail="Invalid or missing API key")

        app = FastAPI(
            title="SecureVariant-Search: Oblivious RAM (ORAM) Path Search over VCF Files",
            description="Implements Path ORAM access patterns over cloud-stored whole-genome VCF indices, completely hiding which genetic loci are being queried.",
            version="2.0.0-DEMO",
        )

        class TaskRequest(BaseModel):
            task_id: str = "TASK-2026-001"
            target_identifier: str = "TARGET-BIO-KEY"
            primary_metric: float = Field(default=28.5, allow_inf_nan=False)
            secondary_metric: float = Field(default=14.2, allow_inf_nan=False)
            status_descriptor: str = "DISCORDANT_ANOMALY"
            is_critical_flag: bool = True
            attributes: Dict[str, Any] = Field(default_factory=dict)

        class ChatRequest(BaseModel):
            query: str

        @app.get("/health")
        def health():
            return {"status": "HEALTHY", "system": "secure-genomic-variant-search", "domain": "Privacy-Preserving Federated Healthcare & FHE", "version": "2.0.0-FRONTIER"}

        @app.post("/api/audit", dependencies=[Depends(require_api_key)])
        def api_audit(req: TaskRequest):
            try:
                PHIGuard.assert_no_phi(req.model_dump_json())
            except SecurityException:
                raise HTTPException(status_code=422, detail="Potential sensitive identifier in request")
            payload = FrontierPayload(
                task_id=req.task_id,
                target_identifier=req.target_identifier,
                primary_metric=req.primary_metric,
                secondary_metric=req.secondary_metric,
                status_descriptor=req.status_descriptor,
                is_critical_flag=req.is_critical_flag,
                attributes=req.attributes,
            )
            return coordinator.process(payload)

        @app.post("/api/chat", dependencies=[Depends(require_api_key)])
        def api_chat(req: ChatRequest):
            try:
                PHIGuard.assert_no_phi(req.query)
            except SecurityException:
                raise HTTPException(status_code=422, detail="Potential sensitive identifier in request")
            return {"response": coordinator.query_supervisory_chat(req.query)}

        return app
    except ImportError:
        return None
