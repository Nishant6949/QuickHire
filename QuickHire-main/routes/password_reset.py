import logging

from flask import Blueprint, render_template, request, url_for, redirect, flash
from werkzeug.security import generate_password_hash
from user_model import db, User

logger = logging.getLogger(__name__)
from services.password_reset import (
    generate_reset_token,
    consume_reset_token,
    send_password_reset_email,
)

password_reset_bp = Blueprint("password_reset", __name__)


@password_reset_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()

        # Always show success message to avoid revealing which emails exist
        user = db.session.execute(
            db.select(User).where(User.work_email == email)
        ).scalar()

        if user:
            token = generate_reset_token(email)
            reset_link = url_for(
                "password_reset.reset_password", token=token, _external=True
            )
            if not send_password_reset_email(email, reset_link):
                logger.warning("Password reset email failed to send for %s", email)

        flash("If an account with that email exists, we've sent a password reset link.")
        return redirect(url_for("password_reset.forgot_password"))

    return render_template("landing page/forgot_password.html")


@password_reset_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm-password")

        if not password or not confirm_password:
            flash("Please fill out all fields.")
            return redirect(url_for("password_reset.reset_password", token=token))

        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("password_reset.reset_password", token=token))

        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return redirect(url_for("password_reset.reset_password", token=token))

        email = consume_reset_token(token)
        if not email:
            flash("This reset link is invalid or has expired.")
            return redirect(url_for("password_reset.forgot_password"))

        user = db.session.execute(
            db.select(User).where(User.work_email == email)
        ).scalar()

        if user:
            user.password = generate_password_hash(
                password, method="pbkdf2:sha256", salt_length=16
            )
            db.session.commit()
            flash("Your password has been reset. Please sign in.")
            return redirect(url_for("auth.login"))

        flash("Something went wrong. Please try again.")
        return redirect(url_for("password_reset.forgot_password"))

    return render_template("landing page/reset_password.html", token=token)
