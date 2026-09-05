"""
Meeting Summarizer Pipeline
Coordinates preprocessing and LLM extraction to return structured minutes.
"""

import json
import re
from typing import Dict, Any
from src.preprocessing.transcript_cleaner import TranscriptCleaner
from src.llm.model import LLMClient
from src.llm.prompts import SYSTEM_PROMPT, EXTRACTION_PROMPT
from src.utils.sanitizer import sanitize_meeting_data, sanitize_text

class MeetingSummarizer:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.cleaner = TranscriptCleaner()

    def process_transcript(self, raw_text: str) -> Dict[str, Any]:
        # 1. Clean and sanitize transcript input
        safe_raw_text = sanitize_text(raw_text)
        cleaned_text = self.cleaner.clean_text(safe_raw_text)
        meta = self.cleaner.extract_metadata_from_header(safe_raw_text)

        # 2. Call LLM for extraction
        prompt = EXTRACTION_PROMPT.format(transcript=cleaned_text)
        response_text = self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT, temperature=0.2)

        # 3. Parse JSON output
        data = self._clean_and_parse_json(response_text)

        # 4. Merge any explicit header metadata if LLM left them blank
        if meta.get('title') and (not data.get('title') or data.get('title') == 'General Meeting'):
            data['title'] = meta['title']
        if meta.get('date') and (not data.get('date') or data.get('date') == 'Today'):
            data['date'] = meta['date']
        if meta.get('attendees') and not data.get('attendees'):
            data['attendees'] = meta['attendees']

        data['raw_transcript'] = safe_raw_text
        data['cleaned_transcript'] = cleaned_text

        # 5. Strictly sanitize all generated fields (summary, action items, decisions)
        data = sanitize_meeting_data(data)
        return data

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
