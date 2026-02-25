# Coding Conventions

**Analysis Date:** 2026-02-25

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (e.g., `user_model.py`, `services/ai.py`, `routes/auth.py`)
- JavaScript files: `snake_case.js` (e.g., `static/js/dashboard.js`, `static/js/utils.js`)
- Directories: `snake_case` for Python, `snake_case` for JavaScript (e.g., `routes/`, `services/`, `static/js/`)

**Functions (Python):**
- Use `snake_case` consistently (e.g., `extract_pdf_text()`, `format_salary()`, `parse_ai_json()`)
- Route handlers use descriptive names matching HTTP operation: `login()`, `register()`, `upload_jd()`, `analyze_jd()`
- Helper functions prefixed with `_` for internal use (e.g., `_close_list()`, `_esc()`)
- Service functions named by operation: `call_claude()`, `score_candidate()`, `send_invite_email()`

**Functions (JavaScript):**
- Use `camelCase` (e.g., `cacheElements()`, `bindStep1()`, `refreshIcons()`)
- Factory/helper functions: `escapeHtml()`, `scoreColorClass()`
- Private/internal functions within IIFE scope pattern

**Variables (Python):**
- Local variables: `snake_case` (e.g., `jd_text`, `user_id`, `salary_min`, `resume_dir`)
- Database model attributes: `snake_case` with type hints (e.g., `candidate_name: Mapped[str]`)
- Private module variables: `logger = logging.getLogger(__name__)`
- Flags: `is_uploading`, `is_analyzing`, `ai_analyzed`, `onboarding_generated`

**Variables (JavaScript):**
- Local variables: `camelCase` (e.g., `currentStep`, `jobId`, `isUploading`)
- Object properties: `camelCase` (e.g., `jdMode`, `analysisResult`, `selectedIds`)
- State object keys: `camelCase` for consistency
- Element references cached with prefix: `els.jdDropZone`, `els.resumeList`

**Types & Classes:**
- Python model classes: `PascalCase` (e.g., `User`, `Job`, `Candidate`)
- SQLAlchemy table names: `snake_case` explicitly set (e.g., `__tablename__ = "jobs"`)
- Enums/constants: `SNAKE_CASE_ALL_CAPS` (e.g., `ERROR_PAGES = {...}`, `allowed = {"open", "draft", "closed", "completed"}`)

## Code Style

**Formatting (Python):**
- No explicit linter/formatter config detected
- Standard Python conventions observed: 4-space indentation
- Line length varies (some lines exceed 88 characters - no strict limit enforced)
- Import organization: stdlib, third-party (Flask, SQLAlchemy, anthropic), local imports

**Formatting (JavaScript):**
- No explicit formatter config detected
- 4-space indentation in IIFE patterns
- Line length not strictly limited
- Var declarations: `var` keyword used consistently (not modern `let`/`const`)

**Code Structure:**
- Python: Clear separation between route handlers, services, utils, models
- JavaScript: IIFE (Immediately Invoked Function Expression) wrapping for namespacing
- Consistent use of guard clauses early in functions (null checks, auth checks)

## Import Organization

**Python Order:**
1. Standard library imports (e.g., `import json`, `import os`, `import logging`)
2. Third-party framework imports (e.g., `from flask import`, `from sqlalchemy import`, `from anthropic import`)
3. Flask-specific extensions (e.g., `from flask_login import`, `from flask_sqlalchemy import`)
4. Local imports (e.g., `from user_model import`, `from services.ai import`, `from utils.formatting import`)

**Pattern observed in files:**
```python
import json
import logging
import os

import anthropic
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from user_model import db, Job, Candidate
from services.ai import call_claude, parse_ai_json
from utils.formatting import extract_pdf_text
```

**Path Aliases:**
- Not applicable - no alias configuration detected
- Relative imports within package hierarchy used directly

## Error Handling

**Python Patterns:**
- Try-except blocks with specific exception catching (e.g., `except json.JSONDecodeError`, `except ValueError`)
- Generic exception fallback: `except Exception as e` with logging (`logger.error()`)
- Silent failures with continue statements for file iteration (e.g., in `upload_resumes()`)
- HTTP error responses via Flask: `return jsonify({"success": False, "error": "..."})` with status code
- Early returns with guard clauses: Check auth/ownership first, return 404 if not found

**Patterns:**
```python
try:
    result = parse_ai_json(raw)
    # process result
except json.JSONDecodeError:
    pass  # Silent failure - use default
except Exception as e:
    logger.error("JD analysis failed: %s", e)
    return jsonify({"success": False, "error": str(e)[:200]})
```

**Error Page Handling:**
- Centralized error handler mapping: `ERROR_PAGES = {code: (title, description, icon)}`
- Error handler callback: `render_error(e)` function called for each HTTP error code
- Flask error handlers registered per code: `app.register_error_handler(code, render_error)`

**JavaScript:**
- Minimal error handling observed
- No explicit try-catch patterns in IIFE code
- Relies on success/fallback response handling from API calls

## Logging

**Framework:** Python `logging` module

**Setup:**
- Logger created per module: `logger = logging.getLogger(__name__)`
- Used in service modules: `services/ai.py`, `services/email.py`, `routes/api/jobs.py`

**Patterns:**
- Debug level: `logger.debug("AI response for %s: %s", candidate.resume_filename, raw[:300])`
- Warning level: `logger.warning("Claude rate limited, retrying in %ds", wait)`
- Error level: `logger.error("JD PDF extraction failed: %s", e)`, `logger.error("Failed to send invite email to %s: %s", to_email, e)`
- Info level: `logger.info("Decision email (%s) sent to %s", decision, to_email)`

**When to Log:**
- External API calls (Anthropic, Gmail)
- File operations (extraction failures)
- Database operations with potential errors
- Email sending success/failure
- Rate limit retry logic

**JavaScript:**
- No logging framework used
- Console methods not called in static JS files

## Comments

**When to Comment (Python):**
- Complex regex patterns with explanation: `fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL) # Extract JSON fence`
- Non-obvious algorithm logic (e.g., salary parsing, time bucketing in analytics)
- Minimal comments overall - code is relatively self-documenting

**JSDoc/TSDoc:**
- Not used in this codebase
- No docstring patterns observed
- Functions are short and self-documenting

**Comments Observed:**
```python
# Silent failure - use default
# Note existence only, never read contents
# Extract key_skills which is a list
```

## Function Design

**Size:**
- Python: Functions range 15-80 lines
- Shorter functions for specific operations (e.g., `format_salary()` = 6 lines)
- Longer functions for complex multi-step operations (e.g., `compute_analytics_data()` = 120+ lines)

**Parameters:**
- Functions accept explicit parameters, not dict unpacking
- Optional parameters with `None` defaults: `def call_claude(client, prompt, system=None, max_retries=3)`
- Route handlers use Flask request object for form/JSON data
- Database sessions accessed via `current_user`, `current_app.config`

**Return Values:**
- Flask routes return tuple: `(response_data, status_code)` or single dict/template
- API endpoints return JSON: `jsonify({"success": True/False, "data": ...})`
- Service functions return processed values or None on failure
- Boolean flags for checks: `if check_password_hash(...)`, `if not user`

**Guard Clauses:**
- Check authentication first: `@login_required` decorator
- Check resource ownership: `if not job or job.user_id != current_user.id: return 404`
- Validate input before processing: `if not all([...])`, `if not files`

## Module Design

**Exports:**
- Blueprint registration: `jobs_api_bp = Blueprint(...)` then registered in `main.py`
- Model exports: Classes defined in `user_model.py`, imported in routes/services
- Service functions exported directly: `from services.ai import call_claude, parse_ai_json`
- Utility functions exported directly: `from utils.formatting import extract_pdf_text, format_salary`

**Pattern:**
```python
# services/ai.py
def parse_ai_json(raw_text):  # Exported
def call_claude(client, prompt, system=None, max_retries=3):  # Exported
def build_jd_analysis_prompt(jd_text):  # Helper
```

**Barrel Files:**
- Not used - imports are direct from specific modules
- `__init__.py` files exist but are empty

**Module Organization:**
- `user_model.py` - All ORM models and database setup
- `routes/` - HTTP endpoint handlers organized by feature
- `services/` - Business logic (AI, PDF, Email)
- `utils/` - Formatting and data transformation helpers
- `static/js/` - Frontend JavaScript organized by page

## Database Access

**Pattern (SQLAlchemy 2.0 style):**
```python
# Query
result = db.session.execute(db.select(User).where(User.work_email == email))
user = result.scalar()

# Get by ID
job = db.session.get(Job, job_id)

# Add/Delete
db.session.add(new_user)
db.session.delete(job)
db.session.commit()
```

**Type Hints:**
- SQLAlchemy Mapped types used consistently: `id: Mapped[int]`, `title: Mapped[str | None]`
- Optional fields: `Mapped[str | None]` with `nullable=True`
- Relationships: `Mapped[list["Job"]]` for one-to-many

## File Organization Best Practices

**Routes organization:**
- Page routes: `routes/auth.py`, `routes/dashboard.py`, `routes/landing.py`
- API routes: `routes/api/jobs.py`, `routes/api/candidates.py`
- Blueprints created per module with url_prefix

**Services:**
- One responsibility each: `services/ai.py` (Claude), `services/email.py` (Gmail), `services/pdf.py` (PDF generation)
- Pure functions without Flask context where possible
- Functions that need Flask config receive `current_app` as context

**Utils:**
- `utils/formatting.py` - Data transformation and HTML rendering
- Focused on output formatting, not business logic

---

*Convention analysis: 2026-02-25*
