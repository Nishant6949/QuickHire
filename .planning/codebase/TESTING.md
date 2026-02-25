# Testing Patterns

**Analysis Date:** 2026-02-25

## Test Framework

**Runner:**
- Not detected - No test framework configured

**Assertion Library:**
- Not used

**Test Files:**
- No test files found in repository
- No `pytest.ini`, `tox.ini`, `conftest.py`, or test configuration files

**Run Commands:**
- Testing infrastructure not set up
- No test runner commands available

## Test File Organization

**Location:**
- Not applicable - no tests present

**Naming:**
- Recommended pattern: `test_*.py` or `*_test.py` for files in `tests/` directory

**Structure:**
- Recommended directory structure:
```
QuickHire/
├── tests/
│   ├── __init__.py
│   ├── test_models.py          # Database model tests
│   ├── test_auth.py            # Authentication routes
│   ├── test_routes/
│   │   ├── test_jobs.py        # Job API endpoints
│   │   └── test_candidates.py  # Candidate API endpoints
│   ├── test_services/
│   │   ├── test_ai.py          # Claude AI service
│   │   ├── test_email.py       # Email service
│   │   └── test_pdf.py         # PDF generation
│   └── test_utils/
│       └── test_formatting.py  # Formatting utilities
├── conftest.py                 # Pytest fixtures
├── pytest.ini                  # Pytest configuration
```

## Test Structure (Recommended Pattern)

**Suggested Pytest structure based on codebase patterns:**

```python
# tests/conftest.py - Shared fixtures
import pytest
from flask import Flask
from user_model import db, User, Job, Candidate

@pytest.fixture
def app():
    """Create app with test configuration"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Flask CLI runner"""
    return app.test_cli_runner()

@pytest.fixture
def sample_user(app):
    """Create test user"""
    user = User(
        first_name="Test",
        last_name="User",
        work_email="test@example.com",
        company_name="Test Corp",
        company_size="10-50",
        role="Recruiter",
        password="hashed_password"
    )
    db.session.add(user)
    db.session.commit()
    return user
```

**Test suite organization:**

```python
# tests/test_auth.py - Authentication route tests
import pytest

class TestAuthRoutes:
    """Authentication endpoint tests"""

    def test_login_with_valid_credentials(self, client, sample_user):
        """User can login with correct password"""
        # Setup
        # Execute
        response = client.post('/login', data={...})
        # Assert
        assert response.status_code == 302

    def test_login_with_invalid_email(self, client):
        """Login fails with non-existent email"""
        response = client.post('/login', data={'login-email': 'nonexistent@test.com'})
        assert response.status_code == 302
        # Check flash message present
```

## Mocking

**Framework:**
- Recommended: `unittest.mock` (stdlib) or `pytest-mock` (plugin)

**Patterns (Recommended):**

```python
# For external API calls (Anthropic, Gmail)
from unittest.mock import patch, MagicMock

def test_analyze_jd_with_ai(client, sample_user, sample_job):
    """JD analysis calls Claude API"""
    with patch('services.ai.anthropic.Anthropic') as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content[0].text = '{"title": "Engineer"}'
        mock_client.messages.create.return_value = mock_response

        response = client.post(f'/dashboard/analyze-jd/{sample_job.id}')
        assert response.json['success'] == True
        mock_client.messages.create.assert_called_once()

# For email sending
def test_send_invite_email(client, sample_candidate):
    """Email sends successfully"""
    with patch('services.email.smtplib.SMTP_SSL') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        from services.email import send_invite_email
        result = send_invite_email("test@test.com", "Candidate", "Engineer", None, 30, "Join us")

        assert result == True
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()

# For file operations
def test_upload_jd_pdf(client, sample_user, tmp_path):
    """JD PDF upload extracts text"""
    with patch('services.pdf.pdfplumber.open') as mock_pdf:
        mock_pdf_obj = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Senior Engineer Role"
        mock_pdf_obj.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf_obj

        client.post('/login', data={...})
        pdf_file = (tmp_path / "test.pdf").write_text("dummy")
        response = client.post('/dashboard/upload-jd', data={'jd_file': pdf_file})

        assert response.json['success'] == True
```

**What to Mock:**
- External API calls: Anthropic Claude API (`anthropic.Anthropic`)
- Email: SMTP server (`smtplib.SMTP_SSL`)
- File I/O: PDF extraction (`pdfplumber.open`)
- Current time: For timestamp testing (use `freezegun` or `unittest.mock.patch`)
- Database queries in service tests (optional - use real DB with fixtures is preferred)

**What NOT to Mock:**
- Database models and relationships (use test DB fixtures)
- Flask request/response objects (use test client)
- Internal service functions (test integration instead)
- Password hashing (test real hashing for security tests)

## Fixtures and Factories

**Test Data (Recommended pattern):**

```python
# tests/fixtures.py - Shared test factories
from user_model import User, Job, Candidate
from datetime import datetime, timezone

def create_user(db_session, **kwargs):
    """Factory for creating test users"""
    defaults = {
        'first_name': 'Test',
        'last_name': 'User',
        'work_email': f'user_{datetime.now().timestamp()}@test.com',
        'company_name': 'Test Company',
        'company_size': '10-50',
        'role': 'Recruiter',
        'password': 'hashed_pw'
    }
    defaults.update(kwargs)
    user = User(**defaults)
    db_session.add(user)
    db_session.commit()
    return user

def create_job(db_session, user, **kwargs):
    """Factory for creating test jobs"""
    defaults = {
        'user_id': user.id,
        'title': 'Senior Engineer',
        'jd_text': 'Looking for a senior engineer with 5+ years experience',
        'department': 'Engineering',
        'location': 'Remote',
        'status': 'open'
    }
    defaults.update(kwargs)
    job = Job(**defaults)
    db_session.add(job)
    db_session.commit()
    return job

def create_candidate(db_session, job, **kwargs):
    """Factory for creating test candidates"""
    defaults = {
        'job_id': job.id,
        'resume_text': 'Engineer with 7 years experience at Tech Corp',
        'resume_filename': 'resume.pdf',
        'candidate_name': 'John Doe',
        'candidate_email': 'john@example.com',
        'match_score': 85,
        'status': 'pending'
    }
    defaults.update(kwargs)
    candidate = Candidate(**defaults)
    db_session.add(candidate)
    db_session.commit()
    return candidate
```

**Location:**
- Recommended: `tests/fixtures.py` for factory functions
- Or use `conftest.py` for pytest fixtures

## Coverage

**Requirements:**
- Not enforced - no coverage configuration detected
- Recommended targets:
  - Critical paths (auth, API endpoints): 80%+
  - Services (AI, Email, PDF): 85%+
  - Utils (formatting): 90%+
  - Models: 80%+

**View Coverage (Recommended):**
```bash
# Install coverage tool
pip install pytest-cov

# Run tests with coverage report
pytest tests/ --cov=. --cov-report=html

# View HTML report
open htmlcov/index.html
```

**Config (Recommended `pytest.ini`):**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --cov=. --cov-report=html --cov-report=term-missing --tb=short
```

## Test Types

**Unit Tests:**
- Scope: Individual functions and methods
- Approach: Mock all external dependencies
- Examples:
  - `test_parse_ai_json()` - JSON parsing with invalid input
  - `test_clamp_score()` - Score boundary validation
  - `test_format_salary()` - Salary formatting with various inputs
- Location: `tests/test_services/` and `tests/test_utils/`

**Integration Tests:**
- Scope: Multiple components working together
- Approach: Use test database, real Flask client, mock only external APIs
- Examples:
  - `test_upload_jd_and_analyze()` - Upload JD file, trigger AI analysis
  - `test_user_registration_and_login()` - Register user, then login
  - `test_candidate_upload_and_screening()` - Upload resumes, score candidates
- Location: `tests/test_routes/` and `tests/test_integration/`

**E2E Tests:**
- Framework: Not used
- Not applicable to this backend-focused API
- Could be added with `selenium` for frontend testing if needed

## Common Patterns (Recommended)

**Async Testing:**
- Not applicable - Flask is synchronous (no async routes detected)

**Error Testing:**
```python
def test_upload_jd_without_file_or_text(client, sample_user):
    """Upload JD fails when neither file nor text provided"""
    client.post('/login', data={...})  # Login first
    response = client.post('/dashboard/upload-jd', data={})
    assert response.status_code == 400
    assert response.json['success'] == False
    assert 'Please provide a job description' in response.json['error']

def test_upload_jd_with_invalid_file_type(client, sample_user):
    """Upload JD rejects non-PDF files"""
    client.post('/login', data={...})
    response = client.post('/dashboard/upload-jd',
                          data={'jd_file': (None, 'test.txt')})
    assert response.json['error'] == 'Only PDF files are supported'

def test_analyze_jd_with_ai_failure(client, sample_job):
    """JD analysis handles AI service failure gracefully"""
    with patch('services.ai.call_claude') as mock_claude:
        mock_claude.side_effect = anthropic.APIError("Service unavailable")
        response = client.post(f'/dashboard/analyze-jd/{sample_job.id}')
        assert response.json['success'] == False
        assert response.json['fallback'] == True
```

**Database Testing:**
```python
def test_candidate_model_relationships(app, sample_user, sample_job):
    """Candidate model maintains proper relationships"""
    with app.app_context():
        candidate = Candidate(
            job_id=sample_job.id,
            resume_text='Resume text',
            resume_filename='resume.pdf'
        )
        db.session.add(candidate)
        db.session.commit()

        assert candidate.job.id == sample_job.id
        assert candidate in sample_job.candidates
        assert candidate.job.user.id == sample_user.id
```

**API Response Testing:**
```python
def test_job_detail_returns_structured_response(client, sample_user, sample_job):
    """Job detail endpoint returns expected JSON structure"""
    client.post('/login', data={...})
    response = client.get(f'/dashboard/job-detail/{sample_job.id}')

    assert response.json['success'] == True
    job = response.json['job']
    assert 'id' in job
    assert 'title' in job
    assert 'candidates' in response.json
    assert isinstance(response.json['candidates'], list)
```

## Testing Priority (Recommended Order)

1. **High Priority (80%+ coverage):**
   - Authentication (`test_auth.py`) - Password hashing, login/logout, authorization
   - Job API (`test_routes/test_jobs.py`) - CRUD operations, job creation
   - Candidate upload (`test_routes/test_candidates.py`) - Resume upload, validation

2. **Medium Priority (70%+ coverage):**
   - AI service (`test_services/test_ai.py`) - Prompt building, JSON parsing, rate limit retry
   - Email service (`test_services/test_email.py`) - Email template generation, error handling
   - Formatting utils (`test_utils/test_formatting.py`) - HTML rendering, salary formatting

3. **Lower Priority (60%+ coverage):**
   - PDF generation (`test_services/test_pdf.py`) - Report and onboarding doc generation
   - Analytics computation (`test_utils/test_formatting.py`) - Data aggregation functions
   - File extraction (`test_utils/test_formatting.py`) - PDF text extraction

---

*Testing analysis: 2026-02-25*
