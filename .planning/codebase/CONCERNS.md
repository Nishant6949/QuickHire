# Codebase Concerns

**Analysis Date:** 2026-02-25

## Tech Debt

**Monolithic JavaScript Files:**
- Issue: Dashboard, jobs, and candidates JavaScript files are extremely large (1116, 657, 248 lines respectively), making them difficult to maintain and test.
- Files: `static/js/dashboard.js`, `static/js/jobs.js`, `static/js/candidates.js`, `static/js/analytics.js`
- Impact: Changes to UI functionality become risky and error-prone. No module boundaries between concerns. Hard to debug issues.
- Fix approach: Refactor into smaller, focused modules using ES6 modules or a bundler like webpack. Separate concerns: file upload, form validation, API calls, rendering.

**Unstructured Frontend State Management:**
- Issue: Dashboard uses a single `state` object with 14+ properties managed manually via global variables. No clear state flow or mutation control.
- Files: `static/js/dashboard.js` (lines 2-15), entire file
- Impact: Race conditions possible during async operations. State mutations hard to trace. Difficult to add features without breaking existing functionality.
- Fix approach: Adopt a state management pattern (Redux-like or Zustand). Centralize state updates. Add middleware for async side effects.

**Raw innerHTML Usage Throughout Frontend:**
- Issue: Frontend code extensively uses `innerHTML` to render dynamic content (50+ instances across JS files). No consistent HTML escaping pattern.
- Files: `static/js/dashboard.js`, `static/js/jobs.js`, `static/js/analytics.js`, `static/js/candidates.js`
- Impact: XSS vulnerability risk if user input isn't properly escaped. Missing consistent HTML escaping utility.
- Fix approach: Use `textContent` for text, create a proper DOM-building utility, or migrate to a templating library. Implement consistent escaping for all user data.

**Lack of Input Validation Consistency:**
- Issue: Form inputs are validated differently across routes. Some routes validate deeply (auth), others minimally (job creation allows empty descriptions).
- Files: `routes/auth.py`, `routes/api/jobs.py`, `routes/api/candidates.py`
- Impact: Data integrity issues. Invalid data stored in database. Users can create jobs with empty required fields.
- Fix approach: Create a validation layer/library. Use Marshmallow or similar for schema validation. Validate at API entry points consistently.

**Missing Request Rate Limiting:**
- Issue: No rate limiting on API endpoints. Users can spam screening operations, PDF generation, email sends, and AI calls.
- Files: `routes/api/candidates.py`, `routes/api/jobs.py`, `services/ai.py`
- Impact: Anthropic API quota exhaustion. Email server abuse. DoS potential against the platform.
- Fix approach: Implement Flask-Limiter or similar. Rate limit per-user and per-endpoint (especially `/start-screening`, `/analyze-jd`, email endpoints).

## Known Bugs

**Candidate Status Not Set to "error" Consistently:**
- Symptoms: When AI screening fails with an exception, `candidate.candidate_name` is set to empty string if None, but `matched_skills` is never initialized, leaving it as NULL in DB.
- Files: `routes/api/candidates.py` (lines 123-139, 172-185)
- Trigger: Upload resumes, start screening when AI fails (any non-RateLimitError exception)
- Impact: Serialization may fail when reading candidates if `matched_skills` is NULL and code tries to parse JSON.
- Workaround: Check for NULL in `serialize_candidate()` already in place (lines 113-117 of `utils/formatting.py`), but inconsistent error state.

**File Name Collision Risk:**
- Symptoms: Multiple users uploading files with same name to same job could overwrite each other in uploads directory.
- Files: `routes/api/candidates.py` (lines 42-44), `routes/api/jobs.py` (lines 37-41)
- Trigger: Upload resume with duplicate filename under same job_id
- Workaround: Currently using `secure_filename()` but not adding timestamp or user ID to prevent collisions.
- Fix approach: Add UUID or timestamp to saved filename: `timestamp_secure_filename(file.filename)`.

**Authentication Bypass in Error Handler:**
- Symptoms: `login_manager.unauthorized_callback = lambda: abort(404)` masks authentication failures as 404 errors.
- Files: `main.py` (line 23)
- Trigger: Access protected route without login
- Impact: Users won't know if page doesn't exist or they lack permission. Potential security through obscurity issue.
- Workaround: Redirect to login page instead of aborting 404.

**Database Session Not Always Committed on Errors:**
- Symptoms: If an exception occurs between `db.session.add()` and `db.session.commit()`, database gets into inconsistent state.
- Files: `routes/api/candidates.py` (lines 57-68), `routes/api/jobs.py` (lines 63-68)
- Trigger: Exception during resume processing after candidate added but before commit
- Impact: Orphaned database records. Jobs marked "ready" even if no resumes were successfully saved.
- Fix approach: Use try-finally blocks or context managers to ensure rollback on error.

## Security Considerations

**Passwords Hashed with Short Salt Length:**
- Risk: `salt_length=8` is very short (OWASP recommends at least 32 bytes). Makes rainbow table attacks more feasible.
- Files: `routes/auth.py` (lines 67-71)
- Current mitigation: Using `pbkdf2:sha256` with 1000+ iterations (Werkzeug default), which is still secure.
- Recommendations: Increase to at least `salt_length=16`. Consider upgrading to argon2 or bcrypt via `werkzeug.security` if available.

**Email Credentials in Flask Config:**
- Risk: GMAIL_ADDRESS and GMAIL_APP_PASSWORD stored in environment variables and loaded via dotenv. .env file is in .gitignore correctly.
- Files: `main.py` (lines 19-20), `.env` file
- Current mitigation: .env is in .gitignore. File permissions should restrict access.
- Recommendations: Use Google App Password (being used) is good. Consider adding secret rotation strategy. Validate .env is never committed.

**No CSRF Protection on State-Changing Endpoints:**
- Risk: DELETE and PATCH endpoints don't validate CSRF tokens. A malicious site could trigger delete operations.
- Files: `routes/api/candidates.py` (lines 72-89, 222-241), `routes/api/jobs.py` (lines 235-252)
- Current mitigation: Endpoints require `@login_required`, limiting CSRF attack surface.
- Recommendations: Add Flask-WTF CSRF protection or implement custom token validation for API endpoints.

**No Input Size Limits on Text Fields:**
- Risk: Job descriptions and custom email messages have no max length enforced in API layer. User can submit multi-MB strings.
- Files: `routes/api/jobs.py` (lines 130, 131), `routes/api/candidates.py` (lines 362-363)
- Current mitigation: Database field is `Text` type (essentially unlimited), but Flask `MAX_CONTENT_LENGTH` (16MB) provides upper bound.
- Recommendations: Add max length validation at API layer (e.g., 10000 chars for JD description).

**Resume PDF Text Extraction Not Sandboxed:**
- Risk: `pdfplumber.open()` processes untrusted PDF files. Malformed PDFs could cause infinite loops or memory exhaustion.
- Files: `utils/formatting.py` (lines 13-20), `routes/api/jobs.py` (lines 44, 47-48)
- Current mitigation: Errors are caught and logged, file is deleted on failure.
- Recommendations: Add timeout to PDF extraction. Limit file size to 50MB max before processing.

**HTML Email Content Not Validated:**
- Risk: Custom email body in `send_custom_email()` allows raw HTML. User input is escaped but not validated for sanity.
- Files: `services/email.py` (lines 135-170), route at `routes/api/candidates.py` (lines 357-382)
- Impact: User could inject invalid/malicious HTML that breaks email rendering or exploits client vulnerabilities.
- Recommendations: Sanitize HTML using bleach library. Allow only safe HTML tags.

**No Verification of Email Ownership:**
- Risk: Extracted candidate email from resume is taken as-is and emails are sent without verification.
- Files: `services/ai.py` (lines 100-119), `routes/api/candidates.py` (lines 273-315)
- Impact: Could spam wrong email addresses. No way to prove candidate actually provided that email.
- Recommendations: Send verification email first with one-time token. Only mark candidate as "invited" after verification.

## Performance Bottlenecks

**N+1 Query Problem in Candidates Dashboard:**
- Problem: Fetches all candidates, then for each candidate iterates to find job details. One query per candidate.
- Files: `routes/dashboard.py` (lines 44-51), `utils/formatting.py` (lines 137-146)
- Cause: Missing `.join()` in query and inefficient iteration in `serialize_candidate()` which accesses `c.job`.
- Improvement path: Add eager loading with `joinedload()` or separate query for all jobs upfront.
- Current query: `db.select(Candidate).join(Job)` is correct, but accessing `c.job` in loop still triggers lazy loads.

**Inefficient Analytics Data Computation:**
- Problem: Computing analytics iterates through all candidates multiple times (lines 204-274 in `utils/formatting.py`).
- Files: `utils/formatting.py` (lines 183-305)
- Cause: Multiple full table scans. No grouping or aggregation at database level.
- Improvement path: Use database aggregation (GROUP BY, COUNT, etc) instead of Python loops. Currently 8+ iterations through `all_candidates`.
- Impact: With 1000+ candidates, response time is 2-5 seconds per request. Blocks analytics page.

**PDF Generation Blocks Request:**
- Problem: `generate_onboarding_doc()` and `generate_candidate_report()` call AI for extraction, then generate PDF synchronously.
- Files: `services/pdf.py` (lines 109-247), `routes/api/candidates.py` (line 397)
- Cause: No async processing or background job queue.
- Improvement path: Move PDF generation to async task (Celery/RQ). Return job ID to client, check status via polling.
- Current impact: User request hangs for 2-3 seconds waiting for AI + PDF generation.

**Database Queries in Template Rendering:**
- Problem: Dashboard page queries for draft job, jobs page queries all jobs and all candidates for filtering.
- Files: `routes/dashboard.py` (line 13-18), `routes/dashboard.py` (line 30)
- Cause: Queries executed per page load, not cached.
- Improvement path: Add query result caching (Redis) with 1-hour TTL. Invalidate on create/update.

## Fragile Areas

**AI Response Parsing:**
- Files: `services/ai.py` (lines 11-19), `services/pdf.py` (lines 117-132)
- Why fragile: Regex-based parsing of Claude JSON output. If Claude returns slightly different format, parsing fails silently or with cryptic error.
- Safe modification: Add detailed logging of raw AI responses. Add validation schema. Implement fallback responses.
- Test coverage: No unit tests for `parse_ai_json()`. Edge cases like malformed JSON untested.

**File Upload Directory Structure:**
- Files: `routes/api/candidates.py` (lines 35-36), `routes/api/jobs.py` (lines 38-39)
- Why fragile: Hardcoded path construction `os.path.join(UPLOAD_FOLDER, "resumes", str(job_id))`. If directory doesn't exist, upload fails silently.
- Safe modification: Always call `os.makedirs(..., exist_ok=True)` before any file operations.
- Test coverage: No tests for directory creation edge cases.

**Candidate Status Transitions:**
- Files: `routes/api/candidates.py` (lines 129, 177, 294, 336), `user_model.py` (line 65)
- Why fragile: No state machine. Any code can set any status. No validation of transitions (e.g., can you go from "final_rejected" to "invited"?).
- Safe modification: Add a `CandidateStatus` enum. Add transition validation method.
- Test coverage: No tests for invalid status transitions.

**Email Sending Failures:**
- Files: `services/email.py` (lines 69-76, 124-132, 161-169)
- Why fragile: Returns False on any exception but doesn't distinguish between "wrong credentials" vs "network timeout" vs "invalid email address".
- Safe modification: Raise specific exceptions. Let caller decide retry strategy.
- Test coverage: No tests for email service. No mock SMTP testing.

## Scaling Limits

**In-Memory State Limit:**
- Current capacity: Single server, ~500 concurrent users before memory exhaustion.
- Limit: `generate_diary.py` appears unused but is a 909-line file. Dashboard state is all in-memory per browser session.
- Scaling path: Implement server-side session storage (Redis). Offload state to database. Use horizontal scaling with load balancer.

**Database Query Performance at Scale:**
- Current capacity: ~10k candidates before analytics queries timeout (3+ seconds).
- Limit: `compute_analytics_data()` iterates all candidates multiple times. No indexes on composite keys.
- Scaling path: Add database indexes on `(job_id, created_at)`, `(job_id, status)`, `(job_id, match_score)`. Implement query result caching.

**Anthropic API Rate Limits:**
- Current capacity: ~100 concurrent screening operations before hitting Anthropic's rate limits.
- Limit: `call_claude()` has retry logic with exponential backoff, but no queue or request prioritization.
- Scaling path: Implement job queue (Celery). Rate limit requests client-side. Add batch screening operation.

**File Storage at Scale:**
- Current capacity: Single server filesystem, ~50GB before space issues.
- Limit: PDFs and resumes stored locally. No cleanup mechanism.
- Scaling path: Move to S3/cloud storage. Implement TTL-based deletion for old uploads (e.g., 90 days).

## Dependencies at Risk

**Anthropic SDK Version Not Pinned:**
- Risk: `anthropic` package imported but no version specified in requirements. API changes could break code.
- Files: `main.py`, `services/ai.py`, `services/pdf.py`, `routes/api/jobs.py`, `routes/api/candidates.py`
- Impact: Upgrading packages could cause breaking changes in AI response format or API.
- Migration plan: Pin to specific version `anthropic==0.43.0` or similar. Add CI tests against minor upgrades.

**pdfplumber Potential Performance Issue:**
- Risk: `pdfplumber` is in-memory PDF processor. Large PDFs (100+ MB) could exhaust RAM or timeout.
- Files: `utils/formatting.py` (lines 13-20)
- Impact: Resume extraction for large PDFs fails or hangs the app.
- Migration plan: Consider pypdf or pdfminer for streaming processing. Add file size pre-check.

**Flask Debug Mode in Production:**
- Risk: `main.py` line 54 runs with `debug=True` by default. This is dangerous in production.
- Files: `main.py` (line 54)
- Impact: Debug toolbar leaks sensitive information. Automatic reloader runs dangerous code.
- Mitigation plan: Check environment variable: `app.run(debug=os.getenv("FLASK_ENV") == "development", ...)`

**No Version Pinning in Dependencies:**
- Risk: No `requirements.txt` or `setup.py` visible in codebase. Virtual environment may have loose version specs.
- Files: Not visible in provided code
- Impact: Deployments may succeed locally but fail in CI/production due to dependency version mismatches.
- Migration plan: Generate `requirements.txt` with exact versions: `pip freeze > requirements.txt`

## Missing Critical Features

**No Audit Logging:**
- Problem: No tracking of who made what changes. User actions (delete job, send invite, hire candidate) not logged.
- Blocks: Compliance requirements. Ability to debug issues. Forensic investigation of data changes.

**No Backup/Recovery Strategy:**
- Problem: SQLite database with no backup mechanism. Single point of failure.
- Blocks: Production deployment. Data recovery if database corrupts.

**No Email Unsubscribe Link:**
- Problem: Emails sent to candidates have no unsubscribe mechanism. May violate CAN-SPAM or equivalent.
- Blocks: Legal compliance. Candidates can't opt-out of emails.

**No Password Reset:**
- Problem: No "forgot password" functionality. Locked-out users can't recover account.
- Blocks: User support burden. Poor UX.

**No Two-Factor Authentication:**
- Problem: Only password-based login. No 2FA option.
- Blocks: Security hardening. Compliance with security-conscious customers.

## Test Coverage Gaps

**No API Endpoint Tests:**
- What's not tested: All routes in `routes/api/candidates.py` and `routes/api/jobs.py`. File upload, AI screening, PDF generation, email sending.
- Files: `routes/api/candidates.py`, `routes/api/jobs.py`
- Risk: Breaking changes to API undetected. Edge cases in error handling not covered.
- Priority: High - These are revenue-critical flows.

**No Frontend Unit Tests:**
- What's not tested: JavaScript form validation, state transitions, API call error handling in `static/js/dashboard.js`.
- Files: `static/js/dashboard.js`, `static/js/jobs.js`, `static/js/candidates.js`
- Risk: UI bugs released to production. Race conditions in async operations.
- Priority: High - Dashboard is most-used feature.

**No Service Layer Tests:**
- What's not tested: `services/ai.py` (parse_ai_json, call_claude), `services/email.py`, `services/pdf.py`.
- Files: `services/ai.py`, `services/email.py`, `services/pdf.py`
- Risk: AI parsing failures, email sending failures, PDF generation errors caught in production.
- Priority: Medium - Can add mocks for external services.

**No Database Migration Tests:**
- What's not tested: Schema changes, data consistency after migrations.
- Files: `user_model.py`
- Risk: Database corruption on upgrades. Lost data.
- Priority: Medium - Only relevant if schema changes frequently.

**No Integration Tests:**
- What's not tested: Full flows like "upload job → upload resumes → screen → send invites → hire". End-to-end candidate journey.
- Files: Multiple routes working together
- Risk: Subtle bugs where features interact. Missing edge case combinations.
- Priority: Medium-High - Critical for user-facing flows.

---

*Concerns audit: 2026-02-25*
