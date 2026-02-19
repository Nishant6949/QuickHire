import io
import json
import logging
import re

import anthropic
from flask import current_app, send_file
from fpdf import FPDF

from services.ai import call_claude, parse_ai_json

logger = logging.getLogger(__name__)


def generate_candidate_report(candidate):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(34, 197, 94)
    pdf.cell(0, 12, "QuickHire", new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(34, 197, 94)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    pdf.set_text_color(40, 40, 40)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Candidate Report", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    job = candidate.job

    def add_field(label, value):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(45, 7, label + ":")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(0, 7, str(value or "N/A"), new_x="LMARGIN", new_y="NEXT")

    add_field("Name", candidate.candidate_name)
    add_field("Email", candidate.candidate_email)
    add_field("Resume File", candidate.resume_filename)
    add_field("Job Title", job.title)
    add_field("Department", job.department)
    add_field("Location", job.location)
    add_field("Status", candidate.status.title())
    if candidate.interview_at:
        add_field("Interview", candidate.interview_at.strftime("%b %d, %Y at %I:%M %p"))

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(34, 197, 94)
    pdf.cell(0, 10, "Match Scores", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    scores = [
        ("Overall Match", candidate.match_score),
        ("Skills", candidate.skills_score),
        ("Experience", candidate.experience_score),
        ("Education", candidate.education_score),
    ]
    for label, score in scores:
        score_val = score or 0
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(45, 7, label + ":")
        pdf.set_font("Helvetica", "B", 10)
        if score_val >= 90:
            pdf.set_text_color(34, 197, 94)
        elif score_val >= 70:
            pdf.set_text_color(234, 179, 8)
        else:
            pdf.set_text_color(239, 68, 68)
        pdf.cell(0, 7, str(score_val) + "/100", new_x="LMARGIN", new_y="NEXT")

    if candidate.matched_skills:
        try:
            skills = json.loads(candidate.matched_skills)
            if skills:
                pdf.ln(4)
                pdf.set_font("Helvetica", "B", 13)
                pdf.set_text_color(34, 197, 94)
                pdf.cell(0, 10, "Matched Skills", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(40, 40, 40)
                pdf.multi_cell(0, 6, ", ".join(skills))
        except (json.JSONDecodeError, TypeError):
            pass

    if candidate.match_summary:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(34, 197, 94)
        pdf.cell(0, 10, "AI Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 6, candidate.match_summary)

    pdf_bytes = pdf.output()
    buffer = io.BytesIO(pdf_bytes)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", candidate.candidate_name or "candidate")
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=f"{safe_name}_report.pdf")


def generate_onboarding_doc(candidate, user):
    job = candidate.job
    api_key = current_app.config.get("ANTHROPIC_API_KEY")

    extracted = {}
    if api_key and candidate.resume_text:
        try:
            client = anthropic.Anthropic(api_key=api_key)
            prompt = (
                "Extract structured data from this resume. Return ONLY valid JSON:\n"
                "{\n"
                '  "full_name": "<name>",\n'
                '  "email": "<email or empty>",\n'
                '  "phone": "<phone or empty>",\n'
                '  "address": "<address or empty>",\n'
                '  "education": [{"degree": "<degree>", "institution": "<school>", "dates": "<dates>"}],\n'
                '  "experience": [{"title": "<role>", "company": "<company>", "duration": "<dates>"}],\n'
                '  "skills": ["<skill1>", "<skill2>"],\n'
                '  "certifications": ["<cert1>"],\n'
                '  "emergency_contact": "<if available or empty>"\n'
                "}\n\n=== RESUME ===\n" + candidate.resume_text
            )
            raw = call_claude(client, prompt)
            extracted = parse_ai_json(raw)
        except Exception as e:
            logger.error("Onboarding AI extraction failed: %s", e)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(34, 197, 94)
    pdf.cell(0, 12, user.company_name or "QuickHire", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "Employee Onboarding Document", new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(34, 197, 94)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
    pdf.ln(10)

    def section_title(title):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(34, 197, 94)
        pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    def field(label, value):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(50, 7, label + ":")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(0, 7, str(value or "N/A"), new_x="LMARGIN", new_y="NEXT")

    section_title("Personal Information")
    field("Name", extracted.get("full_name") or candidate.candidate_name)
    field("Email", extracted.get("email") or candidate.candidate_email)
    field("Phone", extracted.get("phone"))
    field("Address", extracted.get("address"))
    if extracted.get("emergency_contact"):
        field("Emergency Contact", extracted["emergency_contact"])
    pdf.ln(4)

    section_title("Position Details")
    field("Job Title", job.title)
    field("Department", job.department)
    field("Location", job.location)
    pdf.ln(4)

    skills = extracted.get("skills", [])
    if skills:
        section_title("Skills & Qualifications")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 6, ", ".join(skills))
        pdf.ln(4)

    matched_skills = []
    if candidate.matched_skills:
        try:
            matched_skills = json.loads(candidate.matched_skills)
        except (json.JSONDecodeError, TypeError):
            pass
    if matched_skills:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, "Matched to JD: " + ", ".join(matched_skills), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    education = extracted.get("education", [])
    if education:
        section_title("Education")
        for ed in education:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(40, 40, 40)
            pdf.cell(0, 7, str(ed.get("degree", "")), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, str(ed.get("institution", "")) + "  |  " + str(ed.get("dates", "")), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        pdf.ln(2)

    experience = extracted.get("experience", [])
    if experience:
        section_title("Work Experience")
        for exp in experience:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(40, 40, 40)
            pdf.cell(0, 7, str(exp.get("title", "")), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, str(exp.get("company", "")) + "  |  " + str(exp.get("duration", "")), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        pdf.ln(2)

    certs = extracted.get("certifications", [])
    if certs and any(certs):
        section_title("Certifications")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        for cert in certs:
            if cert:
                pdf.cell(0, 6, "- " + str(cert), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    if candidate.final_notes:
        section_title("Interviewer Notes")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 6, candidate.final_notes)

    pdf_bytes = pdf.output()
    buffer = io.BytesIO(pdf_bytes)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", candidate.candidate_name or "candidate")
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=f"{safe_name}_onboarding.pdf")
