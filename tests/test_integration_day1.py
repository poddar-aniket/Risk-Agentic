"""
tests/test_integration_day1.py

Integration test: NewsDataSource -> EventExtractionAgent
Fetches real articles from NewsData.io and runs the first agent in the pipeline.

Run from repo root:
    set PYTHONPATH=.
    python tests/test_integration_day1.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ── 1. Validate env vars before doing anything ─────────────────────────────
missing = [v for v in ("NEWSDATA_API_KEY", "GEMINI_API_KEY") if not os.getenv(v)]
if missing:
    print(f"[FAIL] Missing env vars: {', '.join(missing)}")
    print("       Make sure your .env is loaded and PYTHONPATH=. is set.")
    sys.exit(1)

from app.ingestion.newsdata import NewsDataSource
from app.llm.gemini_client import GeminiClient
from app.agents.event_extraction import EventExtractionAgent
from app.state import PipelineState

# ── 2. Config ──────────────────────────────────────────────────────────────
CORRECT_MODEL = "gemini-2.5-flash-lite"
MAX_ARTICLES_TO_TEST = 3   # keep low — each article = 1 Gemini call

# ── 3. Fetch articles ──────────────────────────────────────────────────────
print("\n=== STEP 1: Fetch articles from NewsData.io ===")
source = NewsDataSource(api_key=os.environ["NEWSDATA_API_KEY"])
articles = source.fetch_events()

if not articles:
    print("[FAIL] NewsDataSource returned 0 articles. Check NEWSDATA_API_KEY and quota.")
    sys.exit(1)

print(f"[OK]   Fetched {len(articles)} articles total. Testing first {MAX_ARTICLES_TO_TEST}.")

# ── 4. Wire up agent ───────────────────────────────────────────────────────
print("\n=== STEP 2: Initialise GeminiClient + EventExtractionAgent ===")
try:
    llm = GeminiClient(
        api_key=os.environ["GEMINI_API_KEY"],
        model_name=CORRECT_MODEL,   # override ash's wrong default until he patches it
    )
    agent = EventExtractionAgent(llm_client=llm)
    print(f"[OK]   GeminiClient initialised (model: {CORRECT_MODEL})")
except Exception as e:
    print(f"[FAIL] Could not initialise GeminiClient or EventExtractionAgent: {e}")
    sys.exit(1)

# ── 5. Run pipeline per article ────────────────────────────────────────────
print("\n=== STEP 3: Run EventExtractionAgent on each article ===\n")

passed = 0
failed = 0

for i, article in enumerate(articles[:MAX_ARTICLES_TO_TEST], start=1):
    print(f"--- Article {i}/{MAX_ARTICLES_TO_TEST} ---")
    print(f"    Title   : {article.title[:90]}")
    print(f"    Source  : {article.url}")

    state = PipelineState(raw_article=article.model_dump())

    try:
        updated_state = agent.run(state)
    except Exception as e:
        print(f"    [FAIL]  Agent raised exception: {e}\n")
        failed += 1
        continue

    event = updated_state.structured_event
    if event is None:
        print("    [FAIL]  structured_event is None after agent.run()\n")
        failed += 1
        continue

    required_keys = {"is_relevant", "event_type", "locations", "severity", "timeframe_status", "summary"}
    missing_keys = required_keys - set(event.keys())
    if missing_keys:
        print(f"    [FAIL]  structured_event missing keys: {missing_keys}\n")
        failed += 1
        continue

    if not (1 <= event["severity"] <= 10):
        print(f"    [FAIL]  severity out of range: {event['severity']}\n")
        failed += 1
        continue

    tag = "[RELEVANT]" if event["is_relevant"] else "[not relevant]"
    print(f"    [OK]    {tag}")
    print(f"            event_type       : {event['event_type']}")
    print(f"            severity         : {event['severity']}/10")
    print(f"            timeframe_status : {event['timeframe_status']}")
    print(f"            locations        : {event['locations']}")
    print(f"            duration_days    : {event.get('estimated_duration_days')}")
    print(f"            summary          : {event['summary'][:120]}")
    print()
    passed += 1

# ── 6. Final result ────────────────────────────────────────────────────────
print("=== RESULT ===")
print(f"    Passed : {passed}/{passed + failed}")
print(f"    Failed : {failed}/{passed + failed}")

if failed == 0:
    print("\n[INTEGRATION TEST PASSED] Day 1 pipeline is working end-to-end.")
    print("Both PRs are ready to merge into dev.\n")
    if __name__=="__main__":
        sys.exit(0)
else:
    print("\n[INTEGRATION TEST FAILED] Fix the errors above before merging PRs.\n")
    sys.exit(1)