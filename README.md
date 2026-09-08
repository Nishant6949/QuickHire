# QuickHire — Capstone Complete Edition

QuickHire is an AI-assisted recruitment web application built with Flask. It supports job creation, PDF job-description parsing, resume uploads, candidate screening/ranking, candidate workflow management, interview invitations, hiring decisions, PDF reports/onboarding documents, analytics, CSV export, account settings, password reset, and deployment health checks.

## What is complete

- Recruiter registration, login, logout and password reset
- Job creation, filtering, status changes and deletion
- PDF or pasted-text job descriptions
- AI JD analysis with a local fallback when no Anthropic key is configured
- PDF resume extraction and candidate creation
- AI candidate scoring plus zero-cost local fallback scoring
- Candidate pool search/filtering and status workflow
- Interview invitation, custom email and hire/reject email workflows
- Console email preview mode for demos without Gmail credentials
- Candidate report PDF and onboarding document generation
- Analytics dashboard and CSV export
- Supabase/PostgreSQL support plus zero-setup SQLite local mode
- Optional Supabase Storage for original PDFs
- Security headers, safe cookies, file-size limit and health endpoint
- Render/Gunicorn deployment configuration
- Demo data seeder and automated tests

## Recommended Python

Use **Python 3.11**. The repository includes `.python-version` to make the intended runtime explicit.

## Quick local setup

```powershell
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\venv\Scripts\python.exe main.py
```

Open `http://127.0.0.1:8080`.

If `DATABASE_URL` is left blank, QuickHire automatically uses `quickhire.db` (SQLite). This is ideal for local demos.

## Create demo data

```powershell
.\venv\Scripts\python.exe seed_demo.py
.\venv\Scripts\python.exe main.py
```

Demo login:

- Email: `demo@quickhire.local`
- Password: `QuickHire123!`

## Supabase/PostgreSQL

For cloud database use, set `DATABASE_URL` to the Supabase Session Pooler PostgreSQL URI. Keep it only in `.env` locally or in the deployment platform's environment-variable settings.

Supabase Storage is optional. To retain original PDFs in a Supabase bucket called `documents`, configure `SUPABASE_URL`, `SUPABASE_KEY`, and `ENABLE_SUPABASE_STORAGE=true`.

## AI mode

Set `ANTHROPIC_API_KEY` for Claude-based semantic analysis. If it is omitted, QuickHire remains fully demonstrable: it extracts skills, contact information, experience and education using its local fallback scorer.

## Email mode

By default `EMAIL_MODE=console`. Email actions succeed in demo mode and a safe preview is written to the terminal. To send real Gmail messages, set `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD`.

## Render deployment

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn main:app`
- Set `FLASK_ENV=production`
- Required production variables: `SECRET_KEY`, `DATABASE_URL`
- Optional: `ANTHROPIC_API_KEY`, Gmail settings, Supabase Storage settings

After deployment, check `/health` to verify database connectivity and optional service configuration.

## Important security note

Never commit `.env`, database passwords, API keys or Gmail app passwords. If a credential has been exposed, rotate it before deployment.

## Candidate job portal

QuickHire now includes a public candidate-facing careers flow:

- `/careers` lists active vacancies across QuickHire employers.
- Candidates can search by role/skill/company and location.
- `/careers/job/<id>` displays the role and a public application form.
- Candidates submit their name, email and a PDF resume.
- The application is stored as a Candidate linked to the selected Job and appears in the recruiter's Candidate Pool.
- If the recruiter has Auto-screen enabled, the application is screened automatically using Anthropic when configured or the local fallback scorer otherwise. The candidate never sees the internal match score.
- Duplicate applications using the same email for the same job are rejected.

Draft and closed jobs are excluded from the public careers page.
