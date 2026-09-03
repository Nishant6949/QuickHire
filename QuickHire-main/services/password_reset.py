import logging
import os
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
    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    expired = datetime.now(timezone.utc) > expires_at

    db.session.delete(reset_token)
    db.session.commit()

    if expired:
        return None
    return email


def send_password_reset_email(to_email, reset_link):
    """Send a real password reset email through the configured transactional provider."""
    from services.messaging import send_email
    html = f"""<div style='font-family:Arial,sans-serif;max-width:560px;margin:auto;padding:32px;border:1px solid #e5e7eb;border-radius:14px'>
    <div style='font-size:24px;font-weight:800;color:#16a34a'>QuickHire</div><h2>Password reset</h2>
    <p>We received a request to reset your QuickHire password. This secure link expires in {TOKEN_EXPIRY_MINUTES} minutes.</p>
    <p><a href='{reset_link}' style='display:inline-block;padding:12px 22px;background:#16a34a;color:white;text-decoration:none;border-radius:8px;font-weight:700'>Reset password</a></p>
    <p style='color:#71717a;font-size:13px'>If you did not request this, ignore this email.</p></div>"""
    return send_email(to_email, "QuickHire - Password Reset", html)
