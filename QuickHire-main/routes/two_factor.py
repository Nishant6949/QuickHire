"""Email OTP pages used by both employer and applicant login."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_user

from services.messaging import send_otp_email
from services.two_factor import create_email_otp, verify_email_otp
from user_model import CandidateAccount, User, db


two_factor_bp = Blueprint("two_factor", __name__, url_prefix="/verify-login")


def pending_account():
    """Get the account that has passed the password step but not the OTP step."""
    account_type = session.get("pending_2fa_type")
    account_id = session.get("pending_2fa_id")

    if account_type == "employer":
        return account_type, db.session.get(User, account_id)
    if account_type == "candidate":
        return account_type, db.session.get(CandidateAccount, account_id)
    return None, None


def account_email(account, account_type):
    """Return the registered email for either account type."""
    return account.work_email if account_type == "employer" else account.email


def account_name(account, account_type):
    """Return a friendly name for the OTP email."""
    return account.first_name if account_type == "employer" else account.full_name


def mask_email(email):
    """Hide part of an email address before displaying it on the OTP screen."""
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    visible = local[:2] if len(local) > 2 else local[:1]
    hidden = "*" * max(3, len(local) - len(visible))
    return f"{visible}{hidden}@{domain}"


def clear_pending_login():
    """Remove temporary OTP session values after login is complete."""
    keys = (
        "pending_2fa_type",
        "pending_2fa_id",
        "pending_2fa_channel",
        "pending_2fa_email_sent",
    )
    for key in keys:
        session.pop(key, None)


@two_factor_bp.route("/", methods=["GET", "POST"])
def choose():
    """Generate an OTP and send it to the account's registered email address."""
    account_type, account = pending_account()
    if account is None:
        clear_pending_login()
        return redirect(url_for("landing.index"))

    # Send once on first visit. POST is used by the retry button.
    should_send = request.method == "POST" or not session.get("pending_2fa_email_sent")
    if should_send:
        code = create_email_otp(account_type, account.id)
        email = account_email(account, account_type)
        name = account_name(account, account_type)

        if not send_otp_email(email, name, code):
            return render_template(
                "security/email_delivery_error.html",
                destination=mask_email(email),
            ), 503

        session["pending_2fa_email_sent"] = True

    return redirect(url_for("two_factor.verify"))


@two_factor_bp.route("/code", methods=["GET", "POST"])
def verify():
    """Check the six-digit OTP and finish the correct type of login."""
    account_type, account = pending_account()
    if account is None:
        clear_pending_login()
        return redirect(url_for("landing.index"))

    if request.method == "POST":
        entered_code = request.form.get("code", "").strip()

        if not verify_email_otp(account_type, account.id, entered_code):
            flash("That verification code is incorrect or has expired. Please try again.")
            return redirect(url_for("two_factor.verify"))

        next_url = session.pop("pending_2fa_next", None)
        clear_pending_login()

        # Employer accounts use Flask-Login. Applicant accounts use a simple session ID.
        if account_type == "employer":
            login_user(account, remember=True)
            default_page = url_for("dashboard_bp.dashboard")
        else:
            session["candidate_account_id"] = account.id
            default_page = url_for("candidate_auth.dashboard")

        # Only accept local relative redirects for safety.
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(default_page)

    email = account_email(account, account_type)
    return render_template(
        "security/verify_otp.html",
        channel="email",
        destination=mask_email(email),
    )


@two_factor_bp.post("/resend")
def resend():
    """Replace the previous OTP with a new code and email it again."""
    account_type, account = pending_account()
    if account is None:
        clear_pending_login()
        return redirect(url_for("landing.index"))

    code = create_email_otp(account_type, account.id)
    sent = send_otp_email(
        account_email(account, account_type),
        account_name(account, account_type),
        code,
    )

    if sent:
        flash("A new verification code has been sent to your registered email.")
        return redirect(url_for("two_factor.verify"))

    flash("We could not send the email. Please check the SendGrid configuration and try again.")
    return redirect(url_for("two_factor.choose"))
