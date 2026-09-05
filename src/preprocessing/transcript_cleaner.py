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
        lines = text.split('\n')
        for line in lines[:20]:
            lower = line.lower()
            if lower.startswith(('meeting:', 'subject:', 'topic:', 'title:')):
                metadata['title'] = line.split(':', 1)[1].strip()
            elif lower.startswith(('date:', 'meeting date:')):
                metadata['date'] = line.split(':', 1)[1].strip()
            elif lower.startswith(('time:', 'duration:')):
                metadata['time'] = line.split(':', 1)[1].strip()
            elif lower.startswith(('attendees:', 'participants:', 'members:')):
                attendees_raw = line.split(':', 1)[1].strip()
                raw_list = re.split(r'[,;]', attendees_raw)
                metadata['attendees'] = [a.strip() for a in raw_list if a.strip()]
        return metadata

    def parse_speaker_turns(self, text: str) -> List[Dict[str, str]]:
        lines = text.split('\n')
        turns = []
        current_turn = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if any(line.lower().startswith(k) for k in ['date:', 'time:', 'meeting:', 'subject:', 'attendees:']):
                continue
            match = self.timestamp_speaker_regex.match(line)
            if match:
                timestamp = match.group(1) or ""
                speaker = match.group(2).strip()
                statement = match.group(3).strip()
                if len(speaker) < 40 and not speaker.lower().startswith(('action item', 'decision', 'note')):
                    if current_turn:
                        turns.append(current_turn)
                    current_turn = {"timestamp": timestamp, "speaker": speaker, "statement": statement}
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
