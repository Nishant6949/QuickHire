"""Recruitment queries and dashboard calculations.

Keeping these helpers outside the Flask routes makes the request handlers short
and easier to explain. The functions only read data and return plain Python
objects; they do not render pages or modify records.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import selectinload

from user_model import Candidate, Job, db


ACTIVE_JOB_STATUSES = {"open", "ready", "processing", "completed"}
SHORTLIST_STATUSES = {"shortlisted", "invited", "interview_done"}
INTERVIEW_STATUSES = {"invited", "interview_done"}


def utc_now_naive():
    """Return the current UTC time in the format used by existing DB rows."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def employer_jobs(user_id):
    """Return all jobs owned by one employer, newest first."""
    statement = (
        db.select(Job)
        .where(Job.user_id == user_id)
        .order_by(Job.created_at.desc())
    )
    return db.session.execute(statement).scalars().all()


def employer_applicants(user_id):
    """Return an employer's applicants ranked by strongest match first."""
    statement = (
        db.select(Candidate)
        .options(selectinload(Candidate.job))
        .join(Job)
        .where(Job.user_id == user_id)
        .order_by(
            Candidate.match_score.desc().nullslast(),
            Candidate.created_at.desc(),
        )
    )
    return db.session.execute(statement).scalars().all()


def active_jobs(jobs):
    """Return jobs that are open to applicants and have not expired."""
    now = utc_now_naive()
    return [
        job
        for job in jobs
        if job.status in ACTIVE_JOB_STATUSES
        and (job.application_deadline is None or job.application_deadline >= now)
    ]


def dashboard_summary(jobs, applicants):
    """Calculate the small set of metrics displayed on the employer dashboard."""
    open_jobs = active_jobs(jobs)
    scored = [item.match_score for item in applicants if item.match_score is not None]

    return {
        "active_jobs": len(open_jobs),
        "total_applicants": len(applicants),
        "shortlisted": sum(item.status in SHORTLIST_STATUSES for item in applicants),
        "interviews": sum(item.status in INTERVIEW_STATUSES for item in applicants),
        "hired": sum(item.status == "final_hired" for item in applicants),
        "avg_score": round(sum(scored) / len(scored)) if scored else 0,
        "upcoming_deadlines": sorted(
            [job for job in open_jobs if job.application_deadline],
            key=lambda job: job.application_deadline,
        )[:5],
        "top_applicants": applicants[:6],
    }


def interview_applicants(user_id):
    """Return applicants currently in the interview part of the pipeline."""
    statement = (
        db.select(Candidate)
        .options(selectinload(Candidate.job))
        .join(Job)
        .where(Job.user_id == user_id)
        .where(Candidate.status.in_(INTERVIEW_STATUSES))
        .order_by(
            Candidate.interview_at.asc().nullslast(),
            Candidate.match_score.desc().nullslast(),
        )
    )
    return db.session.execute(statement).scalars().all()
