# Codebase Structure

**Analysis Date:** 2026-02-25

## Directory Layout

```
/Users/mik/Desktop/code/QuickHire/
├── main.py                          # Flask application entry point
├── user_model.py                    # SQLAlchemy ORM models (User, Job, Candidate)
├── generate_diary.py                # Utility script (purpose unclear from context)
├── routes/                          # Route handlers and blueprints
│   ├── __init__.py
│   ├── auth.py                      # Authentication routes (/login, /register, /logout)
│   ├── landing.py                   # Landing page route (/)
│   ├── dashboard.py                 # Dashboard page routes (/dashboard/*, read-only views)
│   └── api/                         # RESTful API endpoints
│       ├── __init__.py
│       ├── jobs.py                  # Job management API (/dashboard/upload-jd, /analyze-jd, etc.)
│       └── candidates.py            # Candidate management API (/dashboard/upload-resumes, /start-screening, etc.)
├── services/                        # Business logic and external integrations
│   ├── __init__.py
│   ├── ai.py                        # Claude AI integration (prompts, scoring, parsing)
│   ├── email.py                     # Email sending (invites, decisions, custom messages)
│   └── pdf.py                       # PDF generation (candidate reports, onboarding docs)
├── utils/                           # Shared utility functions
│   ├── __init__.py
│   └── formatting.py                # Data formatting, PDF extraction, analytics computation
├── templates/                       # Jinja2 HTML templates
│   ├── landing page/                # Public pages
│   │   ├── index.html               # Home/landing page
│   │   ├── auth.html                # Login form
│   │   ├── register.html            # Registration form
│   │   ├── _header.html             # Header component
│   │   └── _footer.html             # Footer component
│   ├── dashboard/                   # Authenticated dashboard pages
│   │   ├── base_dashboard.html      # Dashboard layout template (extends base)
│   │   ├── dashboard.html           # Main dashboard/overview page
│   │   ├── jobs.html                # Jobs management page
│   │   ├── candidates.html          # Candidates management page
│   │   ├── analytics.html           # Analytics/reporting page
│   │   ├── settings.html            # User settings page
│   │   └── _sidebar.html            # Sidebar navigation component
│   └── error.html                   # Error page template (400, 403, 404, 405, 500)
├── static/                          # Client-side assets
│   ├── js/                          # JavaScript files
│   │   ├── auth.js                  # Login/register form handling
│   │   ├── dashboard.js             # Dashboard interactions
│   │   ├── jobs.js                  # Job upload, creation, filtering, status updates
│   │   ├── candidates.js            # Resume upload, screening, candidate interactions
│   │   ├── analytics.js             # Analytics page and data visualization
│   │   ├── settings.js              # Settings form handling
│   │   ├── landing.js               # Landing page interactions
│   │   ├── sidebar.js               # Sidebar navigation logic
│   │   ├── toast.js                 # Toast notification system
│   │   ├── utils.js                 # Shared utility functions (fetch wrappers, date formatting)
│   │   └── register.js              # Registration form handling (separate from auth.js)
│   ├── css/                         # Stylesheet files
│   └── assets/                      # Static assets
│       └── external-platform-logos/ # Job platform logos (Indeed, LinkedIn, Jora, seek)
├── uploads/                         # User-uploaded files (generated at runtime)
│   ├── jd/                          # Job description PDFs (organized by user_id)
│   └── resumes/                     # Resume PDFs (organized by job_id)
├── instance/                        # Flask instance folder (database file, app-specific data)
├── .planning/                       # GSD planning documents
│   └── codebase/                    # Architecture and codebase analysis files
├── .venv/                           # Python virtual environment
├── .vscode/                         # VS Code settings
├── .git/                            # Git repository
├── .gitignore                       # Git ignore rules
├── .env                             # Environment variables (NOT committed - secrets here)
└── requirements.txt                 # Python dependencies
```

## Directory Purposes

**main.py:**
- Purpose: Flask application factory and entry point
- Contains: Flask app initialization, blueprint registration, configuration, database schema creation, error handler setup
- Key files: Imports from user_model, routes, services

**user_model.py:**
- Purpose: SQLAlchemy ORM model definitions
- Contains: User, Job, Candidate classes with relationships, database column definitions, types
- Key files: Imported by main.py and all routes/services

**routes/:**
- Purpose: HTTP request handlers organized by feature area
- Contains: Flask Blueprint definitions with @route decorators
- Key files: auth.py (7-96 lines), landing.py (1-9 lines), dashboard.py (1-93 lines), api/jobs.py (253 lines), api/candidates.py (418 lines)

**routes/api/:**
- Purpose: RESTful API endpoints for frontend JavaScript interactions
- Contains: POST/GET/DELETE/PATCH endpoints returning JSON
- Key files: jobs.py (upload, analyze, create, detail, filter, update status, delete), candidates.py (upload, screen, results, send emails, make decisions, generate docs, analytics)

**services/:**
- Purpose: Business logic, external API integrations
- Contains: ai.py (Claude prompting, prompt building, JSON parsing, scoring), email.py (Gmail integration), pdf.py (PDF generation with fpdf)
- Key files: ai.py (158 lines), email.py (not fully shown but referenced), pdf.py (248 lines)

**utils/:**
- Purpose: Shared utility functions used across routes and services
- Contains: PDF text extraction, HTML formatting, data serialization, analytics computation
- Key files: formatting.py (336 lines, most comprehensive utility module)

**templates/:**
- Purpose: Server-side rendered HTML pages using Jinja2
- Contains: Layout templates, page templates, component partials
- Organization: Separated into landing page (public) and dashboard (protected) subdirectories

**static/js/:**
- Purpose: Client-side logic for form submission, API calls, UI interactions
- Contains: Event handlers, fetch wrappers, data transformations
- Key files: jobs.js (upload UI), candidates.js (resume upload, screening), analytics.js (data viz), utils.js (shared helpers)

**static/css/:**
- Purpose: Stylesheets (not examined in detail)
- Contains: Page layouts, component styles, responsive design

**uploads/:**
- Purpose: Runtime file storage for user PDFs
- Structure: `uploads/jd/{user_id}/` for job descriptions, `uploads/resumes/{job_id}/` for candidate resumes
- Generated: Created at runtime via `os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)` in main.py line 47

**instance/:**
- Purpose: Flask instance folder for app-specific data
- Contains: SQLite database file (configured via DATABASE_URL env var)
- Generated: Created by Flask at runtime

## Key File Locations

**Entry Points:**

- `main.py` - Application startup and configuration
- `routes/auth.py` - Login/register/logout endpoints
- `routes/landing.py` - Home page endpoint (/)
- `routes/dashboard.py` - Dashboard view routes (protected pages)
- `routes/api/jobs.py` - Job API endpoints
- `routes/api/candidates.py` - Candidate API endpoints

**Configuration:**

- `main.py` - Flask app config, blueprint registration, error handlers
- `.env` - Environment variables (secrets, database URL, API keys)
- `requirements.txt` - Python package dependencies

**Core Logic:**

- `services/ai.py` - Claude API integration, prompt engineering, response parsing
- `services/email.py` - Email sending via Gmail
- `services/pdf.py` - PDF generation for reports and onboarding
- `utils/formatting.py` - Data transformation, PDF text extraction, analytics

**Data Models:**

- `user_model.py` - SQLAlchemy models and relationships

**Frontend:**

- `templates/landing page/` - Public pages (index.html, auth.html, register.html)
- `templates/dashboard/` - Authenticated pages (jobs.html, candidates.html, analytics.html, settings.html)
- `static/js/` - Client-side logic (jobs.js, candidates.js, auth.js, etc.)

## Naming Conventions

**Files:**

- Route files: `snake_case.py` (auth.py, landing.py, dashboard.py)
- Service files: `snake_case.py` (ai.py, email.py, pdf.py)
- Utility files: `snake_case.py` (formatting.py)
- HTML templates: `snake_case.html` or `_component_name.html` (underscore prefix for partials)
- JavaScript: `snake_case.js` (auth.js, dashboard.js, utils.js)
- Classes/Models: `PascalCase` (User, Job, Candidate)

**Directories:**

- Feature areas: `snake_case/` (routes/api/, services/, utils/, static/js/)
- Subdirectories: `snake_case/` (landing page/, dashboard/, external-platform-logos/)
- Runtime data: `lowercase/` (uploads/, instance/)

**Functions:**

- Utility functions: `snake_case` with clear intent (extract_pdf_text, format_salary, serialize_candidate, build_jobs_list, compute_analytics_data)
- Route handlers: `snake_case` named after endpoint action (login, register, upload_jd, analyze_jd, start_screening, send_invites)
- Prompt builders: `build_*_prompt` (build_jd_analysis_prompt, build_screening_prompt)
- Service functions: `snake_case` matching business domain (call_claude, score_candidate, send_invite_email, generate_candidate_report)

**Database Models:**

- Table classes: `PascalCase` (User, Job, Candidate)
- Columns: `snake_case` (first_name, work_email, company_name, salary_min, salary_max, match_score, created_at, updated_at)
- Relationships: `lowercase` (user, job, candidates)
- Relationships (reverse): Specified in `relationship(back_populates=...)` to match forward direction

**Variables:**

- Query variables: `lowercase` (user, job, candidate, candidates, jobs_data, all_jobs)
- Configuration: `UPPERCASE` (SECRET_KEY, DATABASE_URL, UPLOAD_FOLDER, ANTHROPIC_API_KEY)
- Local/temp: `snake_case` (draft_job, new_user, jd_text, resume_text)
- Class attributes (columns): `snake_case` in model definition

## Where to Add New Code

**New Feature (e.g., interview scheduling):**
- Primary code: `routes/api/{feature_name}.py` for API endpoints
- Supporting logic: `services/{feature_name}.py` for business logic
- Utilities: `utils/formatting.py` (add helper functions if needed)
- Tests: Place test files next to source files as `*_test.py` or `test_*.py` (none exist yet)

**New Component/Module:**
- Implementation: Create file in appropriate directory:
  - Route handlers → `routes/` or `routes/api/`
  - Business logic → `services/`
  - Helpers → `utils/`
  - Frontend → `static/js/`
  - Templates → `templates/`
- Register in main.py: If new blueprint, add `app.register_blueprint(bp)` line

**Utilities (shared helpers):**
- Shared helpers: Add to `utils/formatting.py` (existing dumping ground)
- Alternative: Create new file in `utils/` if it becomes a distinct domain (e.g., `utils/analytics.py`, `utils/validation.py`)

**Templates:**
- Public templates: Place in `templates/landing page/`
- Dashboard templates: Place in `templates/dashboard/`
- Partials (reusable components): Prefix with underscore `_component_name.html`

**JavaScript:**
- Page-specific logic: Create `static/js/{page_name}.js` (jobs.js, candidates.js, analytics.js)
- Shared utilities: Add to `static/js/utils.js`

## Special Directories

**uploads/:**
- Purpose: Store user-uploaded PDF files
- Generated: Yes, created at runtime via `os.makedirs()`
- Committed: No, added to `.gitignore`
- Structure: `uploads/jd/{user_id}/` for job description PDFs, `uploads/resumes/{job_id}/` for resume PDFs
- Cleanup: Deleted when job or candidate is deleted

**instance/:**
- Purpose: Flask instance folder for SQLite database
- Generated: Yes, created by Flask
- Committed: No, added to `.gitignore`
- Contains: SQLite database file specified in DATABASE_URL

**__pycache__/:**
- Purpose: Python bytecode cache
- Generated: Yes, automatically created by Python
- Committed: No, added to `.gitignore`

**.venv/:**
- Purpose: Python virtual environment
- Generated: Yes, created by `python -m venv .venv`
- Committed: No, added to `.gitignore`

**.planning/codebase/:**
- Purpose: GSD mapping documents (architecture, testing, conventions, etc.)
- Generated: Yes, created by Claude mapper agent
- Committed: Yes, committed to repo for reference

---

*Structure analysis: 2026-02-25*
