"""
FastAPI routes — approval queue endpoints, consumed by the Next.js frontend.

TODO (Day 4 — owner: poddar-aniket):
- GET /queue                          -> list pending decisions + reasoning trail
- POST /queue/{id}/approve            -> mark approved; (Day 5 stretch: trigger
                                          simulated execution layer)
- POST /queue/{id}/reject             -> body: {"reason": str}; mark rejected
                                          AND write the rejection reason to RAG
                                          so the Decision Agent avoids repeating it
- CORS must be configured so the Next.js dev server can call this API.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/queue")
def list_queue():
    raise NotImplementedError("GET /queue — Day 4")


@router.post("/queue/{decision_id}/approve")
def approve_decision(decision_id: int):
    raise NotImplementedError("POST /queue/{id}/approve — Day 4")


@router.post("/queue/{decision_id}/reject")
def reject_decision(decision_id: int, reason: str):
    raise NotImplementedError("POST /queue/{id}/reject — Day 4")
