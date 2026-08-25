from sqlalchemy.exc import IntegrityError
from flask import Blueprint, render_template, request, url_for, redirect, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user

from user_model import db, login_manager, User

auth_bp = Blueprint('auth', __name__)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_bp.dashboard'))

    if request.method == 'POST':
        email = request.form.get('login-email', '').strip().lower()
        password = request.form.get('login-password', '')

        user = db.session.execute(db.select(User).where(User.work_email == email)).scalar_one_or_none()
        if not user or not check_password_hash(user.password, password):
            flash('Invalid email or password.')
            return redirect(url_for('auth.login'))

        login_user(user, remember=True)
        next_url = request.args.get('next')
        if next_url and next_url.startswith('/') and not next_url.startswith('//'):
            return redirect(next_url)
        return redirect(url_for('dashboard_bp.dashboard'))

    return render_template('landing page/auth.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_bp.dashboard'))

    if request.method == 'POST':
        email = request.form.get('work-email', '').strip().lower()
        raw_password = request.form.get('password', '')
        raw_confirm = request.form.get('confirm-password', '')
        first_name = request.form.get('first-name', '').strip()
        last_name = request.form.get('last-name', '').strip()
        company_name = request.form.get('company-name', '').strip()
        company_size = request.form.get('company-size', '').strip()
        role = request.form.get('role', '').strip()
        terms = request.form.get('terms')

        if not all([first_name, last_name, email, company_name, company_size, role, raw_password, terms]):
            flash('Please fill out all required fields and accept the terms.')
            return redirect(url_for('auth.register'))

        if '@' not in email or len(email) > 254:
            flash('Please enter a valid work email address.')
            return redirect(url_for('auth.register'))

        if raw_password != raw_confirm:
            flash('Passwords do not match. Please try again.')
            return redirect(url_for('auth.register'))

        if len(raw_password) < 8:
            flash('Password must be at least 8 characters.')
            return redirect(url_for('auth.register'))

        if db.session.execute(db.select(User).where(User.work_email == email)).scalar_one_or_none():
            flash('You already have an account. Please login instead.')
            return redirect(url_for('auth.login'))

        new_user = User(
            first_name=first_name[:100],
            last_name=last_name[:100],
            work_email=email,
            company_name=company_name[:200],
            company_size=company_size[:100],
            role=role[:100],
            password=generate_password_hash(raw_password, method='pbkdf2:sha256', salt_length=16),
        )

        try:
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('An account or workspace with those details already exists.')
            return redirect(url_for('auth.register'))

        login_user(new_user, remember=True)
        return redirect(url_for('dashboard_bp.dashboard'))

    return render_template('landing page/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing.index'))
