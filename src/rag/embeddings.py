"""
Embeddings Generation Module for RAG
Generates normalized semantic vector representations for meeting text chunks.
Uses scikit-learn TF-IDF vectorizer with sublinear term frequency and n-grams
to ensure 100% offline self-contained operation with instant zero-cost retrieval.
"""

from typing import List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

class EmbeddingGenerator:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words='english',
            sublinear_tf=True
        )
        self.is_fitted = False

    def fit_transform(self, corpus: List[str]) -> np.ndarray:
        if not corpus:
            return np.zeros((0, 1))
        dense = self.vectorizer.fit_transform(corpus).toarray()
        self.is_fitted = True
        return dense

    def transform(self, texts: List[str]) -> np.ndarray:
        if not self.is_fitted:
            return self.fit_transform(texts)
        try:
            return self.vectorizer.transform(texts).toarray()
        except Exception:
            # Re-fit if vocabulary vocabulary changed
            return self.fit_transform(texts)

    def embed_query(self, query: str) -> np.ndarray:
        if not self.is_fitted:
            return np.zeros((1, 10))
        return self.vectorizer.transform([query]).toarray()
