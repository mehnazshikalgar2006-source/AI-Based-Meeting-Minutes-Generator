"""
Persistent Vector Store for Meeting Records
Stores chunk embeddings, document metadata, and performs cosine similarity search.
"""

import os
import json
from typing import List, Dict, Any
import numpy as np
from src.rag.embeddings import EmbeddingGenerator
from src.utils.sanitizer import sanitize_text

class MeetingVectorStore:
    def __init__(self, store_path: str = "database/vector_store/index.json"):
        self.store_path = store_path
        self.embedder = EmbeddingGenerator()
        self.documents: List[Dict[str, Any]] = []
        self.embeddings: np.ndarray = np.zeros((0, 1))
        self.load()

    def add_meeting(self, meeting_id: str, title: str, date: str, chunks: List[str]):
        """Adds meeting chunks and updates embeddings, replacing any prior chunks for this meeting."""
        safe_title = sanitize_text(title)
        self.documents = [doc for doc in self.documents if doc.get("meeting_id") != meeting_id]
        for i, chunk in enumerate(chunks):
            safe_chunk = sanitize_text(chunk)
            if not safe_chunk.strip():
                continue
            self.documents.append({
                "chunk_id": f"{meeting_id}_chunk_{i}",
                "meeting_id": meeting_id,
                "title": safe_title,
                "date": date,
                "text": safe_chunk
            })
        self._rebuild_index()
        self.save()

    def delete_meeting(self, meeting_id: str):
        """Removes all chunks associated with meeting_id and rebuilds index."""
        self.documents = [doc for doc in self.documents if doc.get("meeting_id") != meeting_id]
        self._rebuild_index()
        self.save()

    def _rebuild_index(self):
        if not self.documents:
            self.embeddings = np.zeros((0, 1))
            return
        corpus = [doc["text"] for doc in self.documents]
        self.embeddings = self.embedder.fit_transform(corpus)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Finds top-k most relevant chunks using cosine similarity."""
        if not self.documents or not self.embedder.is_fitted:
            return []

        safe_query = sanitize_text(query)
        q_vec = self.embedder.embed_query(safe_query)
        if q_vec.shape[1] != self.embeddings.shape[1]:
            # Dimension mismatch safeguard
            self._rebuild_index()
            q_vec = self.embedder.embed_query(safe_query)

        # Cosine similarity
        norm_q = np.linalg.norm(q_vec)
        norm_docs = np.linalg.norm(self.embeddings, axis=1)
        # Avoid division by zero
        norm_docs[norm_docs == 0] = 1e-10
        if norm_q == 0:
            norm_q = 1e-10

        scores = np.dot(self.embeddings, q_vec.T).flatten() / (norm_docs * norm_q)

        # Sort indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            # Include results with positive relevance
            results.append({
                "score": round(max(0.0, min(1.0, score)), 4),
                "document": self.documents[idx]
            })
        return results

    def save(self):
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump({"documents": self.documents}, f, indent=2)

    def load(self):
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.documents = data.get("documents", [])
                    if self.documents:
                        self._rebuild_index()
            except Exception as e:
                print(f"Error loading vector store: {e}")
                self.documents = []

    def clear(self):
        self.documents = []
        self.embeddings = np.zeros((0, 1))
        if os.path.exists(self.store_path):
            os.remove(self.store_path)
