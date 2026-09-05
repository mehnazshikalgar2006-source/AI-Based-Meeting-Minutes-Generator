"""
Discussion Points Extraction Module
Identifies key agenda topics and conversational points from cleaned transcripts.
"""

from typing import List
import re

class DiscussionExtractor:
    def __init__(self):
        pass

    def extract(self, text: str) -> List[str]:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        points = []
        for l in lines:
            m = re.match(r'^(?:\[\d{1,2}:\d{2}\]\s*)?([A-Za-z\s]+?):\s*(.+)$', l)
            if m:
                spk = m.group(1).strip()
                stmt = m.group(2).strip()
                if len(stmt) > 35 and not stmt.lower().startswith(('decision', 'action item')):
                    points.append(f"{spk}: {stmt}")
            elif l.startswith(('-', '*', '•')) and len(l) > 20:
                points.append(re.sub(r'^[-*•\s]+', '', l))

        if not points:
            points = [l for l in lines if len(l) > 30][:6]
        return points[:8]
