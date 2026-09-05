"""
Unit Tests for Embeddings, Vector Store, and RAG Retriever
"""

import unittest
import os
from src.rag.embeddings import EmbeddingGenerator
from src.rag.vector_store import MeetingVectorStore
from src.rag.retriever import MeetingRetriever
from src.llm.model import LLMClient

class TestRAG(unittest.TestCase):
    def setUp(self):
        self.test_index_path = "database/vector_store/test_unit_index.json"
        self.vs = MeetingVectorStore(self.test_index_path)
        self.llm = LLMClient(provider="built-in-nlp")
        self.retriever = MeetingRetriever(self.vs, self.llm)

    def tearDown(self):
        self.vs.clear()
        if os.path.exists(self.test_index_path):
            os.remove(self.test_index_path)

    def test_embeddings_generation(self):
        embedder = EmbeddingGenerator()
        corpus = ["Meeting discussing machine learning and natural language processing.", "Sprint planning discussion on payment gateways."]
        matrix = embedder.fit_transform(corpus)
        self.assertEqual(matrix.shape[0], 2)
        q_vec = embedder.embed_query("machine learning")
        self.assertEqual(q_vec.shape[1], matrix.shape[1])

    def test_vector_store_add_and_search(self):
        self.vs.add_meeting(
            meeting_id="m_unit_1",
            title="Database Architecture",
            date="2026-09-05",
            chunks=[
                "We finalized SQLite for storing meeting metadata and action items.",
                "The export module generates PDF and Word documents."
            ]
        )
        self.assertEqual(len(self.vs.documents), 2)

        results = self.vs.search("SQLite database metadata", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertIn("SQLite", results[0]["document"]["text"])
        self.assertTrue(results[0]["score"] > 0)

    def test_rag_answer_synthesis(self):
        self.vs.add_meeting(
            meeting_id="m_unit_2",
            title="QA Meeting",
            date="2026-09-05",
            chunks=["Priya Nair will execute the regression testing suite across iOS and Android."]
        )
        ans = self.retriever.answer_question("Who will execute regression testing?")
        self.assertTrue(len(ans["sources"]) >= 1)
        self.assertIn("Priya", ans["answer"])

if __name__ == "__main__":
    unittest.main()
