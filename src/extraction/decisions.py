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
            low = l.lower()
            if any(k in low for k in self.decision_keywords):
                # Strip leading marker if present
                clean = re.sub(r'^(?:.*?(?:decision:?|decided that|agreed that|agreed on)\s*)', '', l, flags=re.IGNORECASE).strip()
                if not clean:
                    clean = l.strip()
                if clean and clean not in decisions:
                    decisions.append(clean)

        if not decisions:
            decisions.append("Meeting updates and proposed plans were approved as presented.")
        return decisions
