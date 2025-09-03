"""Generate a PDF guide explaining how the QR Attendance System works.
Run: python generate_system_guide_pdf.py
Outputs: system_guide.pdf
"""
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak
from reportlab.lib import fonts

README_SECTION_TITLE = "How the System Works (Step by Step)"
OUTPUT = "system_guide.pdf"

# Core guide content (condensed/adapted from README)
CONTENT = [
    ("Overview", "A Django-based QR code attendance platform allowing student onboarding, seminar lifecycle control, QR generation, scanning, and export."),
    ("Data Model", "Student (id, contact, course), Seminar (manual status: Inactive/Active/Ended), Attendance (unique student+seminar record with timestamp)."),
    ("Student Import", "Upload CSV: student_id,name,email,phone,course. Existing IDs update, new IDs create records."),
    ("QR Generation", "Bulk regenerate creates/overwrites images per student; individual generate shows one QR. Download ZIP for all codes."),
    ("QR Image Storage", "Images saved under media/qr_codes/. Safe to regenerate; filenames include student ID."),
    ("Scanning Flow", "Active seminar selected -> camera decodes QR -> AJAX POST -> backend validates & creates attendance -> JSON response updates UI with sound feedback."),
    ("Manual / Upload Fallback", "If camera blocked, user can type student ID or upload an image containing a QR code."),
    ("Duplicate Protection", "Database uniqueness + get_or_create ensures no multiple rows for same student & seminar. Duplicate triggers alternate sound."),
    ("Seminar Status", "Manually toggled; only Active seminars appear in scanner. No timezone auto-transitions to avoid drift issues."),
    ("Attendance Export", "Per-seminar CSV: student identity fields + date/time split. Live ORM join ensures updated student info."),
    ("Missing QR Handling", "Student list shows placeholder if image missing; run regenerate to fill gaps."),
    ("Admin Customization", "Minimal index (recent actions removed) plus user/group management and inline seminar status editing."),
    ("Security Notes", "Avoid embedding full PII in QR. Change admin creds. Set DEBUG=False in production. Configure ALLOWED_HOSTS & HTTPS."),
    ("Extensibility", "Possible additions: signed QR payloads, source tracking, WebSocket dashboards, async generation, pagination."),
    ("Deployment", "Collect static, use Whitenoise or CDN, run under Gunicorn/Uvicorn behind Nginx with HTTPS. Backup DB & media."),
    ("Troubleshooting", "1) Missing seminar -> set Active. 2) Duplicate sound -> camera still sees QR. 3) Empty export -> no scans yet. 4) Missing QR -> regenerate."),
]


def header_footer(c: canvas.Canvas, doc):
    c.saveState()
    page = doc.page
    c.setFont("Helvetica", 8)
    c.drawString(20*mm, 10*mm, f"QR Attendance System Guide | Page {page}")
    c.drawRightString(200*mm, 10*mm, datetime.now().strftime("%Y-%m-%d"))
    c.restoreState()


def build_pdf(path: Path):
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    h_style = styles['Heading2']
    body = styles['BodyText']
    body.fontSize = 9
    body.leading = 12

    story = []
    story.append(Paragraph("QR Attendance System – Technical Guide", title_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Concise internal document explaining functional flow, architecture choices, and operational best practices.", body))
    story.append(Spacer(1, 12))

    for section, text in CONTENT:
        story.append(Paragraph(section, h_style))
        story.append(Paragraph(text, body))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Generated automatically. You can extend this file by editing generate_system_guide_pdf.py.", body))

    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=20*mm, bottomMargin=15*mm)
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)


if __name__ == "__main__":
    out_path = Path(OUTPUT)
    build_pdf(out_path)
    print(f"Generated {out_path.resolve()}")
