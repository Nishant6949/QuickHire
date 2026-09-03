"""Simple email OTP logic used after a correct password login."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from user_model import LoginOTP, db

OTP_MINUTES = 5
MAX_ATTEMPTS = 5


def hash_code(code):
    """Convert an OTP into a hash so the readable code is not stored in the database."""
    return hashlib.sha256(code.encode()).hexdigest()


def create_email_otp(account_type, account_id):
    """Create one new six-digit OTP for an employer or applicant account."""
    # Remove an older code so only the newest OTP works.
    db.session.execute(
        db.delete(LoginOTP).where(
            LoginOTP.account_type == account_type,
            LoginOTP.account_id == account_id,
        )
    )

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_MINUTES)

    otp = LoginOTP(
        account_type=account_type,
        account_id=account_id,
        code_hash=hash_code(code),
        expires_at=expires_at,
    )
    db.session.add(otp)
    db.session.commit()
    return code


def verify_email_otp(account_type, account_id, code):
    """Return True only when the OTP is correct, unexpired and within the attempt limit."""
    otp = db.session.execute(
        db.select(LoginOTP).where(
            LoginOTP.account_type == account_type,
            LoginOTP.account_id == account_id,
        )
    ).scalar_one_or_none()

    if otp is None:
        return False

    # SQLite may return a datetime without timezone information.
    expires_at = otp.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    expired = datetime.now(timezone.utc) > expires_at
    too_many_attempts = otp.attempts >= MAX_ATTEMPTS
    if expired or too_many_attempts:
        db.session.delete(otp)
        db.session.commit()
        return False

    otp.attempts += 1
    entered_hash = hash_code((code or "").strip())
    is_correct = secrets.compare_digest(otp.code_hash, entered_hash)

    # A successful OTP is single-use, so delete it immediately.
    if is_correct:
        db.session.delete(otp)

    db.session.commit()
    return is_correct
