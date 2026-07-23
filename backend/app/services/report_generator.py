"""
Generates a downloadable PDF report from a ReviewSummary (Milestone 2's analysis output).

Milestone-aware by design: this report only contains what the platform can actually produce
today (findings, severity breakdown, snippets) — it does not fabricate a remediation section or
narrative summary, since those are Remediation Agent / PR Summary Agent output (Milestone 3).
The report says so explicitly rather than silently omitting them, so nobody mistakes an early
export for a complete one.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.schemas import ReviewSummary, Submission

_SEVERITY_COLORS = {
    "critical": colors.HexColor("#c62328"),
    "high": colors.HexColor("#c62328"),
    "medium": colors.HexColor("#a06600"),
    "low": colors.HexColor("#1477bf"),
    "info": colors.HexColor("#6d6485"),
}
_SEVERITY_BG = {
    "critical": colors.HexColor("#ffe4e4"),
    "high": colors.HexColor("#ffe4e4"),
    "medium": colors.HexColor("#fff3dc"),
    "low": colors.HexColor("#e3f3ff"),
    "info": colors.HexColor("#f0eef7"),
}
_BRAND_PINK = colors.HexColor("#c2185b")
_BRAND_PURPLE = colors.HexColor("#5e35b1")
_TEXT_MUTED = colors.HexColor("#6d6485")


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], textColor=_BRAND_PURPLE, fontSize=22, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="ReportSubtitle", parent=styles["Normal"], textColor=_TEXT_MUTED, fontSize=10.5, spaceAfter=18,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", parent=styles["Heading2"], textColor=_BRAND_PURPLE, spaceBefore=18, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="FindingTitle", parent=styles["Heading3"], textColor=colors.HexColor("#241b3a"),
        fontSize=12.5, spaceBefore=0, spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="FindingBody", parent=styles["Normal"], fontSize=9.5, leading=13.5, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="FindingMeta", parent=styles["Normal"], fontSize=8, textColor=_TEXT_MUTED, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="Snippet", parent=styles["Code"], fontSize=8.5, leading=11, backColor=colors.HexColor("#14101f"),
        textColor=colors.HexColor("#d8d2f5"), borderPadding=8, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Disclaimer", parent=styles["Normal"], fontSize=8, textColor=_TEXT_MUTED,
        alignment=TA_CENTER, spaceBefore=24,
    ))
    return styles


def _escape(text: str) -> str:
    """Reportlab Paragraphs interpret a subset of HTML/XML — escape user/code content so
    submitted code containing '<', '>', or '&' can't be misinterpreted as markup tags."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _severity_badge_table(severity: str, styles) -> Table:
    label = severity.upper()
    t = Table([[label]], colWidths=[0.85 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _SEVERITY_BG.get(severity, colors.whitesmoke)),
        ("TEXTCOLOR", (0, 0), (-1, -1), _SEVERITY_COLORS.get(severity, colors.black)),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def generate_pdf_report(submission: Submission, summary: ReviewSummary) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
    )
    styles = _build_styles()
    story = []

    # --- Header ---
    story.append(Paragraph("AI Code Review &amp; Security Analysis Report", styles["ReportTitle"]))
    generated = summary.generated_at.strftime("%B %d, %Y at %H:%M UTC")
    story.append(Paragraph(
        f"Submission {submission.id[:8]} · {submission.language.value} ({submission.source.value}) "
        f"· generated {generated}",
        styles["ReportSubtitle"],
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2d6f7")))
    story.append(Spacer(1, 14))

    # --- Scope note (milestone-honest) ---
    story.append(Paragraph(
        "This report covers the Code Analysis and Security Vulnerability agents' findings "
        "(pattern-based static analysis — see the project's detection-rules documentation for "
        "what each rule catches and its known limitations). Remediation suggestions and a "
        "PR-style narrative summary are produced by later-milestone agents not yet reflected here.",
        styles["FindingMeta"],
    ))

    # --- Severity summary ---
    story.append(Paragraph("Severity summary", styles["SectionHeading"]))
    counts = summary.counts_by_severity
    sev_rows = [["Critical", "High", "Medium", "Low", "Info"],
                [str(counts.critical), str(counts.high), str(counts.medium), str(counts.low), str(counts.info)]]
    sev_table = Table(sev_rows, colWidths=[1.0 * inch] * 5)
    sev_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4f2ff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2d6f7")),
    ]))
    story.append(sev_table)

    if summary.agent_errors:
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "Note: " + " · ".join(_escape(e) for e in summary.agent_errors),
            ParagraphStyle(name="AgentError", parent=styles["FindingMeta"], textColor=colors.HexColor("#a06600")),
        ))

    # --- Findings ---
    story.append(Paragraph("Findings", styles["SectionHeading"]))

    if not summary.findings:
        story.append(Paragraph(
            "No issues found by the Code Analysis or Security Vulnerability agents.",
            styles["FindingBody"],
        ))
    else:
        for finding in summary.findings:
            block = []
            loc = finding.location
            loc_text = f"L{loc.start_line}" if loc.start_line == loc.end_line else f"L{loc.start_line}\u2013{loc.end_line}"
            category_label = "Security" if finding.category == "security" else "Code Quality"

            header_table = Table(
                [[_severity_badge_table(finding.severity.value, styles),
                  Paragraph(_escape(finding.title), styles["FindingTitle"]),
                  Paragraph(loc_text, styles["FindingMeta"])]],
                colWidths=[0.95 * inch, 4.6 * inch, 0.7 * inch],
            )
            header_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (2, 0), (2, 0), "RIGHT"),
            ]))
            block.append(header_table)

            tags = [category_label]
            if finding.owasp_category:
                tags.append(finding.owasp_category)
            if finding.cwe_id:
                tags.append(finding.cwe_id)
            if finding.knowledge_base_refs:
                tags.append("KB-grounded")
            block.append(Paragraph(" · ".join(_escape(t) for t in tags), styles["FindingMeta"]))

            block.append(Paragraph(_escape(finding.description), styles["FindingBody"]))

            if loc.snippet:
                snippet_text = _escape(loc.snippet).replace("\n", "<br/>")
                block.append(Paragraph(snippet_text, styles["Snippet"]))

            block.append(Spacer(1, 6))
            block.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#efe7fb")))
            block.append(Spacer(1, 6))

            story.append(KeepTogether(block))

    story.append(Paragraph(
        "Generated by the AI Code Review &amp; Security Analysis Agent &mdash; pattern-based "
        "static analysis, not a substitute for human review or a formal security audit.",
        styles["Disclaimer"],
    ))

    doc.build(story)
    return buffer.getvalue()
