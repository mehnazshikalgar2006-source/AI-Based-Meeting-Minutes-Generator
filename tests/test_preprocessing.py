"""
Unit Tests for Transcript Preprocessing Module
"""

import unittest
from src.preprocessing.transcript_cleaner import TranscriptCleaner

class TestTranscriptCleaner(unittest.TestCase):
    def setUp(self):
        self.cleaner = TranscriptCleaner()

    def test_clean_text_removes_fillers(self):
        raw = "Um, hello everyone, uh, we should start the meeting."
        cleaned = self.cleaner.clean_text(raw, remove_fillers=True)
        self.assertNotIn("Um", cleaned)
        self.assertNotIn("uh", cleaned)
        self.assertIn("hello everyone", cleaned)

    def test_extract_metadata_from_header(self):
        text = (
            "Meeting: Sprint Planning\n"
            "Date: 2026-09-05\n"
            "Time: 10:00 AM\n"
            "Attendees: Alice, Bob, Charlie\n"
            "Alice: Let's begin."
        )
        meta = self.cleaner.extract_metadata_from_header(text)
        self.assertEqual(meta["title"], "Sprint Planning")
        self.assertEqual(meta["date"], "2026-09-05")
        self.assertEqual(meta["time"], "10:00 AM")
        self.assertIn("Alice", meta["attendees"])
        self.assertIn("Bob", meta["attendees"])

    def test_parse_speaker_turns(self):
        text = (
            "[10:00] Alice: Welcome everyone to the sprint review.\n"
            "[10:05] Bob: The API endpoints are ready for integration."
        )
        turns = self.cleaner.parse_speaker_turns(text)
        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[0]["speaker"], "Alice")
        self.assertIn("Welcome", turns[0]["statement"])
        self.assertEqual(turns[1]["speaker"], "Bob")

    def test_chunk_transcript(self):
        long_text = "This is a sentence. " * 100
        chunks = self.cleaner.chunk_transcript(long_text, max_chars_per_chunk=200, overlap=20)
        self.assertTrue(len(chunks) > 1)

    def test_non_attendee_metadata_filtering(self):
        text = (
            "Meeting Title: Security Architecture Review\n"
            "Date: 2026-09-12\n"
            "Time: 02:00 PM\n"
            "Location: Virtual Google Meet\n"
            "Facilitator: Sarah Connor\n"
            "Attendees: John Connor, Kyle Reese\n"
            "Date: 2026-09-12\n"
            "Facilitator: Welcome everyone.\n"
            "Sarah Connor: Let's begin the review."
        )
        meta = self.cleaner.extract_metadata_from_header(text)
        self.assertEqual(meta["title"], "Security Architecture Review")
        self.assertEqual(meta["date"], "2026-09-12")
        self.assertIn("Sarah Connor", meta["attendees"])
        self.assertIn("John Connor", meta["attendees"])
        self.assertIn("Kyle Reese", meta["attendees"])
        # Ensure metadata keywords are NOT in attendees
        for banned in ["Facilitator", "Meeting Title", "Date", "Time", "Location", "Meeting"]:
            self.assertNotIn(banned, meta["attendees"])

        turns = self.cleaner.parse_speaker_turns(text)
        speakers = [t["speaker"] for t in turns]
        self.assertNotIn("Facilitator", speakers)
        self.assertNotIn("Date", speakers)
        self.assertIn("Sarah Connor", speakers)

if __name__ == "__main__":
    unittest.main()
