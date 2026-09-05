"""
Prompts for Meeting Minutes Summarization and Extraction
"""

SYSTEM_PROMPT = """You are an expert executive secretary and AI Meeting Assistant.
Your job is to convert meeting transcripts into highly accurate, structured, and actionable meeting minutes.
Ensure exact attribution of tasks, owners, deadlines, key discussion points, and ratified decisions.
"""

EXTRACTION_PROMPT = """Analyze the meeting transcript below and extract structured information strictly in JSON format.
Return ONLY valid JSON matching this schema:
{{
  "title": "Meeting Title or Subject",
  "date": "YYYY-MM-DD or string date if mentioned, else Today",
  "attendees": ["Person 1", "Person 2"],
  "executive_summary": "Comprehensive summary of the meeting",
  "discussion_points": [
    "Detailed point discussed during the meeting",
    "Another key topic discussed"
  ],
  "decisions": [
    "Key formal decision agreed upon",
    "Another decision ratified"
  ],
  "action_items": [
    {{
      "task": "Exact task description",
      "owner": "Name of person responsible (or Unassigned)",
      "deadline": "Target date/time (or TBD)",
      "priority": "High / Medium / Low",
      "status": "Pending"
    }}
  ]
}}

Transcript:
{transcript}
"""

RAG_QA_PROMPT = """You are an AI assistant answering questions about past organizational meetings based on historical meeting minutes.
Use the following retrieved meeting excerpts to answer the question truthfully, citing the specific meeting title or date when relevant.
If the answer cannot be determined from the excerpts, state that clearly.

Retrieved Meeting Context:
{context}

User Question:
{question}

Answer:
"""
