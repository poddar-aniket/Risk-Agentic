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
