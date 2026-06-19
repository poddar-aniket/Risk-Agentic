"""
Event Extraction Agent — turns one raw article into a structured Event.

This is the first node in the pipeline, so its output (state.structured_event)
is the contract every later agent reads from. Keep Event's schema (in
app/agents/schemas.py) authoritative — don't let other agents reach back into
raw_article once structured_event exists.
"""
from app.agents.base import BaseAgent
from app.agents.schemas import Event
from app.ingestion.base import RawArticle
from app.state import PipelineState

EXTRACTION_PROMPT_TEMPLATE = """You are an analyst for a supply-chain risk monitoring system. You are given one news article. Decide whether it describes a real-world event that could disrupt supply chains, logistics, or sourcing — for example: natural disasters, strikes or labor action, political unrest, infrastructure failures, regulatory changes, pandemics/health emergencies, or transport disruptions.

Most articles will NOT describe such an event. If this one doesn't, set is_relevant to false and fill the remaining fields with your best reasonable guess rather than leaving them ambiguous.

If it DOES describe such an event, base every field strictly on what the article itself says — do not speculate beyond it:
- event_type: the closest matching category
- locations: every specific place (city, region, port, state, country) the article says is actually affected
- severity: a 1-10 judgment of how disruptive this event is, grounded only in the scale and specificity described
- timeframe_status: ongoing, resolved, or expected, based on the article's own tense/language
- estimated_duration_days: your best estimate if the article gives any indication, otherwise leave it null
- summary: a one or two sentence plain-language summary

Article title: {title}
Article content: {content}
"""


class EventExtractionAgent(BaseAgent):
    def run(self, state: PipelineState) -> PipelineState:
        if state.raw_article is None:
            raise ValueError("EventExtractionAgent requires state.raw_article to be set before run()")

        article = RawArticle(**state.raw_article)
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(title=article.title, content=article.content)

        event: Event = self.llm_client.generate(prompt, Event)
        state.structured_event = event.model_dump()
        return state