"""QuickHire email helper.

This file keeps all SendGrid email code in one place.
It uses Python's built-in urllib library, so no SendGrid package is required.
"""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

# Load the .env file from the QuickHire-main folder.
PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


def email_delivery_ready():
    """Check that the SendGrid API key and sender email are available."""
    api_key = os.getenv("SENDGRID_API_KEY", "").strip()
    sender_email = os.getenv("SENDGRID_FROM_EMAIL", "").strip()
    return bool(api_key and sender_email)


def send_email(to_email, subject, html, reply_to=None):
    """Send one email through SendGrid.

    Returns True when SendGrid accepts the message.
    Returns False when configuration or sending fails.
    """
    api_key = os.getenv("SENDGRID_API_KEY", "").strip()
    sender_email = os.getenv("SENDGRID_FROM_EMAIL", "").strip()
    sender_name = os.getenv("SENDGRID_FROM_NAME", "QuickHire").strip() or "QuickHire"

    # Check the two settings that are required to send an email.
    if not api_key:
        print("EMAIL ERROR: SENDGRID_API_KEY is missing from .env")
        return False

    if not sender_email:
        print("EMAIL ERROR: SENDGRID_FROM_EMAIL is missing from .env")
        return False

    # Build the email in the JSON format SendGrid expects.
    email_data = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": subject,
            }
        ],
        "from": {
            "email": sender_email,
            "name": sender_name,
        },
        "content": [
            {
                "type": "text/html",
                "value": html,
            }
        ],
    }

    # Reply-to is optional.
    if reply_to:
        email_data["reply_to"] = {"email": reply_to}

    # Create the HTTPS request to SendGrid.
    request = Request(
        SENDGRID_URL,
        data=json.dumps(email_data).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        # Send the request. SendGrid normally returns HTTP 202.
        with urlopen(request, timeout=15) as response:
            status = response.getcode()

        print(f"SendGrid status: {status}")

        if 200 <= status < 300:
            print(f"Email accepted for delivery to {to_email}")
            return True

        print(f"EMAIL ERROR: SendGrid returned status {status}")
        return False

    except HTTPError as error:
        # Print SendGrid's real error message without exposing the API key.
        details = error.read().decode("utf-8", errors="replace")
        print(f"EMAIL ERROR: SendGrid HTTP {error.code}")
        print(details)
        return False

    except URLError as error:
        print(f"EMAIL ERROR: Could not connect to SendGrid: {error.reason}")
        return False

    except Exception as error:
        print(f"EMAIL ERROR: {error}")
        return False


def otp_email_html(name, code):
    """Create the HTML body for the six-digit login verification email."""
    display_name = name or "there"

    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 560px; margin: auto;">
        <h2>QuickHire</h2>
        <p>Hi {display_name},</p>
        <p>Your QuickHire verification code is:</p>
        <h1 style="letter-spacing: 6px;">{code}</h1>
        <p>This code expires in 5 minutes.</p>
        <p>If you did not try to sign in, you can ignore this email.</p>
    </div>
    """


def send_otp_email(to_email, name, code):
    """Prepare and send the login OTP email."""
    html = otp_email_html(name, code)

    return send_email(
        to_email=to_email,
        subject="Your QuickHire verification code",
        html=html,
    )
