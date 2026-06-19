"""
Seed script — loads 10-15 case study records from data/seed/*.json into
ChromaDB via RAGClient before the first real pipeline run.

TODO (Day 2 — owner: poddar-aniket):
- Allocate 2+ real hours for writing realistic case studies — this is not a
  20-minute task, and weak seed data quietly weakens every downstream agent
  that queries RAG for precedent.
"""


def seed_rag() -> None:
    raise NotImplementedError("Seed RAG with case studies — Day 2")


if __name__ == "__main__":
    seed_rag()
