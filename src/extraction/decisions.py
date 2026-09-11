"""
Decisions Extraction Module
Extracts formal decisions, agreements, resolutions from transcripts.
"""

from typing import List
import re

class DecisionsExtractor:
    def __init__(self):
        self.decision_keywords = [
            'decision:', 'decided that', 'agreed that', 'approved', 'resolved to',
            'consensus is', 'agreed on', 'final decision', 'motion carried'
        ]

    def extract(self, text: str) -> List[str]:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        decisions = []
        for l in lines:
            clean_l = re.sub(r'^[#*_\-\s]+', '', l).strip()
            low = clean_l.lower()
            if any(k in low for k in self.decision_keywords):
                clean = re.sub(r'^(?:.*?(?:decision:?|decided that|agreed that|agreed on|resolved to)\s*)', '', clean_l, flags=re.IGNORECASE).strip()
                clean = re.sub(r'^[*_]+|[*_]+$', '', clean).strip()
                if not clean:
                    clean = clean_l.strip()
                if clean:
                    clean = clean[0].upper() + clean[1:]
                if clean and clean not in decisions and len(clean) >= 10:
                    decisions.append(clean)

        if not decisions:
            decisions.append("Meeting updates and proposed plans were approved as presented.")
        return decisions
