"""
Transcript Preprocessing and Cleaning Module
Cleans raw transcripts, normalizes speaker timestamps, removes filler noise,
and extracts structural metadata.
"""

import re
import io
from typing import List, Dict, Any
from src.utils.sanitizer import sanitize_text

class TranscriptCleaner:
    def __init__(self):
        self.fillers = [
            r'\b(um+)\b', r'\b(uh+)\b', r'\b(er+)\b', r'\b(ah+)\b',
            r'\b(like\s*,?\s*you\s+know)\b', r'\b(you\s+know\s+what\s+I\s+mean)\b'
        ]
        self.filler_pattern = re.compile('|'.join(self.fillers), re.IGNORECASE)
        self.timestamp_speaker_regex = re.compile(
            r'^(?:(?:\[|\()?\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)\s*(?:\]|\))?\s*)?([A-Za-z0-9\s\.\,\-\(\)\']+?):\s*(.*)$'
        )

    def clean_text(self, text: str, remove_fillers: bool = True) -> str:
        if not text:
            return ""
        # 1. Immediately scrub any accidental API keys or credentials
        cleaned = sanitize_text(text)
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        cleaned = cleaned.replace('\u00a0', ' ')
        if remove_fillers:
            cleaned = self.filler_pattern.sub('', cleaned)

        cleaned_lines = []
        for line in cleaned.split('\n'):
            line = re.sub(r'\s+', ' ', line).strip()
            if line:
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)

    def extract_metadata_from_header(self, text: str) -> Dict[str, Any]:
        metadata = {"title": "", "date": "", "time": "", "attendees": []}
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        collecting_attendees = False
        
        for line in lines[:25]:
            clean_l = re.sub(r'^[#*_\-\s]+', '', line).strip()
            clean_l = re.sub(r'[*_]+$', '', clean_l).strip()
            lower = clean_l.lower()
            
            if collecting_attendees:
                if lower.startswith(('date:', 'meeting date:', 'time:', 'duration:', 'meeting:', 'subject:', 'topic:', 'title:', 'agenda:', 'discussion:', 'decision:')) or re.match(r'^(?:\[\d{1,2}:\d{2}\]|\w+\s*:)', clean_l):
                    collecting_attendees = False
                elif clean_l.startswith(('-', '*', '•')) or re.match(r'^\d+\.', clean_l):
                    att = re.sub(r'^[-*•\d\.\s]+', '', clean_l).strip()
                    att_clean = re.sub(r'\s*\([^)]*\)', '', att).strip()
                    if att_clean and att_clean not in metadata['attendees'] and len(att_clean) < 45:
                        metadata['attendees'].append(att_clean)
                    continue

            if lower.startswith(('meeting:', 'subject:', 'topic:', 'title:', 'meeting title:', 'meeting name:')):
                val = clean_l.split(':', 1)[1].strip()
                val = re.sub(r'^[*_]+|[*_]+$', '', val).strip()
                if val:
                    metadata['title'] = val
            elif lower.startswith(('date:', 'meeting date:', 'date & time:', 'date/time:')):
                val = clean_l.split(':', 1)[1].strip()
                val = re.sub(r'^[*_]+|[*_]+$', '', val).strip()
                if val:
                    metadata['date'] = val
            elif lower.startswith(('time:', 'duration:', 'meeting time:')):
                val = clean_l.split(':', 1)[1].strip()
                val = re.sub(r'^[*_]+|[*_]+$', '', val).strip()
                if val:
                    metadata['time'] = val
            elif lower.startswith(('attendees:', 'participants:', 'members:', 'present:')):
                val = clean_l.split(':', 1)[1].strip()
                val = re.sub(r'^[*_]+|[*_]+$', '', val).strip()
                if val:
                    raw_list = re.split(r'[,;]', val)
                    for a in raw_list:
                        a_clean = re.sub(r'\s*\([^)]*\)', '', a).strip()
                        if a_clean and a_clean not in metadata['attendees']:
                            metadata['attendees'].append(a_clean)
                else:
                    collecting_attendees = True

        # Fallback date detection if not matched via explicit prefix
        if not metadata['date']:
            for line in lines[:15]:
                date_match = re.search(
                    r'\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:January|February|March|April|May|June|July|August|September|October|November|December|[A-Z][a-z]{2})\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})\b',
                    line,
                    re.IGNORECASE
                )
                if date_match:
                    metadata['date'] = date_match.group(0).strip()
                    break

        # Fallback time detection
        if not metadata['time']:
            for line in lines[:15]:
                time_match = re.search(
                    r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?(?:\s*[-–to]+\s*\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)?\b',
                    line
                )
                if time_match and not line.strip().startswith('['):
                    metadata['time'] = time_match.group(0).strip()
                    break

        # Fallback title detection from first prominent line if not already found
        if not metadata['title'] and lines:
            first_line = lines[0].strip()
            clean_first = re.sub(r'^[#*_\-\s]+', '', first_line).strip()
            first_lower = clean_first.lower()
            if not any(first_lower.startswith(k) for k in ['date:', 'time:', 'attendees:', 'participants:', '[']) and len(clean_first) < 80 and ':' not in clean_first:
                metadata['title'] = clean_first

        return metadata

    def parse_speaker_turns(self, text: str) -> List[Dict[str, str]]:
        lines = text.split('\n')
        turns = []
        current_turn = None
        skip_prefixes = [
            'date:', 'time:', 'meeting:', 'subject:', 'topic:', 'title:',
            'attendees:', 'participants:', 'members:', 'present:', 'agenda:'
        ]
        non_speaker_names = {
            'action item', 'action items', 'decision', 'decisions', 'note', 'notes',
            'attendees', 'participants', 'members', 'present', 'agenda', 'summary',
            'executive summary', 'task', 'tasks', 'todo'
        }
        for line in lines:
            line = line.strip()
            if not line:
                continue
            clean_line = re.sub(r'^[#*_\-\s]+', '', line).strip()
            clean_lower = clean_line.lower()
            if any(clean_lower.startswith(k) for k in skip_prefixes):
                continue
            match = self.timestamp_speaker_regex.match(line)
            if match:
                timestamp = match.group(1) or ""
                speaker = match.group(2).strip()
                statement = match.group(3).strip()
                speaker_clean = re.sub(r'^[*_\-\s]+|[*_\-\s]+$', '', speaker).strip()
                speaker_clean = re.sub(r'\s*\([^)]*\)', '', speaker_clean).strip()
                if len(speaker_clean) < 40 and speaker_clean.lower() not in non_speaker_names and not speaker_clean.lower().startswith(('action item', 'decision', 'note')):
                    if current_turn:
                        turns.append(current_turn)
                    current_turn = {"timestamp": timestamp, "speaker": speaker_clean, "statement": statement}
                    continue
            if current_turn:
                current_turn['statement'] += " " + line
            else:
                turns.append({"timestamp": "", "speaker": "Speaker", "statement": line})
        if current_turn:
            turns.append(current_turn)
        return turns

    def chunk_transcript(self, text: str, max_chars_per_chunk: int = 1500, overlap: int = 150) -> List[str]:
        if len(text) <= max_chars_per_chunk:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars_per_chunk
            if end < len(text):
                bp = text.rfind('\n', start, end)
                if bp == -1 or bp <= start:
                    bp = text.rfind('. ', start, end)
                if bp > start:
                    end = bp + 1
            chunks.append(text[start:end].strip())
            start = end - overlap if end < len(text) else end
        return [c for c in chunks if c]

    @staticmethod
    def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
        ext = filename.lower().split('.')[-1]
        if ext == 'txt':
            try:
                return file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                return file_bytes.decode('latin-1', errors='ignore')
        elif ext == 'docx':
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            return '\n'.join([p.text for p in doc.paragraphs if p.text.strip()])
        elif ext == 'pdf':
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
            return '\n'.join(pages_text)
        else:
            raise ValueError(f'Unsupported format: .{ext}')
