# tests/test_geo_agent.py

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from app.llm.gemini_client import GeminiClient
from app.rag.client import RAGClient
from app.agents.geo import GeoAgent
from app.state import PipelineState


def get_mock_state() -> PipelineState:
    return PipelineState(
        structured_event={
            "title": "Cyclone Michaung Approaches Andhra Pradesh Coast",
            "event_type": "natural_disaster",
            "location": "Andhra Pradesh, India",
            "severity": 7,
            "description": (
                "Cyclone Michaung is expected to make landfall near Bapatla, "
                "Andhra Pradesh with wind speeds of 100-110 kmph. Heavy rainfall "
                "forecast across coastal Andhra and parts of Tamil Nadu. "
                "Visakhapatnam and Chennai ports on high alert."
            ),
            "published_at": "2024-12-04T06:00:00Z",
        }
    )


def run_test():
    print("Starting Geo Agent integration test...\n")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    print("Initializing RAG client...")
    rag = RAGClient()

    count = rag.collection_count("past_events")
    if count == 0:
        raise RuntimeError(
            "ChromaDB is empty. Run: python app/rag/seed.py before this test."
        )
    print(f"RAG client ready. past_events collection has {count} entries.\n")

    print("Initializing Gemini client...")
    llm = GeminiClient(api_key=api_key)
    print("Gemini client ready.\n")

    print("Initializing Geo Agent...")
    agent = GeoAgent(llm_client=llm, rag_client=rag)
    print("Geo Agent ready.\n")

    state = get_mock_state()
    print("Running Geo Agent with mock event:")
    print(f"  Event: {state.structured_event['title']}")
    print(f"  Location: {state.structured_event['location']}")
    print(f"  Severity: {state.structured_event['severity']}/10\n")

    result_state = agent.run(state)
    geo_impact = result_state.affected_regions  # dict now, not the raw schema object

    print("Geo Agent output:")
    print("-" * 60)
    print(f"Geographic spread : {geo_impact['geographic_spread']}")
    print(f"Estimated duration: {geo_impact['estimated_duration_days']} days")
    print(f"Description       : {geo_impact['description']}")
    print(f"\nAffected regions:")
    for r in geo_impact["primary_regions"]:
        print(f"  - {r}")
    print(f"\nAffected routes:")
    for r in geo_impact["affected_routes"]:
        print(f"  - {r}")
    print(f"\nInfrastructure at risk:")
    for i in geo_impact["infrastructure_at_risk"]:
        print(f"  - {i}")
    print(f"\nReasoning:\n{geo_impact['reasoning']}")
    print("-" * 60)
    print("\nGeo Agent test passed.")

    return result_state  # handy if a future end-to-end test wants to chain off this


if __name__ == "__main__":
    run_test()