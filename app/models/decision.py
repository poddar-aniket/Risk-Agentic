from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, JSON
from sqlalchemy.sql import func

from app.db.session import Base


class Decision(Base):
    """Mirrors DecisionProposal + SupervisorFeedback (app/agents/schemas.py),
    plus the HITL outcome. Finalized Day 4 against the real schemas."""

    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)

    # --- Decision Agent output (DecisionProposal) ---
    action_type = Column(String, nullable=False)
    target_supplier_name = Column(String, nullable=False)
    target_product = Column(String, nullable=False)
    justification = Column(Text, nullable=False)
    magnitude = Column(String, nullable=False)
    estimated_resolution_days = Column(Integer, nullable=False)
    previously_rejected_options_checked = Column(Boolean, default=False)

    # --- Supervisor Agent output (SupervisorFeedback) ---
    confidence_score = Column(Float, nullable=False)
    supervisor_approved = Column(Boolean, nullable=False)
    critique = Column(Text, nullable=True)
    suggested_revision = Column(Text, nullable=True)
    proportionality_check = Column(String, nullable=True)

    # --- HITL outcome (separate from supervisor_approved above) ---
    status = Column(String, default="pending")  # "pending" | "approved" | "rejected"
    rejection_reason = Column(Text, nullable=True)

    # --- Full pipeline state fields ---
    structured_event = Column(JSON, nullable=True)
    affected_regions = Column(JSON, nullable=True)
    risk_assessment = Column(JSON, nullable=True)
    supplier_impact = Column(JSON, nullable=True)
    decision_proposal = Column(JSON, nullable=True)
    supervisor_feedback = Column(JSON, nullable=True)
    iteration_count = Column(Integer, default=1)
    hitl_framing = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now())