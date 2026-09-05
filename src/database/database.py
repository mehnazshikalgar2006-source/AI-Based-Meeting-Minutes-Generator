"""
Database Management Module
Handles SQLite operations for storing, retrieving, updating, and querying meeting records and action items.
"""

import sqlite3
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.utils.sanitizer import sanitize_meeting_data

class DatabaseManager:
    def __init__(self, db_path: str = "database/metadata.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self):
        """Initializes database tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meetings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    date TEXT,
                    time TEXT,
                    attendees TEXT,
                    executive_summary TEXT,
                    discussion_points TEXT,
                    decisions TEXT,
                    action_items TEXT,
                    status TEXT DEFAULT 'Draft',
                    raw_transcript TEXT,
                    cleaned_transcript TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id TEXT,
                    task TEXT NOT NULL,
                    owner TEXT,
                    deadline TEXT,
                    priority TEXT DEFAULT 'Medium',
                    status TEXT DEFAULT 'Pending',
                    FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE
                )
            """)

    def save_meeting(self, data: Dict[str, Any]) -> str:
        """Saves or updates a meeting record and its individual action items."""
        # Strictly sanitize all meeting fields before persistence
        data = sanitize_meeting_data(data)
        meeting_id = data.get("id") or str(uuid.uuid4())[:8]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        title = data.get("title", "Untitled Meeting")
        date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        time = data.get("time", "")
        attendees = json.dumps(data.get("attendees", []))
        summary = data.get("executive_summary", "")
        discussion_points = json.dumps(data.get("discussion_points", []))
        decisions = json.dumps(data.get("decisions", []))
        action_items = json.dumps(data.get("action_items", []))
        status = data.get("status", "Draft")
        raw_transcript = data.get("raw_transcript", "")
        cleaned_transcript = data.get("cleaned_transcript", "")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO meetings (
                    id, title, date, time, attendees, executive_summary,
                    discussion_points, decisions, action_items, status,
                    raw_transcript, cleaned_transcript, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    date=excluded.date,
                    time=excluded.time,
                    attendees=excluded.attendees,
                    executive_summary=excluded.executive_summary,
                    discussion_points=excluded.discussion_points,
                    decisions=excluded.decisions,
                    action_items=excluded.action_items,
                    status=excluded.status,
                    raw_transcript=excluded.raw_transcript,
                    cleaned_transcript=excluded.cleaned_transcript,
                    updated_at=excluded.updated_at
            """, (
                meeting_id, title, date, time, attendees, summary,
                discussion_points, decisions, action_items, status,
                raw_transcript, cleaned_transcript, now, now
            ))

            # Synchronize individual action items table
            cursor.execute("DELETE FROM action_items WHERE meeting_id = ?", (meeting_id,))
            for item in data.get("action_items", []):
                cursor.execute("""
                    INSERT INTO action_items (meeting_id, task, owner, deadline, priority, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    meeting_id,
                    item.get("task", ""),
                    item.get("owner", "Unassigned"),
                    item.get("deadline", "TBD"),
                    item.get("priority", "Medium"),
                    item.get("status", "Pending")
                ))

        return meeting_id

    def get_meeting(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single meeting by ID with parsed JSON fields."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def list_meetings(self) -> List[Dict[str, Any]]:
        """Returns all meetings ordered by creation date descending."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def update_meeting_status(self, meeting_id: str, status: str):
        """Updates the review status of a meeting (Draft / Reviewed / Approved)."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE meetings SET status = ?, updated_at = ? WHERE id = ?", (status, now, meeting_id))

    def update_action_item_status(self, action_id: int, status: str):
        """Updates an individual action item's status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE action_items SET status = ? WHERE id = ?", (status, action_id))

    def delete_meeting(self, meeting_id: str):
        """Deletes a meeting and related action items."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM action_items WHERE meeting_id = ?", (meeting_id,))
            cursor.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))

    def get_stats(self) -> Dict[str, Any]:
        """Calculates system metrics for the dashboard."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM meetings")
            total_meetings = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM action_items WHERE status = 'Pending'")
            pending_actions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM action_items WHERE status = 'Completed'")
            completed_actions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM meetings WHERE status = 'Approved'")
            approved_meetings = cursor.fetchone()[0]

            return {
                "total_meetings": total_meetings,
                "pending_actions": pending_actions,
                "completed_actions": completed_actions,
                "approved_meetings": approved_meetings
            }

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        for key in ["attendees", "discussion_points", "decisions", "action_items"]:
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    d[key] = []
            else:
                d[key] = []
        return d
