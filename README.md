# 🎙️ AI-Based Meeting Minutes Generator from Transcripts

An intelligent, web-based system that automatically converts unstructured conversational meeting transcripts into structured, reviewable, and publication-ready meeting minutes using Generative AI and Retrieval-Augmented Generation (RAG).

---

## 🎓 Academic Project Information

- **Project Title:** AI-Based Meeting Minutes Generator from Transcripts
- **Class / Division:** S.Y. B.Sc. (AI & ML)
- **Academic Year:** 2026–2027
- **Project Guide / Mentor:** Prof. Sarita Byagar
- **Team Members:**
  1. **Mehnaz Ibrahim Shikalgar** — Roll No. 44
  2. **Dipika Subhash Tupat** — Roll No. 27

---

## 🌟 Key Features

1. **Multi-Format Transcript Ingestion**:
   - Accepts `.txt`, `.docx`, `.pdf`, and audio files (`.mp3`, `.wav`, `.m4a`).
   - Built-in 1-click sample loaders for academic project reviews and sprint planning.
2. **Intelligent Preprocessing**:
   - Removes conversational filler words (`um`, `uh`, `er`, `you know`).
   - Normalizes timestamps and detects speaker turns automatically.
3. **GenAI & Smart Offline NLP Processing**:
   - **100% Offline Mode (Default)**: Zero-cost, zero-API-key smart pattern NLP engine.
   - **Cloud GenAI Providers**: Seamless toggle for Google Gemini (`gemini-2.5-flash`) and OpenAI (`gpt-4o-mini`).
4. **Structured Information Extraction**:
   - Executive Summary (abstractive synthesis)
   - Key Agenda & Discussion Points
   - Ratified Decisions & Resolutions
   - Action Items with Responsible Owners, Deadlines, Priorities, and Status
5. **Human Review & Approval Workflow (PRD FR-13 / FR-14)**:
   - Status tagging (`Draft` ➔ `Reviewed` ➔ `Approved`).
   - Inline editor to polish summaries or add agenda items before official sign-off.
   - Interactive action item completion tracker.
6. **Semantic Search via RAG (Retrieval-Augmented Generation)**:
   - Natural language queries across historical meeting records.
   - Sublinear TF-IDF semantic embeddings with cosine similarity matching.
   - AI-synthesized answers citing matching meeting titles, dates, and exact excerpts.
7. **Official Document Export**:
   - **Adobe PDF**: ReportLab-powered publication layout with colored metadata tables, decision callouts, and task grids.
   - **Microsoft Word (.docx)**: python-docx styled document ready for corporate or academic circulation.
   - **Markdown (.md)** and **JSON**: Instant downloads for documentation and API integrations.

---

## 🏗️ System Architecture

```
Raw Meeting Transcript (.txt, .docx, .pdf, audio)
                    │
                    ▼
     [Transcript Cleaner & Preprocessor]
                    │
                    ▼
     [LLM / Offline NLP Summarization Pipeline]
                    │
   ┌────────────────┼────────────────┬────────────────┐
   ▼                ▼                ▼                ▼
Summary     Discussion Points    Decisions       Action Items
   │                │                │                │
   └────────────────┴────────┬───────┴────────────────┘
                             ▼
              [Structured Meeting Minutes]
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [Human Review & Edit]             [Storage & Indexing]
            │                                 │
     ┌──────┴──────┐                   ┌──────┴──────┐
     ▼             ▼                   ▼             ▼
PDF Export    Word Export       SQLite (metadata)  RAG Vector Store
(ReportLab)   (python-docx)    (database/metadata.db) (Cosine Similarity)
                                                     │
                                                     ▼
                                            [Semantic Search]
```

---

## 📂 Project Directory Structure

```
AI-Meeting-Minutes-Generator/
├── app.py                     # Main Streamlit web application entry point
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation & user guide
├── .env.example               # Configuration and API key template
├── .gitignore                 # Git ignore rules
│
├── data/
│   ├── transcripts/           # Sample and uploaded transcripts
│   │   ├── sample_academic_meeting.txt
│   │   └── sample_sprint_planning.txt
│   ├── processed/             # Cleaned transcript files
│   └── meetings/              # Saved structured meeting records
│
├── database/
│   ├── metadata.db            # SQLite database (meetings & action items)
│   └── vector_store/          # RAG vector store and embeddings index
│       └── index.json
│
├── src/
│   ├── preprocessing/         # Transcript cleaning and speaker segmentation
│   │   └── transcript_cleaner.py
│   ├── llm/                   # Multi-provider LLM client, prompts, and pipeline
│   │   ├── model.py
│   │   ├── summarizer.py
│   │   └── prompts.py
│   ├── extraction/            # Discussion, decisions, and action item extractors
│   │   ├── discussion_points.py
│   │   ├── decisions.py
│   │   └── action_items.py
│   ├── rag/                   # Embeddings, vector index, and retriever
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   └── retriever.py
│   ├── database/              # SQLite CRUD operations
│   │   └── database.py
│   ├── export/                # PDF and Word document generators
│   │   ├── pdf_export.py
│   │   └── word_export.py
│   └── speech/                # Audio upload and Whisper STT handler
│       └── whisper_transcription.py
│
├── ui/                        # Modular Streamlit user-interface views
│   ├── upload.py              # Transcript upload and preprocessing preview
│   ├── minutes.py             # Structured minutes view, review, and edit
│   ├── search.py              # RAG semantic search across past sessions
│   └── export.py              # Multi-format document export center
│
├── outputs/                   # Generated documents for download
│   ├── pdf/
│   └── word/
│
└── tests/                     # Automated test suite
    ├── test_preprocessing.py
    ├── test_llm.py
    ├── test_extraction.py
    ├── test_rag.py
    └── test_database.py
```

---

## 🚀 How to Run the Application

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
If you want to use Google Gemini or OpenAI in addition to the built-in offline NLP engine, copy `.env.example` to `.env` and insert your keys:
```bash
cp .env.example .env
```

### 3. Launch the Web Application
```bash
streamlit run app.py
```
The website will open automatically in your default browser at:
`http://localhost:8501`

### 4. Run Automated Unit Tests
```bash
python -m unittest discover tests -v
```
*(All 15 test cases validate preprocessing, extraction, LLM fallback, RAG vector retrieval, and database operations.)*

---

## 👥 Authors & Acknowledgments

- **Mehnaz Ibrahim Shikalgar** (Roll No. 44)
- **Dipika Subhash Tupat** (Roll No. 27)
- **Project Guide:** Prof. Sarita Byagar  
*Department of AI & Machine Learning, Academic Year 2026–2027*
