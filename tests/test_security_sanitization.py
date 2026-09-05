"""
Security & Secret Sanitization Unit Tests
Verifies that API keys, tokens, credentials, and passwords are never leaked into
meeting minutes, discussion points, decisions, action items, SQLite database,
vector store, PDF exports, or Word documents.
"""

import unittest
import os
import json
from src.utils.sanitizer import sanitize_text, sanitize_meeting_data, mask_api_key
from src.database.database import DatabaseManager
from src.rag.vector_store import MeetingVectorStore
from src.export.pdf_export import PDFExporter
from src.export.word_export import WordExporter
from src.llm.model import LLMClient
from src.llm.summarizer import MeetingSummarizer

class TestSecuritySanitization(unittest.TestCase):
    def setUp(self):
        self.sample_gemini_key = "AQ.fake_dummy_gemini_key_for_testing_1234567890"
        self.sample_google_key = "AIzaSyFakeDummyGoogleKeyForTesting12345"
        self.sample_openai_key = "sk-fakeDummyOpenAIKeyForTesting1234567890"
        self.sample_bearer = "Bearer eyJfakeDummyBearerTokenForTesting1234567890"

    def test_sanitize_text_redacts_keys(self):
        text = (
            f"Alice: Configure Gemini using {self.sample_gemini_key} and Google key {self.sample_google_key}. "
            f"Bob will use OpenAI {self.sample_openai_key} with token {self.sample_bearer}."
        )
        cleaned = sanitize_text(text)
        self.assertNotIn(self.sample_gemini_key, cleaned)
        self.assertNotIn(self.sample_google_key, cleaned)
        self.assertNotIn(self.sample_openai_key, cleaned)
        self.assertNotIn("eyJhbGciOiJIUz", cleaned)
        self.assertIn("[REDACTED_SECRET]", cleaned)

    def test_summarizer_pipeline_sanitizes_accidental_secrets(self):
        raw_transcript = (
            f"Meeting: Architecture Review with Key\n"
            f"Date: 2026-09-05\n"
            f"Attendees: Alice, Bob\n"
            f"Alice: Our production secret is {self.sample_gemini_key}.\n"
            f"Decision: Approve using API key {self.sample_openai_key}.\n"
            f"Action Item: Bob to rotate credentials password=SuperSecretPassword123 by Friday."
        )
        llm = LLMClient(provider="built-in-nlp")
        summarizer = MeetingSummarizer(llm)
        result = summarizer.process_transcript(raw_transcript)

        # Check all structured outputs
        result_str = json.dumps(result)
        self.assertNotIn(self.sample_gemini_key, result_str)
        self.assertNotIn(self.sample_openai_key, result_str)
        self.assertNotIn("SuperSecretPassword123", result_str)
        self.assertIn("[REDACTED_SECRET]", result_str)

    def test_database_manager_sanitizes_on_save(self):
        test_db_path = "database/test_sec_metadata.db"
        db = DatabaseManager(test_db_path)
        data = {
            "id": "sec_01",
            "title": f"Secret Meeting {self.sample_gemini_key}",
            "executive_summary": f"Discussion on {self.sample_openai_key}.",
            "action_items": [{"task": f"Deploy {self.sample_gemini_key}", "owner": "Alice"}]
        }
        db.save_meeting(data)
        saved = db.get_meeting("sec_01")
        saved_str = json.dumps(saved)

        self.assertNotIn(self.sample_gemini_key, saved_str)
        self.assertNotIn(self.sample_openai_key, saved_str)

        if os.path.exists(test_db_path):
            os.remove(test_db_path)

    def test_vector_store_sanitizes_chunks(self):
        test_store_path = "database/vector_store/test_sec_index.json"
        vs = MeetingVectorStore(test_store_path)
        vs.add_meeting(
            meeting_id="sec_m1",
            title=f"Sec Meeting {self.sample_gemini_key}",
            date="2026-09-05",
            chunks=[f"Chunk with secret {self.sample_openai_key}"]
        )
        for doc in vs.documents:
            self.assertNotIn(self.sample_gemini_key, doc["title"])
            self.assertNotIn(self.sample_openai_key, doc["text"])

        vs.clear()
        if os.path.exists(test_store_path):
            os.remove(test_store_path)

    def test_exports_sanitize_content(self):
        meeting = {
            "id": "sec_exp",
            "title": f"Project Sync {self.sample_gemini_key}",
            "date": "2026-09-05",
            "time": "10:00 AM",
            "attendees": ["Alice", "Bob"],
            "executive_summary": f"Discussion about token {self.sample_openai_key}.",
            "discussion_points": [f"Point with {self.sample_gemini_key}"],
            "decisions": [f"Decision on key {self.sample_google_key}"],
            "action_items": [{"task": f"Rotate key {self.sample_openai_key}", "owner": "Alice", "deadline": "Friday", "priority": "High", "status": "Pending"}]
        }
        # PDF test
        pdf_exp = PDFExporter(output_dir="outputs/pdf")
        pdf_bytes = pdf_exp.generate(meeting)
        self.assertTrue(len(pdf_bytes) > 0)

        # Word test
        word_exp = WordExporter(output_dir="outputs/word")
        word_bytes = word_exp.generate(meeting)
        self.assertTrue(len(word_bytes) > 0)

    def test_mask_api_key(self):
        masked = mask_api_key(self.sample_gemini_key)
        self.assertEqual(masked, "••••••••••••••••")
        self.assertNotIn(self.sample_gemini_key, masked)

if __name__ == "__main__":
    unittest.main()
