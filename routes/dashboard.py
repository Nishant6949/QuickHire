from flask import Blueprint, render_template
from flask_login import login_required, current_user

from user_model import db, Job, Candidate
from utils.formatting import serialize_candidate, job_stats_for_user, build_jobs_list

dashboard_bp = Blueprint('dashboard_bp', __name__, url_prefix='/dashboard')


@dashboard_bp.route("/")
@login_required
def dashboard():
    draft_job = db.session.execute(
        db.select(Job)
        .where(Job.user_id == current_user.id)
        .where(Job.status.in_(("draft", "ready", "processing")))
        .order_by(Job.updated_at.desc())
    ).scalars().first()

    return render_template(
        "dashboard/dashboard.html",
        active_page="dashboard",
        draft_job=draft_job
    )


@dashboard_bp.route("/jobs")
@login_required
def jobs():
    all_jobs = build_jobs_list(current_user.id)
    departments = sorted(set(j["department"] for j in all_jobs if j["department"]))
    stats = job_stats_for_user(current_user.id)

    return render_template(
        "dashboard/jobs.html", active_page="jobs",
        departments=departments, jobs_data=all_jobs,
        total=stats["total"], open_count=stats["open"],
        draft_count=stats["draft"], completed_count=stats["completed"],
    )


@dashboard_bp.route("/candidates")
@login_required
def candidates():
    all_candidates = db.session.execute(
        db.select(Candidate)
        .join(Job)
        .where(Job.user_id == current_user.id)
        .where(Candidate.match_score.isnot(None))
        .order_by(Candidate.match_score.desc())
    ).scalars().all()

    candidates_data = []
    for c in all_candidates:
        data = serialize_candidate(c)
        data["job_id"] = c.job_id
        data["job_title"] = c.job.title if c.job else "Unknown"
        candidates_data.append(data)

    total_count = len(candidates_data)
    invited_count = sum(1 for c in candidates_data if c["status"] in ("invited", "interview_done", "shortlisted"))
    pending_count = sum(1 for c in candidates_data if c["status"] in ("pending", "scored"))
    hired_count = sum(1 for c in candidates_data if c["status"] == "final_hired")

    unique_jobs = {}
    for c in candidates_data:
        if c["job_id"] and c["job_title"]:
            unique_jobs[c["job_id"]] = c["job_title"]
    job_filter_options = sorted(unique_jobs.items(), key=lambda x: x[1])

    return render_template(
        "dashboard/candidates.html",
        active_page="candidates",
        candidates_data=candidates_data,
        total_count=total_count,
        invited_count=invited_count,
        pending_count=pending_count,
        hired_count=hired_count,
        job_filter_options=job_filter_options,
    )


@dashboard_bp.route("/analytics")
@login_required
def analytics():
    return render_template("dashboard/analytics.html", active_page="analytics")


@dashboard_bp.route("/settings")
@login_required
def settings():
    return render_template("dashboard/settings.html", active_page="settings")
