from flask import Blueprint, render_template, request, url_for, redirect, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user
from user_model import db, login_manager, User

auth_bp = Blueprint('auth', __name__)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@auth_bp.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('login-email')
        password = request.form.get('login-password')

        result = db.session.execute(db.select(User).where(User.work_email == email))
        user = result.scalar()

        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('auth.login'))

        if not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('auth.login'))

        login_user(user)
        return redirect(url_for('dashboard_bp.dashboard'))

    return render_template("landing page/auth.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("work-email")
        raw_password = request.form.get('password')
        raw_confirm = request.form.get('confirm-password')

        existing_user = db.session.execute(
            db.select(User).where(User.work_email == email)
        ).scalar()

        if existing_user:
            flash("You already have an account. Please login instead.")
            return redirect(url_for("auth.login"))

        if raw_password != raw_confirm:
            flash("Passwords do not match. Please try again.")
            return redirect(url_for("auth.register"))

        first_name = request.form.get("first-name")
        last_name = request.form.get("last-name")
        company_name = request.form.get("company-name")
        company_size = request.form.get("company-size")
        role = request.form.get("role")
        terms = request.form.get("terms")

        if not all([first_name, last_name, email, raw_password, terms]):
            flash("Please fill out all required fields and accept the terms.")
            return redirect(url_for("auth.register"))

        hashed_password = generate_password_hash(
            raw_password,
            method='pbkdf2:sha256',
            salt_length=8
        )

        new_user = User(
            first_name=first_name,
            last_name=last_name,
            work_email=email,
            company_name=company_name,
            company_size=company_size,
            role=role,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for("dashboard_bp.dashboard"))

    return render_template("landing page/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("landing.index"))
