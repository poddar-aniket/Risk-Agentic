"""
RAGClient — ChromaDB wrapper. Called directly from agent code (no LangChain
RAG chains) so it's clear exactly what context each agent receives.

TODO (Day 2 — owner: poddar-aniket):
- Initialize a persistent ChromaDB client + collection at `persist_directory`.
- Use sentence-transformers (all-MiniLM-L6-v2, local, free) for embeddings.
- Implement add() for seeding/storing new records (events, risk assessments,
  decisions, outcomes, human rejections + reasons, supplier history).
- Implement query(top_k) for retrieval.
- IMPORTANT: ash119821's Risk Analysis Agent depends on this interface —
  agree on its method signatures by 11am Day 2, before either of you is
  deep into your own piece.
"""


class RAGClient:
    def __init__(self, persist_directory: str = "./data/chroma"):
        self.persist_directory = persist_directory

    def add(self, documents: list[str], metadatas: list[dict], ids: list[str]) -> None:
        raise NotImplementedError("Wire up ChromaDB add — Day 2")

    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        raise NotImplementedError("Wire up ChromaDB query — Day 2")
