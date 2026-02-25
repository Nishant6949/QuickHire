from fpdf import FPDF

class DiaryPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def subsection_title(self, title):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text):
        self.set_font("Helvetica", "", 11)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def bold_text(self, text):
        self.set_font("Helvetica", "B", 11)
        self.multi_cell(0, 6, text)

    def bullet_point(self, text, indent=10):
        self.set_x(self.l_margin + indent)
        self.set_font("Helvetica", "", 11)
        bw = self.get_string_width("- ")
        self.cell(bw, 6, "- ")
        self.multi_cell(0, 6, text)
        self.ln(1)

    def bullet_bold_value(self, label, value, indent=10):
        self.set_x(self.l_margin + indent)
        self.set_font("Helvetica", "B", 11)
        lw = self.get_string_width(label)
        self.cell(lw, 6, label)
        self.set_font("Helvetica", "", 11)
        self.multi_cell(0, 6, value)
        self.ln(1)

    def files_table(self, header, files_left, files_right=None):
        col_w = (self.w - self.l_margin - self.r_margin) / 2
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(220, 235, 210)
        self.cell(col_w, 8, "Files Used", border=1, fill=True)
        self.cell(col_w, 8, header, border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        max_rows = max(len(files_left), len(files_right) if files_right else 0)
        for i in range(max_rows):
            left = files_left[i] if i < len(files_left) else ""
            right = files_right[i] if files_right and i < len(files_right) else ""
            self.cell(col_w, 7, left, border=1)
            self.cell(col_w, 7, right, border=1, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def progress_table(self, rows):
        date_w = 28
        member_w = 28
        notes_w = self.w - self.l_margin - self.r_margin - date_w - member_w
        line_h = 5.0

        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(220, 235, 210)
        self.cell(date_w, 8, "Date", border=1, fill=True)
        self.cell(member_w, 8, "Member", border=1, fill=True)
        self.cell(notes_w, 8, "Notes", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "", 9)
        for row in rows:
            date, member, notes = row
            lines = self.multi_cell(notes_w - 4, line_h, notes, dry_run=True, output="LINES")
            row_h = max(len(lines) * line_h + 6, 14)

            if self.get_y() + row_h > self.h - 25:
                self.add_page()
                self.set_font("Helvetica", "B", 9)
                self.set_fill_color(220, 235, 210)
                self.cell(date_w, 8, "Date", border=1, fill=True)
                self.cell(member_w, 8, "Member", border=1, fill=True)
                self.cell(notes_w, 8, "Notes", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
                self.set_font("Helvetica", "", 9)

            y_start = self.get_y()
            x_start = self.get_x()
            self.rect(x_start, y_start, date_w, row_h)
            self.rect(x_start + date_w, y_start, member_w, row_h)
            self.rect(x_start + date_w + member_w, y_start, notes_w, row_h)
            self.set_xy(x_start + 1, y_start + 2)
            self.cell(date_w - 2, line_h, date)
            self.set_xy(x_start + date_w + 1, y_start + 2)
            self.cell(member_w - 2, line_h, member)
            self.set_xy(x_start + date_w + member_w + 2, y_start + 2)
            self.multi_cell(notes_w - 4, line_h, notes)
            self.set_y(y_start + row_h)
        self.ln(6)

    def meeting_record(self, number, subtitle, date, time, location, objective, present, absent, topics, next_date, next_time, next_loc, next_obj):
        if self.get_y() > self.h - 100:
            self.add_page()

        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, f"MEETING {number}" + (f" ({subtitle})" if subtitle else ""), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        info = [
            ("Project Title: ", "QuickHire: AI-Native Resume Screening Web-App"),
            ("Facilitator: ", "Fakhra Jabeen"),
            ("Team Members: ", "Aatmik Dahal, Nishant Khadka, Nischal Gautam, Upadesh Silwal"),
            ("Date: ", f"{date} | Time: {time} | Location: {location}"),
        ]
        for label, value in info:
            self.set_font("Helvetica", "B", 10)
            lw = self.get_string_width(label)
            self.cell(lw, 5.5, label)
            self.set_font("Helvetica", "", 10)
            self.multi_cell(0, 5.5, value)
            self.ln(1)

        self.ln(2)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 5.5, "Meeting Objective(s):", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.5, objective)
        self.ln(2)

        self.set_font("Helvetica", "B", 10)
        self.cell(0, 5.5, "Attendance:", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.bullet_bold_value("Present: ", present, indent=8)
        self.bullet_bold_value("Absent: ", absent, indent=8)
        self.ln(1)

        self.set_font("Helvetica", "B", 10)
        self.cell(0, 5.5, "Agenda/Issues:", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        for i, topic in enumerate(topics, 1):
            self.set_x(self.l_margin + 8)
            self.set_font("Helvetica", "B", 10)
            tl = f"Topic {i}: "
            tw = self.get_string_width(tl)
            self.cell(tw, 5.5, tl)
            self.set_font("Helvetica", "", 10)
            self.multi_cell(0, 5.5, topic)
            self.ln(1)
        self.ln(1)

        self.set_font("Helvetica", "B", 10)
        nw = self.get_string_width("Next Meeting: ")
        self.cell(nw, 5.5, "Next Meeting: ")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 5.5, f"{next_date}, {next_time}, {next_loc}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

        if next_obj:
            self.set_font("Helvetica", "B", 10)
            ow = self.get_string_width("Objective(s): ")
            self.cell(ow, 5.5, "Objective(s): ")
            self.set_font("Helvetica", "", 10)
            self.multi_cell(0, 5.5, next_obj)

        self.ln(4)
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(6)


def build_pdf():
    pdf = DiaryPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 28)
    pdf.cell(0, 14, "IT Capstone Project 1", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 26)
    pdf.cell(0, 14, "PROGRESS REPORT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "for", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "QUICKHIRE: AI-NATIVE RESUME SCREENING", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "WEB-APP", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Team Members:", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    for m in ["Aatmik Dahal (s8140413)", "Nishant Khadka", "Nischal Gautam", "Upadesh Silwal"]:
        pdf.cell(0, 8, m, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Supervisor: Fakhra Jabeen", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Date: 20th February 2026", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.add_page()
    pdf.section_title("Table of Contents")
    toc = [
        "1. Introduction",
        "2. Frontend UI/UX Subsystem Progress Report",
        "3. Backend & Security Subsystem Progress Report",
        "4. AI Engine & Screening Subsystem Progress Report",
        "5. Database Subsystem Progress Report",
        "6. Miscellaneous Features",
        "7. Design and Style Constants",
        "8. Database Schema",
        "9. Meeting Records",
    ]
    pdf.set_font("Helvetica", "", 12)
    for item in toc:
        pdf.cell(0, 8, item, new_x="LMARGIN", new_y="NEXT")

    pdf.add_page()
    pdf.section_title("Introduction")
    pdf.body_text(
        "This is our group's progress report and diary for the MVP of \"QuickHire.\" "
        "When we kicked off, we split things into 2 main workstreams -- the frontend "
        "(all the page templates, styling, and interactivity) and the backend (server "
        "logic with the database). This doc is basically the merged and cleaned up version "
        "of everyone's individual progress logs that we kept as we went."
    )
    pdf.body_text(
        "We set some pretty strict rules early on about how we wanted the architecture "
        "to look since the whole point is building a B2B SaaS tool that screens resumes "
        "using AI. Right now we're sitting at about 80% done. The main stuff works -- "
        "the step-by-step wizard flow on the frontend, the login protection on all "
        "dashboard pages, the database with our User, Job, and Candidate tables, and "
        "the AI scoring engine. You can go through the full loop: upload a job "
        "description, upload resumes, run the AI screening, and see ranked results. "
        "That whole pipeline is working end to end."
    )
    pdf.body_text(
        "The last 20% is mostly about moving from our local database to a cloud-hosted "
        "PostgreSQL for production, getting the email invite feature to actually send "
        "without errors, and finishing up the post-interview workflow where you mark "
        "people as hired or rejected and generate onboarding documents."
    )
    pdf.body_text(
        "We've been pretty good about tracking our meetings and what everyone worked on, "
        "which you can see below. One thing worth mentioning -- during testing we ran "
        "into an interesting problem where candidates who stuffed their resumes with "
        "keywords (the kind of thing people do to game screening systems) were scoring "
        "way too high. So we've been tweaking the AI prompt to look at whether someone "
        "actually used a skill in context rather than just listing it."
    )
    pdf.body_text(
        "We set up our version control early on and used feature branches for each "
        "subsystem. Merges went through pull requests with review. We could have just "
        "detailed changes in commit messages, but since we'd already started keeping "
        "these logs we figured we'd keep going with it."
    )
    pdf.ln(2)
    pdf.bold_text("Project Repositories:")
    pdf.ln(2)
    pdf.bullet_bold_value("Git Repository: ", "https://github.com/dahalaatmik/QuickHire.git")
    pdf.bullet_bold_value("Live Gantt Chart: ", "[Attached separately]")

    pdf.add_page()
    pdf.section_title("Frontend UI/UX Subsystem Progress Report")

    pdf.files_table(
        "FRONTEND & UI/UX",
        ["index.html", "auth.html", "register.html", "_header.html", "_footer.html",
         "base_dashboard.html", "dashboard.html", "jobs.html", "candidates.html",
         "analytics.html", "settings.html"],
        ["landing.js", "auth.js", "register.js", "sidebar.js", "toast.js",
         "utils.js", "dashboard.js", "jobs.js", "candidates.js",
         "analytics.js", "styles.css"]
    )

    pdf.progress_table([
        ("22/01/26", "Upadesh",
         "Started setting up the design system for the whole app. We decided to go "
         "dark-mode-first so I defined all the colour variables at the top of the "
         "stylesheet -- background shades, a green accent colour, text colours at "
         "different brightness levels, and border styles. Also set up spacing values "
         "that scale smoothly between mobile and desktop, and font sizes from extra "
         "small to extra large.\n\n"
         "Built the landing page skeleton after that. Went with a layout where the eye "
         "naturally scans left to right and down for the hero section. Made the navbar "
         "as a reusable partial with a frosted glass effect (semi-transparent background "
         "with a blur behind it) and the footer as another partial, then pulled them "
         "into the main page using template includes."),

        ("24/01/26", "Upadesh",
         "Wrote the landing page script, ended up being around 226 lines. All vanilla "
         "JavaScript, no libraries.\n\n"
         "First part handles the hamburger menu for mobile. It opens and closes the "
         "nav menu, locks the background from scrolling, and closes if you press Escape "
         "or tap a link. Also auto-closes if someone rotates their phone to landscape "
         "and the screen gets wider.\n\n"
         "Second part is a simple smooth scroll for all the anchor links on the page.\n\n"
         "Third part was the tricky one -- the features carousel. It watches which "
         "feature section is visible on screen and syncs the scroll position to match. "
         "Had to add a short cooldown between scroll events so it doesn't jump around, "
         "plus swipe detection for touch screens with a minimum drag distance before it "
         "registers. Renders all the icons at the end."),

        ("28/01/26", "Nishant",
         "Built the login page and registration page.\n\n"
         "The login page has a card layout with the email field, password field, and a "
         "toggle button to show or hide the password (the little eye icon). There's a "
         "submit button with a loading spinner that appears while it processes.\n\n"
         "The registration page was more involved -- used a two-column grid to put "
         "fields side by side: first name and last name, email and company name, then "
         "dropdowns for company size and role, password and confirm password each with "
         "their own show/hide toggles, and a terms checkbox at the bottom. Made separate "
         "small scripts for handling the password visibility on each page."),

        ("02/02/26", "Upadesh",
         "Built the base dashboard template that every dashboard page extends from. "
         "The structure is a sidebar on the left (fixed width) with navigation items "
         "that get a green highlight when active, then a main content area with a top "
         "bar. The top bar has a menu button for mobile (hidden on desktop), breadcrumbs "
         "showing where you are, and a profile dropdown with a notification bell.\n\n"
         "The profile dropdown is accessible -- it tells screen readers whether it's "
         "open or closed. Scripts load in a specific order: sidebar logic first, then "
         "the toast notification system, then utilities, then whatever the specific page "
         "needs.\n\n"
         "The sidebar script is only about 31 lines. It handles the mobile sidebar "
         "sliding in and out and the profile dropdown. Getting the dropdown to close "
         "when you click outside of it took a bit of fiddling."),

        ("04/02/26", "Upadesh",
         "This was a big one -- built the main dashboard page with the 4-step wizard.\n\n"
         "Step 1 is the job description upload. There's a toggle between uploading a "
         "PDF or pasting text directly. The upload mode has a drag-and-drop zone. When "
         "you drop a file it shows the filename with a remove button. While the AI "
         "analyses it there's a loading animation, then when done it shows the extracted "
         "fields and skills as little tags.\n\n"
         "Step 2 is resume upload -- supports multiple files at once, shows a list of "
         "what you've uploaded with a count and an Add More button.\n\n"
         "Step 3 is where the screening results show up. A progress bar fills as each "
         "resume gets scored. You can sort by different criteria and filter by skills. "
         "There's a Select All checkbox and buttons for exporting or sending interview "
         "invites.\n\n"
         "Step 4 is for post-interview actions with groupings by status (still being "
         "fleshed out)."),

        ("06/02/26", "Nishant",
         "Made two small but important utility files.\n\n"
         "The first one has two helper functions we use everywhere: one that sanitises "
         "text before putting it on the page (prevents injection attacks), and another "
         "that returns a colour label based on a candidate's score -- green for 90 and "
         "above, amber for 70 to 89, red for anything below 70. We use that second one "
         "all over the place for the coloured score badges.\n\n"
         "Also made the toast notification system -- a small popup that appears at the "
         "bottom of the screen with a checkmark and a message, then fades out after "
         "about 3 seconds. Nothing fancy but it works well for confirming actions."),

        ("10/02/26", "Upadesh",
         "Built the jobs page. Has 4 stat cards at the top showing totals for postings, "
         "open positions, drafts, and completed hires. Each card has a coloured accent "
         "bar along the top edge.\n\n"
         "Below that there's a search box and 3 filter dropdowns -- department (9 options "
         "like Engineering, Design, Marketing, etc.), status, and date range. The table "
         "populates dynamically from job data that the server passes to the page.\n\n"
         "Also built the job detail slide-out panel where you can change the status, "
         "delete the posting, and switch between tabs for the job description and "
         "candidate list. Plus a modal form for creating new jobs with fields for title, "
         "department, location, salary range, description, and required skills."),

        ("12/02/26", "Nishant",
         "Built the candidates page. Similar layout to the jobs page -- stat cards on "
         "top (total candidates, invited, pending review, hired), a search bar, and "
         "filter dropdowns for status and which job they applied to.\n\n"
         "Each table row stores extra information as data attributes which makes the "
         "filtering logic much simpler. Rows show the candidate's info, their skills "
         "as small tags, a score badge with the matching colour, status badge, and "
         "action buttons for contacting or removing them.\n\n"
         "The script uses a single event listener on the whole table body instead of "
         "attaching one to every row, which is cleaner. Clicking delete shows a "
         "confirmation dialog first. Clicking contact opens a modal. Clicking the row "
         "itself opens the full detail view with the complete score breakdown."),

        ("14/02/26", "Upadesh",
         "Wrote the main dashboard script which ended up being the biggest file at over "
         "500 lines. It tracks everything in a single state object: which wizard step "
         "you're on, the current job, whether you're in upload or paste mode for the "
         "job description, the uploaded files, screening results, selected candidates, "
         "and so on.\n\n"
         "One thing that helped performance a lot was grabbing all the page elements "
         "once upfront -- about 102 references -- instead of searching the page for "
         "them every time they're needed.\n\n"
         "The main structure is a navigation function for moving between wizard steps, "
         "then separate setup logic for each of the 4 steps. Step 1 handles the job "
         "description upload and AI analysis. Step 2 does the multi-resume upload. "
         "Step 3 fires off the screening and checks for progress. Step 4 is the "
         "post-interview flow.\n\n"
         "There's also a restore function that picks up where you left off if you "
         "come back to an in-progress job."),

        ("17/02/26", "Nishant",
         "Built the analytics page script (252 lines). The main function fetches data "
         "from the server based on whatever time range is selected (7 days, 30 days, "
         "or 90 days) and then calls 6 different rendering functions.\n\n"
         "One builds a bar chart from scratch showing hiring trends. Another shows the "
         "hiring funnel (Applied, Scored, Shortlisted, Invited, Hired) with percentage "
         "drop-offs between each stage. A third shows the most common skills as tags "
         "where the brightness varies based on how frequently that skill appears.\n\n"
         "Also put together the Settings page with 4 tabs (General, Notifications, "
         "Team, Billing). Made sure every page refreshes the icons after any page "
         "content updates so they actually show up -- that tripped us up a few times "
         "early on."),
    ])

    pdf.add_page()
    pdf.section_title("Backend & Security Subsystem Progress Report")

    pdf.files_table(
        "BACKEND ROUTING & SECURITY",
        ["main.py", "user_model.py", "routes/__init__.py", "routes/auth.py"],
        ["routes/dashboard.py", "routes/landing.py", "routes/api/jobs.py", "routes/api/candidates.py"]
    )

    pdf.progress_table([
        ("25/01/26", "Nischal",
         "Set up the Flask backend using the app factory pattern so everything stays "
         "cleanly separated. Environment variables load from a config file -- the secret "
         "key, database path, the AI API key, and the Gmail credentials for the email "
         "feature later.\n\n"
         "Set the max upload size to 16MB since we need to handle PDF uploads. "
         "Registered 4 route groups:\n"
         "- One for the public homepage\n"
         "- One for login, registration, and logout\n"
         "- One for all the protected dashboard pages\n"
         "- One for the JSON data endpoints\n\n"
         "Also added custom error pages for the common HTTP errors (400, 403, 404, "
         "405, 500). Each one shows a friendly icon and message instead of the ugly "
         "default browser error screens."),

        ("01/02/26", "Nischal",
         "Got the login session management working. The system looks up users by their "
         "ID when checking if someone is logged in.\n\n"
         "One thing we decided early on -- instead of redirecting unauthorised users to "
         "a login page (which is the default behaviour), we return a \"Page Not Found\" "
         "error. That way if someone tries to hit a dashboard URL without being logged "
         "in, they just see a 404 page. Doesn't reveal that the page even exists, which "
         "is better from a security standpoint.\n\n"
         "Built the registration flow. It collects all the form fields (name, email, "
         "company, password, etc.), checks if the email is already taken, verifies "
         "passwords match, then hashes the password securely. After creating the user "
         "it auto-logs them in and redirects straight to the dashboard."),

        ("05/02/26", "Nischal",
         "Added login protection to every single dashboard route. Built the login flow:\n"
         "1. Look up the email in the database\n"
         "2. If no match, show \"That email does not exist\"\n"
         "3. Check password\n"
         "4. If wrong, show \"Password incorrect\"\n"
         "5. If good, log them in and redirect to dashboard\n\n"
         "Flash messages show up in the template so the user gets clear feedback on "
         "what went wrong. Logout is simple -- just ends the session and sends them "
         "back to the landing page."),

        ("09/02/26", "Nischal",
         "Tested all 5 protected routes to make sure the guards work:\n"
         "- The main dashboard page renders the wizard and passes any in-progress "
         "job data\n"
         "- The jobs page pulls the user's job list with stats\n"
         "- The candidates page joins candidates to their jobs, filtered by the "
         "current user, only showing scored ones sorted by match score\n"
         "- Analytics and settings are straightforward page renders\n\n"
         "Tested with a logged-out browser session -- confirmed all 5 routes return "
         "a 404 instead of redirecting. This was important to us since it stops people "
         "from guessing what URLs exist on the site."),

        ("16/02/26", "Nischal",
         "Found a bug. During longer upload sessions (big job description PDF then "
         "multiple resumes), the session was expiring mid-workflow. The user would "
         "upload a job description, start adding resumes, and then get kicked out "
         "because the default session timeout is too short.\n\n"
         "Dug into the session configuration and increased the timeout. That fixed it.\n\n"
         "Also updated the dashboard page to look for the user's most recent "
         "in-progress job and pass it to the page. This way the wizard can pick up "
         "where you left off -- it reads the saved data and fills everything back in. "
         "Really useful when someone closes their browser mid-screening."),
    ])

    pdf.add_page()
    pdf.section_title("AI Engine & Screening Subsystem Progress Report")

    pdf.files_table(
        "AI ENGINE & PARSING",
        ["services/ai_service.py", "services/pdf_parser.py", "routes/api/screening.py"],
        ["utils/ranking.py", "utils/formatting.py", "requirements.txt"]
    )

    pdf.progress_table([
        ("08/02/26", "Aatmik",
         "Got the AI API hooked up using our API key from the config. Wrote the PDF "
         "text extraction module -- we picked pdfplumber over other PDF libraries "
         "because it handles tables and weird layouts much better. Tested it on a "
         "bunch of different job description formats including some with multi-column "
         "layouts and embedded images. It pulls out the raw text and we store that in "
         "the database.\n\n"
         "Added the new libraries to our dependency list alongside the existing ones. "
         "Also included the PDF generation library since we'll need it later for "
         "creating onboarding documents."),

        ("10/02/26", "Aatmik",
         "Spent most of the day on prompt engineering. The goal was to get the AI to "
         "always return a clean, structured response with a consistent format. Used "
         "example outputs in the prompt so the model knows exactly what we expect:\n"
         "- Job title, required skills as a list, experience benchmarks with minimum "
         "and maximum years, education requirements, and weighted criteria where the "
         "skills, experience, and education weights all add up to 1.0.\n\n"
         "Tested against 10 different job description types (software engineer, data "
         "analyst, product manager, etc.) and the output was consistent every time. "
         "Added retry logic for the rare cases where the response comes back "
         "malformed -- usually just needs a second attempt."),

        ("14/02/26", "Aatmik",
         "Built the screening loop. Here's how it works:\n"
         "1. The frontend sends a request to start screening with the job ID\n"
         "2. The server grabs all the candidates for that job\n"
         "3. For each one, sends the resume text plus the job criteria to the AI\n"
         "4. AI comes back with scores: overall match (0 to 100), skills score, "
         "experience score, education score, a list of matched skills, and a text "
         "summary explaining the rating\n"
         "5. All of that gets saved to the candidate's record\n"
         "6. The frontend checks for updates and fills in the progress bar as each "
         "one finishes\n\n"
         "Tested with 5 resumes against a Software Engineer job description. Top "
         "candidate got 94% overall. The score breakdown was detailed -- 96% skills, "
         "91% experience, 92% education. Felt pretty accurate when we compared it "
         "to the actual resumes."),

        ("18/02/26", "Aatmik",
         "Ran into something interesting during testing. We had a test resume that was "
         "basically just a copy-paste of every skill from the job description -- no "
         "real context, no project descriptions, just a big list. It scored 88%. "
         "Meanwhile a genuinely qualified candidate with actual work experience only "
         "scored 82%. That's not right.\n\n"
         "The problem was our prompt was treating keyword presence the same as "
         "demonstrated experience. So I started reworking the prompt:\n"
         "- Made the AI explain why it scored each skill, citing specific resume content\n"
         "- Added a distinction between a skill being listed versus actually shown "
         "through project work\n"
         "- Added a confidence score for each skill match\n"
         "- Put in penalties for resumes where skills aren't backed up by any real work\n\n"
         "After the changes, the keyword-stuffed resume dropped to 61% and the real "
         "candidate went up to 91%. Still refining but the direction is good."),
    ])

    pdf.add_page()
    pdf.section_title("Database Subsystem Progress Report")

    pdf.files_table(
        "DATABASE MANAGEMENT",
        ["user_model.py", "main.py"],
        ["instance/quickhire_users_info.db", "utils/formatting.py"]
    )

    pdf.progress_table([
        ("27/01/26", "Nischal",
         "Set up the database using the newer declarative style with Python type hints "
         "which is a lot cleaner than the older way.\n\n"
         "Created the shared database object, the login manager, and the User model. "
         "User has the basics: ID, first name, last name, work email (must be unique), "
         "company name (also unique), company size, role, and the hashed password. It "
         "extends the standard user mixin so session features like checking whether "
         "someone is logged in just work out of the box.\n\n"
         "The database file gets automatically created when the app starts for the "
         "first time. If you ever need to reset everything you just delete that file."),

        ("03/02/26", "Nischal",
         "Added the Job model. It's linked to User through a foreign key so each job "
         "belongs to whoever created it. We set it up with cascade delete, meaning if "
         "you delete a user, all their jobs go too.\n\n"
         "Job has a lot of fields: the job description text and filename, title, "
         "department, location, skills, salary minimum and maximum, seniority level, "
         "status (which goes through draft, ready, processing, open, completed, "
         "closed), and timestamps.\n\n"
         "One important design choice -- Job has a one-to-many link with Candidate "
         "using the same cascade pattern. But on the candidates page, we show "
         "candidates from ALL jobs for the user, not just one. So deleting a job "
         "removes its candidates, but the candidates page still shows a global pool "
         "from all remaining jobs."),

        ("12/02/26", "Nischal",
         "Added the Candidate model. Fields include: resume text and filename, "
         "candidate name and email, then all the AI scoring fields (overall match, "
         "skills score, experience score, education score -- all empty until screening "
         "runs). Also stores the matched skills and a summary of the AI's reasoning.\n\n"
         "Status goes through several stages: pending, scored, invited, interview "
         "done, shortlisted, then either final hired or final rejected.\n\n"
         "Built some helper functions for the templates:\n"
         "- One that turns a candidate record into a plain dictionary for display\n"
         "- One that calculates job statistics (total, open, draft, completed counts)\n"
         "- One that returns all jobs as a list of dictionaries\n\n"
         "Tested the full create-read-delete cycle: creating through the upload route, "
         "reading on the jobs page, deleting with cascade -- all working."),

        ("18/02/26", "Nischal",
         "Started thinking about production deployment. Our current local database is "
         "fine for the MVP but it doesn't handle multiple people writing at the same "
         "time, which we'll need once real users are on the platform.\n\n"
         "The plan is:\n"
         "1. Add a migration tool for managing database changes properly\n"
         "2. Swap the database connection from local to our cloud-hosted PostgreSQL "
         "instance\n"
         "3. The model definitions stay the same since the database library handles "
         "the differences automatically\n"
         "4. Run the migration commands to set everything up\n\n"
         "Tested locally against a PostgreSQL instance and all our queries worked fine "
         "since we used database-agnostic syntax throughout. Did find one issue though "
         "-- one of our text columns that stores structured data will need a dedicated "
         "JSON column type for PostgreSQL."),
    ])

    pdf.add_page()
    pdf.section_title("Miscellaneous Features")

    pdf.files_table(
        "MISCELLANEOUS",
        ["static/css/styles.css", ".env", "requirements.txt", "Procfile"],
        [".gitignore", "utils/formatting.py", "templates/error.html", ".claude/ (docs)"]
    )

    pdf.progress_table([
        ("20/01/26", "Upadesh",
         "Set up the single stylesheet for the entire project. It ended up being "
         "around 3100 lines by the end but it's organised in clear sections so it's "
         "still manageable:\n"
         "1. Colour variables and resets at the top\n"
         "2. Container layout with responsive max-width and safe-area padding\n"
         "3. Landing page: frosted glass navbar, hero section with grid layout, "
         "features carousel, team grid, footer\n"
         "4. Login and registration page styles\n"
         "5. Dashboard layout: sidebar, top bar, content area\n"
         "6. Dashboard components: drag-and-drop zones, slide-out panels, modals, "
         "wizard steps\n"
         "7. Responsive breakpoints at 4 screen widths for mobile through desktop\n"
         "8. Additional pages: stat cards, tables, badges, settings tabs\n\n"
         "Everything uses colour variables instead of hard-coded values. Mobile-first "
         "approach with enhancements added at wider screen sizes throughout."),

        ("20/01/26", "Aatmik",
         "Got the project environment set up. Created the config file with the secret "
         "key, database path, AI API key, and the Gmail credentials for the invite "
         "feature.\n\n"
         "Set up the dependency list with all our packages -- the web framework, "
         "security tools, database library, login management, environment config, "
         "PDF reader, AI client, and PDF writer. Keeping them unpinned for now.\n\n"
         "Created the deployment config for hosting and set up version control rules "
         "to keep sensitive files, compiled files, and the database out of the "
         "repository.\n\n"
         "Also established the folder structure: separate directories for route "
         "handlers, AI services, utility functions, static files, and page templates."),

        ("15/02/26", "Aatmik",
         "Added custom error pages to the main server file. Registered handlers for "
         "5 common error types (bad request, forbidden, not found, method not allowed, "
         "and server error). Each one renders our error template with a matching icon "
         "and a user-friendly message.\n\n"
         "For example, a 404 shows a search icon with \"Page Not Found\" and a 500 "
         "shows a warning triangle with \"Server Error.\" Way better than showing the "
         "default debug page or a blank browser error to users."),

        ("19/02/26", "Nishant",
         "Put together a documentation directory with 8 files. The idea was to have "
         "everything documented so anyone (or any AI tool) could pick up the codebase "
         "and know what's going on.\n\n"
         "Includes: a main readme with dev commands and architecture overview, a "
         "design system file with all the colour and typography tokens, coding "
         "conventions, responsive design rules with breakpoint strategy, the full "
         "project file layout, patterns for common UI components like buttons and "
         "cards, and notes on where we want to take things next."),
    ])

    pdf.add_page()
    pdf.section_title("Design and Style Constants")

    pdf.subsection_title("Colour Palette (Dark Mode)")
    pdf.bullet_bold_value("Canvas Background: ", "Deep black (#070809)")
    pdf.bullet_bold_value("Surface/Cards: ", "Dark charcoal (#0F1114)")
    pdf.bullet_bold_value("Elevated Elements: ", "Dark grey (#161A1F)")
    pdf.bullet_bold_value("Primary Accent: ", "Green (#22C55E)")
    pdf.bullet_bold_value("Secondary Accent: ", "Darker green (#16A34A)")
    pdf.bullet_bold_value("Success: ", "Green -- used for scores 90% and above")
    pdf.bullet_bold_value("Warning: ", "Amber -- used for scores 70% to 89%")
    pdf.bullet_bold_value("Danger: ", "Red -- used for scores below 70%")
    pdf.bullet_bold_value("Primary Text: ", "Near-white (#FAFAFA) for headings and main content")
    pdf.bullet_bold_value("Secondary Text: ", "Muted grey (#A1A1AA) for body text and descriptions")
    pdf.bullet_bold_value("Disabled Text: ", "Darker grey (#71717A) for placeholders and hints")
    pdf.bullet_bold_value("Borders: ", "Very faint white (6% opacity)")
    pdf.bullet_bold_value("Accent Borders: ", "Faint green (15% opacity)")
    pdf.bullet_bold_value("Glow Effects: ", "Green glow (25% opacity, used on button hover)")
    pdf.ln(2)

    pdf.subsection_title("Typography")
    pdf.bullet_bold_value("Font: ", "Inter (with system font fallbacks)")
    pdf.bullet_bold_value("Headlines: ", "Bold weight, near-white colour")
    pdf.bullet_bold_value("Body Text: ", "Regular weight, muted grey")
    pdf.bullet_bold_value("Labels: ", "Semi-bold, darker grey, uppercase, wider letter spacing")
    pdf.bullet_bold_value("Scale: ", "Fluid sizing from 0.75rem (small) to 4rem (hero headings)")
    pdf.ln(2)

    pdf.subsection_title("Spacing")
    pdf.body_text(
        "All spacing values use fluid scaling that adjusts smoothly between small "
        "screens and large screens. We defined 7 spacing levels from extra small "
        "(about 4px on mobile, 8px on desktop) up to triple extra large (about 48px "
        "on mobile, 80px on desktop). This means the layout breathes and adapts without "
        "needing lots of media query overrides."
    )
    pdf.ln(2)

    pdf.subsection_title("Key Text Strings")
    pdf.bullet_bold_value("App Name: ", "QuickHire")
    pdf.bullet_bold_value("Tagline: ", "\"Scale Your Team, Not Your Workload.\"")
    pdf.bullet_bold_value("Drop Zone Prompt: ", "\"Drop Job Description PDF here to initialize the AI Agent.\"")
    pdf.ln(2)

    pdf.subsection_title("Visual Effects")
    pdf.bullet_bold_value("Shadows: ", "4 levels from subtle (1px blur) to dramatic (48px blur)")
    pdf.bullet_bold_value("Glassmorphism: ", "Semi-transparent dark background with 20px blur behind it")
    pdf.bullet_bold_value("Button Glow: ", "Green glow that intensifies on hover")
    pdf.bullet_bold_value("Transitions: ", "Fast (150ms), Base (250ms), Slow (350ms)")

    pdf.add_page()
    pdf.section_title("Database Schema (Current SQLite MVP)")

    pdf.subsection_title("1. Users Table (Implemented)")
    pdf.bullet_point("id (Primary Key, Auto-increment)")
    pdf.bullet_point("first_name (Required)")
    pdf.bullet_point("last_name (Required)")
    pdf.bullet_point("work_email (Unique, Required)")
    pdf.bullet_point("company_name (Unique)")
    pdf.bullet_point("company_size")
    pdf.bullet_point("role")
    pdf.bullet_point("password (Securely hashed)")
    pdf.bullet_point("Relationship: One user has many jobs (cascade delete)")
    pdf.ln(3)

    pdf.subsection_title("2. Jobs Table (Implemented)")
    pdf.bullet_point("id (Primary Key, Auto-increment)")
    pdf.bullet_point("user_id (Foreign Key to Users, Required)")
    pdf.bullet_point("jd_text (Full text of the job description)")
    pdf.bullet_point("jd_filename")
    pdf.bullet_point("title")
    pdf.bullet_point("department")
    pdf.bullet_point("location")
    pdf.bullet_point("required_skills (Stored as text or structured data)")
    pdf.bullet_point("salary_min")
    pdf.bullet_point("salary_max")
    pdf.bullet_point("seniority_level")
    pdf.bullet_point("employment_type")
    pdf.bullet_point("salary_range_text")
    pdf.bullet_point("ai_analyzed (Whether the AI has processed this job)")
    pdf.bullet_point("status (draft / ready / processing / open / completed / closed)")
    pdf.bullet_point("created_at (Auto-set to current time)")
    pdf.bullet_point("updated_at (Auto-updated on changes)")
    pdf.bullet_point("Relationship: One job has many candidates (cascade delete)")
    pdf.ln(3)

    pdf.subsection_title("3. Candidates Table (Implemented)")
    pdf.bullet_point("id (Primary Key, Auto-increment)")
    pdf.bullet_point("job_id (Foreign Key to Jobs, Required)")
    pdf.bullet_point("resume_text (Full text of the resume)")
    pdf.bullet_point("resume_filename")
    pdf.bullet_point("candidate_name")
    pdf.bullet_point("candidate_email")
    pdf.bullet_point("match_score (Overall score 0-100, empty before screening)")
    pdf.bullet_point("skills_score (Skills sub-score 0-100)")
    pdf.bullet_point("experience_score (Experience sub-score 0-100)")
    pdf.bullet_point("education_score (Education sub-score 0-100)")
    pdf.bullet_point("matched_skills (List of skills that matched the job)")
    pdf.bullet_point("match_summary (AI-generated explanation of the score)")
    pdf.bullet_point("status (pending / scored / invited / interview_done / shortlisted / final_hired / final_rejected)")
    pdf.bullet_point("interview_at (Scheduled interview date, if any)")
    pdf.bullet_point("final_notes (Notes about the candidate)")
    pdf.bullet_point("onboarding_generated (Whether onboarding docs were created)")
    pdf.bullet_point("created_at (Auto-set to current time)")

    pdf.add_page()
    pdf.section_title("Meeting Records")

    pdf.meeting_record(
        number=1, subtitle=None,
        date="19/01/2026", time="7:00 PM", location="Discord",
        objective="Initial kick-off, decide on the tech stack, and figure out who's doing what.",
        present="Aatmik Dahal, Nishant Khadka, Nischal Gautam, Upadesh Silwal",
        absent="None",
        topics=[
            "Locked in the tech stack. Going with Python and Flask on the backend, plain HTML/CSS/JS "
            "on the frontend (no React or Vue -- we want to keep it simple with vanilla JavaScript "
            "and self-contained scripts). Local database for the MVP, planning to move to cloud-hosted "
            "PostgreSQL later. Using server-side templates and organised route groups to keep things "
            "tidy. Session-based login with secure password hashing.",
            "Divvied up the work. Upadesh is handling all the UI/UX and frontend stuff (templates, "
            "design system, interactions). Nischal has the backend, database, and security "
            "(server routes, database models, authentication flow). Aatmik is doing the AI engine "
            "(API integration, PDF parsing, prompt engineering). Nishant is on testing, QA, and some "
            "of the frontend pages like the analytics dashboard.",
            "Set up the GitHub repo and agreed on branching rules -- feature branches with pull "
            "requests and code review before merging. Got the config file set up and created the "
            "initial folder structure. Decided to go with a single stylesheet for the MVP to keep "
            "things simple and reduce page load times.",
        ],
        next_date="26/01/2026", next_time="8:00 PM", next_loc="Discord",
        next_obj="Check on frontend progress, nail down the database schema, and define the AI data flow."
    )

    pdf.meeting_record(
        number=2, subtitle=None,
        date="26/01/2026", time="8:00 PM", location="Discord",
        objective="Review frontend progress, nail down database schema, and define the AI data flow.",
        present="Aatmik Dahal, Nishant Khadka, Nischal Gautam, Upadesh Silwal",
        absent="None",
        topics=[
            "Upadesh showed the landing page with all the animations working -- the features "
            "carousel that tracks what's visible on screen, smooth scrolling, the frosted glass "
            "navbar. Everyone liked the dark mode look with the deep black background and green "
            "accent. We talked about using an F-pattern reading layout for the hero and went with "
            "a 2-column responsive grid layout.",
            "Nischal walked through the database design. 3 models: User, Job, Candidate. We spent "
            "a while discussing how the candidate pool should work -- you need to see candidates "
            "across all jobs on the candidates page, but deleting a job should only remove its own "
            "candidates. Settled on using cascade delete on the relationships and doing a filtered "
            "join by user ID for the global candidate view.",
            "Aatmik explained how the AI integration will work. The key thing is getting consistent "
            "structured output from the model -- we'll use example outputs in the prompt. Also "
            "discussed weighted scoring (skills + experience + education weights that add up to "
            "1.0) and the need for reasoning steps to catch keyword-stuffed resumes. Went with "
            "pdfplumber over other PDF libraries for text extraction since it handles complex "
            "document layouts better.",
        ],
        next_date="09/02/2026", next_time="8:00 PM", next_loc="Discord",
        next_obj="Hook up the frontend dashboard to the backend and test security."
    )

    pdf.meeting_record(
        number=3, subtitle=None,
        date="09/02/2026", time="8:00 PM", location="Discord",
        objective="Connect the dashboard UI to the Flask backend and test the security setup.",
        present="Aatmik Dahal, Nishant Khadka, Nischal Gautam, Upadesh Silwal",
        absent="None",
        topics=[
            "Nischal demoed the route protection. Showed that hitting any dashboard URL without "
            "being logged in gives a \"Page Not Found\" error instead of a login redirect -- our "
            "deliberate choice to prevent people from discovering what pages exist. Tested all 5 "
            "protected routes and they all work correctly.",
            "Ran through the full user flow together: register a new account, log in, land on the "
            "dashboard wizard. Tested all the edge cases on registration -- duplicate emails, "
            "mismatched passwords, missing required fields. Everything shows the right error "
            "messages. Login works both ways (correct and incorrect credentials). Auto-login after "
            "registration drops you right into the dashboard.",
            "Found a session timeout bug. When you upload a big job description PDF (we allow up to "
            "16MB) and then start adding resume PDFs, the whole thing can take long enough that the "
            "default session expires. Nischal took the action item to look into the session timeout "
            "settings. Also talked about needing the dashboard to pass in-progress job data to the "
            "page so the wizard can restore where you left off.",
        ],
        next_date="18/02/2026", next_time="8:00 PM", next_loc="Discord",
        next_obj="Full end-to-end testing, check AI scoring accuracy, and put together the 80% progress report."
    )

    pdf.meeting_record(
        number=4, subtitle="The 80% Milestone Review",
        date="18/02/2026", time="8:00 PM", location="Discord",
        objective="Full end-to-end MVP test, check AI accuracy, and put together the 80% completion report.",
        present="Aatmik Dahal, Nishant Khadka, Nischal Gautam, Upadesh Silwal",
        absent="None",
        topics=[
            "Did the full end-to-end test. Registered a fresh account, logged in, went through "
            "all 4 wizard steps. Uploaded a Software Engineer job description (the parser pulled "
            "out 847 words), the AI analysed it and came back with 12 required skills. Uploaded 5 "
            "test resumes. Ran the screening -- progress bar worked, each candidate got scored. "
            "Top candidate hit 94% overall (96% skills, 91% experience, 92% education). Results "
            "showed up in the grid with the right colour coding. Select All and Send Interview "
            "Invite buttons both worked. The core system is officially working.",
            "Nishant brought up the keyword-stuffing issue. A test resume that just listed every "
            "skill from the job description with zero context scored 88%, which is way too high. "
            "Aatmik started tweaking the prompt to make the AI tell the difference between skills "
            "that are simply listed versus actually shown through project work. Added reasoning "
            "steps and confidence scores. After the changes the stuffed resume dropped to 61% "
            "and the legitimate candidate went from 82% to 91%. Much better.",
            "Listed out what's left for the remaining 20%:\n"
            "1. Email invites -- the send-invites endpoint is throwing email server errors with "
            "Gmail right now. Need to sort out the app-specific password configuration and handle "
            "the scheduling link attachment.\n"
            "2. Post-interview workflow in Step 4 -- hired/not hired toggles, notes field, status "
            "transitions, and onboarding PDF generation.\n"
            "3. Database migration from local to cloud-hosted PostgreSQL. Mostly just a config "
            "swap and running the migration tool, plus a column type adjustment for structured "
            "data.",
        ],
        next_date="TBD", next_time="TBD", next_loc="Discord",
        next_obj="Final bug fixes, email configuration, and database migration."
    )

    output_path = "/Users/mik/Downloads/QuickHire_Progress_Report_Diary.pdf"
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    build_pdf()
