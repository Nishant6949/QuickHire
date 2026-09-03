"""Employer login, registration and logout routes."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from user_model import User, db, login_manager


auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id):
    """Reload the signed-in employer from the database for Flask-Login."""
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Check employer credentials, then start the email OTP step."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))

    if request.method == "POST":
        email = request.form.get("login-email", "").strip().lower()
        password = request.form.get("login-password", "")

        # Look up the employer by work email.
        user = db.session.execute(
            db.select(User).where(User.work_email == email)
        ).scalar_one_or_none()

        # Passwords are checked against the stored hash.
        if not user or not check_password_hash(user.password, password):
            flash("Invalid email or password.")
            return redirect(url_for("auth.login"))

        # Do not fully sign in yet. OTP verification is the second step.
        session["pending_2fa_type"] = "employer"
        session["pending_2fa_id"] = user.id
        session["pending_2fa_next"] = request.args.get("next")
        session.pop("pending_2fa_email_sent", None)
        return redirect(url_for("two_factor.choose"))

    return render_template("landing page/auth.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Create a new employer account and continue to email OTP verification."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_bp.dashboard"))

    if request.method == "POST":
        first_name = request.form.get("first-name", "").strip()
        last_name = request.form.get("last-name", "").strip()
        email = request.form.get("work-email", "").strip().lower()
        company_name = request.form.get("company-name", "").strip()
        company_size = request.form.get("company-size", "").strip()
        role = request.form.get("role", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm-password", "")
        accepted_terms = request.form.get("terms")

        required = [
            first_name,
            last_name,
            email,
            company_name,
            company_size,
            role,
            password,
            accepted_terms,
        ]
        if not all(required):
            flash("Please fill out all required fields and accept the terms.")
            return redirect(url_for("auth.register"))

        if "@" not in email or len(email) > 254:
            flash("Please enter a valid work email address.")
            return redirect(url_for("auth.register"))

        if password != confirm_password:
            flash("Passwords do not match. Please try again.")
            return redirect(url_for("auth.register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return redirect(url_for("auth.register"))

        existing = db.session.execute(
            db.select(User).where(User.work_email == email)
        ).scalar_one_or_none()
        if existing:
            flash("You already have an account. Please login instead.")
            return redirect(url_for("auth.login"))

        # Store a secure password hash instead of the readable password.
        new_user = User(
            first_name=first_name[:100],
            last_name=last_name[:100],
            work_email=email,
            company_name=company_name[:200],
            company_size=company_size[:100],
            role=role[:100],
            password=generate_password_hash(password, method="pbkdf2:sha256", salt_length=16),
        )

        try:
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("An account or workspace with those details already exists.")
            return redirect(url_for("auth.register"))

        # Registration also confirms the email through the same OTP flow.
        session["pending_2fa_type"] = "employer"
        session["pending_2fa_id"] = new_user.id
        session.pop("pending_2fa_email_sent", None)
        return redirect(url_for("two_factor.choose"))

    return render_template("landing page/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """End the employer session and return to the public home page."""
    logout_user()
    return redirect(url_for("landing.index"))
