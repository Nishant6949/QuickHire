"""Public Careers Portal routes.

This file keeps the public job-search and application flow in one place.
The functions are intentionally small and commented so the flow is easy to
follow during a project demonstration.
"""

import json
import logging
from datetime import datetime, timezone

import anthropic
from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from sqlalchemy import func
from werkzeug.utils import secure_filename

from routes.candidate_auth import candidate_login_required, current_candidate_account
from services.ai import score_candidate
from services.notifications import notify_candidate, notify_recruiter
from services.storage import upload_file
from user_model import Candidate, Job, db
from utils.formatting import extract_pdf_text, format_salary

logger = logging.getLogger(__name__)

careers_bp = Blueprint("careers", __name__, url_prefix="/careers")

# Only jobs with one of these statuses are visible to applicants.
PUBLIC_JOB_STATUSES = {"open", "ready", "processing", "completed"}


def get_public_job(job_id):
    """Return a public job or show a 404 page when it is unavailable."""
    job = db.session.get(Job, job_id)

    if not job or job.status not in PUBLIC_JOB_STATUSES:
        abort(404)

    return job


def make_skills_list(value):
    """Convert stored skills into a clean Python list for the template."""
    if not value:
        return []

    value = value.strip()
    if not value:
        return []

    # Some jobs store skills as JSON, for example ["Python", "SQL"].
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except (json.JSONDecodeError, TypeError):
        pass

    # Older records may store skills as a comma-separated string.
    return [item.strip() for item in value.split(",") if item.strip()]


def make_job_card(job):
    """Prepare the job information used by the Careers Portal templates."""
    return {
        "id": job.id,
        "title": job.title or "Untitled position",
        "company": job.user.company_name if job.user else "QuickHire Employer",
        "department": job.department or "General",
        "location": job.location or "Location not specified",
        "employment_type": job.employment_type or "Not specified",
        "seniority_level": job.seniority_level or "",
        "salary": job.salary_range_text or format_salary(job.salary_min, job.salary_max),
        "skills": make_skills_list(job.required_skills),
        "created_at": job.created_at,
        "application_deadline": job.application_deadline,
    }


def show_application_error(job, account, message, status=400):
    """Show the job page again with a clear application error message."""
    return (
        render_template(
            "careers/job_detail.html",
            job=job,
            card=make_job_card(job),
            candidate_account=account,
            application_error=message,
        ),
        status,
    )


def current_utc_time():
    """Return the current UTC time without timezone information for database comparison."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@careers_bp.get("")
@careers_bp.get("/")
def jobs():
    """Display public jobs and apply optional keyword/location filters."""
    keyword = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()

    # Start with jobs that are public and have not passed their deadline.
    statement = (
        db.select(Job)
        .where(Job.status.in_(PUBLIC_JOB_STATUSES))
        .where(Job.title.isnot(None))
        .where(
            (Job.application_deadline.is_(None))
            | (Job.application_deadline >= current_utc_time())
        )
        .order_by(Job.created_at.desc())
    )

    job_rows = db.session.execute(statement).scalars().all()

    # Filter by title, department, skill or company when a keyword is entered.
    if keyword:
        search_text = keyword.lower()
        job_rows = [
            job
            for job in job_rows
            if search_text in (job.title or "").lower()
            or search_text in (job.department or "").lower()
            or search_text in (job.required_skills or "").lower()
            or search_text in (job.user.company_name if job.user else "").lower()
        ]

    # Filter by location when the applicant enters one.
    if location:
        location_text = location.lower()
        job_rows = [
            job for job in job_rows
            if location_text in (job.location or "").lower()
        ]

    return render_template(
        "careers/jobs.html",
        jobs=[make_job_card(job) for job in job_rows],
        q=keyword,
        location=location,
    )


@careers_bp.get("/job/<int:job_id>")
def job_detail(job_id):
    """Display the full details for one public job."""
    job = get_public_job(job_id)

    return render_template(
        "careers/job_detail.html",
        job=job,
        card=make_job_card(job),
        candidate_account=current_candidate_account(),
    )


@careers_bp.post("/job/<int:job_id>/apply")
@candidate_login_required
def apply(job_id):
    """Accept an applicant's PDF resume and create an application record."""
    job = get_public_job(job_id)
    account = current_candidate_account()

    # Do not accept applications after the closing date.
    if job.application_deadline and job.application_deadline < current_utc_time():
        return show_application_error(
            job,
            account,
            "Applications for this vacancy have closed.",
            410,
        )

    applicant_name = account.full_name
    applicant_email = account.email.lower()
    resume = request.files.get("resume")

    # Validate the uploaded resume before processing it.
    if not resume or not (resume.filename or "").strip():
        return show_application_error(job, account, "Please attach a PDF resume.")

    if "@" not in applicant_email or len(applicant_email) > 254:
        return show_application_error(job, account, "Please enter a valid email address.")

    if not resume.filename.lower().endswith(".pdf"):
        return show_application_error(job, account, "Resume must be a PDF file.")

    # Prevent the same applicant from applying to the same job twice.
    existing_application = db.session.execute(
        db.select(Candidate)
        .where(Candidate.job_id == job.id)
        .where(func.lower(Candidate.candidate_email) == applicant_email)
    ).scalar_one_or_none()

    if existing_application:
        return show_application_error(
            job,
            account,
            "An application with this email has already been submitted for this job.",
            409,
        )

    # Read the uploaded file into memory once.
    filename = secure_filename(resume.filename)
    file_bytes = resume.read()

    if not file_bytes:
        return show_application_error(job, account, "The uploaded PDF is empty.")

    # Extract text from the PDF so QuickHire can screen the resume.
    try:
        resume_text = extract_pdf_text(file_bytes)
    except Exception as error:
        logger.warning("Resume text extraction failed: %s", error)
        resume_text = ""

    if not resume_text:
        return show_application_error(
            job,
            account,
            "We could not read text from that PDF. Please upload a text-based resume PDF.",
        )

    # File storage is optional. The application can still work using extracted text.
    try:
        upload_file("documents", f"resumes/{job.id}/{filename}", file_bytes)
    except Exception as error:
        logger.info("Resume storage was skipped: %s", error)

    # Create the application record.
    candidate = Candidate(
        job_id=job.id,
        resume_text=resume_text,
        resume_filename=filename,
        candidate_name=applicant_name[:200],
        candidate_email=applicant_email,
        status="pending",
    )
    db.session.add(candidate)

    # Run AI screening only when the employer enabled automatic screening.
    if job.user and job.user.auto_screen:
        try:
            api_key = current_app.config.get("ANTHROPIC_API_KEY")
            ai_client = anthropic.Anthropic(api_key=api_key) if api_key else None
            score_candidate(candidate, ai_client, job.jd_text)
        except Exception as error:
            logger.warning("Automatic screening failed: %s", error)
            candidate.status = "pending"

    # Notify both sides after a successful application.
    notify_recruiter(
        job.user_id,
        "New application received",
        f"{applicant_name} applied for {job.title or 'your vacancy'}.",
        category="application",
        link="/dashboard/candidates",
    )

    notify_candidate(
        applicant_email,
        "Application submitted",
        f"Your application for {job.title or 'this position'} was received successfully.",
        category="application",
    )

    db.session.commit()

    return redirect(url_for("careers.application_success", job_id=job.id))


@careers_bp.get("/job/<int:job_id>/application-success")
def application_success(job_id):
    """Show a confirmation page after an application is submitted."""
    job = get_public_job(job_id)

    return render_template(
        "careers/application_success.html",
        job=job,
        card=make_job_card(job),
    )
