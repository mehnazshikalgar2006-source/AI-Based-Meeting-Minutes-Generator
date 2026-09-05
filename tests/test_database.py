"""
Unit Tests for Database Module
"""

import unittest
import os
from src.database.database import DatabaseManager

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "database/test_metadata.db"
        self.db = DatabaseManager(self.test_db_path)

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_save_and_get_meeting(self):
        data = {
            "id": "meet_123",
            "title": "Faculty Sync",
            "date": "2026-09-05",
            "time": "02:00 PM",
            "attendees": ["Prof. Sarita Byagar", "Mehnaz Shikalgar"],
            "executive_summary": "Discussed academic timeline.",
            "discussion_points": ["Point A", "Point B"],
            "decisions": ["Decision 1"],
            "action_items": [
                {"task": "Prepare slides", "owner": "Mehnaz", "deadline": "Sept 12", "priority": "High", "status": "Pending"}
            ],
            "status": "Draft"
        }
        saved_id = self.db.save_meeting(data)
        self.assertEqual(saved_id, "meet_123")

        fetched = self.db.get_meeting("meet_123")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["title"], "Faculty Sync")
        self.assertEqual(len(fetched["attendees"]), 2)
        self.assertEqual(len(fetched["action_items"]), 1)

    def test_update_status(self):
        data = {"id": "meet_456", "title": "Review", "status": "Draft"}
        self.db.save_meeting(data)
        self.db.update_meeting_status("meet_456", "Approved")
        fetched = self.db.get_meeting("meet_456")
        self.assertEqual(fetched["status"], "Approved")

    def test_delete_meeting(self):
        data = {"id": "meet_789", "title": "To Delete"}
        self.db.save_meeting(data)
        self.assertIsNotNone(self.db.get_meeting("meet_789"))
        self.db.delete_meeting("meet_789")
        self.assertIsNone(self.db.get_meeting("meet_789"))

if __name__ == "__main__":
    unittest.main()
