"""
Unit Tests for LLM Client & Summarizer Module
"""

import unittest
import json
from src.llm.model import LLMClient
from src.llm.summarizer import MeetingSummarizer

class TestLLM(unittest.TestCase):
    def setUp(self):
        # Test built-in offline NLP engine
        self.llm = LLMClient(provider="built-in-nlp")
        self.summarizer = MeetingSummarizer(self.llm)

    def test_offline_nlp_generation(self):
        prompt = (
            "Meeting: Project Sync\n"
            "Date: 2026-09-05\n"
            "Attendees: Alice, Bob\n"
            "Alice: Let's finalize the roadmap.\n"
            "Decision: Approved roadmap.\n"
            "Action Item: Alice to update slides by Friday."
        )
        response = self.llm.generate(prompt)
        data = json.loads(response)
        self.assertIn("title", data)
        self.assertIn("executive_summary", data)
        self.assertIn("action_items", data)

    def test_summarizer_pipeline(self):
        raw = (
            "Meeting: Academic Review\n"
            "Date: 2026-09-05\n"
            "Attendees: Prof. Sarita Byagar, Mehnaz, Dipika\n"
            "Prof: Welcome to the review.\n"
            "Decision: Architecture approved.\n"
            "Action Item: Mehnaz to evaluate RAG by September 10."
        )
        minutes = self.summarizer.process_transcript(raw)
        self.assertEqual(minutes["title"], "Academic Review")
        self.assertTrue(len(minutes["action_items"]) >= 1)
        self.assertIn("cleaned_transcript", minutes)

if __name__ == "__main__":
    unittest.main()
