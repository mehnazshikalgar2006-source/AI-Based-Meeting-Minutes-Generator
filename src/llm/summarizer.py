"""
Meeting Summarizer Pipeline
Coordinates preprocessing, LLM extraction, and deterministic validation to return structured minutes.
"""

import json
import re
from typing import Dict, Any, List
from src.preprocessing.transcript_cleaner import TranscriptCleaner
from src.extraction.action_items import ActionItemsExtractor
from src.extraction.decisions import DecisionsExtractor
from src.llm.model import LLMClient
from src.llm.prompts import SYSTEM_PROMPT, EXTRACTION_PROMPT
from src.utils.sanitizer import sanitize_meeting_data, sanitize_text

GENERIC_TITLES = {
    'general meeting', 'meeting title', 'meeting minutes', 'untitled',
    'title', 'meeting title or subject', '<actual meeting title>', 'tbd', ''
}
GENERIC_DATES = {
    'today', 'tbd', 'n/a', 'yyyy-mm-dd or string date if mentioned, else today',
    '<actual date or today>', ''
}
PLACEHOLDER_NAMES = {
    'person 1', 'person 2', 'person 3', 'facilitator', 'team members',
    'speaker', 'attendees', 'participants', 'everyone', 'all',
    '<name 1>', '<name 2>', 'unassigned', 'tbd'
}

class MeetingSummarizer:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.cleaner = TranscriptCleaner()
        self.action_extractor = ActionItemsExtractor()
        self.decision_extractor = DecisionsExtractor()

    def process_transcript(self, raw_text: str) -> Dict[str, Any]:
        # 1. Clean and sanitize transcript input
        safe_raw_text = sanitize_text(raw_text)
        cleaned_text = self.cleaner.clean_text(safe_raw_text)
        meta = self.cleaner.extract_metadata_from_header(safe_raw_text)
        turns = self.cleaner.parse_speaker_turns(safe_raw_text)

        # 2. Call LLM for extraction
        prompt = EXTRACTION_PROMPT.format(transcript=cleaned_text)
        response_text = self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT, temperature=0.2)

        # 3. Parse JSON output
        data = self._clean_and_parse_json(response_text)

        # 4. Reconcile Title
        curr_title = data.get('title', '').strip()
        if curr_title.lower() in GENERIC_TITLES and meta.get('title'):
            data['title'] = meta['title']
        elif not curr_title and meta.get('title'):
            data['title'] = meta['title']
        elif not data.get('title'):
            data['title'] = "Meeting Minutes"

        # 5. Reconcile Date
        curr_date = data.get('date', '').strip()
        if curr_date.lower() in GENERIC_DATES and meta.get('date'):
            data['date'] = meta['date']
        elif not curr_date and meta.get('date'):
            data['date'] = meta['date']
        elif not data.get('date'):
            data['date'] = "Today"

        # 6. Reconcile Attendees
        curr_attendees = data.get('attendees', [])
        if not isinstance(curr_attendees, list):
            curr_attendees = [str(curr_attendees)]
        data['attendees'] = self._reconcile_attendees(curr_attendees, meta.get('attendees', []), turns)

        # 7. Reconcile Decisions
        decisions = data.get('decisions', [])
        if not decisions or not isinstance(decisions, list):
            decisions = self.decision_extractor.extract(cleaned_text)
        data['decisions'] = [d.strip() for d in decisions if d.strip()]

        # 8. Reconcile Action Items (eliminate placeholders, map owners & deadlines)
        raw_actions = data.get('action_items', [])
        if not isinstance(raw_actions, list):
            raw_actions = []
        data['action_items'] = self._reconcile_action_items(raw_actions, cleaned_text, data['attendees'])

        data['raw_transcript'] = safe_raw_text
        data['cleaned_transcript'] = cleaned_text

        # 9. Strictly sanitize all generated fields (summary, action items, decisions)
        data = sanitize_meeting_data(data)
        return data

    def _reconcile_attendees(self, current_attendees: List[str], meta_attendees: List[str], speaker_turns: List[Dict[str, str]]) -> List[str]:
        raw_list = []
        for a in current_attendees:
            if a.strip().lower() not in PLACEHOLDER_NAMES:
                raw_list.append(a.strip())
        for a in meta_attendees:
            if a.strip().lower() not in PLACEHOLDER_NAMES:
                raw_list.append(a.strip())
        for t in speaker_turns:
            spk = t.get("speaker", "").strip()
            if spk and spk.lower() not in PLACEHOLDER_NAMES and len(spk) < 35:
                raw_list.append(spk)

        unique = []
        for name in raw_list:
            clean = re.sub(r'\s*\([^)]*\)', '', name).strip()
            if not clean or clean.lower() in PLACEHOLDER_NAMES:
                continue
            is_sub = False
            for i, existing in enumerate(unique):
                parts_clean = set(re.findall(r'\w+', clean.lower()))
                parts_exist = set(re.findall(r'\w+', existing.lower()))
                if parts_clean and parts_clean.issubset(parts_exist):
                    is_sub = True
                    break
                elif parts_exist and parts_exist.issubset(parts_clean):
                    unique[i] = clean
                    is_sub = True
                    break
            if not is_sub:
                unique.append(clean)
        return unique if unique else ["Team Members"]

    def _reconcile_action_items(self, items: List[Dict[str, Any]], cleaned_text: str, attendees: List[str]) -> List[Dict[str, Any]]:
        rule_items = self.action_extractor.extract(cleaned_text, attendees=attendees)

        reconciled = []
        seen = set()

        for item in items:
            task = item.get("task", "").strip()
            owner = item.get("owner", "Unassigned").strip()
            deadline = item.get("deadline", "TBD").strip()
            priority = item.get("priority", "Medium").strip()
            status = item.get("status", "Pending").strip()

            if not task or any(p.search(task) for p in self.action_extractor.meta_patterns) or len(task) < 5:
                continue

            if owner.lower() in {'unassigned', 'tbd', '<responsible person or persons>', 'none', ''}:
                for att in attendees:
                    if att.lower() in task.lower() and att.lower() not in {'team members', 'speaker'}:
                        owner = att
                        task = re.sub(r'^(?:action item:?\s*)?' + re.escape(att) + r'\s+(?:to|will|shall|must|is assigned to)\s+', '', task, flags=re.IGNORECASE).strip()
                        break

            if deadline.lower() in {'tbd', 'n/a', '<specific deadline or date>', 'none', ''}:
                for dp in self.action_extractor.deadline_patterns:
                    dm = re.search(dp, task, re.IGNORECASE)
                    if dm:
                        deadline = dm.group(1).strip()
                        break

            if deadline.lower() not in {'tbd', 'n/a', '<specific deadline or date>', 'none', ''}:
                task = re.sub(r'[\(\[]\s*(?:deadline|due|target date):?\s*' + re.escape(deadline) + r'[\)\]]', '', task, flags=re.IGNORECASE).strip()
                task = re.sub(r'(?:,\s*)?(?:deadline|due date|target date):\s*' + re.escape(deadline) + r'\.?$', '', task, flags=re.IGNORECASE).strip()
                task = re.sub(r'(?:,\s*)?(?:\b(?:by|due(?: on)?|deadline is|before|target date:?)\s+)?' + re.escape(deadline) + r'\.?$', '', task, flags=re.IGNORECASE).strip()

            task = task.rstrip('.,; ').strip()
            if task:
                task = task[0].upper() + task[1:]

            dedup_key = f"{owner.lower()}::{task.lower()}"
            if dedup_key not in seen and len(task) >= 5:
                seen.add(dedup_key)
                reconciled.append({
                    "task": task,
                    "owner": owner,
                    "deadline": deadline,
                    "priority": priority,
                    "status": status
                })

        # Merge in any rule-extracted items missed by the LLM
        for r_item in rule_items:
            r_task = r_item["task"]
            r_owner = r_item["owner"]
            covered = False
            for existing in reconciled:
                if (r_owner.lower() == existing["owner"].lower() or r_owner.lower() in existing["owner"].lower()) and any(w in existing["task"].lower() for w in r_task.lower().split()[:3]):
                    covered = True
                    if existing["owner"] == "Unassigned" and r_owner != "Unassigned":
                        existing["owner"] = r_owner
                    if existing["deadline"] == "TBD" and r_item["deadline"] != "TBD":
                        existing["deadline"] = r_item["deadline"]
                    break
            if not covered and r_task != "Review and circulate finalized meeting minutes":
                reconciled.append(r_item)

        if not reconciled and rule_items:
            return rule_items

        return reconciled

    def _clean_and_parse_json(self, raw_response: str) -> Dict[str, Any]:
        text = raw_response.strip()
        if text.startswith('```'):
            text = re.sub(r'^```(?:json)?\n', '', text)
            text = re.sub(r'\n```$', '', text)
            text = text.strip()

        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            try:
                return json.loads(json_str)
            except Exception as e:
                print(f"JSON parsing failed: {e}")

        return {
            "title": "Meeting Minutes",
            "date": "Today",
            "attendees": [],
            "executive_summary": raw_response[:300] if raw_response else "No summary generated.",
            "discussion_points": [],
            "decisions": [],
            "action_items": []
        }
