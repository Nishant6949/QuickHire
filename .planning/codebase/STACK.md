# Technology Stack

**Analysis Date:** 2026-02-25

## Languages

**Primary:**
- Python 3.14.2 - Backend application logic, routing, database models, AI integration, email services, PDF processing

**Secondary:**
- HTML/CSS/JavaScript - Frontend templates and static assets in `templates/` and `static/`

## Runtime

**Environment:**
- Python 3.14.2 (development environment at `/Users/mik/Desktop/code/QuickHire/.venv`)

**Package Manager:**
- pip (Python package manager)
- Lockfile: `requirements.txt` (minimal - lists dependencies without versions pinned)

## Frameworks

**Core:**
- Flask 3.x - Web application framework, routing, request handling
  - Location: `main.py` - Flask app initialization and configuration
  - Blueprints: `routes/auth.py`, `routes/landing.py`, `routes/dashboard.py`, `routes/api/jobs.py`, `routes/api/candidates.py`

**ORM/Database:**
- Flask-SQLAlchemy - SQL database abstraction and ORM layer
- SQLAlchemy - Core ORM with type-annotated models
  - Models: `user_model.py` - User, Job, Candidate models with relationships

**Authentication:**
- Flask-Login - Session and user authentication management
  - Configured: `user_model.py` - LoginManager initialization
  - Protected routes: All routes in `routes/` use `@login_required` decorator

**Build/Deployment:**
- Gunicorn - WSGI HTTP server for production
  - Procfile: `web: gunicorn main:app`

## Key Dependencies

**Critical:**
- anthropic 0.x - Claude AI API client for candidate screening and job description analysis
  - Usage: `services/ai.py` - score_candidate(), call_claude()
  - Usage: `routes/api/candidates.py` - AI-powered resume screening
  - Usage: `routes/api/jobs.py` - JD analysis and structured data extraction

- flask_sqlalchemy - Database session management and ORM integration
- sqlalchemy - Type-annotated declarative base models

- python-dotenv - Environment variable loading from `.env` file

**PDF Processing:**
- pdfplumber - Extract text from PDF files
  - Usage: `utils/formatting.py` - extract_pdf_text() function
  - Processes: Resume PDFs, Job Description PDFs

- fpdf2 - Generate PDF reports for candidates and onboarding documents
  - Usage: `services/pdf.py` - generate_candidate_report(), generate_onboarding_doc()

**Email:**
- Built-in smtplib (Python stdlib) - SMTP email delivery
  - Usage: `services/email.py` - Gmail SMTP connection and message delivery

**Web Framework Support:**
- werkzeug - WSGI utilities, secure file uploads, utilities
  - Usage: `routes/api/candidates.py`, `routes/api/jobs.py` - secure_filename() for upload handling

## Configuration

**Environment:**
- Configuration via `.env` file (present but not version-controlled)
- Loaded by `python-dotenv` in `main.py` using `load_dotenv()`

**Required Configuration Variables:**
```
SECRET_KEY              # Flask session secret
DATABASE_URL            # SQLAlchemy database connection string
ANTHROPIC_API_KEY       # Claude API key for AI features
GMAIL_ADDRESS           # Gmail account for sending emails
GMAIL_APP_PASSWORD      # Gmail app-specific password for SMTP auth
```

**Flask App Configuration:**
- `UPLOAD_FOLDER` - Set to `uploads/` directory in project root
- `MAX_CONTENT_LENGTH` - Set to 16 MB (for resume uploads)
- `SQLALCHEMY_DATABASE_URI` - From DATABASE_URL env var

## Platform Requirements

**Development:**
- Python 3.14.2+
- pip for dependency management
- `.env` file with required configuration variables

**Production:**
- Python 3.14.2+ runtime
- PostgreSQL or other SQLAlchemy-compatible database
- SMTP-compatible mail server (Gmail or alternative)
- Anthropic API access with valid API key
- Gunicorn or compatible WSGI server

---

*Stack analysis: 2026-02-25*
