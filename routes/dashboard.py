from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user, logout_user
from sqlalchemy.orm import selectinload

from user_model import db, User, Job, Candidate, TeamMember
from services.storage import delete_file
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
        .options(selectinload(Candidate.job))
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
    team_members = db.session.execute(
        db.select(TeamMember)
        .where(TeamMember.owner_id == current_user.id)
        .order_by(TeamMember.created_at.asc())
    ).scalars().all()
    return render_template(
        "dashboard/settings.html", active_page="settings", team_members=team_members
    )


@dashboard_bp.route("/settings/save", methods=["POST"])
@login_required
def settings_save():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    if "company_name" in data:
        company_name = str(data["company_name"]).strip()
        if not company_name:
            return jsonify({"success": False, "error": "Company name is required"}), 400
        current_user.company_name = company_name[:200]
    if "company_size" in data:
        current_user.company_size = str(data["company_size"])[:100]
    if "auto_screen" in data:
        current_user.auto_screen = bool(data["auto_screen"])
    if "match_threshold" in data:
        try:
            threshold = int(data["match_threshold"])
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Match threshold must be a number"}), 400
        current_user.match_threshold = max(0, min(100, threshold))
    if "bias_detection" in data:
        current_user.bias_detection = bool(data["bias_detection"])
    if "notif_matches" in data:
        current_user.notif_matches = bool(data["notif_matches"])
    if "notif_weekly" in data:
        current_user.notif_weekly = bool(data["notif_weekly"])
    if "notif_expire" in data:
        current_user.notif_expire = bool(data["notif_expire"])
    if "notif_updates" in data:
        current_user.notif_updates = bool(data["notif_updates"])

    db.session.commit()
    return jsonify({"success": True})



@dashboard_bp.route("/settings/team", methods=["POST"])
@login_required
def settings_add_team_member():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    role = str(data.get("role", "Interviewer")).strip()
    if not name or not email or "@" not in email:
        return jsonify({"success": False, "error": "Enter a valid name and email"}), 400
    allowed_roles = {"Recruiter", "Hiring Manager", "Interviewer", "Viewer"}
    if role not in allowed_roles:
        return jsonify({"success": False, "error": "Invalid team role"}), 400
    existing = db.session.execute(
        db.select(TeamMember).where(TeamMember.owner_id == current_user.id, TeamMember.email == email)
    ).scalar_one_or_none()
    if existing:
        return jsonify({"success": False, "error": "That person is already in your team"}), 409
    member = TeamMember(owner_id=current_user.id, name=name[:200], email=email[:254], role=role, status="invited")
    db.session.add(member)
    db.session.commit()
    return jsonify({"success": True, "member": {"id": member.id, "name": member.name, "email": member.email, "role": member.role, "status": member.status}})


@dashboard_bp.route("/settings/team/<int:member_id>", methods=["DELETE"])
@login_required
def settings_remove_team_member(member_id):
    member = db.session.get(TeamMember, member_id)
    if not member or member.owner_id != current_user.id:
        return jsonify({"success": False, "error": "Team member not found"}), 404
    db.session.delete(member)
    db.session.commit()
    return jsonify({"success": True})

def _delete_all_user_data(user):
    """Delete all jobs, candidates, and storage files for a user."""
    jobs = db.session.execute(
        db.select(Job).where(Job.user_id == user.id)
    ).scalars().all()

    for job in jobs:
        for candidate in job.candidates:
            try:
                delete_file("documents", f"resumes/{job.id}/{candidate.resume_filename}")
            except Exception:
                pass
        db.session.delete(job)

    db.session.commit()


@dashboard_bp.route("/settings/delete-data", methods=["POST"])
@login_required
def settings_delete_data():
    _delete_all_user_data(current_user)
    return jsonify({"success": True})


@dashboard_bp.route("/settings/close-account", methods=["POST"])
@login_required
def settings_close_account():
    _delete_all_user_data(current_user)
    user = db.session.get(User, current_user.id)
    db.session.delete(user)
    db.session.commit()
    logout_user()
    return jsonify({"success": True, "redirect": "/"})
