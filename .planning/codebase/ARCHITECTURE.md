# Architecture

**Analysis Date:** 2026-02-25

## Pattern Overview

**Overall:** MVC (Model-View-Controller) pattern with Blueprint-based layered architecture using Flask framework.

**Key Characteristics:**
- Server-side template rendering with client-side AJAX interactions
- Separation of concerns: routes → services → models
- Database-first approach with SQLAlchemy ORM
- External AI integration (Anthropic Claude) for resume screening and job description analysis
- User-scoped data isolation (all data tied to `current_user`)
- RESTful API endpoints for client-side operations

## Layers

**Presentation Layer:**
- Purpose: Render HTML templates and serve JSON responses for frontend interactions
- Location: `templates/`, `static/`
- Contains: Jinja2 HTML templates (landing pages, dashboard views) and JavaScript files for client-side logic
- Depends on: Dashboard route handlers, API endpoints
- Used by: Browsers, client-side JavaScript

**Route/Controller Layer:**
- Purpose: Handle HTTP requests, validate user access, orchestrate business logic
- Location: `routes/` (auth.py, dashboard.py, landing.py), `routes/api/` (jobs.py, candidates.py)
- Contains: Flask Blueprints with `@route` decorators and request handlers
- Depends on: Database models, services, utilities for formatting
- Used by: Flask app, HTTP clients

**Service/Business Logic Layer:**
- Purpose: Encapsulate domain logic, external integrations, and complex operations
- Location: `services/` (ai.py, email.py, pdf.py)
- Contains: Functions for AI prompting, email sending, PDF generation
- Depends on: Database models, external APIs (Anthropic, Gmail)
- Used by: Route handlers

**Model/Data Layer:**
- Purpose: Define database schema and relationships
- Location: `user_model.py`
- Contains: SQLAlchemy models (User, Job, Candidate) with ORM mappings
- Depends on: SQLAlchemy, Flask-SQLAlchemy, Flask-Login
- Used by: Routes, services, all data operations

**Utility Layer:**
- Purpose: Provide shared helper functions for formatting, data extraction, analytics
- Location: `utils/formatting.py`
- Contains: PDF text extraction, HTML rendering, serialization, analytics computation
- Depends on: Database models, pdfplumber library
- Used by: Routes, services

## Data Flow

**Job Creation Workflow:**

1. User submits job description (text or PDF) via `/dashboard/upload-jd` endpoint
2. Handler extracts PDF text using `extract_pdf_text()` from `utils/formatting.py`
3. Create draft Job record in database with `user_id = current_user.id`
4. User triggers `/dashboard/analyze-jd/<job_id>` to call Claude via `services/ai.py`
5. AI extracts title, department, location, seniority, employment type, salary, skills
6. Handler stores analysis results back to Job record with `ai_analyzed=True`
7. User creates additional jobs manually via `/dashboard/create-job` endpoint

**Candidate Screening Workflow:**

1. User uploads resume PDFs via `/dashboard/upload-resumes/<job_id>` endpoint
2. For each PDF: extract text, create Candidate record with `status="pending"`, store resume file
3. Set job status to "ready"
4. User triggers `/dashboard/start-screening/<job_id>` endpoint
5. Set job status to "processing"
6. For each candidate: call `score_candidate()` from `services/ai.py`
   - Builds screening prompt with job description + resume text
   - Claude returns match scores (overall, skills, experience, education) and summary
   - Extracts candidate name, email, matched skills
   - Updates candidate record with scores and `status="scored"`
7. Set job status to "completed"
8. Frontend fetches sorted results via `/dashboard/results/<job_id>`

**Candidate Communication Workflow:**

1. User selects candidates and sends invites via `/dashboard/send-invites` endpoint
2. Handler calls `send_invite_email()` from `services/email.py`
3. Email sent to `candidate.candidate_email` with scheduling link and custom message
4. Candidate status updated to "invited"
5. User can send custom emails via `/dashboard/send-custom-email`
6. Final decision (hire/reject) via `/dashboard/final-decision`
   - Calls `send_decision_email()` with hire/reject message
   - Sets status to "final_hired" or "final_rejected"
7. For hired candidates: generate onboarding PDF via `/dashboard/generate-onboarding/<candidate_id>`
   - Calls Claude to extract structured data from resume
   - Generates PDF with personal info, position details, skills, education, experience

**State Management:**

- Job workflow: `draft` → `ready` (resumes uploaded) → `processing` (AI screening) → `completed`
- Candidate workflow: `pending` (uploaded) → `scored` (AI analyzed) → `invited` (contacted) → `interview_done` (optional) → `shortlisted` → `final_hired/final_rejected`
- Error handling: Candidates and jobs can have `status="error"` if processing fails
- Data isolation: SQLAlchemy relationships enforce user ownership via `Job.user_id` and cascading foreign keys

## Key Abstractions

**Job:**
- Purpose: Represents a job opening with requirements
- Examples: `user_model.py` lines 28-49
- Pattern: Contains job description text, extracted metadata (title, department, location, salary), required skills, and relationship to multiple candidates

**Candidate:**
- Purpose: Represents a resume submission for a job with AI-generated matching scores
- Examples: `user_model.py` lines 51-71
- Pattern: Stores resume text, extracted candidate info (name, email), AI scores (match, skills, experience, education), matched skills list, status, and final hiring decision

**User:**
- Purpose: Represents a recruiter/hiring manager account
- Examples: `user_model.py` lines 16-26
- Pattern: Stores user authentication (email, password), company info (name, size, role), and relationship to multiple jobs

**Claude API Abstraction:**
- Purpose: Centralized AI prompt handling with retry logic
- Examples: `services/ai.py` lines 29-47 (`call_claude`), lines 50-73 (`build_jd_analysis_prompt`), lines 76-97 (`build_screening_prompt`)
- Pattern: Functions build structured prompts and return parsed JSON responses; `call_claude()` implements exponential backoff retry for rate limiting

**Serialization:**
- Purpose: Convert database objects to JSON-serializable dicts
- Examples: `utils/formatting.py` lines 111-134 (`serialize_candidate`), lines 137-180 (`build_jobs_list`)
- Pattern: Single responsibility functions that transform ORM objects into API response objects with computed fields (status badges, formatted dates, etc.)

## Entry Points

**Web Application:**
- Location: `main.py` (Flask application factory)
- Triggers: `python main.py` runs Flask dev server on port 8080
- Responsibilities: Initialize Flask app, load configuration from environment, register blueprints, set up database context, configure error handlers

**Landing Page:**
- Location: `routes/landing.py` lines 1-9
- Triggers: GET `/` (unauthenticated users)
- Responsibilities: Render landing page template

**Authentication:**
- Location: `routes/auth.py` lines 14-96
- Triggers: GET/POST `/login`, GET/POST `/register`, GET `/logout`
- Responsibilities: User login/registration with password hashing, Flask-Login integration, session management

**Dashboard:**
- Location: `routes/dashboard.py` lines 10-93
- Triggers: GET `/dashboard/`, GET `/dashboard/jobs`, GET `/dashboard/candidates`, GET `/dashboard/analytics`, GET `/dashboard/settings` (all `@login_required`)
- Responsibilities: Fetch user-scoped data, compute stats, render dashboard views

**Job Management API:**
- Location: `routes/api/jobs.py` lines 26-253
- Triggers: POST `/dashboard/upload-jd`, POST `/dashboard/analyze-jd/<job_id>`, POST `/dashboard/create-job`, GET `/dashboard/job-detail/<job_id>`, GET `/dashboard/jobs-filtered`, PATCH `/dashboard/update-job-status/<job_id>`, DELETE `/dashboard/delete-job/<job_id>`
- Responsibilities: Upload/create/analyze jobs, fetch job details with candidates, filter jobs by department/status/date, update job status, delete jobs and associated files

**Candidate Management API:**
- Location: `routes/api/candidates.py` lines 23-418
- Triggers: POST `/dashboard/upload-resumes/<job_id>`, DELETE `/dashboard/remove-resume/<candidate_id>`, POST `/dashboard/start-screening/<job_id>`, POST `/dashboard/screen-new-candidates/<job_id>`, GET `/dashboard/results/<job_id>`, DELETE `/dashboard/delete-candidate/<candidate_id>`, GET `/dashboard/candidate-pdf/<candidate_id>`, GET `/dashboard/resume-pdf/<candidate_id>`, POST `/dashboard/send-invites`, POST `/dashboard/final-decision`, POST `/dashboard/send-custom-email`, POST `/dashboard/generate-onboarding/<candidate_id>`, GET `/dashboard/analytics-data`, GET `/dashboard/analytics-export-csv`
- Responsibilities: Resume upload/processing, AI screening orchestration, candidate PDF reports, interview/hiring decisions, email communications, onboarding document generation, analytics computation

## Error Handling

**Strategy:** User-facing error messages via JSON responses, server-side logging, graceful fallbacks for optional features

**Patterns:**

- **Authentication:** Return 404 on unauthorized access (via `login_manager.unauthorized_callback = lambda: abort(404)`)
- **Resource Not Found:** Return 404 with `{"success": False, "error": "Job not found"}` for invalid IDs or ownership mismatches
- **File Processing:** Try-except with file cleanup on PDF extraction failure; fallback to user-entered text if PDF fails
- **AI Integration:** Rate limiting handled with `anthropic.RateLimitError` caught and retried; on failure, candidate gets `status="error"` with error message; requests can continue with other candidates
- **Validation:** Check required fields (email, password, file types), return 400 with validation error message
- **Database:** SQLAlchemy transactions with `db.session.commit()` after mutations; cascade delete on user/job deletion

**Global Error Pages:** `main.py` lines 25-39 register error handlers for 400, 403, 404, 405, 500 that render custom error.html template

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module with logger instances in each service module
- Pattern: `logger.error()`, `logger.warning()`, `logger.debug()` for operational events, PDF extraction failures, AI processing errors

**Validation:**
- Pattern: Route handlers check required fields before processing; type conversion with try-except for numeric fields (salary)
- Location: `routes/api/jobs.py` lines 124-141, `routes/api/candidates.py` lines 279-280

**Authentication:**
- Pattern: Flask-Login `@login_required` decorator on all dashboard and API endpoints; `current_user` context variable in handlers
- Location: `routes/auth.py` lines 9-11 (user loader), all dashboard/API routes

**File Management:**
- Pattern: User-scoped upload directories using `current_user.id` path; secure filename handling with `werkzeug.utils.secure_filename`
- Location: `routes/api/jobs.py` lines 38-40, `routes/api/candidates.py` lines 35-36
- Cleanup: Resume files deleted when candidate/job deleted; JD files cleaned up on extraction failure

**Environment Configuration:**
- Pattern: `.env` file loading with `python-dotenv`; Flask app config object stores secrets and paths
- Required env vars: `SECRET_KEY`, `DATABASE_URL`, `ANTHROPIC_API_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`
- Location: `main.py` lines 11-20

---

*Architecture analysis: 2026-02-25*
