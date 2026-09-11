"""
Main Application Entry Point - AI-Based Meeting Minutes Generator
Built for S.Y. B.Sc. (AI & ML) Academic Project 2026-2027
Students: Mehnaz Ibrahim Shikalgar (Roll 44), Dipika Subhash Tupat (Roll 27)
Guide: Prof. Sarita Byagar
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.database import DatabaseManager
from src.rag.vector_store import MeetingVectorStore
from src.rag.retriever import MeetingRetriever
from src.llm.model import LLMClient
from src.llm.summarizer import MeetingSummarizer
from src.preprocessing.transcript_cleaner import TranscriptCleaner

from ui.upload import render_upload_page
from ui.minutes import render_minutes_page
from ui.search import render_search_page
from ui.export import render_export_page
from src.utils.sanitizer import sanitize_text, sanitize_meeting_data, mask_api_key

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="AI Meeting Minutes Generator",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Professional Modern Styling
st.markdown("""
<style>
    /* Main Layout Styling */
    .main {
        background-color: #f8fafc;
    }
    
    /* Header Container */
    .app-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
        color: white;
        padding: 24px 28px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.15);
    }
    .app-header h1 {
        color: white !important;
        font-size: 26px;
        margin: 0;
        padding-bottom: 6px;
        font-weight: 700;
    }
    .app-header p {
        color: #bfdbfe !important;
        font-size: 14px;
        margin: 0;
    }

    /* Metric Cards */
    .metric-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
    }
    .metric-card .num {
        font-size: 24px;
        font-weight: bold;
        color: #1e3a8a;
    }
    .metric-card .label {
        font-size: 12px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        background-color: #f1f5f9;
        border-radius: 8px 8px 0px 0px;
        gap: 6px;
        padding: 8px 18px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e3a8a !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_database_manager():
    return DatabaseManager("database/metadata.db")

@st.cache_resource
def get_vector_store():
    return MeetingVectorStore("database/vector_store/index.json")

def seed_sample_data_if_empty(db_manager: DatabaseManager, vector_store: MeetingVectorStore, summarizer: MeetingSummarizer):
    """Auto-seeds sample transcripts on first run if database is empty."""
    stats = db_manager.get_stats()
    if stats["total_meetings"] == 0:
        sample_files = [
            ("data/transcripts/sample_academic_meeting.txt", "Approved"),
            ("data/transcripts/sample_sprint_planning.txt", "Reviewed")
        ]
        cleaner = TranscriptCleaner()
        for sample_path, init_status in sample_files:
            if os.path.exists(sample_path):
                with open(sample_path, "r", encoding="utf-8") as f:
                    content = f.read()
                result = summarizer.process_transcript(content)
                result["status"] = init_status
                meeting_id = db_manager.save_meeting(result)
                
                # Chunk and index
                chunks = cleaner.chunk_transcript(result.get("cleaned_transcript", content))
                all_chunks = [result.get("executive_summary", "")] + chunks
                vector_store.add_meeting(
                    meeting_id=meeting_id,
                    title=result.get("title", "Meeting"),
                    date=result.get("date", "Today"),
                    chunks=[c for c in all_chunks if c.strip()]
                )

def save_env_key(key_name: str, key_value: str):
    env_path = ".env"
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key_name}="):
            new_lines.append(f"{key_name}={key_value.strip()}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key_name}={key_value.strip()}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    os.environ[key_name] = key_value.strip()

def main():
    # Initialize Core Services
    db_manager = get_database_manager()
    vector_store = get_vector_store()

    # Sidebar: Model Config & Academic Credits
    with st.sidebar:
        st.markdown("### ⚙️ Engine Settings")
        
        provider_options = [
            "Built-in Smart NLP (Offline / No Key Needed)",
            "Google Gemini (Cloud GenAI)",
            "OpenAI (Cloud LLM)"
        ]

        # Check if GEMINI_API_KEY is configured in env or Streamlit secrets
        has_gemini_key = bool(os.getenv("GEMINI_API_KEY", "").strip())
        if not has_gemini_key:
            try:
                if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                    has_gemini_key = bool(str(st.secrets["GEMINI_API_KEY"]).strip())
            except Exception:
                has_gemini_key = False

        default_provider_index = 1 if has_gemini_key else 0

        selected_provider_label = st.selectbox(
            "AI Inference Provider",
            options=provider_options,
            index=default_provider_index,
            help="Switch between 100% offline rule-based NLP and cloud GenAI models."
        )

        api_key = None
        model_name = None
        if "Gemini" in selected_provider_label:
            provider = "gemini"
            env_key = os.getenv("GEMINI_API_KEY", "").strip()
            if not env_key:
                try:
                    if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                        env_key = str(st.secrets["GEMINI_API_KEY"]).strip()
                except Exception:
                    pass

            if env_key:
                st.markdown(
                    "<div style='background-color:#ecfdf5; border:1px solid #6ee7b7; padding:7px 12px; border-radius:6px; color:#065f46; font-size:12.5px; font-weight:600; margin-bottom:8px;'>"
                    "🔒 Gemini API Key: Configured in Environment / Secrets (Masked)</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<div style='background-color:#fffbeb; border:1px solid #fde68a; padding:7px 12px; border-radius:6px; color:#92400e; font-size:12.5px; margin-bottom:8px;'>"
                    "⚠️ No Gemini key found in .env. Enter key below:</div>",
                    unsafe_allow_html=True
                )

            # Never pass raw env_key as value to prevent exposing it in DOM / websocket payloads
            new_key_input = st.text_input(
                "Gemini API Key",
                value="",
                type="password",
                placeholder="Paste key to save or update..." if not env_key else "Paste new key to update...",
                help="Key is stored strictly server-side in .env and is never displayed."
            )
            model_name = st.selectbox("Gemini Model", options=["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"], index=0)

            # Effective API key resolution strictly on backend
            api_key = new_key_input.strip() if new_key_input.strip() else env_key

            c_save, c_test = st.columns(2)
            with c_save:
                if st.button("💾 Save Key", use_container_width=True):
                    if new_key_input.strip():
                        save_env_key("GEMINI_API_KEY", new_key_input.strip())
                        st.success("API Key saved securely to .env!")
                        st.rerun()
                    else:
                        st.warning("Please paste a key into the input field first.")
            with c_test:
                if st.button("🧪 Test Connection", use_container_width=True):
                    if not api_key:
                        st.warning("No API key available to test.")
                    else:
                        with st.spinner("Testing API connection securely..."):
                            res = LLMClient.validate_key("gemini", api_key, model_name)
                            if res.get("valid"):
                                st.success("✅ " + res.get("message", "Connected!"))
                            else:
                                safe_err = sanitize_text(res.get("error", "Connection failed."))
                                st.error("❌ " + safe_err)

        elif "OpenAI" in selected_provider_label:
            provider = "openai"
            env_key = os.getenv("OPENAI_API_KEY", "").strip()

            if env_key:
                st.markdown(
                    "<div style='background-color:#ecfdf5; border:1px solid #6ee7b7; padding:7px 12px; border-radius:6px; color:#065f46; font-size:12.5px; font-weight:600; margin-bottom:8px;'>"
                    "🔒 OpenAI API Key: Configured in .env (Masked)</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<div style='background-color:#fffbeb; border:1px solid #fde68a; padding:7px 12px; border-radius:6px; color:#92400e; font-size:12.5px; margin-bottom:8px;'>"
                    "⚠️ No OpenAI key found in .env. Enter key below:</div>",
                    unsafe_allow_html=True
                )

            new_openai_input = st.text_input(
                "OpenAI API Key",
                value="",
                type="password",
                placeholder="Paste key to save or update..." if not env_key else "Paste new key to update...",
                help="Key is stored strictly server-side in .env and is never displayed."
            )
            model_name = "gpt-4o-mini"
            api_key = new_openai_input.strip() if new_openai_input.strip() else env_key

            c_save, c_test = st.columns(2)
            with c_save:
                if st.button("💾 Save Key", use_container_width=True):
                    if new_openai_input.strip():
                        save_env_key("OPENAI_API_KEY", new_openai_input.strip())
                        st.success("API Key saved securely to .env!")
                        st.rerun()
                    else:
                        st.warning("Please paste a key into the input field first.")
            with c_test:
                if st.button("🧪 Test Connection", use_container_width=True):
                    if not api_key:
                        st.warning("No API key available to test.")
                    else:
                        with st.spinner("Testing API connection securely..."):
                            res = LLMClient.validate_key("openai", api_key, model_name)
                            if res.get("valid"):
                                st.success("✅ " + res.get("message", "Connected!"))
                            else:
                                safe_err = sanitize_text(res.get("error", "Connection failed."))
                                st.error("❌ " + safe_err)
        else:
            provider = "built-in-nlp"
            st.success("🟢 100% Offline NLP Mode Active")

        temperature = st.slider("Temperature / Creativity", min_value=0.0, max_value=1.0, value=0.2, step=0.05)

        # Instantiate LLM Client & Summarizer
        llm_client = LLMClient(provider=provider, api_key=api_key, model_name=model_name)
        summarizer = MeetingSummarizer(llm_client)
        retriever = MeetingRetriever(vector_store, llm_client)

        # Auto-seed sample meetings if needed
        seed_sample_data_if_empty(db_manager, vector_store, summarizer)

        st.markdown("---")

        # Live Metrics
        st.markdown("### 📊 System Overview")
        stats = db_manager.get_stats()
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            st.metric("Meetings", stats["total_meetings"])
            st.metric("Approved", stats["approved_meetings"])
        with c_m2:
            st.metric("Pending Tasks", stats["pending_actions"])
            st.metric("Completed", stats["completed_actions"])

        st.markdown(f"**Indexed RAG Chunks:** `{len(vector_store.documents)}`")

        st.markdown("---")

        # Project Credits (from PRD & Synopsis)
        st.markdown("### 🎓 Academic Project Info")
        st.markdown("""
        **Project Title:**  
        *AI-Based Meeting Minutes Generator from Transcripts*  
        
        **Team Members:**  
        1. **Mehnaz Ibrahim Shikalgar** (Roll 44)  
        2. **Dipika Subhash Tupat** (Roll 27)  
        
        **Class / Year:**  
        S.Y. B.Sc. (AI & ML) | 2026–2027  
        
        **Guide / Mentor:**  
        **Prof. Sarita Byagar**  
        """)

        if st.button("🔄 Re-seed Sample Meetings", use_container_width=True):
            seed_sample_data_if_empty(db_manager, vector_store, summarizer)
            st.success("Sample meetings re-seeded!")
            st.rerun()

    # Top App Header
    st.markdown("""
    <div class="app-header">
        <h1>🎙️ AI-Based Meeting Minutes Generator</h1>
        <p>Automated meeting summarization, decision extraction, action item tracking & semantic RAG search from transcripts</p>
    </div>
    """, unsafe_allow_html=True)

    # Main Navigation Tabs
    tab_dashboard, tab_upload, tab_minutes, tab_search, tab_export = st.tabs([
        "🏠 Dashboard & Overview",
        "📤 Upload & Generate",
        "📋 Meeting Minutes",
        "🔍 Semantic Search (RAG)",
        "📥 Export Center"
    ])

    with tab_dashboard:
        render_dashboard_overview(db_manager, vector_store)

    with tab_upload:
        render_upload_page(summarizer, db_manager, vector_store)

    with tab_minutes:
        render_minutes_page(db_manager, vector_store)

    with tab_search:
        render_search_page(retriever, vector_store, db_manager)

    with tab_export:
        render_export_page(db_manager)

def render_dashboard_overview(db_manager: DatabaseManager, vector_store: MeetingVectorStore):
    st.markdown("### 🌟 Welcome to AI-Based Meeting Minutes Generator")
    st.markdown(
        "This platform transforms unstructured conversational meeting transcripts into structured, "
        "reviewable, and publication-ready records with **action item attribution**, **decisions extraction**, "
        "and **RAG-powered historical retrieval**."
    )

    stats = db_manager.get_stats()

    # Metric Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"<div class='metric-card'><div class='num'>{stats['total_meetings']}</div><div class='label'>Total Meetings</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card'><div class='num'>{stats['approved_meetings']}</div><div class='label'>Approved Minutes</div></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='metric-card'><div class='num'>{stats['pending_actions']}</div><div class='label'>Pending Action Items</div></div>", unsafe_allow_html=True)
    with m4:
        st.markdown(f"<div class='metric-card'><div class='num'>{len(vector_store.documents)}</div><div class='label'>Indexed RAG Chunks</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Architectural Highlights
    st.markdown("#### ⚙️ Technical Architecture & Pipeline")
    st.markdown("""
    ```
    Raw Transcript (TXT / DOCX / PDF / Audio)
       │
       ▼
    Preprocessing (Noise & Filler Removal, Speaker Turn Segmentation)
       │
       ▼
    LLM / NLP Extraction (Executive Summary, Decisions, Action Items with Owners & Deadlines)
       │
       ├──► Web UI: Human Review & Edit Workflow (Draft ➔ Reviewed ➔ Approved)
       │
       ├──► Persistent Storage: SQLite (metadata.db)
       │
       ├──► RAG Layer: TF-IDF Semantic Embeddings + Vector Store ➔ Natural Language QA
       │
       └──► Document Export: Publication-Ready PDF (ReportLab) & Microsoft Word (python-docx)
    ```
    """)

    st.markdown("<br>", unsafe_allow_html=True)

    # Key Product Features Accordions
    c_feat1, c_feat2 = st.columns(2)
    with c_feat1:
        st.markdown("""
        **✨ Core Capabilities:**
        - **Multi-Format Input:** Ingest text transcripts, Word `.docx`, PDF documents, or audio recordings.
        - **Speaker Segmentation:** Parses and cleans dialogue into clear speaker-turn units.
        - **Structured Extraction:** Automatically isolates decisions and action items with owners and deadlines.
        - **Review & Verification:** Strict human-in-the-loop review workflow before official ratification.
        """)
    with c_feat2:
        st.markdown("""
        **🔒 Privacy & Storage:**
        - **100% Offline Capable:** Built-in Smart Pattern NLP engine runs with zero API keys and zero cost.
        - **Local SQLite Database:** All meeting metadata and action items stored securely in `database/metadata.db`.
        - **Semantic RAG Search:** Natural-language queries search historical meetings with similarity scores and citations.
        - **Dual Document Export:** Instant generation of styled PDF and `.docx` reports.
        """) 

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 **Getting Started:** Go to the **Upload & Generate** tab to try one of the pre-loaded sample transcripts, or click **Semantic Search (RAG)** to search across pre-indexed meetings!")

if __name__ == "__main__":
    main()
