"""
Run this locally (with a real GEMINI_API_KEY in .env) to confirm the real
Gemini call actually works end-to-end, before wiring it into the full pipeline.

Usage (from the Risk-Agentic/ root, with your venv activated):
    python scripts/manual_smoke_test.py
"""
from app.agents.event_extraction import EventExtractionAgent
from app.llm.factory import create_llm_client
from app.state import PipelineState
from app.utils.config import load_config

SAMPLE_ARTICLE = {
    "source": "manual_test",
    "title": "Cyclone forces closure of Chennai port for third consecutive day",
    "content": (
        "Operations at Chennai port remained suspended for a third day as Cyclone "
        "Mira continued to batter the Tamil Nadu coastline. Port authorities said "
        "container handling has been halted entirely, with an estimated backlog of "
        "40 vessels. Officials expect operations to resume within 4-6 days once "
        "weather conditions stabilize."
    ),
}


def main():
    config = load_config()
    llm_client = create_llm_client(config)
    agent = EventExtractionAgent(llm_client=llm_client)

    state = PipelineState(raw_article=SAMPLE_ARTICLE)
    result = agent.run(state)

    print("structured_event:")
    for key, value in result.structured_event.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
