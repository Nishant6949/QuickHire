import os

# Configure before importing the app.
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['EMAIL_MODE'] = 'console'
os.environ.pop('ANTHROPIC_API_KEY', None)

from main import app
from user_model import db, User, Job, Candidate
from werkzeug.security import generate_password_hash
from services.ai import analyze_job_description_fallback, score_candidate_fallback


def setup_function():
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.drop_all()
        db.create_all()


def test_health():
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
        assert response.get_json()['database'] == 'ok'


def test_local_jd_analysis():
    result = analyze_job_description_fallback(
        'Senior Python Developer\nLocation: Sydney\nFull-time role using Python, Flask, SQL and AWS.'
    )
    assert result['title']
    assert result['location'] == 'Sydney'
    assert 'Python' in result['key_skills']


def test_local_candidate_scoring():
    with app.app_context():
        user = User(first_name='Test', last_name='User', work_email='t@example.com', company_name='Test Co', company_size='1-10', role='Recruiter', password='x')
        db.session.add(user); db.session.flush()
        job = Job(user_id=user.id, title='Python Developer', jd_text='Python Flask SQL AWS Docker', status='ready')
        db.session.add(job); db.session.flush()
        c = Candidate(job_id=job.id, resume_filename='resume.pdf', resume_text='Jane Doe\njane@example.com\n5 years Python Flask SQL AWS Docker. Bachelor degree.')
        score_candidate_fallback(c, job.jd_text)
        assert c.match_score >= 60
        assert c.candidate_email == 'jane@example.com'
        assert c.status == 'scored'


def test_authenticated_job_creation():
    with app.app_context():
        user = User(
            first_name='Test', last_name='Recruiter', work_email='test@example.com',
            company_name='Test Company', company_size='1-10', role='Recruiter',
            password=generate_password_hash('Password123!')
        )
        db.session.add(user); db.session.commit()

    with app.test_client() as client:
        response = client.post('/login', data={'login-email': 'test@example.com', 'login-password': 'Password123!'}, follow_redirects=False)
        assert response.status_code == 302
        response = client.post('/dashboard/create-job', data={
            'title': 'Backend Developer', 'department': 'Engineering',
            'location': 'Sydney', 'description': 'Python Flask SQL', 'skills': 'Python, Flask, SQL'
        })
        assert response.status_code == 200
        assert response.get_json()['success'] is True
