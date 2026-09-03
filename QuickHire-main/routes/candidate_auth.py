"""Applicant account pages.

This file is intentionally written in a simple style for teaching and demos.
It handles applicant login, registration, dashboard, profile and saved jobs.
"""

from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from user_model import Candidate, CandidateAccount, Job, Notification, SavedJob, db

candidate_auth_bp = Blueprint("candidate_auth", __name__, url_prefix="/candidate")


def current_candidate_account():
    """Return the applicant who is currently signed in, or None."""
    account_id = session.get("candidate_account_id")
    if not account_id:
        return None
    return db.session.get(CandidateAccount, account_id)


def candidate_login_required(view):
    """Protect applicant pages so only a valid signed-in applicant can open them."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        # A session ID alone is not enough. The account must still exist.
        account = current_candidate_account()
        if account is None:
            session.pop("candidate_account_id", None)
            flash("Please sign in as an applicant to continue.")
            return redirect(url_for("candidate_auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@candidate_auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Check an applicant's email/password, then start email OTP verification."""
    if current_candidate_account():
        return redirect(url_for("candidate_auth.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Find the applicant account using the entered email address.
        account = db.session.execute(
            db.select(CandidateAccount).where(CandidateAccount.email == email)
        ).scalar_one_or_none()

        # Do not reveal whether the email or password was wrong.
        if not account or not check_password_hash(account.password, password):
            flash("Invalid applicant email or password.")
            return redirect(url_for("candidate_auth.login"))

        # Save only temporary information until the OTP is verified.
        session.pop("candidate_account_id", None)
        session["pending_2fa_type"] = "candidate"
        session["pending_2fa_id"] = account.id
        session["pending_2fa_next"] = request.args.get("next")
        session.pop("pending_2fa_email_sent", None)
        return redirect(url_for("two_factor.choose"))

    return render_template("careers/candidate_login.html")


@candidate_auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Create a new applicant account and send it through email OTP verification."""
    if current_candidate_account():
        return redirect(url_for("candidate_auth.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        # Basic form validation keeps registration easy to understand.
        if not name or "@" not in email or len(password) < 8:
            flash("Enter your name, a valid email and a password of at least 8 characters.")
            return redirect(url_for("candidate_auth.register"))

        if password != confirm:
            flash("Passwords do not match.")
            return redirect(url_for("candidate_auth.register"))

        existing = db.session.execute(
            db.select(CandidateAccount).where(CandidateAccount.email == email)
        ).scalar_one_or_none()
        if existing:
            flash("An applicant account with this email already exists.")
            return redirect(url_for("candidate_auth.login"))

        # Store a password hash, never the plain password.
        account = CandidateAccount(
            full_name=name[:200],
            email=email,
            password=generate_password_hash(password, method="pbkdf2:sha256", salt_length=16),
        )

        try:
            db.session.add(account)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("That applicant account already exists.")
            return redirect(url_for("candidate_auth.login"))

        # New accounts also confirm their identity with an email OTP.
        session["pending_2fa_type"] = "candidate"
        session["pending_2fa_id"] = account.id
        session.pop("pending_2fa_email_sent", None)
        return redirect(url_for("two_factor.choose"))

    return render_template("careers/candidate_register.html")


@candidate_auth_bp.get("/dashboard")
@candidate_login_required
def dashboard():
    """Show the applicant's applications, notifications and saved jobs."""
    account = current_candidate_account()

    # Applications are linked by the applicant's registered email address.
    applications = db.session.execute(
        db.select(Candidate)
        .where(func.lower(Candidate.candidate_email) == account.email.lower())
        .order_by(Candidate.created_at.desc())
    ).scalars().all()

    notifications = db.session.execute(
        db.select(Notification)
        .where(Notification.candidate_account_id == account.id)
        .order_by(Notification.created_at.desc())
        .limit(12)
    ).scalars().all()

    saved_jobs = db.session.execute(
        db.select(Job)
        .join(SavedJob, SavedJob.job_id == Job.id)
        .where(SavedJob.candidate_account_id == account.id)
        .order_by(SavedJob.created_at.desc())
        .limit(6)
    ).scalars().all()

    unread_count = sum(1 for item in notifications if not item.is_read)
    active_count = sum(
        1 for item in applications
        if (item.status or "pending") not in ("final_hired", "final_rejected")
    )
    interview_count = sum(
        1 for item in applications
        if (item.status or "") in ("invited", "interview_done")
    )

    return render_template(
        "careers/candidate_dashboard.html",
        account=account,
        applications=applications,
        notifications=notifications,
        unread_count=unread_count,
        saved_jobs=saved_jobs,
        active_count=active_count,
        interview_count=interview_count,
    )


@candidate_auth_bp.post("/notifications/read-all")
@candidate_login_required
def notifications_read_all():
    """Mark every unread applicant notification as read."""
    account = current_candidate_account()
    items = db.session.execute(
        db.select(Notification).where(
            Notification.candidate_account_id == account.id,
            Notification.is_read.is_(False),
        )
    ).scalars().all()

    for item in items:
        item.is_read = True

    db.session.commit()
    return redirect(url_for("candidate_auth.dashboard"))


@candidate_auth_bp.get("/logout")
def logout():
    """Remove the applicant session and return to the jobs page."""
    session.pop("candidate_account_id", None)
    return redirect(url_for("careers.jobs"))


@candidate_auth_bp.route("/profile", methods=["GET", "POST"])
@candidate_login_required
def profile():
    """Display or update the applicant's basic profile information."""
    account = current_candidate_account()

    if request.method == "POST":
        account.full_name = request.form.get("name", "").strip()[:200] or account.full_name
        account.phone = request.form.get("phone", "").strip()[:50] or None
        account.location = request.form.get("location", "").strip()[:160] or None
        account.headline = request.form.get("headline", "").strip()[:200] or None
        account.skills = request.form.get("skills", "").strip() or None
        db.session.commit()

        flash("Profile updated successfully.")
        return redirect(url_for("candidate_auth.profile"))

    return render_template("careers/candidate_profile.html", account=account)


@candidate_auth_bp.post("/saved-jobs/<int:job_id>/toggle")
@candidate_login_required
def toggle_saved_job(job_id):
    """Save a job for later, or remove it when it is already saved."""
    account = current_candidate_account()
    job = db.session.get(Job, job_id)
    if not job:
        return redirect(url_for("careers.jobs"))

    existing = db.session.execute(
        db.select(SavedJob).where(
            SavedJob.candidate_account_id == account.id,
            SavedJob.job_id == job_id,
        )
    ).scalar_one_or_none()

    if existing:
        db.session.delete(existing)
        flash("Job removed from saved jobs.")
    else:
        db.session.add(SavedJob(candidate_account_id=account.id, job_id=job_id))
        flash("Job saved for later.")

    db.session.commit()
    return redirect(request.referrer or url_for("careers.jobs"))
