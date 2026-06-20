"""
FastAPI routes — approval queue endpoints, consumed by the Next.js frontend.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.decision_repository import DecisionRepository
from app.db.session import get_db
from app.rag.client import RAGClient

router = APIRouter()
_rag_client = RAGClient()  # module-level: embedding model load is expensive, load once


class RejectRequest(BaseModel):
    reason: str


@router.get("/queue")
def list_queue(db: Session = Depends(get_db)):
    return DecisionRepository(db).get_pending()


@router.post("/queue/{decision_id}/approve")
def approve_decision(decision_id: int, db: Session = Depends(get_db)):
    decision = DecisionRepository(db).approve(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@router.post("/queue/{decision_id}/reject")
def reject_decision(decision_id: int, payload: RejectRequest, db: Session = Depends(get_db)):
    repo = DecisionRepository(db)
    decision = repo.reject(decision_id, payload.reason)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Per architecture: rejection reason gets written to RAG so the
    # Decision Agent avoids proposing the same rejected option again.
    _rag_client.add(
        collection_name="rejections",
        documents=[
            f"Proposed action: {decision.action_type} on {decision.target} -- "
            f"{decision.justification}. Rejected: {payload.reason}"
        ],
        metadatas=[{"decision_id": decision.id, "rejection_reason": payload.reason}],
        ids=[f"decision_{decision.id}_rejection"],
    )
    return decision