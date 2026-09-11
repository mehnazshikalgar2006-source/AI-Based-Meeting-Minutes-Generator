"""
Unit Tests for Information Extraction Modules
"""

import unittest
from src.extraction.action_items import ActionItemsExtractor
from src.extraction.decisions import DecisionsExtractor
from src.extraction.discussion_points import DiscussionExtractor

class TestExtraction(unittest.TestCase):
    def setUp(self):
        self.action_extractor = ActionItemsExtractor()
        self.decision_extractor = DecisionsExtractor()
        self.discussion_extractor = DiscussionExtractor()

    def test_action_item_extraction_with_owner_deadline(self):
        transcript = (
            "Alex: We need this done.\n"
            "Action Item: Sarah Chen to finish database migration by September 10, 2026."
        )
        actions = self.action_extractor.extract(transcript)
        self.assertTrue(len(actions) >= 1)
        found = False
        for a in actions:
            if "Sarah" in a.get("owner", "") or "Sarah" in a.get("task", ""):
                found = True
        self.assertTrue(found)

    def test_decision_extraction(self):
        transcript = (
            "Decision: The project architecture is approved.\n"
            "Prof: Next topic."
        )
        decisions = self.decision_extractor.extract(transcript)
        self.assertTrue(len(decisions) >= 1)
        self.assertTrue(any("architecture is approved" in d for d in decisions))

    def test_discussion_extraction(self):
        transcript = (
            "[10:00] Alice: We investigated three different vector stores including Chroma and FAISS.\n"
            "[10:05] Bob: SQLite is the best choice for storing local meeting metadata."
        )
        points = self.discussion_extractor.extract(transcript)
        self.assertTrue(len(points) >= 1)

    def test_compound_owners_and_explicit_deadlines(self):
        transcript = (
            "Action Item: Mehnaz and Dipika to prepare the project presentation slides by September 12, 2026.\n"
            "Action Item: Prof. Sarita Byagar to review the final draft by Friday 5 PM."
        )
        actions = self.action_extractor.extract(transcript)
        self.assertEqual(len(actions), 2)
        
        # Verify first action item
        self.assertEqual(actions[0]["owner"], "Mehnaz and Dipika")
        self.assertEqual(actions[0]["deadline"], "September 12, 2026")
        self.assertNotIn("September 12, 2026", actions[0]["task"])
        self.assertNotIn("Mehnaz and Dipika to", actions[0]["task"])
        
        # Verify second action item
        self.assertEqual(actions[1]["owner"], "Prof. Sarita Byagar")
        self.assertTrue("Friday" in actions[1]["deadline"])

    def test_rejection_of_conversational_meta_discussions(self):
        transcript = (
            "Mehnaz: The pipeline comprises structured extraction of action items, decisions, and discussion points.\n"
            "Prof: Let's make sure the action item extraction identifies responsible owners and strict deadlines.\n"
            "Prof: Let's finalize the action items for this week:\n"
            "Action Item: Dipika to design the PDF templates by September 8, 2026."
        )
        actions = self.action_extractor.extract(transcript)
        # Only the real action item should be extracted, conversational meta mentions discarded
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["owner"], "Dipika")
        self.assertEqual(actions[0]["deadline"], "September 8, 2026")

    def test_speaker_commitment_extraction(self):
        transcript = (
            "[10:05] Mehnaz Shikalgar: I will build the evaluation benchmark by tomorrow EOD.\n"
            "[10:10] Dipika Tupat: I will complete the export tests by Wednesday."
        )
        actions = self.action_extractor.extract(transcript)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]["owner"], "Mehnaz Shikalgar")
        self.assertTrue("tomorrow" in actions[0]["deadline"].lower())
        self.assertEqual(actions[1]["owner"], "Dipika Tupat")
        self.assertTrue("wednesday" in actions[1]["deadline"].lower())

    def test_full_pipeline_zero_placeholders(self):
        from src.llm.model import LLMClient
        from src.llm.summarizer import MeetingSummarizer

        transcript = (
            "Meeting: AI Architecture & Roadmap Sync\n"
            "Date: 2026-09-15\n"
            "Attendees: Mehnaz Shikalgar, Dipika Tupat, Prof. Sarita Byagar\n\n"
            "[10:00] Prof. Sarita Byagar: Welcome to the AI architecture review.\n"
            "Decision: Approved Streamlit and SQLite architecture.\n"
            "Action Item: Mehnaz to finalize RAG pipeline evaluation by September 18, 2026.\n"
            "Action Item: Dipika to deliver word export module by September 20, 2026.\n"
            "Action Item: Mehnaz and Dipika to prepare research report by September 22, 2026."
        )
        summarizer = MeetingSummarizer(LLMClient(provider="built-in-nlp"))
        res = summarizer.process_transcript(transcript)

        # Title checks
        self.assertEqual(res["title"], "AI Architecture & Roadmap Sync")
        self.assertNotIn(res["title"].lower(), ["meeting title", "general meeting", "untitled"])

        # Date checks
        self.assertEqual(res["date"], "2026-09-15")
        self.assertNotEqual(res["date"], "Today")

        # Attendees checks
        self.assertIn("Mehnaz Shikalgar", res["attendees"])
        self.assertIn("Dipika Tupat", res["attendees"])
        self.assertIn("Prof. Sarita Byagar", res["attendees"])
        self.assertNotIn("Facilitator", res["attendees"])
        self.assertNotIn("Person 1", res["attendees"])

        # Action items zero placeholder checks
        self.assertEqual(len(res["action_items"]), 3)
        for item in res["action_items"]:
            self.assertNotIn(item["owner"], ["Unassigned", "TBD", ""])
            self.assertNotIn(item["deadline"], ["TBD", "N/A", ""])
            self.assertTrue(len(item["task"]) >= 5)

    def test_user_commitment_and_explanatory_text_stripping(self):
        transcript = (
            "Mehnaz: I will complete the transcript processing module by Friday because the sprint ends then.\n"
            "Dipika: I promise to implement the UI layout by next Monday in order to present to the committee."
        )
        actions = self.action_extractor.extract(transcript)
        self.assertEqual(len(actions), 2)

        # First item
        self.assertEqual(actions[0]["owner"], "Mehnaz")
        self.assertEqual(actions[0]["task"], "Complete the transcript processing module")
        self.assertEqual(actions[0]["deadline"], "Friday")
        self.assertNotIn("because", actions[0]["task"].lower())

        # Second item
        self.assertEqual(actions[1]["owner"], "Dipika")
        self.assertEqual(actions[1]["task"], "Implement the UI layout")
        self.assertEqual(actions[1]["deadline"], "next Monday")
        self.assertNotIn("in order to", actions[1]["task"].lower())

    def test_discussion_extractor_ignores_metadata(self):
        transcript = (
            "Meeting: Quarterly Planning Session\n"
            "Date: 2026-09-12\n"
            "Attendees: Alice, Bob\n"
            "Facilitator: Alice\n"
            "Alice: We are migrating the database to cloud infrastructure.\n"
            "Bob: The migration timeline is estimated at two weeks.\n"
            "Meeting adjourned."
        )
        points = self.discussion_extractor.extract(transcript)
        self.assertTrue(len(points) >= 1)
        for p in points:
            self.assertNotIn("Meeting: Quarterly", p)
            self.assertNotIn("Attendees:", p)
            self.assertNotIn("Date:", p)
            self.assertNotIn("Facilitator:", p)
            self.assertNotIn("Meeting adjourned", p)

if __name__ == "__main__":
    unittest.main()
