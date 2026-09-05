"""
Meeting Minutes Display & Review UI Module
Displays structured minutes, supports inline editing, review workflow (Draft/Reviewed/Approved),
and interactive action item tracking.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from src.export.pdf_export import PDFExporter
from src.export.word_export import WordExporter
from src.utils.sanitizer import sanitize_meeting_data

def render_minutes_page(db_manager, vector_store):
    st.markdown("### 📋 Structured Meeting Minutes & Review")

    # Load all meetings for dropdown selection
    all_meetings = db_manager.list_meetings()

    if not all_meetings:
        st.info("ℹ️ No meetings recorded yet. Please upload or generate a meeting first in the **Upload & Generate** tab!")
        return

    meeting_options = {f"{m.get('title', 'Untitled')} ({m.get('date', 'N/A')}) - [{m.get('id')}]": m['id'] for m in all_meetings}
    
    # Check default selected meeting
    current_id = st.session_state.get("current_meeting_id")
    default_index = 0
    if current_id:
        for idx, (label, mid) in enumerate(meeting_options.items()):
            if mid == current_id:
                default_index = idx
                break

    selected_label = st.selectbox(
        "Select Meeting Record to View / Review",
        options=list(meeting_options.keys()),
        index=default_index,
        key="meeting_selector"
    )

    selected_id = meeting_options[selected_label]
    meeting = db_manager.get_meeting(selected_id)
    if not meeting:
        st.error("Could not load meeting data.")
        return

    # Strictly sanitize meeting data so no credentials or secrets can be displayed
    meeting = sanitize_meeting_data(meeting)

    st.session_state["current_meeting_id"] = selected_id
    st.session_state["current_meeting"] = meeting

    st.markdown("---")

    # Header Card
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.subheader(f"📌 {meeting.get('title', 'Meeting Minutes')}")
        st.markdown(
            f"**📅 Date:** `{meeting.get('date', 'N/A')}` &nbsp;|&nbsp; "
            f"**⏰ Time:** `{meeting.get('time', 'Standard Session') or 'Standard Session'}`"
        )
        attendees = meeting.get('attendees', [])
        if attendees:
            att_html = " ".join([f"<span style='background-color:#e0e7ff; color:#3730a3; padding:3px 10px; border-radius:12px; font-size:13px; margin-right:6px; font-weight:500;'>👤 {a}</span>" for a in attendees])
            st.markdown(f"**Attendees:** {att_html}", unsafe_allow_html=True)
    
    with col_head2:
        # Review Workflow (FR-13 & FR-14)
        current_status = meeting.get("status", "Draft")
        status_colors = {"Draft": "#fef3c7", "Reviewed": "#dbeafe", "Approved": "#d1fae5"}
        status_text_colors = {"Draft": "#92400e", "Reviewed": "#1e40af", "Approved": "#065f46"}

        st.markdown(
            f"<div style='text-align:right; margin-bottom:8px;'>"
            f"<span style='background-color:{status_colors.get(current_status, '#eee')}; "
            f"color:{status_text_colors.get(current_status, '#333')}; "
            f"padding:6px 14px; border-radius:16px; font-weight:bold; font-size:14px; border:1px solid rgba(0,0,0,0.1);'>"
            f"Status: {current_status}</span></div>",
            unsafe_allow_html=True
        )

        new_status = st.selectbox(
            "Change Review Status",
            options=["Draft", "Reviewed", "Approved"],
            index=["Draft", "Reviewed", "Approved"].index(current_status) if current_status in ["Draft", "Reviewed", "Approved"] else 0,
            key=f"status_select_{selected_id}"
        )
        if new_status != current_status:
            db_manager.update_meeting_status(selected_id, new_status)
            meeting["status"] = new_status
            st.toast(f"Status updated to: {new_status}")
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs for Minutes Detail vs Raw Transcript
    tab_view, tab_edit, tab_raw = st.tabs(["📑 Structured Minutes View", "✏️ Edit Minutes", "📜 Raw Transcript"])

    with tab_view:
        # 1. Executive Summary
        st.markdown("#### 1. 📝 Executive Summary")
        summary_text = meeting.get("executive_summary", "No summary recorded.")
        st.markdown(
            f"<div style='background-color:#f8fafc; border-left: 4px solid #3b82f6; padding: 14px 18px; border-radius: 4px; line-height: 1.6; font-size:15px; color:#1e293b; margin-bottom:18px;'>"
            f"{summary_text}</div>",
            unsafe_allow_html=True
        )

        # 2. Key Discussion Points
        st.markdown("#### 2. 💬 Key Discussion Points")
        discussions = meeting.get("discussion_points", [])
        if discussions:
            for pt in discussions:
                st.markdown(
                    f"<div style='background-color:#ffffff; border:1px solid #e2e8f0; padding:10px 14px; border-radius:6px; margin-bottom:8px; display:flex; align-items:flex-start;'>"
                    f"<span style='color:#3b82f6; margin-right:10px; font-size:16px;'>🔹</span>"
                    f"<span style='color:#334155; font-size:14.5px;'>{pt}</span></div>",
                    unsafe_allow_html=True
                )
        else:
            st.write("No discussion points recorded.")

        st.markdown("<br>", unsafe_allow_html=True)

        # 3. Decisions Made & Resolutions
        st.markdown("#### 3. 🎯 Key Decisions Made & Ratified")
        decisions = meeting.get("decisions", [])
        if decisions:
            for dec in decisions:
                st.markdown(
                    f"<div style='background-color:#ecfdf5; border: 1px solid #6ee7b7; border-left: 4px solid #10b981; padding: 12px 16px; border-radius: 6px; margin-bottom: 8px; color: #065f46; font-size: 14.5px; font-weight: 500;'>"
                    f"✅ <b>Decision:</b> {dec}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.write("No formal decisions recorded.")

        st.markdown("<br>", unsafe_allow_html=True)

        # 4. Action Items & Deliverables Tracker
        st.markdown("#### 4. 📌 Action Items, Owners & Deadlines")
        action_items = meeting.get("action_items", [])
        if action_items:
            # Display interactive table
            df_items = []
            for i, item in enumerate(action_items):
                df_items.append({
                    "#": i + 1,
                    "Task Description": item.get("task", ""),
                    "Responsible Owner": item.get("owner", "Unassigned"),
                    "Target Deadline": item.get("deadline", "TBD"),
                    "Priority": item.get("priority", "Medium"),
                    "Status": item.get("status", "Pending")
                })
            
            df = pd.DataFrame(df_items)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Quick status update toggles
            with st.expander("⚡ Quick Update Action Item Status", expanded=False):
                st.markdown("Mark tasks as In Progress or Completed:")
                c_idx, c_st, c_btn = st.columns([1, 2, 1])
                with c_idx:
                    item_num = st.selectbox("Task #", options=list(range(1, len(action_items) + 1)), key="task_num_sel")
                with c_st:
                    item_st = st.selectbox("New Status", options=["Pending", "In Progress", "Completed"], key="task_st_sel")
                with c_btn:
                    st.write("")
                    st.write("")
                    if st.button("Apply Status", key="apply_task_st"):
                        action_items[item_num - 1]["status"] = item_st
                        meeting["action_items"] = action_items
                        db_manager.save_meeting(meeting)
                        st.success(f"Task #{item_num} updated to '{item_st}'!")
                        st.rerun()

        else:
            st.write("No action items recorded.")

        st.markdown("---")

        # Quick Export Buttons directly on minutes page
        col_exp1, col_exp2, col_del = st.columns([2, 2, 1])
        with col_exp1:
            pdf_exp = PDFExporter()
            pdf_bytes = pdf_exp.generate(meeting)
            st.download_button(
                label="📄 Download Official PDF Minutes",
                data=pdf_bytes,
                file_name=f"Minutes_{meeting.get('title', 'meeting')[:25]}_{selected_id}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        with col_exp2:
            word_exp = WordExporter()
            word_bytes = word_exp.generate(meeting)
            st.download_button(
                label="📝 Download Word Document (.docx)",
                data=word_bytes,
                file_name=f"Minutes_{meeting.get('title', 'meeting')[:25]}_{selected_id}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        with col_del:
            if st.button("🗑️ Delete Record", type="secondary", use_container_width=True):
                db_manager.delete_meeting(selected_id)
                vector_store.delete_meeting(selected_id)
                st.warning("Meeting record deleted.")
                st.session_state["current_meeting_id"] = None
                st.session_state["current_meeting"] = None
                st.rerun()

    with tab_edit:
        st.markdown("#### ✏️ Edit Meeting Minutes Content")
        with st.form("edit_minutes_form"):
            edit_title = st.text_input("Meeting Title", value=meeting.get("title", ""))
            c_ed1, c_ed2 = st.columns(2)
            with c_ed1:
                edit_date = st.text_input("Meeting Date", value=meeting.get("date", ""))
            with c_ed2:
                edit_time = st.text_input("Meeting Time", value=meeting.get("time", ""))

            attendees_list = meeting.get("attendees", [])
            edit_attendees = st.text_input(
                "Attendees (comma-separated)",
                value=", ".join(attendees_list) if isinstance(attendees_list, list) else str(attendees_list)
            )

            edit_summary = st.text_area("Executive Summary", value=meeting.get("executive_summary", ""), height=150)

            disc_list = meeting.get("discussion_points", [])
            edit_disc = st.text_area(
                "Discussion Points (one per line)",
                value="\n".join(disc_list) if isinstance(disc_list, list) else str(disc_list),
                height=120
            )

            dec_list = meeting.get("decisions", [])
            edit_dec = st.text_area(
                "Decisions (one per line)",
                value="\n".join(dec_list) if isinstance(dec_list, list) else str(dec_list),
                height=100
            )

            save_submit = st.form_submit_button("💾 Save All Changes to Database", type="primary", use_container_width=True)

            if save_submit:
                meeting["title"] = edit_title
                meeting["date"] = edit_date
                meeting["time"] = edit_time
                meeting["attendees"] = [a.strip() for a in edit_attendees.split(",") if a.strip()]
                meeting["executive_summary"] = edit_summary
                meeting["discussion_points"] = [d.strip() for d in edit_disc.split("\n") if d.strip()]
                meeting["decisions"] = [d.strip() for d in edit_dec.split("\n") if d.strip()]

                db_manager.save_meeting(meeting)
                # Re-index in vector store with updated contents
                vector_store.add_meeting(
                    meeting_id=selected_id,
                    title=edit_title,
                    date=edit_date,
                    chunks=[edit_summary] + meeting["discussion_points"]
                )
                st.success("Meeting record and vector index updated successfully!")
                st.rerun()

    with tab_raw:
        st.markdown("#### 📜 Raw Meeting Transcript")
        raw_tr = meeting.get("raw_transcript", "")
        if raw_tr:
            st.code(raw_tr, language="text")
        else:
            st.write("No raw transcript text preserved for this record.")
