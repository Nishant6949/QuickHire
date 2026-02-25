# QuickHire

## What This Is

QuickHire is an AI-powered recruitment platform that helps recruiters upload job descriptions, screen candidate resumes using Claude AI, and manage the hiring pipeline — from initial screening through interview invitations to final hiring decisions. Built with Flask (Python) backend, Jinja2 templates, and vanilla JavaScript frontend.

## Core Value

Recruiters can upload resumes and get AI-powered candidate scoring and ranking against job descriptions — the screening automation is the product's reason to exist.

## Requirements

### Validated

<!-- Shipped and confirmed valuable — existing MVP capabilities. -->

- ✓ User registration and login with session management — existing
- ✓ Job description upload (PDF or text) with AI-powered analysis — existing
- ✓ Manual job creation with metadata fields — existing
- ✓ Resume PDF upload and text extraction — existing
- ✓ AI-powered candidate screening with match scoring — existing
- ✓ Candidate ranking and results display — existing
- ✓ Interview invitation emails with scheduling links — existing
- ✓ Final hiring decisions (hire/reject) with email notifications — existing
- ✓ Custom email messaging to candidates — existing
- ✓ PDF report generation for candidates — existing
- ✓ Onboarding document generation — existing
- ✓ Analytics dashboard with hiring metrics — existing
- ✓ Job filtering by department, status, and date — existing
- ✓ User settings page — existing
- ✓ Landing page with public marketing content — existing

### Active

<!-- Current scope: codebase restructuring, optimization, and production hardening. -->

- [ ] Restructure files/folders to follow Flask best practices (app factory pattern, clean blueprints)
- [ ] Deep audit and remove all dead code, consolidate duplicated logic
- [ ] Move business logic from JS to Python — JS handles only DOM manipulation and animations
- [ ] Fix all security gaps (CSRF, XSS, rate limiting, input validation, debug mode, salt length)
- [ ] Fix all performance bottlenecks (N+1 queries, analytics aggregation, PDF generation)
- [ ] Improve code readability through clean naming, small functions, logical organization
- [ ] Pin all dependency versions in requirements.txt

### Out of Scope

<!-- Explicit boundaries. -->

- Supabase auth integration — planned for later milestone, not this one
- Hosting/deployment setup — not hosting at the moment
- New features (notifications, moderation, real-time chat) — optimize what exists first
- Test suite creation — focus is on restructuring, not adding tests this milestone
- Mobile app — web only
- OAuth/social login — deferred to Supabase auth milestone

## Context

QuickHire is a working MVP. The codebase grew organically and now needs cleanup before going public. Key technical context:

- **Stack:** Python 3.14.2, Flask 3.x, SQLAlchemy ORM, Anthropic Claude API, Gmail SMTP, pdfplumber, fpdf2
- **Architecture:** MVC with Flask Blueprints, server-side Jinja2 rendering + client-side AJAX
- **Current pain points:** Monolithic JS files with business logic, inconsistent validation, no CSRF protection, debug mode enabled by default, N+1 queries, analytics computed in Python loops instead of DB
- **Codebase map:** Full analysis available in `.planning/codebase/` (7 documents)

## Constraints

- **Tech stack**: Python/Flask backend, vanilla JS frontend (no React/Vue/Angular) — keep existing stack
- **Auth**: Current Flask-Login stays until Supabase migration in future milestone
- **Database**: SQLAlchemy ORM stays, optimize queries within it
- **AI**: Anthropic Claude API integration stays as-is, just clean up the service layer
- **No new dependencies** unless they solve a specific security/performance problem (e.g., Flask-Limiter for rate limiting, Flask-WTF for CSRF)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Minimal JS — DOM/animations only | User wants Python to handle all logic; JS is presentation layer | — Pending |
| Flask best practices structure | Standard app factory pattern for production readiness | — Pending |
| Fix ALL security gaps | App will be public; no known vulnerabilities acceptable | — Pending |
| Fix ALL performance bottlenecks | Analytics, N+1, PDF gen all need fixing | — Pending |
| Clean code over documentation | Clear naming and small functions preferred over docstrings | — Pending |
| Deep audit + consolidate | Remove dead code AND merge duplicated logic | — Pending |

---
*Last updated: 2026-02-25 after initialization*
