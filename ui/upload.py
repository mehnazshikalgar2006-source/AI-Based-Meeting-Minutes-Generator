"""
Upload & Ingestion UI Module
Handles uploading transcripts (.txt, .docx, .pdf, .mp3, .wav), sample loading,
preprocessing preview, and trigger for AI minutes generation.
"""

import os
import streamlit as st
from src.preprocessing.transcript_cleaner import TranscriptCleaner
from src.speech.whisper_transcription import AudioTranscriber
from src.llm.summarizer import MeetingSummarizer
from src.utils.sanitizer import sanitize_text, sanitize_meeting_data

def render_upload_page(summarizer: MeetingSummarizer, db_manager, vector_store):
    st.markdown("### 📤 Upload & Process Meeting Transcript")
    st.markdown(
        "Upload your meeting transcript file, select a pre-loaded sample meeting, "
        "or paste raw meeting conversation text below to generate structured meeting minutes."
    )

    cleaner = TranscriptCleaner()

    # Sample Transcript Quick Loader
    col_sample1, col_sample2, col_sample3 = st.columns([1, 1, 1])
    with col_sample1:
        if st.button("🎓 Load Sample Academic Review", use_container_width=True):
            sample_path = "data/transcripts/sample_academic_meeting.txt"
            if os.path.exists(sample_path):
                with open(sample_path, "r", encoding="utf-8") as f:
                    st.session_state["transcript_input"] = f.read()
                st.success("Loaded 'AI-Based Meeting Minutes Generator Project Review' transcript!")
    with col_sample2:
        if st.button("📱 Load Sample Sprint Planning", use_container_width=True):
            sample_path = "data/transcripts/sample_sprint_planning.txt"
            if os.path.exists(sample_path):
                with open(sample_path, "r", encoding="utf-8") as f:
                    st.session_state["transcript_input"] = f.read()
                st.success("Loaded 'Sprint 14 Planning - Fintech Mobile App' transcript!")
    with col_sample3:
        if st.button("🔄 Clear Input", use_container_width=True):
            st.session_state["transcript_input"] = ""
            st.rerun()

    st.markdown("---")

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a transcript file (.txt, .docx, .pdf) or audio (.mp3, .wav, .m4a)",
        type=["txt", "docx", "pdf", "mp3", "wav", "m4a"],
        help="Upload text transcripts, PDF transcripts, Word documents, or audio recordings."
    )

    if uploaded_file is not None:
        fname = uploaded_file.name.lower()
        file_bytes = uploaded_file.getvalue()
        if fname.endswith(('mp3', 'wav', 'm4a')):
            with st.spinner("Transcribing audio file via Speech-to-Text pipeline..."):
                transcriber = AudioTranscriber(api_key=os.getenv("OPENAI_API_KEY"))
                res = transcriber.transcribe(file_bytes, uploaded_file.name)
                st.session_state["transcript_input"] = res.get("text", "")
                if res.get("warning"):
                    st.info(f"ℹ️ {res['warning']}")
                st.success(f"Audio transcription extracted ({len(st.session_state['transcript_input'])} characters) via {res.get('provider', 'STT')}!")
        else:
            try:
                extracted = cleaner.extract_text_from_file(file_bytes, uploaded_file.name)
                st.session_state["transcript_input"] = extracted
                st.success(f"Successfully extracted text from '{uploaded_file.name}' ({len(extracted)} characters)!")
            except Exception as e:
                st.error(f"Error reading file: {e}")

    # Transcript Text Area
    raw_text = st.text_area(
        "Transcript Content",
        value=st.session_state.get("transcript_input", ""),
        height=260,
        placeholder="Paste meeting conversation, discussion transcript, or speaker dialogue here...\n\nExample:\n[10:00] Alice: Welcome everyone to the roadmap review.\n[10:05] Bob: I will finish the database schema by Friday.\nDecision: We will use SQLite for local metadata.",
        key="transcript_area"
    )

    if raw_text != st.session_state.get("transcript_input", ""):
        st.session_state["transcript_input"] = raw_text

    # Preprocessing Options
    col_opt1, col_opt2 = st.columns([1, 1])
    with col_opt1:
        remove_fillers = st.checkbox("Strip conversational filler words (um, uh, you know)", value=True)
    with col_opt2:
        auto_index_rag = st.checkbox("Automatically index in RAG vector database upon generation", value=True)

    # Preview Preprocessed Data
    if raw_text.strip():
        with st.expander("🔍 Preview Preprocessed Transcript & Detected Speaker Turns", expanded=False):
            cleaned = cleaner.clean_text(raw_text, remove_fillers=remove_fillers)
            meta = cleaner.extract_metadata_from_header(raw_text)
            turns = cleaner.parse_speaker_turns(cleaned)

            p_col1, p_col2 = st.columns(2)
            with p_col1:
                st.markdown("**Detected Header Metadata:**")
                st.json(meta)
                st.markdown(f"**Speaker Turns Detected:** {len(turns)}")
            with p_col2:
                st.markdown("**Cleaned Transcript Preview:**")
                st.code(cleaned[:600] + ("..." if len(cleaned) > 600 else ""), language="text")

    st.markdown("<br>", unsafe_allow_html=True)

    # Generate Button
    generate_btn = st.button("🚀 Generate AI Meeting Minutes", type="primary", use_container_width=True)

    if generate_btn:
        if not raw_text.strip():
            st.warning("⚠️ Please upload a transcript or paste meeting dialogue text first!")
            return

        with st.spinner("🤖 Processing transcript, running NLP extraction & synthesizing structured minutes..."):
            try:
                # 1. Strictly sanitize raw input before any processing
                safe_input = sanitize_text(raw_text)

                # 2. Process via summarizer
                result = summarizer.process_transcript(safe_input)
                result = sanitize_meeting_data(result)
                
                # 3. Save into SQLite
                meeting_id = db_manager.save_meeting(result)
                result["id"] = meeting_id

                # 4. Index into RAG vector store if enabled
                if auto_index_rag:
                    chunks = cleaner.chunk_transcript(result.get("cleaned_transcript", safe_input))
                    # Also include the executive summary as a prime chunk
                    all_chunks = [result.get("executive_summary", "")] + chunks
                    vector_store.add_meeting(
                        meeting_id=meeting_id,
                        title=result.get("title", "Meeting"),
                        date=result.get("date", "Today"),
                        chunks=[c for c in all_chunks if c.strip()]
                    )

                st.session_state["current_meeting"] = result
                st.session_state["current_meeting_id"] = meeting_id
                st.success(f"🎉 Meeting minutes generated and saved successfully! (ID: {meeting_id})")
                st.info("👉 Switch to the **Meeting Minutes** tab to view, edit, review, or export your minutes!")

            except Exception as e:
                safe_err = sanitize_text(str(e))
                st.error(f"Failed to generate meeting minutes: {safe_err}")
