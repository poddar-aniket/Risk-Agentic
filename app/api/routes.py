"""
FastAPI routes — approval queue endpoints, consumed by the Next.js frontend.
"""
from app.orchestration.scheduler import run_pipeline_once, stream_pipeline
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import json
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.decision_repository import DecisionRepository
from app.db.session import get_db
from app.orchestration.execution import execute_approved_decision
from app.rag.client import RAGClient
from app.models.supplier import Supplier
from app.models.inventory import Inventory
from typing import Optional

router = APIRouter()
_rag_client = RAGClient()  # module-level: embedding model load is expensive, load once

@router.get("/health")
def health():
    return {"status": "ok"}

class RejectRequest(BaseModel):
    reason: str


class CreateSupplierRequest(BaseModel):
    name: str
    region: str
    products_supplied: str
    contact_email: Optional[str] = None
    status: str = "active"


class CreateInventoryRequest(BaseModel):
    supplier_id: int
    product: str
    stock_level: float = 0
    avg_daily_consumption: float = 0
    reorder_lead_time: int = 0
    reorder_threshold: float = 0
@router.get("/queue")
def list_queue(db: Session = Depends(get_db)):
    # The frontend expects all decisions to apply 'All / Pending / Approved / Rejected' filters locally.
    return DecisionRepository(db).list()



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
    def event_generator():
        for event in stream_pipeline():
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).all()


@router.post("/suppliers")
def create_supplier(payload: CreateSupplierRequest, db: Session = Depends(get_db)):
    supplier = Supplier(
        name=payload.name,
        region=payload.region,
        products_supplied=payload.products_supplied,
        contact_email=payload.contact_email,
        status=payload.status,
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.put("/suppliers/{supplier_id}")
def update_supplier(supplier_id: int, payload: CreateSupplierRequest, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    supplier.name = payload.name
    supplier.region = payload.region
    supplier.products_supplied = payload.products_supplied
    supplier.contact_email = payload.contact_email
    supplier.status = payload.status
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/suppliers/{supplier_id}")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    # Cascade delete associated inventory
    db.query(Inventory).filter(Inventory.supplier_id == supplier_id).delete()
    
    db.delete(supplier)
    db.commit()
    return {"ok": True}



@router.get("/inventory")
def list_inventory(db: Session = Depends(get_db)):
    return db.query(Inventory).all()


@router.post("/inventory")
def create_inventory(payload: CreateInventoryRequest, db: Session = Depends(get_db)):
    # Upsert logic: if supplier and product match, update existing.
    existing = db.query(Inventory).filter(
        Inventory.supplier_id == payload.supplier_id,
        Inventory.product == payload.product
    ).first()

    if existing:
        existing.stock_level = payload.stock_level
        existing.avg_daily_consumption = payload.avg_daily_consumption
        existing.reorder_lead_time = payload.reorder_lead_time
        existing.reorder_threshold = payload.reorder_threshold
        db.commit()
        db.refresh(existing)
        return existing

    inventory = Inventory(
        supplier_id=payload.supplier_id,
        product=payload.product,
        stock_level=payload.stock_level,
        avg_daily_consumption=payload.avg_daily_consumption,
        reorder_lead_time=payload.reorder_lead_time,
        reorder_threshold=payload.reorder_threshold,
    )
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    return inventory


@router.put("/inventory/{inventory_id}")
def update_inventory(inventory_id: int, payload: CreateInventoryRequest, db: Session = Depends(get_db)):
    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    inventory.supplier_id = payload.supplier_id
    inventory.product = payload.product
    inventory.stock_level = payload.stock_level
    inventory.avg_daily_consumption = payload.avg_daily_consumption
    inventory.reorder_lead_time = payload.reorder_lead_time
    inventory.reorder_threshold = payload.reorder_threshold
    db.commit()
    db.refresh(inventory)
    return inventory


@router.delete("/inventory/{inventory_id}")
def delete_inventory(inventory_id: int, db: Session = Depends(get_db)):
    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    db.delete(inventory)
    db.commit()
    return {"ok": True}
