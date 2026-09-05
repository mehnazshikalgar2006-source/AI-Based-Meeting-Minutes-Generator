"""
RAG Retriever Module
Retrieves relevant meeting context and generates answers with source citations.
"""

from typing import Dict, Any, List
from src.rag.vector_store import MeetingVectorStore
from src.llm.model import LLMClient
from src.llm.prompts import RAG_QA_PROMPT

class MeetingRetriever:
    def __init__(self, vector_store: MeetingVectorStore, llm_client: LLMClient):
        self.vector_store = vector_store
        self.llm = llm_client

    def answer_question(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        results = self.vector_store.search(question, top_k=top_k)
        if not results:
            return {
                "answer": "No relevant meeting records found in the database. Please generate and save meeting minutes first.",
                "sources": [],
                "confidence": 0.0
            }

        context_blocks = []
        sources = []
        avg_score = sum(r['score'] for r in results) / len(results)

        for i, res in enumerate(results):
            doc = res['document']
            sources.append({
                "meeting_title": doc['title'],
                "date": doc['date'],
                "chunk_text": doc['text'],
                "relevance_score": res['score']
            })
            context_blocks.append(f"Source [{i+1}] (Meeting: {doc['title']}, Date: {doc['date']}):\n{doc['text']}")

        full_context = "\n\n".join(context_blocks)
        prompt = RAG_QA_PROMPT.format(context=full_context, question=question)

        answer_text = self.llm.generate(prompt, temperature=0.1)

        return {
            "answer": answer_text.strip(),
            "sources": sources,
            "confidence": round(avg_score, 3)
        }
