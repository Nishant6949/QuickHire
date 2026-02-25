# External Integrations

**Analysis Date:** 2026-02-25

## APIs & External Services

**AI/LLM:**
- Anthropic Claude API - AI-powered candidate screening and job description analysis
  - SDK/Client: `anthropic` Python package
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Model: `claude-sonnet-4-20250514` (specified in `services/ai.py` line 33)
  - Usage:
    - `services/ai.py` - call_claude(), score_candidate()
    - `routes/api/candidates.py` - Candidate resume screening (lines 125, 174)
    - `routes/api/jobs.py` - Job description analysis and extraction (line 85)
  - Features Used:
    - Structured JSON extraction from job descriptions
    - Resume scoring with candidate matching
    - Skill extraction and analysis
    - Rate limiting handling with exponential backoff retry

## Data Storage

**Databases:**
- SQLAlchemy-compatible relational database (configured via `DATABASE_URL` env var)
  - Connection: `DATABASE_URL` environment variable
  - Client: `flask_sqlalchemy` (Flask integration) with `sqlalchemy` ORM
  - Models: `user_model.py`
    - User - Stores recruiter/hiring manager accounts
    - Job - Job postings with descriptions and metadata
    - Candidate - Resume submissions with AI-generated scores and match data
  - Features: Cascading deletes, relationships, timestamps, type-annotated models

**File Storage:**
- Local filesystem only
  - Resume uploads: `uploads/resumes/{job_id}/` directory
  - JD file uploads: `uploads/jd/{user_id}/` directory
  - Generated PDFs: Streamed directly to client (no persistent storage)
  - Max upload size: 16 MB (configured in `main.py` line 17)
  - Upload handling: `werkzeug.utils.secure_filename()` for security

**Caching:**
- None detected

## Authentication & Identity

**Auth Provider:**
- Custom authentication with Flask-Login
  - Implementation: Session-based with password hashing
  - Location: `routes/auth.py` - User registration and login
  - Location: `user_model.py` - User model with UserMixin
  - Session management: `flask_login.login_required` decorator protects all API routes
  - Unauthorized redirect: Returns 404 (configured in `main.py` line 23)

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry, Rollbar, or similar)

**Logs:**
- Python `logging` module (stdlib)
  - Approach: Console logging with logger instances in each module
  - Loggers:
    - `routes/api/candidates.py` - Resume extraction, screening errors, email delivery
    - `routes/api/jobs.py` - JD processing and analysis errors
    - `services/email.py` - Email send failures
    - `services/ai.py` - Claude API rate limiting and response parsing
  - Levels: WARNING, ERROR, INFO, DEBUG

## CI/CD & Deployment

**Hosting:**
- Heroku (inferred from `Procfile` presence)
  - Procfile: `web: gunicorn main:app`
  - Deployment: Python buildpack via gunicorn WSGI

**CI Pipeline:**
- None detected (no GitHub Actions, CircleCI, or similar)

## Environment Configuration

**Required env vars:**
```
SECRET_KEY              # Flask session secret for security
DATABASE_URL            # Database connection string (PostgreSQL or compatible)
ANTHROPIC_API_KEY       # Anthropic API key for Claude access
GMAIL_ADDRESS           # Gmail account for sending emails (from address)
GMAIL_APP_PASSWORD      # Gmail app-specific password for SMTP authentication
```

**Secrets location:**
- `.env` file (present at project root, not version-controlled per `.gitignore`)
- Never commit secrets to git

**Sample .env structure:**
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost/quickhire_users_info
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
GMAIL_ADDRESS=your-gmail@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- Email callbacks: Implicit via SMTP delivery confirmation
  - Send invite email: `services/email.py` send_invite_email() (lines 11-76)
  - Send decision email: `services/email.py` send_decision_email() (lines 79-132)
  - Send custom email: `services/email.py` send_custom_email() (lines 135-169)
  - Success/failure returned as boolean to API callers

## Email Integration

**Provider:** Gmail SMTP
  - Server: smtp.gmail.com:465 (SSL/TLS)
  - Authentication: App-specific password (OAuth would be better)
  - Service location: `services/email.py`

**Email Templates:**
  - Interview invitations with scheduling links
  - Hiring decisions (acceptance/rejection)
  - Custom messages from recruiters
  - All templates use HTML styling with dark theme (QuickHire branding)
  - Built dynamically in Python strings (no template engine)

**Email Features:**
- MIME multipart HTML messages
- Candidate name and company name personalization
- Scheduling link injection for interview coordination
- Custom message support
- Error handling with logging fallback

---

*Integration audit: 2026-02-25*
