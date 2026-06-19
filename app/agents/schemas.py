"""
Pydantic output schemas for agents. Starting this as a shared module (rather
than defining schemas inline per-agent-file) so the team has one place to
look up exactly what shape each agent's output is — important since Geo
Agent, Risk Analysis Agent, etc. all read structured_event off PipelineState
and need to know its exact fields without digging through prompt code.

Day 1 (owner: ash119821): Event, EventType, TimeframeStatus.
Later agents (Geo, Risk Analysis, Decision, Supervisor) should add their own
schemas here as they're built, following the same pattern.
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    NATURAL_DISASTER = "natural_disaster"
    STRIKE_LABOR_ACTION = "strike_labor_action"
    POLITICAL_UNREST = "political_unrest"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    REGULATORY_CHANGE = "regulatory_change"
    PANDEMIC_HEALTH = "pandemic_health"
    TRANSPORT_DISRUPTION = "transport_disruption"
    OTHER = "other"


class TimeframeStatus(str, Enum):
    ONGOING = "ongoing"
    RESOLVED = "resolved"
    EXPECTED = "expected"  # anticipated but hasn't started yet


class RiskAssessment(BaseModel):
    """Structured output of the Risk Analysis Agent."""

    risk_score: int = Field(
        ...,
        ge=1,
        le=10,
        description=(
            "Overall supply-chain risk score 1-10, grounded in the rubric: "
            "1-3 = minor/localized, low urgency; "
            "4-6 = moderate disruption, some products/routes affected; "
            "7-8 = serious, multiple suppliers or products at risk, buffer < 2 weeks; "
            "9-10 = critical, imminent stockout or major multi-region collapse."
        ),
    )
    rationale: str = Field(
        ...,
        description=(
            "Written explanation of the score, explicitly referencing: "
            "the event type and severity, which suppliers/regions are affected, "
            "days of stock remaining for affected products, "
            "historical precedent from similar past events if available."
        ),
    )
    affected_products: list[str] = Field(
        default_factory=list,
        description="Specific products at risk based on affected suppliers and regions.",
    )
    affected_supplier_names: list[str] = Field(
        default_factory=list,
        description="Names of suppliers directly impacted by this event.",
    )
    urgency: str = Field(
        ...,
        description="One of: 'low', 'medium', 'high', 'critical' — summary label for dashboard display.",
    )
    recommended_review_within_hours: int = Field(
        ...,
        description="How many hours before a human should review this — e.g. 2 for critical, 24 for low.",
    )


class ActionType(str, Enum):
    PLACE_REORDER = "place_reorder"
    FIND_ALTERNATE_SUPPLIER = "find_alternate_supplier"
    INCREASE_SAFETY_STOCK = "increase_safety_stock"
    HOLD_SUPPLIER = "hold_supplier"
    EXPEDITE_SHIPMENT = "expedite_shipment"
    MONITOR_ONLY = "monitor_only"


class SupplierImpact(BaseModel):
    """Structured output of the Supplier Agent."""

    affected_suppliers: list[dict] = Field(
        default_factory=list,
        description=(
            "List of affected supplier records, each with: id, name, region, "
            "products_supplied, status."
        ),
    )
    affected_products: list[str] = Field(
        default_factory=list,
        description="Deduplicated list of all products at risk across all affected suppliers.",
    )
    inventory_summary: list[dict] = Field(
        default_factory=list,
        description=(
            "Per-product inventory snapshot: product, supplier_name, stock_level, "
            "avg_daily_consumption, days_of_stock_remaining, reorder_lead_time, reorder_placed."
        ),
    )
    total_suppliers_affected: int = Field(
        default=0,
        description="Count of unique suppliers affected — used by Decision Agent to size response.",
    )


class DecisionProposal(BaseModel):
    """Structured output of the Decision Agent."""

    action_type: ActionType = Field(
        ...,
        description="The category of mitigation action being proposed.",
    )
    target_supplier_name: str = Field(
        ...,
        description="Name of the supplier this action targets.",
    )
    target_product: str = Field(
        ...,
        description="Specific product this action addresses.",
    )
    justification: str = Field(
        ...,
        description=(
            "Clear explanation of why this action was chosen, referencing the risk score, "
            "days of stock remaining, and any relevant historical precedent from RAG."
        ),
    )
    magnitude: str = Field(
        ...,
        description=(
            "Concrete size of the action — e.g. '500 units reorder', '2 week hold', "
            "'identify 3 alternate suppliers in Maharashtra'."
        ),
    )
    estimated_resolution_days: int = Field(
        ...,
        description="How many days this action is expected to take to resolve the risk.",
    )
    previously_rejected_options_checked: bool = Field(
        default=False,
        description="Whether RAG was queried for previously rejected options before proposing this.",
    )


class Event(BaseModel):
    """Structured output of the Event Extraction Agent."""

    is_relevant: bool = Field(
        ...,
        description=(
            "Whether this article actually describes a real-world event that "
            "could disrupt supply chains, logistics, or sourcing. Most fetched "
            "articles will NOT be relevant — set this false rather than forcing "
            "a fake classification onto unrelated news."
        ),
    )
    event_type: EventType = Field(
        ..., description="Closest matching category. Use OTHER if none fit well."
    )
    locations: list[str] = Field(
        default_factory=list,
        description="Specific place names mentioned that are actually affected: city, region, port, state, or country.",
    )
    severity: int = Field(
        ...,
        ge=1,
        le=10,
        description=(
            "1-10 judgment of how disruptive this event is, based only on the "
            "scale and specificity of impact described in the article itself "
            "— 1 is a minor localized inconvenience, 10 is a major, "
            "multi-region, long-duration disruption."
        ),
    )
    timeframe_status: TimeframeStatus = Field(
        ..., description="Whether the event is ongoing, resolved, or expected, per the article's own language."
    )
    estimated_duration_days: Optional[int] = Field(
        None, description="Best estimate if the article gives any indication of duration; otherwise null."
    )
    summary: str = Field(..., description="One or two sentence plain-language summary of what happened.")
