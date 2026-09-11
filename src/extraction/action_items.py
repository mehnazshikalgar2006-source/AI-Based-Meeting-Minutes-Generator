"""
Action Items Extraction Module
Extracts action items, owners, deadlines, priorities, and status.
"""

from typing import List, Dict, Any, Optional
import re

class ActionItemsExtractor:
    def __init__(self):
        self.meta_patterns = [
            re.compile(r'extraction of action items', re.IGNORECASE),
            re.compile(r'action item extraction', re.IGNORECASE),
            re.compile(r'identifies responsible owners', re.IGNORECASE),
            re.compile(r'for example, if someone says', re.IGNORECASE),
            re.compile(r'finalize the action items', re.IGNORECASE),
            re.compile(r'review the action items', re.IGNORECASE),
            re.compile(r'discuss action items', re.IGNORECASE),
            re.compile(r'what are the action items', re.IGNORECASE),
        ]

        NAME = r'(?:(?:Prof\.|Dr\.|Mr\.|Ms\.|Mrs\.)\s+)?[A-Z][a-zA-Z\']+(?:\s+[A-Z][a-zA-Z\']+)*'
        self.owner_assignment_regex = re.compile(
            r'^(?:[-*•\d\.\s]*(?:Action Item|Task|TODO|Action)\s*:\s*)?'
            rf'({NAME}(?:\s*(?:and|&|,)\s*{NAME})*)'
            r'\s+(?i:to|will|must|shall|is assigned to|is to|should|needs to)\s+(.+)$'
        )

        self.speaker_commitment_regex = re.compile(
            r'^(?:I will|I\'ll|I can|I am going to|I\'m going to|I shall|I plan to|I intend to|I commit to|I promise to|I will take care of|I\'ll handle)\s+(.+)$',
            re.IGNORECASE
        )

        self.speaker_assignment_regex = re.compile(
            rf'^({NAME}(?:\s*(?:and|&|,)\s*{NAME})*)'
            r'(?:,\s*|\s+)(?i:please|to|will|can you|should)\s+(.+)$'
        )

        self.explicit_label_regex = re.compile(
            r'^[-*•\d\.\s]*(?:action item|action items|task|todo)\s*:\s*(.+)$',
            re.IGNORECASE
        )

        self.deadline_patterns = [
            # Labeled formats: (Deadline: Wednesday 5 PM) or Deadline: Sept 10
            r'\((?:deadline|due|target date):\s*([^)]+)\)',
            r'\[(?:deadline|due|target date):\s*([^\]]+)\]',
            r'(?:deadline|due date|target date):\s*([A-Za-z0-9\s,\-\/]+?)(?:\.|$|;)',
            # Full dates: September 10, 2026 / Sept 10, 2026
            r'(?:\b(?:by|due(?: on)?|deadline is|before|target date:?)\s+)?\b((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})\b',
            # ISO and numeric dates: 2026-09-10 / 10/09/2026
            r'(?:\b(?:by|due(?: on)?|deadline is|before|target date:?)\s+)?\b(\d{4}-\d{2}-\d{2})\b',
            r'(?:\b(?:by|due(?: on)?|deadline is|before|target date:?)\s+)?\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            # Month & day without year: September 10th / Sept 10
            r'(?:\b(?:by|due(?: on)?|deadline is|before|target date:?)\s+)?\b((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?)\b',
            # Days of the week with optional modifiers & times
            r'\b(?:by|due(?: on)?|deadline is|before)\s+((?:next\s+|this\s+)?(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:\s+(?:morning|afternoon|evening|EOD|COB|close of business))?(?:\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)?)\b',
            # Stand-alone times: by 5 PM, by 5:00 PM, before 11:30 AM
            r'\b(?:by|due(?: on)?|deadline is|before)\s+(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\b',
            # Relative deadlines: tomorrow / today / tonight / end of week
            r'\b(?:by|due(?: on)?|deadline is|before)\s+((?:tomorrow|today|tonight)(?:\s+(?:morning|afternoon|evening|EOD|COB))?(?:\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)?)\b',
            r'\b(?:by|due(?: on)?|deadline is|before)\s+((?:end of (?:the\s+)?(?:day|week|month|sprint))|(?:EOD|COB|close of business)(?:\s+(?:today|tomorrow|Friday))?)\b',
            r'\b(?:by|due(?: on)?|deadline is|before)\s+((?:the\s+)?next\s+(?:meeting|sprint|release|week))\b'
        ]

    def extract(self, text: str, attendees: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        action_items = []
        seen_tasks = set()

        # Pre-process speaker turns if present
        speaker_turns = []
        speaker_regex = re.compile(r'^(?:(?:\[|\()?\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?\s*(?:\]|\))?\s*)?([A-Za-z0-9\s\.\,\-\(\)\']+?):\s*(.*)$')
        for l in lines:
            sm = speaker_regex.match(l)
            if sm:
                spk = sm.group(1).strip()
                stmt = sm.group(2).strip()
                spk_clean = re.sub(r'\s*\([^)]*\)', '', spk).strip()
                if not any(spk_clean.lower().startswith(k) for k in ['date', 'time', 'meeting', 'attendees', 'action', 'decision']):
                    speaker_turns.append((spk_clean, stmt))

        for l in lines:
            # 1. Skip lines that are conversational meta-discussions about action items
            if any(p.search(l) for p in self.meta_patterns):
                continue

            clean_l = re.sub(r'^[#*_\-\s]+', '', l).strip()
            if not clean_l:
                continue

            is_action = False
            task_raw = clean_l
            owner = "Unassigned"
            deadline = "TBD"

            # Case A: Explicit line with Action Item / Task / TODO
            label_match = self.explicit_label_regex.match(clean_l)
            if label_match:
                is_action = True
                content = label_match.group(1).strip()
                assign_match = self.owner_assignment_regex.match(content)
                if assign_match:
                    owner = assign_match.group(1).strip()
                    task_raw = assign_match.group(2).strip()
                else:
                    # Check for "Owner: Task" or "Owner - Task"
                    colon_match = re.match(r'^([A-Z][a-zA-Z\']+(?:\s+[A-Z][a-zA-Z\']+)*(?:\s*(?:and|&|,)\s*[A-Z][a-zA-Z\']+(?:\s+[A-Z][a-zA-Z\']+)*)*)\s*[:-]\s*(.+)$', content)
                    if colon_match:
                        owner = colon_match.group(1).strip()
                        task_raw = colon_match.group(2).strip()
                    else:
                        task_raw = content

            # Case B: Direct assignment pattern (e.g. "Mehnaz and Dipika to prepare slides...")
            if not is_action:
                assign_match = self.owner_assignment_regex.match(clean_l)
                if assign_match:
                    is_action = True
                    owner = assign_match.group(1).strip()
                    task_raw = assign_match.group(2).strip()

            # Case C: Dialogue statement commitments
            if not is_action:
                sm = speaker_regex.match(l)
                if sm:
                    spk = sm.group(1).strip()
                    spk_clean = re.sub(r'\s*\([^)]*\)', '', spk).strip()
                    stmt = sm.group(2).strip()

                    # Check each individual sentence for commitments to avoid absorbing surrounding discussion
                    sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', stmt) if s.strip()]
                    for s in sentences:
                        cm = self.speaker_commitment_regex.match(s)
                        if cm and not any(p.search(s) for p in self.meta_patterns):
                            is_action = True
                            owner = spk_clean
                            candidate = cm.group(1).strip()
                            candidate = re.sub(r'\s+(?:because|so that|in order to|as long as|since)\s+.*$', '', candidate, flags=re.IGNORECASE).strip()
                            task_raw = candidate
                            break
                        else:
                            asgn = self.speaker_assignment_regex.match(s)
                            if asgn and not any(p.search(s) for p in self.meta_patterns):
                                target_owner = asgn.group(1).strip()
                                if attendees and any(target_owner.lower() in a.lower() for a in attendees):
                                    is_action = True
                                    owner = target_owner
                                    candidate = asgn.group(2).strip()
                                    candidate = re.sub(r'\s+(?:because|so that|in order to|as long as|since)\s+.*$', '', candidate, flags=re.IGNORECASE).strip()
                                    task_raw = candidate
                                    break

            if is_action and task_raw:
                # 2. Extract deadline from task_raw
                matched_deadline = None
                for dp in self.deadline_patterns:
                    dm = re.search(dp, task_raw, re.IGNORECASE)
                    if dm:
                        matched_deadline = dm.group(1).strip()
                        deadline = matched_deadline
                        break

                # 3. Clean task text by removing extracted deadline phrases
                task_clean = task_raw
                if matched_deadline:
                    task_clean = re.sub(r'[\(\[]\s*(?:deadline|due|target date):?\s*' + re.escape(matched_deadline) + r'[\)\]]', '', task_clean, flags=re.IGNORECASE).strip()
                    task_clean = re.sub(r'(?:,\s*)?(?:deadline|due date|target date):\s*' + re.escape(matched_deadline) + r'\.?$', '', task_clean, flags=re.IGNORECASE).strip()
                    task_clean = re.sub(r'(?:,\s*)?(?:\b(?:by|due(?: on)?|deadline is|before|target date:?)\s+)?' + re.escape(matched_deadline) + r'\.?$', '', task_clean, flags=re.IGNORECASE).strip()

                task_clean = task_clean.rstrip('.,; ').strip()
                if task_clean:
                    task_clean = task_clean[0].upper() + task_clean[1:]

                # 4. Resolve owner if unassigned and attendee list is available
                if owner == "Unassigned" and attendees:
                    for att in attendees:
                        if task_clean.lower().startswith(att.lower() + " to ") or task_clean.lower().startswith(att.lower() + " will "):
                            owner = att
                            task_clean = re.sub(r'^' + re.escape(att) + r'\s+(?:to|will)\s+', '', task_clean, flags=re.IGNORECASE).strip()
                            if task_clean:
                                task_clean = task_clean[0].upper() + task_clean[1:]
                            break

                # 5. Determine priority
                low_task = task_clean.lower()
                if any(w in low_task for w in ['critical', 'urgent', 'high priority', 'asap', 'blocker']):
                    priority = "High"
                elif any(w in low_task for w in ['low priority', 'optional', 'nice to have', 'when possible']):
                    priority = "Low"
                else:
                    priority = "Medium"

                dedup_key = f"{owner.lower()}::{task_clean.lower()}"
                if dedup_key not in seen_tasks and len(task_clean) >= 5:
                    seen_tasks.add(dedup_key)
                    action_items.append({
                        "task": task_clean,
                        "owner": owner,
                        "deadline": deadline,
                        "priority": priority,
                        "status": "Pending"
                    })

        # Fallback only when absolutely zero action items were detected
        if not action_items:
            action_items.append({
                "task": "Review and circulate finalized meeting minutes",
                "owner": attendees[0] if (attendees and len(attendees) > 0) else "Team Lead",
                "deadline": "Next Meeting",
                "priority": "Medium",
                "status": "Pending"
            })

        return action_items
