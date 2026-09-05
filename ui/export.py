"""
Export Center UI Module
Provides multi-format export capabilities (PDF, Word DOCX, Markdown, JSON),
live previews, and management of generated output files.
"""

import os
import json
import streamlit as st
import pandas as pd
from src.export.pdf_export import PDFExporter
from src.export.word_export import WordExporter

def render_export_page(db_manager):
    st.markdown("### 📥 Document Export Center")
    st.markdown(
        "Generate and download official, publication-ready meeting minutes in "
        "**PDF**, **Microsoft Word (.docx)**, **Markdown**, or **JSON** formats."
    )

    all_meetings = db_manager.list_meetings()
    if not all_meetings:
        st.info("ℹ️ No meetings found to export. Generate a meeting in **Upload & Generate** first!")
        return

    meeting_options = {f"{m.get('title', 'Untitled')} ({m.get('date', 'N/A')})": m['id'] for m in all_meetings}
    selected_label = st.selectbox("Select Meeting to Export:", options=list(meeting_options.keys()), key="export_meeting_sel")
    selected_id = meeting_options[selected_label]
    meeting = db_manager.get_meeting(selected_id)

    if not meeting:
        st.error("Meeting data not found.")
        return

    st.markdown("---")

    col_info, col_status = st.columns([3, 1])
    with col_info:
        st.markdown(f"**Document Title:** `{meeting.get('title')}`")
        st.markdown(f"**Date:** `{meeting.get('date')}` &nbsp;|&nbsp; **Time:** `{meeting.get('time') or 'Standard Session'}`")
    with col_status:
        st.markdown(f"**Review Status:** `{meeting.get('status', 'Draft')}`")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4 Export Cards
    c1, c2, c3, c4 = st.columns(4)

    pdf_exporter = PDFExporter()
    word_exporter = WordExporter()

    with c1:
        st.markdown("#### 📄 Adobe PDF")
        st.caption("Publication-ready formatted document with colored tables, headers, and academic metadata.")
        pdf_bytes = pdf_exporter.generate(meeting)
        st.download_button(
            label="⬇️ Download PDF",
            data=pdf_bytes,
            file_name=f"Meeting_Minutes_{selected_id}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary"
        )

    with c2:
        st.markdown("#### 📝 Word DOCX")
        st.caption("Editable Microsoft Word document with formatted styles and native Word tables.")
        word_bytes = word_exporter.generate(meeting)
        st.download_button(
            label="⬇️ Download Word",
            data=word_bytes,
            file_name=f"Meeting_Minutes_{selected_id}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

    with c3:
        st.markdown("#### 📋 Markdown (.md)")
        st.caption("Clean GitHub-flavored markdown file suitable for documentation repositories or wikis.")
        md_content = _generate_markdown(meeting)
        st.download_button(
            label="⬇️ Download Markdown",
            data=md_content,
            file_name=f"Meeting_Minutes_{selected_id}.md",
            mime="text/markdown",
            use_container_width=True
        )

    with c4:
        st.markdown("#### 💻 JSON Data")
        st.caption("Complete structured schema export for API integration and machine processing.")
        json_content = json.dumps(meeting, indent=2)
        st.download_button(
            label="⬇️ Download JSON",
            data=json_content,
            file_name=f"Meeting_Minutes_{selected_id}.json",
            mime="application/json",
            use_container_width=True
        )

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # Live Document Preview
    with st.expander("👁️ Preview Formatted Meeting Minutes", expanded=True):
        st.markdown(_generate_markdown(meeting))

    # Saved Outputs List
    with st.expander("📁 Previously Generated Files in outputs/ directory", expanded=False):
        pdf_files = os.listdir("outputs/pdf") if os.path.exists("outputs/pdf") else []
        word_files = os.listdir("outputs/word") if os.path.exists("outputs/word") else []

        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.markdown(f"**PDF Files ({len(pdf_files)}):**")
            for pf in pdf_files[-10:]:
                st.text(f"• outputs/pdf/{pf}")
        with f_col2:
            st.markdown(f"**Word Files ({len(word_files)}):**")
            for wf in word_files[-10:]:
                st.text(f"• outputs/word/{wf}")

def _generate_markdown(m: dict) -> str:
    lines = [
        f"# {m.get('title', 'Meeting Minutes')}",
        "",
        f"**Date:** {m.get('date', 'N/A')}  ",
        f"**Time:** {m.get('time', 'Standard Session') or 'Standard Session'}  ",
        f"**Status:** {m.get('status', 'Draft')}  ",
        f"**Attendees:** {', '.join(m.get('attendees', [])) if isinstance(m.get('attendees'), list) else m.get('attendees')}",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        m.get('executive_summary', 'No summary.'),
        "",
        "## 2. Key Discussion Points"
    ]
    for d in m.get('discussion_points', []):
        lines.append(f"- {d}")
    lines.append("")
    lines.append("## 3. Decisions Made & Resolutions")
    for dec in m.get('decisions', []):
        lines.append(f"- **[APPROVED]** {dec}")
    lines.append("")
    lines.append("## 4. Action Items & Deliverables")
    lines.append("| # | Task Description | Owner | Deadline | Priority | Status |")
    lines.append("|---|---|---|---|---|---|")
    for i, item in enumerate(m.get('action_items', [])):
        lines.append(f"| {i+1} | {item.get('task', '')} | {item.get('owner', 'Unassigned')} | {item.get('deadline', 'TBD')} | {item.get('priority', 'Medium')} | {item.get('status', 'Pending')} |")
    lines.append("")
    lines.append("---")
    lines.append("*Generated by AI-Based Meeting Minutes Generator | S.Y. B.Sc. (AI & ML) Project 2026-2027*")
    return "\n".join(lines)
