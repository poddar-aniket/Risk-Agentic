"""
FastAPI routes — approval queue endpoints, consumed by the Next.js frontend.
"""
from app.orchestration.scheduler import run_pipeline_once
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.decision_repository import DecisionRepository
from app.db.session import get_db
from app.orchestration.execution import execute_approved_decision
from app.rag.client import RAGClient

router = APIRouter()
_rag_client = RAGClient()  # module-level: embedding model load is expensive, load once


class RejectRequest(BaseModel):
    reason: str


@router.get("/queue")
def list_queue(db: Session = Depends(get_db)):
    # The frontend expects all decisions to apply 'All / Pending / Approved / Rejected' filters locally.
    return DecisionRepository(db).get_pending()


@router.post("/queue/{decision_id}/approve")
def approve_decision(decision_id: int, db: Session = Depends(get_db)):
    try:
        decision = DecisionRepository(db).approve(decision_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    # Stage 5: simulated execution. The approval itself has already
    # succeeded above -- a lookup miss here (e.g. LLM-proposed supplier/
    # product name not matching a real row) is logged and skipped, not
    # surfaced as a failed approval. See app/orchestration/execution.py
    # for the full action_type -> table mutation mapping and its scope.
    execution_result = execute_approved_decision(decision, db)

    return {"decision": decision, "simulated_execution": execution_result}


@router.post("/queue/{decision_id}/reject")
def reject_decision(decision_id: int, payload: RejectRequest, db: Session = Depends(get_db)):
    repo = DecisionRepository(db)
    try:
        decision = repo.reject(decision_id, payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")

    _rag_client.add(
        collection_name="rejections",
        documents=[
            f"Proposed action: {decision.action_type} on {decision.target_supplier_name} / "
            f"{decision.target_product} -- {decision.justification}. Rejected: {payload.reason}"
        ],
        metadatas=[{"decision_id": decision.id, "rejection_reason": payload.reason}],
        ids=[f"decision_{decision.id}_rejection"],
    )
    return decision

@router.post("/pipeline/run")
def trigger_pipeline():
    try:
        status = run_pipeline_once()
        if status == "skipped":
            raise HTTPException(
                status_code=400,
                detail="No new relevant articles were found in this ingestion cycle."
            )
        return {"status": "Pipeline completed successfully. New decisions added to queue."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}"
        )