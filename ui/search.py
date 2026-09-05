"""
Semantic Search & RAG UI Module
Supports natural-language search across past meeting records,
displaying retrieved context chunks with similarity scores and synthesized AI answers.
"""

import streamlit as st
from src.rag.retriever import MeetingRetriever
from src.utils.sanitizer import sanitize_text

def render_search_page(retriever: MeetingRetriever, vector_store, db_manager):
    st.markdown("### 🔍 Semantic Search Across Past Meetings (RAG)")
    st.markdown(
        "Ask questions in natural language across all historical meeting records. "
        "The RAG (Retrieval-Augmented Generation) pipeline searches the vector database using "
        "semantic similarity and synthesizes a direct answer with citations."
    )

    doc_count = len(vector_store.documents)
    if doc_count == 0:
        st.warning("⚠️ No meetings have been indexed in the vector store yet! Generate or seed meetings in the **Upload & Generate** tab first.")
        return

    st.markdown(
        f"<div style='background-color:#eff6ff; border:1px solid #bfdbfe; padding:10px 16px; border-radius:6px; color:#1e40af; margin-bottom:16px; font-size:14px;'>"
        f"📊 <b>Vector Store Status:</b> <b>{doc_count}</b> meeting chunks indexed across historical sessions.</div>",
        unsafe_allow_html=True
    )

    # Suggested Query Chips
    st.markdown("**Suggested Questions:**")
    q_col1, q_col2, q_col3 = st.columns(3)
    with q_col1:
        if st.button("❓ What was decided about the architecture?", use_container_width=True):
            st.session_state["rag_query"] = "What was decided about the project architecture and technology stack?"
    with q_col2:
        if st.button("❓ Who is responsible for testing?", use_container_width=True):
            st.session_state["rag_query"] = "Who is responsible for testing and what are their deadlines?"
    with q_col3:
        if st.button("❓ What were the biometric decisions?", use_container_width=True):
            st.session_state["rag_query"] = "What was decided regarding biometric authentication in the fintech app?"

    # Query Input
    query = st.text_input(
        "Enter your question:",
        value=st.session_state.get("rag_query", ""),
        placeholder="e.g., What are the deadlines for Mehnaz and Dipika? Or: What was decided about SQLite?",
        key="search_input_box"
    )

    col_btn, col_k = st.columns([3, 1])
    with col_k:
        top_k = st.slider("Top Sources (k)", min_value=1, max_value=5, value=3)
    with col_btn:
        st.write("")
        st.write("")
        search_clicked = st.button("🔎 Search Meeting Records", type="primary", use_container_width=True)

    if search_clicked or (query and query != st.session_state.get("last_searched_query")):
        if not query.strip():
            st.warning("Please enter a question or query.")
            return

        st.session_state["last_searched_query"] = query

        with st.spinner("🧠 Querying vector store, calculating cosine similarity & synthesizing answer..."):
            try:
                safe_query = sanitize_text(query)
                response = retriever.answer_question(safe_query, top_k=top_k)
                answer = sanitize_text(response.get("answer", "No answer could be generated."))
                sources = response.get("sources", [])
                conf = response.get("confidence", 0.0)

                # Display Synthesized Answer
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("#### 💡 AI-Synthesized Answer")
                st.markdown(
                    f"<div style='background-color:#f0fdf4; border:1px solid #86efac; border-left:5px solid #22c55e; padding:16px 20px; border-radius:6px; font-size:15.5px; color:#14532d; line-height:1.6; margin-bottom:20px;'>"
                    f"{answer}</div>",
                    unsafe_allow_html=True
                )

                # Display Retrieved Citations
                st.markdown(f"#### 📚 Retrieved Meeting Sources ({len(sources)} citations)")
                if sources:
                    for i, src in enumerate(sources):
                        score = src.get("relevance_score", 0.0)
                        score_pct = int(score * 100) if score <= 1.0 else int(score)
                        safe_chunk = sanitize_text(src.get('chunk_text', ''))
                        safe_m_title = sanitize_text(src.get('meeting_title', 'Meeting'))
                        st.markdown(
                            f"<div style='background-color:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:14px 18px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.05);'>"
                            f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>"
                            f"<span style='font-weight:bold; color:#1e3a8a; font-size:15px;'>📄 Source [{i+1}]: {safe_m_title}</span>"
                            f"<span style='background-color:#e0e7ff; color:#3730a3; padding:2px 10px; border-radius:12px; font-size:12px; font-weight:600;'>Relevance: {score_pct}%</span>"
                            f"</div>"
                            f"<div style='color:#64748b; font-size:12.5px; margin-bottom:6px;'>📅 Meeting Date: {src.get('date', 'N/A')}</div>"
                            f"<div style='background-color:#f8fafc; border-left:3px solid #94a3b8; padding:8px 12px; font-size:13.5px; color:#334155; line-height:1.5;'>"
                            f"{safe_chunk}</div>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                else:
                    st.info("No matching context chunks passed the relevance threshold.")

            except Exception as e:
                st.error(f"Error during RAG semantic search: {sanitize_text(str(e))}")

    # Indexed meetings overview
    st.markdown("<br><hr>", unsafe_allow_html=True)
    with st.expander("🗄️ View All Indexed Historical Meetings in Vector Store", expanded=False):
        unique_meetings = {}
        for doc in vector_store.documents:
            mid = doc.get("meeting_id")
            if mid not in unique_meetings:
                unique_meetings[mid] = {
                    "Title": doc.get("title"),
                    "Date": doc.get("date"),
                    "Chunks Indexed": 1
                }
            else:
                unique_meetings[mid]["Chunks Indexed"] += 1

        if unique_meetings:
            import pandas as pd
            df_docs = pd.DataFrame(list(unique_meetings.values()))
            st.dataframe(df_docs, use_container_width=True, hide_index=True)
        else:
            st.write("No documents currently indexed.")
