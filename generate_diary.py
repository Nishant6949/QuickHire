#!/usr/bin/env python3
"""Generate QuickHire Progress Report / Diary PDF with 8 meeting records."""

from fpdf import FPDF
import os


class DiaryPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 8, "QuickHire: AI-Native Resume Screening Web-App | Progress Report", align="C")
            self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, text):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def subsection_title(self, text):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(0, 0, 0)
        self.cell(0, 9, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bold_text(self, label, value=""):
        self.set_font("Helvetica", "B", 10)
        if value:
            self.cell(0, 6, f"{label} {value}", new_x="LMARGIN", new_y="NEXT")
        else:
            self.cell(0, 6, label, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)

    def bullet_point(self, text):
        self.set_font("Helvetica", "", 10)
        self.cell(6, 5.5, "-")
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def bullet_bold(self, label, value):
        self.set_font("Helvetica", "B", 10)
        lw = self.get_string_width(label + " ")
        self.cell(8, 5.5, "-")
        self.cell(lw, 5.5, label)
        self.set_font("Helvetica", "", 10)
        remaining_w = self.w - self.r_margin - self.get_x()
        if remaining_w < 20:
            self.ln()
            self.cell(8, 5.5, "")
            self.multi_cell(0, 5.5, value)
        else:
            self.multi_cell(0, 5.5, value)
        self.ln(1)

    def files_table(self, left_header, right_header, files_left, files_right):
        col_w = 92
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(210, 225, 245)
        self.cell(col_w, 7, left_header, border=1, fill=True)
        self.cell(col_w, 7, right_header, border=1, fill=True)
        self.ln()
        self.set_font("Helvetica", "", 9)
        rows = list(zip(files_left, files_right))
        for i, (f, p) in enumerate(rows):
            fill = i % 2 == 0
            if fill:
                self.set_fill_color(240, 245, 255)
            self.cell(col_w, 7, f, border=1, fill=fill)
            self.cell(col_w, 7, p, border=1, fill=fill)
            self.ln()
            self.set_fill_color(255, 255, 255)
        self.ln(4)

    def progress_table(self, rows):
        col_w = [38, 38, 108]
        line_h = 5.0

        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(210, 225, 245)
        headers = ["Date", "Team Member", "Notes"]
        for i, h in enumerate(headers):
            self.cell(col_w[i], 8, h, border=1, fill=True, align="C")
        self.ln()
        self.set_font("Helvetica", "", 8)

        for row_i, r in enumerate(rows):
            fill = row_i % 2 == 0
            if fill:
                self.set_fill_color(240, 245, 255)
            else:
                self.set_fill_color(255, 255, 255)

            lines_per_col = []
            for ci, val in enumerate(r):
                w = col_w[ci] - 4
                n = max(1, int(self.get_string_width(val) / w) + 1)
                lines_per_col.append(n)

            row_h = max(max(lines_per_col) * line_h + 6, 14)

            y_before = self.get_y()
            if y_before + row_h > self.h - self.b_margin - 5:
                self.add_page()
                y_before = self.get_y()

            x_start = self.get_x()
            for ci, val in enumerate(r):
                x = x_start + sum(col_w[:ci])
                self.set_xy(x, y_before)
                self.rect(x, y_before, col_w[ci], row_h, style="DF" if fill else "D")
                self.set_xy(x + 2, y_before + 2)
                self.multi_cell(col_w[ci] - 4, line_h, val, align="L")

            self.set_xy(x_start, y_before + row_h)

    def meeting_record(self, number, subtitle, date, time, location, objective,
                       present, absent, topics, next_meeting_text):
        if self.get_y() > self.h - 80:
            self.add_page()

        self.set_draw_color(0, 0, 0)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, f"MEETING {number}", new_x="LMARGIN", new_y="NEXT")
        if subtitle:
            self.set_font("Helvetica", "B", 11)
            self.cell(0, 7, subtitle, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        self.bold_text("Project Title:", "QuickHire: Smart Resume Screening")
        self.bold_text("Facilitator:", "Fakhra Jabeen")
        self.bold_text("Team Members:", "Aatmik Dahal, Nishant Khadka, Nischal Gautam, Upadesh Silwal")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, f"Date: {date} | Time: {time} | Location: {location}", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        self.bold_text("Meeting Objective(s):")
        self.body_text(objective)

        self.bold_text("Attendance:")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, f"  Present: {present}", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 6, f"  Absent: {absent}", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        self.bold_text("Agenda/Issues:")
        for i, t in enumerate(topics):
            if self.get_y() > self.h - 20:
                self.add_page()
            self.bullet_bold(f"Topic {i+1}:", t)

        self.ln(2)
        self.bold_text("Next Meeting:", next_meeting_text)
        self.ln(4)


def build_pdf():
    pdf = DiaryPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ── COVER PAGE ──
    pdf.ln(25)
    pdf.set_font("Helvetica", "B", 28)
    pdf.cell(0, 14, "IT Capstone Project 1", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 28)
    pdf.cell(0, 14, "PROGRESS REPORT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "QUICKHIRE: AI-NATIVE RESUME SCREENING", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "WEB-APP", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Team Members:", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    members = [
        "- Aatmik Dahal (s8140413)",
        "- Nishant Khadka",
        "- Nischal Gautam",
        "- Upadesh Silwal",
    ]
    for m in members:
        pdf.cell(0, 7, m, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Sponsor: Fakhra Jabeen", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Date: 7th March 2026", align="C", new_x="LMARGIN", new_y="NEXT")

    # ── TABLE OF CONTENTS ──
    pdf.add_page()
    pdf.section_title("Table of Contents")
    toc = [
        "1. Introduction",
        "2. Frontend UI/UX Subsystem Progress Report",
        "3. Backend & Security Subsystem Progress Report",
        "4. AI Engine & Screening Subsystem Progress Report",
        "5. Database Subsystem Progress Report",
        "6. Design and Style Constants",
        "7. Database Schema",
        "8. Meeting Records",
    ]
    for i, t in enumerate(toc):
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(10, 7, f"  {i+1}.")
        pdf.cell(0, 7, t.split(". ", 1)[1], new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # ── 1. INTRODUCTION ──
    pdf.section_title("Introduction")
    pdf.body_text(
        'This is our group\'s comprehensive progress report and diary for the Minimum Viable Product '
        '(MVP) of "QuickHire."'
    )
    pdf.body_text(
        "At the start of the project, we established strict architectural guidelines focusing on creating a "
        "B2B SaaS platform that automates resume screening using Large Language Models (LLMs). "
        "The MVP is now complete and fully deployed to production. The core functionalities -- frontend "
        "interface, backend route-guarding, cloud database integration, and the Claude AI resume-ranking "
        "engine -- are all operational with little to no bugs remaining. The system has been tested "
        "end-to-end and is stable in its current state."
    )
    pdf.body_text(
        "The final phase of the project involved migrating our local SQLite database to Supabase "
        "(PostgreSQL), implementing the automated email-invite API with Google Calendar integration, "
        "deploying to Vercel, and finalizing the post-interview HR workflow including onboarding "
        "PDF generation. All of these milestones have been achieved as part of the MVP delivery."
    )
    pdf.body_text(
        "Our group has kept meticulous track of our meeting records and subsystem developments, "
        "which are provided below. We have also identified a real-world edge case during "
        'testing -- candidates submitting "AI-optimized resumes" to bypass ATS systems -- and '
        "actively innovated our prompt engineering to neutralize this bias."
    )

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Project Repositories:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(1)
    pdf.bullet_bold("Git:", "https://github.com/dahalaatmik/QuickHire.git")
    pdf.bullet_bold("Live URL:", "https://quick-hire-vzf7.vercel.app/")
    pdf.ln(4)

    # ── 2. FRONTEND UI/UX SUBSYSTEM ──
    pdf.add_page()
    pdf.section_title("Frontend UI/UX Subsystem Progress Report")
    pdf.files_table("Files Used", "FRONTEND & UI/UX",
        ["landing_page.html", "dashboard.html", "styles.css"],
        ["landing_animations.js", "auth_forms.js", "sidebar_nav.js"]
    )

    pdf.progress_table([
        ["22/01/2026", "Upadesh",
         "Established the UI/UX Design System (Strict Dark Mode: #0B0C10 background, "
         "Neon Cyan accents). Built the base HTML structure for the Landing Page "
         "utilizing the F-Pattern reading layout."],
        ["24/01/2026", "Upadesh",
         "Implemented JavaScript animations for the Landing Page. Created "
         'the "Kinso-style" sticky scroll where the dashboard mockup changes as '
         "the user scrolls through feature texts."],
        ["28/01/2026", "Nishant",
         "Built the Sign-in and Registration frontend forms. Added JavaScript "
         "form validation for email format checking, password strength, and "
         "matching confirmation fields."],
        ["02/02/2026", "Upadesh",
         "Developed the B2B Dashboard UI. Built the sidebar navigation, the Job "
         "Creation drag-and-drop zone, and the Candidate Ranking data table."],
        ["06/02/2026", "Nishant",
         "Created the dynamic Match Score ring component. Used JavaScript to alter "
         "the CSS ring colour based on data (Green for above 90 percent, Yellow for "
         "70 to 89 percent, Red for below 70 percent)."],
        ["14/02/2026", "Upadesh",
         "Built the Slide-out Candidate Drawer UI. Added z-index overlays and smooth "
         "transition animations for when a user clicks a candidate row."],
    ])

    # ── 3. BACKEND & SECURITY SUBSYSTEM ──
    pdf.add_page()
    pdf.section_title("Backend & Security Subsystem Progress Report")
    pdf.files_table("Files Used", "BACKEND ROUTING & SECURITY",
        ["app.py", "routes.py"],
        ["auth_controller.py", "session_manager.py"]
    )

    pdf.progress_table([
        ["01/02/2026", "Nischal",
         "Set up the core Python backend server architecture. Created routing logic "
         "for /login, /register, and API endpoints for the frontend to hit."],
        ["05/02/2026", "Nischal",
         "Implemented Werkzeug security modules. Built the logic to execute "
         "PBKDF2 password hashing with unique salts before storage."],
        ["09/02/2026", "Nischal",
         "Built dashboard route-guards and session management. Tested security: "
         "unauthenticated users attempting to access /dashboard or /candidates "
         "are successfully hard-bounced back to /login."],
        ["16/02/2026", "Nischal",
         "Discovered a bug where session tokens were expiring prematurely during "
         "long resume uploads. Patched the timeout configuration to allow for "
         "heavy processing."],
    ])

    # ── 4. AI ENGINE & SCREENING SUBSYSTEM ──
    pdf.add_page()
    pdf.section_title("AI Engine & Screening Subsystem Progress Report")
    pdf.files_table("Files Used", "AI ENGINE & PARSING",
        ["ai_core.py", "pdf_parser.py"],
        ["claude_service.py", "ranking_algo.py"]
    )

    pdf.progress_table([
        ["08/02/2026", "Aatmik",
         "Integrated the Claude API via the Anthropic SDK. Wrote the PDF parser "
         "script using pdfplumber to extract raw text strings from uploaded Job "
         "Description documents."],
        ["10/02/2026", "Aatmik",
         "Engineered the API prompt to force Claude to return a strictly structured "
         "JSON object containing job requirements, required skills, and experience "
         "benchmarks for accurate scoring."],
        ["14/02/2026", "Aatmik",
         "Built the bulk-resume processing loop. The Python backend successfully "
         "sends multiple resumes to the AI, compares them against the job description, "
         "and generates a match score from 0 to 100."],
        ["18/02/2026", "Aatmik",
         "Innovation/Edge Case: Identified an issue during testing where "
         '"AI-optimized resumes" (keyword-stuffed by applicants) scored artificially '
         "high. Began modifying prompt constraints to weigh semantic contextual "
         "experience over simple keyword matching to neutralize this bias."],
    ])

    # ── 5. DATABASE SUBSYSTEM ──
    pdf.add_page()
    pdf.section_title("Database Subsystem Progress Report")
    pdf.files_table("Files Used", "DATABASE MANAGEMENT",
        ["db_config.py", "schema.sql"],
        ["models.py", "crud_operations.py"]
    )

    pdf.progress_table([
        ["03/02/2026", "Nischal",
         "Implemented local SQLite database to facilitate rapid MVP development. "
         "Mapped relational schemas for Users, Organizations, Job Postings, "
         "and Candidates."],
        ["12/02/2026", "Nischal",
         "Finalized CRUD operations for Job Postings. Added cascading delete logic. "
         "Tested and verified: deleting a Job Posting now successfully purges all "
         "linked candidate applications for that specific job while keeping the "
         "candidate in the global pool."],
        ["18/02/2026", "Nischal",
         "Began preparing the schema migration scripts to move the database from "
         "local SQLite to Supabase (PostgreSQL) for our upcoming production "
         "deployment."],
    ])

    # ── 6. DESIGN AND STYLE CONSTANTS ──
    pdf.add_page()
    pdf.section_title("Design and Style Constants")

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Colors (Strict Dark Mode)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(1)
    pdf.bullet_bold("Canvas Background:", "Deep Void #0B0C10")
    pdf.bullet_bold("Surface/Cards:", "Charcoal #1F2833")
    pdf.bullet_bold("Primary Accent:", "Neon Cyan #66FCF1")
    pdf.bullet_bold("Secondary Accent:", "Muted Teal #45A29E")
    pdf.bullet_bold("High-Match Status:", "Emerald Green #2ECC71")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Typography (Inter Font)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(1)
    pdf.bullet_bold("Headlines:", "fontWeight: 700, Color: #FFFFFF")
    pdf.bullet_bold("Body Text:", "fontWeight: 400, Color: #C5C6C7")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Key Text Strings", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(1)
    pdf.bullet_bold("App Name:", "QuickHire")
    pdf.bullet_bold("Tagline:", '"Scale Your Team, Not Your Workload."')
    pdf.bullet_bold("Drop Zone:", '"Drop Job Description PDF here to initialize the AI Agent."')
    pdf.ln(4)

    # ── 7. DATABASE SCHEMA ──
    pdf.section_title("Database Schema (Current SQLite MVP)")

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "1. Organizations Table", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for f in ["org_id (PK, Integer)", "org_name (VARCHAR)", "website_url (TEXT)"]:
        pdf.bullet_point(f)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "2. Users Table", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for f in ["user_id (PK, Integer)", "org_id (FK, Integer)", "email (VARCHAR, Unique)", "password_hash (TEXT)"]:
        pdf.bullet_point(f)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "3. Job Postings Table", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for f in ["job_id (PK, Integer)", "org_id (FK, Integer)", "job_title (VARCHAR)",
              "ai_criteria (JSON)", "status (VARCHAR - Open, Drafting, Closed)"]:
        pdf.bullet_point(f)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "4. Candidates Table", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for f in ["candidate_id (PK, Integer)", "job_id (FK, Integer)", "name (VARCHAR)",
              "match_score (DECIMAL)", "resume_blob_path (TEXT)",
              "status (VARCHAR - Pending, Interview, Hired, Rejected)"]:
        pdf.bullet_point(f)
    pdf.ln(6)

    # ── 8. MEETING RECORDS ──
    pdf.add_page()
    pdf.section_title("Meeting Records")

    # Meeting 1 - 19/01/2026
    pdf.meeting_record(
        1, "",
        "19/01/2026", "7:00 PM", "Discord",
        "Initial project kick-off, finalize tech stack, and distribute workload for the MVP architecture.",
        "Aatmik Dahal, Nishant Khadka, Nischal Gautam, Upadesh Silwal",
        "None",
        [
            "Confirmed Python for backend logic, HTML/JS/CSS for frontend, and "
            "SQLite for the initial MVP database (planning Supabase for production).",
            "Assigned roles: Aatmik on AI API and overall architecture, Nishant on "
            "frontend forms and database setup, Upadesh supporting UI components, "
            "Nischal supporting backend security.",
            "Created the GitHub repository and established branching and commit rules.",
        ],
        "26/01/2026, 8:00 PM, Discord"
    )

    # Meeting 2 - 23/01/2026 (NEW)
    pdf.meeting_record(
        2, "",
        "23/01/2026", "7:30 PM", "Discord",
        "Review initial frontend progress and discuss database schema requirements.",
        "Aatmik Dahal, Nishant Khadka, Upadesh Silwal",
        "Nischal Gautam",
        [
            "Aatmik presented the landing page structure with the dark mode design system. "
            "The F-Pattern layout and sticky scroll animation concept were approved by the team.",
            "Discussed the database schema requirements. Agreed on four core tables: Organizations, "
            "Users, Job Postings, and Candidates. Nishant confirmed he would begin building the "
            "SQLite schema for rapid MVP development.",
            "Reviewed the project timeline and confirmed the target of having the AI scoring "
            "pipeline functional by mid-February. Aatmik outlined the Anthropic SDK integration plan.",
        ],
        "26/01/2026, 8:00 PM, Discord"
    )

    # Meeting 3 - 26/01/2026
    pdf.meeting_record(
        3, "",
        "26/01/2026", "8:00 PM", "Discord",
        "Review Frontend progress, confirm database relational logic, and define AI data flow.",
        "Aatmik Dahal, Nishant Khadka, Nischal Gautam, Upadesh Silwal",
        "None",
        [
            "Aatmik demonstrated the Landing Page JavaScript animations. Team approved the "
            "dark mode minimalist aesthetic and the sticky scroll dashboard mockup.",
            "Nishant presented the SQLite schema. We established a critical business logic "
            "rule: the Candidate Pool must retain candidate data globally for the organization, "
            "even if a specific job posting is deleted.",
            "Aatmik outlined the JSON payload structure required for the Claude API to read "
            "the Job Descriptions effectively. Discussed how the prompt engineering would "
            "need to enforce structured output.",
        ],
        "02/02/2026, 8:00 PM, Discord"
    )

    # Meeting 4 - 02/02/2026 (NEW)
    pdf.meeting_record(
        4, "",
        "02/02/2026", "8:00 PM", "Discord",
        "Review authentication implementation and plan the dashboard backend integration.",
        "Aatmik Dahal, Nishant Khadka",
        "Nischal Gautam, Upadesh Silwal",
        [
            "Nishant demonstrated the completed Sign-in and Registration frontend forms with "
            "JavaScript validation. Email format checking, password strength meters, and matching "
            "confirmation fields were all working correctly.",
            "Aatmik walked through the Flask app factory setup and Blueprint routing structure. "
            "Discussed how the backend would handle user sessions using Flask-Login and Werkzeug "
            "for password hashing.",
            "Noted the absence of Nischal and Upadesh for the second consecutive meeting. "
            "Agreed that Aatmik and Nishant would continue driving the core development to "
            "stay on schedule. Tasks originally assigned to absent members were redistributed.",
        ],
        "06/02/2026, 7:30 PM, Discord"
    )

    # Meeting 5 - 06/02/2026 (NEW)
    pdf.meeting_record(
        5, "",
        "06/02/2026", "7:30 PM", "Discord",
        "Review the AI integration setup and discuss the resume upload workflow.",
        "Aatmik Dahal, Nishant Khadka, Upadesh Silwal",
        "Nischal Gautam",
        [
            "Aatmik demonstrated the initial Claude API integration. The system was able to "
            "accept a job description and a sample resume, then return a structured JSON "
            "response with match scoring. Early results looked promising.",
            "Discussed the resume upload workflow. Agreed to use Supabase cloud storage for "
            "production file management since Vercel serverless functions have limited local "
            "storage. For the MVP, local storage would suffice.",
            "Nishant showed the dynamic Match Score ring component for the frontend. The colour-coded "
            "ring (green, yellow, red) based on percentage thresholds was approved by the team.",
            "Upadesh attended and was asked to help test the upload flow across different browsers. "
            "He agreed to run compatibility checks during the following week.",
        ],
        "09/02/2026, 8:00 PM, Discord"
    )

    # Meeting 6 - 09/02/2026
    pdf.meeting_record(
        6, "",
        "09/02/2026", "8:00 PM", "Discord",
        "Connect the UI dashboard to the Python backend and test security implementations.",
        "Aatmik Dahal, Nishant Khadka, Nischal Gautam, Upadesh Silwal",
        "None",
        [
            "Aatmik successfully demonstrated the route-locking mechanism using Flask-Login. "
            "Unauthenticated users are correctly bounced back to the login page when attempting "
            "to access protected routes.",
            "Tested the Job Posting creation flow from the frontend to the backend database. "
            "Data successfully writes to SQLite. The form validation and backend processing "
            "were working as expected.",
            "Identified a bug where session tokens were expiring too quickly during large file "
            "uploads. Aatmik took ownership of patching the timeout configuration to handle "
            "longer processing times.",
        ],
        "13/02/2026, 8:00 PM, Discord"
    )

    # Meeting 7 - 13/02/2026 (NEW)
    pdf.meeting_record(
        7, "",
        "13/02/2026", "8:00 PM", "Discord",
        "Review the bulk resume screening results and test the candidate management interface.",
        "Aatmik Dahal, Nishant Khadka",
        "Nischal Gautam, Upadesh Silwal",
        [
            "Aatmik demonstrated the complete AI screening pipeline. Multiple resumes were uploaded, "
            "processed through pdfplumber for text extraction, scored by Claude, and displayed with "
            "match percentages on the candidate cards. The end-to-end flow worked reliably.",
            "Tested the candidate drawer UI that Aatmik had built. Clicking a candidate row slides "
            "out a detailed panel with their score breakdown and resume highlights. The transition "
            "animations were smooth and the z-index overlays functioned correctly.",
            "Discussed the remaining work: email invitation system with Google Calendar links, "
            "analytics dashboard, onboarding PDF generation, and the Supabase migration. Set a "
            "target to have everything ready for deployment by the 18th.",
        ],
        "18/02/2026, 8:00 PM, Discord"
    )

    # Meeting 8 - 18/02/2026
    pdf.meeting_record(
        8, "(Final Stages Review)",
        "18/02/2026", "8:00 PM", "Discord",
        "Run full end-to-end system tests, evaluate AI accuracy, and review the project status ahead of submission.",
        "Aatmik Dahal, Nishant Khadka, Nischal Gautam, Upadesh Silwal",
        "None",
        [
            "Ran end-to-end MVP tests: Logged in, uploaded a JD, uploaded 5 test resumes. "
            "The AI correctly parsed, evaluated, and ranked the best candidate at a 94 percent "
            "match. Core system is officially operational with little to no bugs remaining.",
            'Nishant raised a testing issue regarding "AI-optimized resumes" scoring artificially '
            "high. Aatmik has already adjusted the prompt engineering to weigh semantic experience "
            "over keyword stuffing, which has successfully neutralized this bias.",
            "The project is now in its final stages. The Supabase migration is complete, the "
            "email-invite API with Google Calendar integration is working, and the application "
            "is live on Vercel. The team confirmed that only minor polish and documentation "
            "remain before the submission deadline on 7th March.",
            "Discussed the documentation deliverables: the User Manual and Technical Implementation "
            "Document are near completion. Nishant confirmed he would finalize formatting. "
            "The team agreed the MVP has met all of its original objectives.",
        ],
        "N/A -- Project is in its final stages. Submission scheduled for 7th March 2026."
    )

    # ── OUTPUT ──
    out_path = os.path.expanduser("~/Downloads/QuickHire_Progress_Report_Diary.pdf")
    pdf.output(out_path)
    print(f"PDF saved to {out_path}")
    print(f"Total pages: {pdf.page_no()}")


if __name__ == "__main__":
    build_pdf()
