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

if __name__ == "__main__":
    unittest.main()
