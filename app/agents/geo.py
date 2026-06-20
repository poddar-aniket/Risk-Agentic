# app/agents/geo.py — corrected

from pydantic import BaseModel, Field
from typing import List
from app.agents.base import BaseAgent
from app.llm.base import LLMClient
from app.rag.client import RAGClient
from app.state import PipelineState


class GeoImpactSchema(BaseModel):
    primary_regions: List[str] = Field(
        description="List of geographic regions directly or indirectly affected by the event."
    )
    affected_routes: List[str] = Field(
        description="List of transport routes, highways, ports, or logistics corridors disrupted."
    )
    infrastructure_at_risk: List[str] = Field(
        description="Specific infrastructure elements at risk: ports, warehouses, road segments, airports."
    )
    geographic_spread: str = Field(
        description="One of: local, regional, national, international. Describes how wide the disruption spreads."
    )
    estimated_duration_days: int = Field(
        description="LLM-reasoned estimate of how many days the geographic disruption is likely to last."
    )
    description: str = Field(
        description="One or two sentence human-readable summary of the overall geographic impact, for use in downstream prompts."
    )
    reasoning: str = Field(
        description="Step-by-step reasoning explaining how the event causes each geographic impact identified."
    )


class GeoAgent(BaseAgent):
    """
    Geo Agent: given a structured event, reasons about which regions,
    transport routes, and infrastructure are affected.
    All reasoning is done by the LLM - no hardcoded radius or distance rules.
    Uses RAG to ground estimates in historical similar disruptions.
    """

    def __init__(self, llm_client: LLMClient, rag_client: RAGClient):
        super().__init__(llm_client)
        self.rag_client = rag_client

    def _fetch_similar_geo_cases(self, event_description: str) -> str:
        results = self.rag_client.query(
            collection_name="past_events",
            query_text=event_description,
            top_k=3,
        )
        if not results:
            return "No similar historical cases found."

        formatted = []
        for i, r in enumerate(results, 1):
            meta = r["metadata"]
            formatted.append(
                f"Case {i}:\n"
                f"  Description: {r['document']}\n"
                f"  Event type: {meta.get('event_type', 'unknown')}\n"
                f"  Location: {meta.get('location', 'unknown')}\n"
                f"  Severity: {meta.get('severity', 'unknown')}/10\n"
                f"  Historical delay: {meta.get('historical_delay_days', 'unknown')} days\n"
                f"  Resolved in: {meta.get('days_to_resolve', 'unknown')} days"
            )
        return "\n\n".join(formatted)

    def _build_prompt(self, event: dict, similar_cases: str) -> str:
        return f"""You are a supply chain geography analyst for an India-focused retail company.

Your task is to analyze a supply chain disruption event and reason about its geographic impact:
which regions are affected, which transport routes and logistics corridors are disrupted,
which infrastructure is at risk, and how long the disruption is likely to last.

You must reason carefully from the event details. Do not apply hardcoded rules.
Think step by step about how this specific event causes geographic disruption.

EVENT DETAILS:
- Type: {event.get('event_type', 'Unknown')}
- Locations: {', '.join(event.get('locations', [])) or 'Unknown'}
- Severity: {event.get('severity', 'Unknown')}/10
- Timeframe: {event.get('timeframe_status', 'Unknown')}
- Estimated duration: {event.get('estimated_duration_days', 'Unknown')} days
- Summary: {event.get('summary', 'Unknown')}

SIMILAR HISTORICAL CASES FROM MEMORY:
{similar_cases}

INSTRUCTIONS:
1. 1. Identify all geographic regions that will be directly or indirectly affected.
   Report regions at the MOST SPECIFIC level the evidence supports — prefer
   naming specific states/cities (e.g. "Tamil Nadu", "Chennai") over broad
   national-level labels like "India". Only use a country-level label if the
   disruption genuinely has no narrower identifiable scope (e.g. a nationwide
   regulatory change). Consider: the epicenter, downstream logistics hubs,
   connecting corridors, and alternate route availability — but list each
   specifically, don't collapse them into one broad region.

2. Identify all transport routes and logistics corridors disrupted. Be specific:
   name highways (e.g. NH44), ports (e.g. JNPT, Vizag), rail corridors, or
   air cargo hubs where relevant.

3. Identify infrastructure at risk: specific ports, warehouses, road segments,
   bridges, airports, or industrial zones.

4. Classify the geographic spread: local (city-level), regional (state/multi-state),
   national (pan-India), or international (cross-border).

5. Estimate how many days the geographic disruption is likely to last, grounded
   in the historical cases above. If no similar case exists, reason from the
   event type and severity.

6. Write a one to two sentence human-readable summary of the overall impact
   (this will be shown to downstream agents and on the dashboard).

7. Write clear step-by-step reasoning explaining each impact you identified.

Ground your analysis in the historical cases provided. Where historical data
exists, reference it explicitly in your reasoning.
"""

    def run(self, state: PipelineState) -> PipelineState:
        if state.structured_event is None:
            raise ValueError("GeoAgent requires state.structured_event")

        event_dict = state.structured_event

        query_text = (
            f"{event_dict.get('title', '')} "
            f"{event_dict.get('event_type', '')} "
            f"{event_dict.get('location', '')} "
            f"{event_dict.get('description', '')}"
        )
        similar_cases = self._fetch_similar_geo_cases(query_text)
        prompt = self._build_prompt(event_dict, similar_cases)

        geo_impact: GeoImpactSchema = self.llm_client.generate(
            prompt=prompt,
            output_schema=GeoImpactSchema,
        )

        state.affected_regions = geo_impact.model_dump(mode="json")
        return state