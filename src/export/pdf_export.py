"""
PDF Export Module
Generates professional, publication-ready PDF meeting minutes using ReportLab.
"""

import io
import os
import re
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from src.utils.sanitizer import sanitize_meeting_data

class PDFExporter:
    def __init__(self, output_dir: str = "outputs/pdf"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, meeting_data: Dict[str, Any], filename: Optional[str] = None) -> bytes:
        """
        Generates a PDF document for the given meeting data.
        Returns bytes and saves to file if filename is provided or generated.
        """
        # Strictly sanitize meeting data so no secrets or API keys can enter PDF
        meeting_data = sanitize_meeting_data(meeting_data)
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()
        
        # Custom styles
        primary_color = colors.HexColor("#1e3a8a")     # Deep Indigo / Navy
        secondary_color = colors.HexColor("#3b82f6")   # Blue
        text_color = colors.HexColor("#1f2937")        # Dark Slate
        bg_card = colors.HexColor("#f8fafc")           # Light gray/slate

        title_style = ParagraphStyle(
            'MeetingTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=primary_color,
            spaceAfter=6
        )

        subtitle_style = ParagraphStyle(
            'MeetingSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748b")
        )

        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=17,
            textColor=primary_color,
            spaceBefore=14,
            spaceAfter=6
        )

        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=text_color
        )

        bullet_style = ParagraphStyle(
            'Bullet',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=text_color,
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=4
        )

        decision_box_style = ParagraphStyle(
            'DecisionBox',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#065f46")
        )

        table_header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.white
        )

        table_cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=text_color
        )

        elements = []

        # 1. Header Banner
        header_text = "OFFICIAL MEETING MINUTES"
        elements.append(Paragraph(f"<b>{header_text}</b>", subtitle_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(meeting_data.get('title', 'Meeting Minutes'), title_style))
        elements.append(Spacer(1, 4))

        # Metadata Table
        meta_rows = [
            [
                Paragraph(f"<b>Date:</b> {meeting_data.get('date', 'N/A')}", body_style),
                Paragraph(f"<b>Time:</b> {meeting_data.get('time', 'N/A') or 'Standard Session'}", body_style),
                Paragraph(f"<b>Status:</b> {meeting_data.get('status', 'Draft')}", body_style)
            ]
        ]
        attendees = meeting_data.get('attendees', [])
        attendees_str = ", ".join(attendees) if isinstance(attendees, list) else str(attendees)
        meta_rows.append([
            Paragraph(f"<b>Attendees:</b> {attendees_str or 'All Invited Members'}", body_style),
            "", ""
        ])

        meta_table = Table(meta_rows, colWidths=[200, 180, 150])
        meta_table.setStyle(TableStyle([
            ('SPAN', (0, 1), (2, 1)),
            ('BACKGROUND', (0, 0), (-1, -1), bg_card),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=10))

        # 2. Executive Summary
        elements.append(Paragraph("1. Executive Summary", section_heading))
        summary = meeting_data.get('executive_summary', 'No executive summary provided.')
        elements.append(Paragraph(summary, body_style))
        elements.append(Spacer(1, 8))

        # 3. Key Discussion Points
        discussions = meeting_data.get('discussion_points', [])
        if discussions:
            elements.append(Paragraph("2. Key Discussion Points", section_heading))
            for pt in discussions:
                elements.append(Paragraph(f"&bull; {pt}", bullet_style))
            elements.append(Spacer(1, 8))

        # 4. Decisions Ratified
        decisions = meeting_data.get('decisions', [])
        if decisions:
            elements.append(Paragraph("3. Decisions Made & Resolutions", section_heading))
            dec_rows = []
            for d in decisions:
                dec_rows.append([Paragraph(f"&#10003; {d}", decision_box_style)])
            dec_table = Table(dec_rows, colWidths=[530])
            dec_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#065f46")),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#a7f3d0")),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(dec_table)
            elements.append(Spacer(1, 10))

        # 5. Action Items Table
        action_items = meeting_data.get('action_items', [])
        elements.append(Paragraph("4. Action Items & Deliverables", section_heading))
        if action_items:
            table_data = [
                [
                    Paragraph("Task Description", table_header_style),
                    Paragraph("Owner", table_header_style),
                    Paragraph("Deadline", table_header_style),
                    Paragraph("Priority", table_header_style),
                    Paragraph("Status", table_header_style)
                ]
            ]
            for item in action_items:
                table_data.append([
                    Paragraph(item.get('task', ''), table_cell_style),
                    Paragraph(item.get('owner', 'Unassigned'), table_cell_style),
                    Paragraph(item.get('deadline', 'TBD'), table_cell_style),
                    Paragraph(item.get('priority', 'Medium'), table_cell_style),
                    Paragraph(item.get('status', 'Pending'), table_cell_style)
                ])

            action_table = Table(table_data, colWidths=[210, 85, 85, 75, 75])
            action_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), primary_color),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(action_table)
        else:
            elements.append(Paragraph("No specific action items recorded.", body_style))

        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"), spaceAfter=8))
        footer_text = (
            "Generated by AI-Based Meeting Minutes Generator | "
            "Academic Project: S.Y. B.Sc. (AI & ML) 2026-2027 | "
            "Prof. Sarita Byagar (Guide)"
        )
        elements.append(Paragraph(f"<font size='7' color='#64748b'>{footer_text}</font>", subtitle_style))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # Save to disk
        safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', meeting_data.get('title', 'meeting_minutes'))[:40]
        meeting_id = meeting_data.get('id', 'temp')
        file_path = os.path.join(self.output_dir, filename or f"{safe_title}_{meeting_id}.pdf")
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        return pdf_bytes
