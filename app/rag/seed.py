# app/rag/seed.py

import json
import os
import sys

# Ensure repo root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.rag.client import RAGClient


def load_cases(seed_path: str) -> list[dict]:
    with open(seed_path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_past_events(rag: RAGClient, cases: list[dict]) -> None:
    documents, metadatas, ids = [], [], []

    for case in cases:
        document = (
            f"{case['title']}. {case['description']} "
            f"Affected regions: {', '.join(case['affected_regions'])}. "
            f"Affected routes: {', '.join(case['affected_routes'])}."
        )
        metadata = {
            "id": case["id"],
            "event_type": case["event_type"],
            "location": case["location"],
            "severity": case["severity"],
            "days_to_resolve": case["days_to_resolve"],
            "historical_delay_days": case["historical_delay_days"],
        }
        documents.append(document)
        metadatas.append(metadata)
        ids.append(f"event_{case['id']}")

    rag.add("past_events", documents, metadatas, ids)
    print(f"   Seeded {len(documents)} past events")


def seed_risk_assessments(rag: RAGClient, cases: list[dict]) -> None:
    documents, metadatas, ids = [], [], []

    for case in cases:
        document = (
            f"Event: {case['title']}. "
            f"Risk score: {case['risk_score']}/10. "
            f"Rationale: {case['risk_rationale']} "
            f"Supplier impact: {case['supplier_impact']}"
        )
        metadata = {
            "id": case["id"],
            "event_type": case["event_type"],
            "risk_score": case["risk_score"],
            "location": case["location"],
            "severity": case["severity"],
        }
        documents.append(document)
        metadatas.append(metadata)
        ids.append(f"risk_{case['id']}")

    rag.add("risk_assessments", documents, metadatas, ids)
    print(f"   Seeded {len(documents)} risk assessments")


def seed_decisions(rag: RAGClient, cases: list[dict]) -> None:
    documents, metadatas, ids = [], [], []

    for case in cases:
        document = (
            f"Event: {case['title']}. "
            f"Decision taken: {case['decision_taken']}. "
            f"Outcome: {case['outcome']}"
        )
        metadata = {
            "id": case["id"],
            "event_type": case["event_type"],
            "risk_score": case["risk_score"],
            "location": case["location"],
            "days_to_resolve": case["days_to_resolve"],
        }
        documents.append(document)
        metadatas.append(metadata)
        ids.append(f"decision_{case['id']}")

    rag.add("decisions", documents, metadatas, ids)
    print(f"   Seeded {len(documents)} decisions")


def seed_outcomes(rag: RAGClient, cases: list[dict]) -> None:
    documents, metadatas, ids = [], [], []

    for case in cases:
        document = (
            f"Event: {case['title']}. "
            f"Action taken: {case['decision_taken']}. "
            f"Result: {case['outcome']}. "
            f"Resolved in {case['days_to_resolve']} days. "
            f"Historical delay: {case['historical_delay_days']} days."
        )
        metadata = {
            "id": case["id"],
            "event_type": case["event_type"],
            "risk_score": case["risk_score"],
            "days_to_resolve": case["days_to_resolve"],
            "historical_delay_days": case["historical_delay_days"],
        }
        documents.append(document)
        metadatas.append(metadata)
        ids.append(f"outcome_{case['id']}")

    rag.add("outcomes", documents, metadatas, ids)
    print(f"   Seeded {len(documents)} outcomes")


def seed_rejections(rag: RAGClient, cases: list[dict]) -> None:
    documents, metadatas, ids = [], [], []

    rejection_cases = [c for c in cases if c.get("rejection_reason")]

    for case in rejection_cases:
        document = (
            f"Event type: {case['event_type']}. "
            f"Location: {case['location']}. "
            f"Proposed action: {case['decision_taken']}. "
            f"Rejection reason: {case['rejection_reason']}"
        )
        metadata = {
            "id": case["id"],
            "event_type": case["event_type"],
            "risk_score": case["risk_score"],
            "rejection_reason": case["rejection_reason"],
        }
        documents.append(document)
        metadatas.append(metadata)
        ids.append(f"rejection_{case['id']}")

    rag.add("rejections", documents, metadatas, ids)
    print(f"   Seeded {len(documents)} rejections")


def seed_supplier_history(rag: RAGClient, cases: list[dict]) -> None:
    documents, metadatas, ids = [], [], []

    for case in cases:
        document = (
            f"Disruption: {case['title']} in {case['location']}. "
            f"Supplier impact: {case['supplier_impact']}. "
            f"Event type: {case['event_type']}. "
            f"Severity: {case['severity']}/10."
        )
        metadata = {
            "id": case["id"],
            "event_type": case["event_type"],
            "location": case["location"],
            "severity": case["severity"],
            "historical_delay_days": case["historical_delay_days"],
        }
        documents.append(document)
        metadatas.append(metadata)
        ids.append(f"supplier_history_{case['id']}")

    rag.add("supplier_history", documents, metadatas, ids)
    print(f"   Seeded {len(documents)} supplier history entries")


def already_seeded(rag: RAGClient) -> bool:
    return rag.collection_count("past_events") > 0


def run_seed(seed_path: str = "data/seed/cases.json") -> None:
    print(" Starting RAG seed process...")

    rag = RAGClient()

    if already_seeded(rag):
        print("  ChromaDB already contains data. Skipping seed to avoid duplicates.")
        print("   To re-seed, delete the data/chroma_db folder and run again.")
        return

    cases = load_cases(seed_path)
    print(f" Loaded {len(cases)} cases from {seed_path}\n")

    seed_past_events(rag, cases)
    seed_risk_assessments(rag, cases)
    seed_decisions(rag, cases)
    seed_outcomes(rag, cases)
    seed_rejections(rag, cases)
    seed_supplier_history(rag, cases)

    print(f"\n Seeding complete. ChromaDB populated at ./data/chroma_db")


if __name__ == "__main__":
    run_seed()