"""
Discussion Points Extraction Module
Identifies key agenda topics and conversational points from cleaned transcripts.
"""

from typing import List
import re

class DiscussionExtractor:
    def __init__(self):
        self.skip_prefixes = (
            'date:', 'time:', 'meeting:', 'subject:', 'topic:', 'title:',
            'meeting title:', 'meeting name:', 'attendees:', 'participants:',
            'members:', 'present:', 'agenda:', 'facilitator:', 'moderator:',
            'location:', 'venue:', 'room:', 'status:', 'decision:', 'action item:'
        )

    def extract(self, text: str) -> List[str]:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        points = []
        for l in lines:
            clean_l = re.sub(r'^[#*_\-\s]+', '', l).strip()
            low = clean_l.lower()
            if any(low.startswith(k) for k in self.skip_prefixes):
                continue

            m = re.match(r'^(?:\[\d{1,2}:\d{2}(?::\d{2})?\s*(?:[AaPp][Mm])?\]\s*)?([A-Za-z\s\.\,\-\']+?):\s*(.+)$', clean_l)
            if m:
                spk = m.group(1).strip()
                stmt = m.group(2).strip()
                spk_clean = re.sub(r'\s*\([^)]*\)', '', spk).strip()
                if spk_clean.lower() in {'speaker', 'all', 'everyone'} or len(spk_clean) < 3:
                    continue
                if any(phrase in stmt.lower() for phrase in ['finalize the action items', 'meeting adjourned']):
                    continue
                if len(stmt) > 35 and not stmt.lower().startswith(('decision', 'action item', 'note:')):
                    points.append(f"{spk_clean}: {stmt}")
            elif clean_l.startswith(('-', '*', '•')) and len(clean_l) > 20:
                bullet_content = re.sub(r'^[-*•\d\.\s]+', '', clean_l).strip()
                if not any(bullet_content.lower().startswith(k) for k in self.skip_prefixes):
                    points.append(bullet_content)

        if not points:
            points = [l for l in lines if len(l) > 30 and not any(l.lower().startswith(k) for k in self.skip_prefixes)][:6]
        return points[:8]
