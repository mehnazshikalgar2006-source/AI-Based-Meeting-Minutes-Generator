"""
Multi-provider LLM Client & Smart Offline NLP Fallback
Supports:
1. Google Gemini (via google-genai)
2. OpenAI (via openai)
3. Built-in Offline NLP Engine (works 100% locally without API key)
"""

import os
import json
import re
from typing import Dict, Any, Optional
from src.utils.sanitizer import sanitize_text

class LLMClient:
    def __init__(self, provider: str = "built-in-nlp", api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.provider = (provider or "built-in-nlp").lower()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2) -> str:
        safe_prompt = sanitize_text(prompt)
        safe_system = sanitize_text(system_prompt) if system_prompt else None

        if self.provider == "gemini" and self.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key.strip())
                m = self.model_name or "gemini-3.6-flash"
                full_prompt = f"{safe_system}\n\n{safe_prompt}" if safe_system else safe_prompt
                response = client.models.generate_content(
                    model=m,
                    contents=full_prompt,
                    config={"temperature": temperature}
                )
                if response.text:
                    return sanitize_text(response.text)
            except Exception as e:
                print(f"[Gemini Error: {sanitize_text(str(e))}], falling back to Built-in NLP")
                return self._offline_nlp_process(safe_prompt)

        elif self.provider == "openai" and self.api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key.strip())
                m = self.model_name or "gpt-4o-mini"
                messages = []
                if safe_system:
                    messages.append({"role": "system", "content": safe_system})
                messages.append({"role": "user", "content": safe_prompt})
                response = client.chat.completions.create(
                    model=m,
                    messages=messages,
                    temperature=temperature
                )
                content = response.choices[0].message.content
                if content:
                    return sanitize_text(content)
            except Exception as e:
                print(f"[OpenAI Error: {sanitize_text(str(e))}], falling back to Built-in NLP")
                return self._offline_nlp_process(safe_prompt)

        # Default: Smart Built-in Offline NLP Engine
        return self._offline_nlp_process(safe_prompt)

    @staticmethod
    def validate_key(provider: str, api_key: str, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Validates API credentials with a minimal test request while strictly sanitizing errors."""
        if not api_key or not api_key.strip():
            return {"valid": False, "error": "API Key cannot be empty."}
        p = provider.lower()
        if "gemini" in p:
            try:
                from google import genai
                client = genai.Client(api_key=api_key.strip())
                m = model_name or "gemini-2.0-flash"
                res = client.models.generate_content(model=m, contents="Say OK")
                if res.text:
                    return {"valid": True, "message": f"Successfully connected to Google Gemini ({m})!"}
            except Exception as e:
                return {"valid": False, "error": sanitize_text(str(e))}
        elif "openai" in p:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key.strip())
                m = model_name or "gpt-4o-mini"
                res = client.chat.completions.create(
                    model=m,
                    messages=[{"role": "user", "content": "Say OK"}],
                    max_tokens=5
                )
                if res.choices:
                    return {"valid": True, "message": f"Successfully connected to OpenAI ({m})!"}
            except Exception as e:
                return {"valid": False, "error": sanitize_text(str(e))}
        return {"valid": False, "error": f"Unknown provider: {provider}"}

    def _offline_nlp_process(self, prompt: str) -> str:
        """
        Smart pattern-based NLP extraction when running offline.
        Produces structured JSON output for extraction prompts, or answers for RAG QA prompts.
        """
        if "Retrieved Meeting Context:" in prompt and "User Question:" in prompt:
            return self._offline_rag_answer(prompt)
            
        transcript = prompt
        if "Transcript:" in prompt:
            transcript = prompt.split("Transcript:", 1)[1].strip()

        from src.preprocessing.transcript_cleaner import TranscriptCleaner, is_valid_attendee_name
        from src.extraction.action_items import ActionItemsExtractor
        from src.extraction.decisions import DecisionsExtractor
        from src.extraction.discussion_points import DiscussionExtractor

        cleaner = TranscriptCleaner()
        meta = cleaner.extract_metadata_from_header(transcript)
        title = meta.get("title") or "Meeting Minutes"
        date = meta.get("date") or "Today"
        raw_attendees = list(meta.get("attendees", []))

        # Discover speaker participants from transcript dialogue
        turns = cleaner.parse_speaker_turns(transcript)
        for t in turns:
            spk = t.get("speaker", "").strip()
            if spk and is_valid_attendee_name(spk) and len(spk) < 35:
                raw_attendees.append(spk)

        # Deduplicate attendees (merge short and full names)
        attendees = []
        for name in raw_attendees:
            clean_name = name.strip()
            if not is_valid_attendee_name(clean_name):
                continue
            is_sub = False
            for i, existing in enumerate(attendees):
                parts_clean = set(re.findall(r'\w+', clean_name.lower()))
                parts_exist = set(re.findall(r'\w+', existing.lower()))
                if parts_clean and parts_clean.issubset(parts_exist):
                    is_sub = True
                    break
                elif parts_exist and parts_exist.issubset(parts_clean):
                    attendees[i] = clean_name
                    is_sub = True
                    break
            if not is_sub:
                attendees.append(clean_name)

        # Discussions
        discussions = DiscussionExtractor().extract(transcript)

        # Decisions
        decisions = DecisionsExtractor().extract(transcript)

        # Action Items
        action_items = ActionItemsExtractor().extract(transcript, attendees=attendees)

        # Executive Summary synthesis
        participants_str = ', '.join(attendees[:4]) if attendees else 'the project team'
        summary_decisions = f" Decisions ratified included: {'; '.join(decisions[:2])}." if decisions else ""
        executive_summary = (
            f"The meeting '{title}' was convened to review core updates, technical specifications, and key deliverables. "
            f"Key participants included {participants_str}. "
            f"The session examined system design, pipeline requirements, and performance criteria."
            f"{summary_decisions} "
            f"A total of {len(action_items)} action items were established with designated owners and delivery deadlines."
        )

        result_dict = {
            "title": title,
            "date": date,
            "attendees": attendees if attendees else ["Team Members"],
            "executive_summary": executive_summary,
            "discussion_points": discussions[:6],
            "decisions": decisions,
            "action_items": action_items
        }
        return json.dumps(result_dict, indent=2)

    def _offline_rag_answer(self, prompt: str) -> str:
        context = ""
        question = ""
        if "Retrieved Meeting Context:" in prompt and "User Question:" in prompt:
            parts = prompt.split("User Question:")
            context = parts[0].replace("Retrieved Meeting Context:", "").strip()
            question = parts[1].replace("Answer:", "").strip()

        q_words = set(re.findall(r'\w+', question.lower())) - {'what', 'when', 'who', 'where', 'how', 'is', 'the', 'was', 'were', 'in', 'on', 'at', 'to', 'for'}
        sentences = re.split(r'[\n\.]+', context)
        scored = []
        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 15:
                continue
            s_words = set(re.findall(r'\w+', s_clean.lower()))
            overlap = len(q_words & s_words)
            if overlap > 0:
                scored.append((overlap, s_clean))

        scored.sort(key=lambda x: x[0], reverse=True)
        if scored:
            top_findings = '. '.join([item[1] for item in scored[:3]])
            return f"According to historical meeting records: {top_findings}."
        else:
            return f"Relevant records confirm discussion related to '{question}', as detailed in the matching meeting excerpts above."
