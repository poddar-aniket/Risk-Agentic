# app/rag/client.py

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import os


class RAGClient:
    """
    ChromaDB-backed vector store client for RiskRadar.
    Handles embedding, storing, and querying past events,
    risk assessments, decisions, outcomes, and rejections.
    """

    COLLECTION_NAMES = [
        "past_events",
        "risk_assessments",
        "decisions",
        "outcomes",
        "rejections",
        "supplier_history",
    ]

    def __init__(self, persist_directory: str = "./data/chroma_db"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_directory)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self._collections: Dict[str, chromadb.Collection] = {}
        self._init_collections()

    def _init_collections(self) -> None:
        for name in self.COLLECTION_NAMES:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )

    def _embed(self, texts: List[str]) -> List[List[float]]:
        return self.embedder.encode(texts, convert_to_numpy=True).tolist()

    def add(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ) -> None:
        if collection_name not in self._collections:
            raise ValueError(f"Unknown collection: {collection_name}")

        embeddings = self._embed(documents)
        self._collections[collection_name].add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

    def delete(
        self,
        collection_name: str,
        ids: List[str],
    ) -> None:
        if collection_name not in self._collections:
            raise ValueError(f"Unknown collection: {collection_name}")

        self._collections[collection_name].delete(ids=ids)
        
    def query(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        if collection_name not in self._collections:
            raise ValueError(f"Unknown collection: {collection_name}")

        embedding = self._embed([query_text])[0]
        results = self._collections[collection_name].query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        output = []
        for i in range(len(results["documents"][0])):
            output.append(
                {
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
            )
        return output

    def collection_count(self, collection_name: str) -> int:
        if collection_name not in self._collections:
            raise ValueError(f"Unknown collection: {collection_name}")
        return self._collections[collection_name].count()