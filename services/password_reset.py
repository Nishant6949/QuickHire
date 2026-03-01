import logging
import smtplib
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app

from user_model import db, ResetToken

logger = logging.getLogger(__name__)

TOKEN_EXPIRY_MINUTES = 15


def _hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def generate_reset_token(email):
    """Generate a password reset token for the given email. Returns the raw token."""
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)

    # Remove any existing tokens for this email
    db.session.execute(
        db.delete(ResetToken).where(ResetToken.email == email)
    )

    reset_token = ResetToken(
        token_hash=token_hash,
        email=email,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRY_MINUTES),
    )
    db.session.add(reset_token)
    db.session.commit()
    return token


def consume_reset_token(token):
    """Validate and remove a reset token. Returns the email if valid, None otherwise."""
    token_hash = _hash_token(token)
    reset_token = db.session.execute(
        db.select(ResetToken).where(ResetToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if not reset_token:
        return None

    email = reset_token.email
    expired = datetime.now(timezone.utc) > reset_token.expires_at

    db.session.delete(reset_token)
    db.session.commit()

    if expired:
        return None
    return email


def send_password_reset_email(to_email, reset_link):
    """Send a password reset email using the same Gmail SMTP credentials."""
    gmail_addr = current_app.config.get("GMAIL_ADDRESS")
    gmail_pass = current_app.config.get("GMAIL_APP_PASSWORD")
    if not gmail_addr or not gmail_pass:
        logger.error("Gmail credentials not configured")
        return False

    html = (
        '<table style="max-width:520px;margin:0 auto;font-family:Inter,sans-serif;background:#0F1114;'
        'border:1px solid rgba(34,197,94,0.15);border-radius:10px;padding:32px;color:#FAFAFA;">'
        '<tr><td style="font-size:20px;font-weight:700;color:#22C55E;padding-bottom:16px;">QuickHire</td></tr>'
        '<tr><td style="height:2px;background:rgba(34,197,94,0.15);"></td></tr>'
        '<tr><td style="padding:20px 0 8px;font-size:18px;font-weight:600;">Password Reset</td></tr>'
        '<tr><td style="color:#A1A1AA;font-size:14px;padding-bottom:16px;">Hi there,</td></tr>'
        '<tr><td style="color:#A1A1AA;font-size:14px;line-height:1.6;padding-bottom:16px;">'
        'We received a request to reset your password. Click the button below to choose a new password. '
        'This link will expire in ' + str(TOKEN_EXPIRY_MINUTES) + ' minutes.</td></tr>'
        '<tr><td style="padding:8px 0 16px;">'
        '<a href="' + reset_link + '" style="display:inline-block;padding:12px 28px;'
        'background:#22C55E;color:#070809;border-radius:6px;text-decoration:none;font-weight:600;font-size:14px;">'
        'Reset Password</a></td></tr>'
        '<tr><td style="color:#71717A;font-size:12px;line-height:1.5;padding-bottom:16px;">'
        'If you didn\'t request this, you can safely ignore this email. Your password will remain unchanged.</td></tr>'
        '<tr><td style="padding:8px 0 0;color:#71717A;font-size:12px;">Sent via QuickHire</td></tr>'
        '</table>'
    )

    msg = MIMEMultipart("alternative")
    msg["From"] = f"QuickHire <{gmail_addr}>"
    msg["To"] = to_email
    msg["Subject"] = "QuickHire - Password Reset"
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_addr, gmail_pass)
            server.send_message(msg)
        logger.info("Password reset email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send password reset email to %s: %s", to_email, e)
        return False
