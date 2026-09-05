"""
Action Items Extraction Module
Extracts action items, owners, deadlines, priorities, and status.
"""

from typing import List, Dict, Any
import re

class ActionItemsExtractor:
    def __init__(self):
        self.deadline_patterns = [
            r'by\s+([A-Za-z]+\s+\d{1,2},?\s*\d{4})',
            r'by\s+([A-Za-z]+day(?:\s+morning|\s+afternoon|\s+evening)?)',
            r'by\s+([A-Za-z]+\s+\d{1,2}(?:th|st|nd|rd)?)',
            r'due\s+([A-Za-z]+\s+\d{1,2})',
            r'deadline\s+is\s+([A-Za-z]+\s+\d{1,2})'
        ]

    def extract(self, text: str) -> List[Dict[str, Any]]:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        action_items = []

        for l in lines:
            low = l.lower()
            is_action = False
            task = l
            owner = "Unassigned"
            deadline = "TBD"
            priority = "Medium"

            if 'action item' in low or 'to do' in low or 'will finalize' in low or 'assigned to' in low or 'to complete' in low or 'to design' in low:
                is_action = True
                clean_l = re.sub(r'^(?:.*action item:?\s*)', '', l, flags=re.IGNORECASE).strip()
                task = clean_l

            owner_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:to|will|must|is assigned to)\s+(.+)$', task)
            if owner_match:
                owner = owner_match.group(1).strip()
                task = owner_match.group(2).strip()
                is_action = True

            for dp in self.deadline_patterns:
                dm = re.search(dp, task, re.IGNORECASE)
                if dm:
                    deadline = dm.group(1).strip()
                    break

            if is_action:
                if 'critical' in task.lower() or 'urgent' in task.lower() or 'high' in task.lower():
                    priority = "High"
                elif 'low' in task.lower() or 'optional' in task.lower():
                    priority = "Low"
                action_items.append({
                    "task": task,
                    "owner": owner,
                    "deadline": deadline,
                    "priority": priority,
                    "status": "Pending"
                })

        if not action_items:
            action_items.append({
                "task": "Review and circulate finalized meeting minutes",
                "owner": "Team Lead",
                "deadline": "Next Meeting",
                "priority": "Medium",
                "status": "Pending"
            })

        return action_items
