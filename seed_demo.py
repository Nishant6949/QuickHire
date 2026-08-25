"""Create a complete demo workspace for presentation/testing.

Run: python seed_demo.py
Login: demo@quickhire.local / QuickHire123!
"""
from werkzeug.security import generate_password_hash

from main import app
from user_model import db, User, Job, Candidate
from services.ai import score_candidate_fallback

DEMO_EMAIL = 'demo@quickhire.local'
DEMO_PASSWORD = 'QuickHire123!'

JD = """Senior Python Developer
Department: Engineering
Location: Sydney / Hybrid
Full-time

We are seeking a Senior Python Developer with 5+ years of experience building web applications.
Required skills include Python, Flask, SQL, PostgreSQL, REST API, Git, Docker, AWS and Agile delivery.
Strong communication and collaboration skills are important.
"""

RESUMES = [
    ("Alex Morgan", "alex.morgan@example.com", """Alex Morgan
alex.morgan@example.com
Senior Software Engineer with 7 years of experience.
Bachelor of Computer Science, University of Sydney.
Skills: Python, Flask, PostgreSQL, SQL, REST API, Docker, AWS, Git, Agile, JavaScript.
Built cloud-native recruitment and analytics platforms and led small engineering teams.
"""),
    ("Priya Shah", "priya.shah@example.com", """Priya Shah
priya.shah@example.com
Software Developer with 4 years experience.
Master of Information Technology.
Skills: Python, Django, SQL, PostgreSQL, Git, Docker, Azure, REST API, Agile.
Experience developing APIs and internal business applications.
"""),
    ("Jordan Lee", "jordan.lee@example.com", """Jordan Lee
jordan.lee@example.com
Graduate IT professional with internship experience.
Bachelor of Information Technology.
Skills: Java, HTML, CSS, JavaScript, Git, SQL, communication.
Interested in backend software engineering and cloud platforms.
"""),
]

with app.app_context():
    db.create_all()
    user = db.session.execute(db.select(User).where(User.work_email == DEMO_EMAIL)).scalar_one_or_none()
    if not user:
        user = User(
            first_name='Demo', last_name='Recruiter', work_email=DEMO_EMAIL,
            company_name='QuickHire Demo', company_size='11-50', role='Recruiter',
            password=generate_password_hash(DEMO_PASSWORD), match_threshold=60,
        )
        db.session.add(user)
        db.session.flush()

    existing = db.session.execute(
        db.select(Job).where(Job.user_id == user.id, Job.title == 'Senior Python Developer')
    ).scalar_one_or_none()
    if existing:
        db.session.delete(existing)
        db.session.flush()

    job = Job(
        user_id=user.id, title='Senior Python Developer', department='Engineering',
        location='Sydney / Hybrid', jd_text=JD, required_skills='Python, Flask, SQL, PostgreSQL, REST API, Docker, AWS, Git',
        status='completed', ai_analyzed=True, seniority_level='Senior', employment_type='Full-time',
    )
    db.session.add(job)
    db.session.flush()

    for idx, (name, email, resume) in enumerate(RESUMES):
        c = Candidate(job_id=job.id, resume_text=resume, resume_filename=f'{name.replace(" ", "_")}.pdf')
        score_candidate_fallback(c, JD)
        c.candidate_name = name
        c.candidate_email = email
        if idx == 0:
            c.status = 'final_hired'
        elif idx == 1:
            c.status = 'shortlisted'
        db.session.add(c)

    db.session.commit()
    print('Demo data ready.')
    print(f'Login: {DEMO_EMAIL}')
    print(f'Password: {DEMO_PASSWORD}')
