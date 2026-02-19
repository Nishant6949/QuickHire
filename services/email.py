import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app

logger = logging.getLogger(__name__)


def send_invite_email(to_email, candidate_name, job_title, interview_dt, duration_min, custom_message, company_name=None, scheduling_link=None):
    gmail_addr = current_app.config.get("GMAIL_ADDRESS")
    gmail_pass = current_app.config.get("GMAIL_APP_PASSWORD")
    if not gmail_addr or not gmail_pass:
        return False

    time_str = interview_dt.strftime("%B %d, %Y at %I:%M %p") if interview_dt else None

    scheduling_section = ""
    if scheduling_link:
        scheduling_section = (
            '<tr><td style="padding:12px 0;color:#A1A1AA;font-size:14px;line-height:1.6;">'
            "Please use the link below to pick an interview time that works best for you."
            "</td></tr>"
            '<tr><td style="padding:8px 0;">'
            '<a href="' + scheduling_link + '" style="display:inline-block;padding:10px 24px;'
            'background:#22C55E;color:#070809;border-radius:6px;text-decoration:none;font-weight:600;">'
            'Choose a Time</a></td></tr>'
        )

    custom_section = ""
    if custom_message:
        custom_section = (
            '<tr><td style="padding:12px 0;color:#A1A1AA;font-size:14px;line-height:1.6;">'
            + custom_message.replace("\n", "<br>") + '</td></tr>'
        )

    html = (
        '<table style="max-width:520px;margin:0 auto;font-family:Inter,sans-serif;background:#0F1114;'
        'border:1px solid rgba(34,197,94,0.15);border-radius:10px;padding:32px;color:#FAFAFA;">'
        '<tr><td style="font-size:20px;font-weight:700;color:#22C55E;padding-bottom:16px;">QuickHire</td></tr>'
        '<tr><td style="height:2px;background:rgba(34,197,94,0.15);"></td></tr>'
        '<tr><td style="padding:20px 0 8px;font-size:18px;font-weight:600;">Interview Invitation</td></tr>'
        '<tr><td style="color:#A1A1AA;font-size:14px;padding-bottom:16px;">Hi ' + (candidate_name or "there") + ',</td></tr>'
        '<tr><td style="color:#A1A1AA;font-size:14px;line-height:1.6;padding-bottom:16px;">'
        'You have been selected for an interview' + (' from <strong style="color:#FAFAFA;">' + (company_name or "") + '</strong>' if company_name else '') + ' for the position of <strong style="color:#FAFAFA;">' + (job_title or "a position") + '</strong>.</td></tr>'
    )

    if time_str and not scheduling_link:
        html += (
            '<tr><td style="padding:8px 0;color:#A1A1AA;font-size:14px;">'
            '<strong style="color:#FAFAFA;">Date & Time:</strong> ' + time_str + '</td></tr>'
            '<tr><td style="padding:8px 0 16px;color:#A1A1AA;font-size:14px;">'
            '<strong style="color:#FAFAFA;">Duration:</strong> ' + str(duration_min) + ' minutes</td></tr>'
        )

    html += scheduling_section + custom_section + (
        '<tr><td style="padding:20px 0 0;color:#71717A;font-size:12px;">Sent via QuickHire</td></tr>'
        '</table>'
    )

    msg = MIMEMultipart("alternative")
    msg["From"] = gmail_addr
    msg["To"] = to_email
    subject_prefix = f"Interview Invitation from {company_name}" if company_name else "Interview Invitation"
    msg["Subject"] = f"{subject_prefix} - {job_title or 'Position'}"
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_addr, gmail_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error("Failed to send invite email to %s: %s", to_email, e)
        return False


def send_decision_email(to_email, candidate_name, job_title, decision, company_name=None):
    gmail_addr = current_app.config.get("GMAIL_ADDRESS")
    gmail_pass = current_app.config.get("GMAIL_APP_PASSWORD")
    if not gmail_addr or not gmail_pass:
        return False

    if decision == "hire":
        subject = f"Congratulations! - {job_title or 'Position'}"
        heading = "Congratulations!"
        body_text = (
            "We are thrilled to inform you that you have been selected for the role of "
            '<strong style="color:#FAFAFA;">' + (job_title or "the position") + "</strong>"
            + (" at <strong style=\"color:#FAFAFA;\">" + company_name + "</strong>" if company_name else "")
            + ". Our team will be in touch shortly with more details about next steps and onboarding."
        )
    else:
        subject = f"Application Update - {job_title or 'Position'}"
        heading = "Application Update"
        body_text = (
            "Thank you for taking the time to interview for the position of "
            '<strong style="color:#FAFAFA;">' + (job_title or "the position") + "</strong>"
            + (" at <strong style=\"color:#FAFAFA;\">" + company_name + "</strong>" if company_name else "")
            + ". After careful consideration, the team has decided to move forward with another candidate. "
            "We truly appreciate your time and interest, and we wish you all the best in your career."
        )

    html = (
        '<table style="max-width:520px;margin:0 auto;font-family:Inter,sans-serif;background:#0F1114;'
        'border:1px solid rgba(34,197,94,0.15);border-radius:10px;padding:32px;color:#FAFAFA;">'
        '<tr><td style="font-size:20px;font-weight:700;color:#22C55E;padding-bottom:16px;">QuickHire</td></tr>'
        '<tr><td style="height:2px;background:rgba(34,197,94,0.15);"></td></tr>'
        '<tr><td style="padding:20px 0 8px;font-size:18px;font-weight:600;">' + heading + '</td></tr>'
        '<tr><td style="color:#A1A1AA;font-size:14px;padding-bottom:16px;">Hi ' + (candidate_name or "there") + ',</td></tr>'
        '<tr><td style="color:#A1A1AA;font-size:14px;line-height:1.6;padding-bottom:16px;">'
        + body_text + '</td></tr>'
        '<tr><td style="padding:20px 0 0;color:#71717A;font-size:12px;">Sent via QuickHire</td></tr>'
        '</table>'
    )

    msg = MIMEMultipart("alternative")
    msg["From"] = gmail_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_addr, gmail_pass)
            server.send_message(msg)
        logger.info("Decision email (%s) sent to %s", decision, to_email)
        return True
    except Exception as e:
        logger.error("Failed to send decision email to %s: %s", to_email, e)
        return False


def send_custom_email(to_email, candidate_name, subject, body_text, company_name=None):
    gmail_addr = current_app.config.get("GMAIL_ADDRESS")
    gmail_pass = current_app.config.get("GMAIL_APP_PASSWORD")
    if not gmail_addr or not gmail_pass:
        return False

    html = (
        '<table style="max-width:520px;margin:0 auto;font-family:Inter,sans-serif;background:#0F1114;'
        'border:1px solid rgba(34,197,94,0.15);border-radius:10px;padding:32px;color:#FAFAFA;">'
        '<tr><td style="font-size:20px;font-weight:700;color:#22C55E;padding-bottom:16px;">'
        + (company_name or "QuickHire") + '</td></tr>'
        '<tr><td style="height:2px;background:rgba(34,197,94,0.15);"></td></tr>'
        '<tr><td style="padding:20px 0 8px;font-size:18px;font-weight:600;">' + subject + '</td></tr>'
        '<tr><td style="color:#A1A1AA;font-size:14px;padding-bottom:16px;">Hi ' + (candidate_name or "there") + ',</td></tr>'
        '<tr><td style="color:#A1A1AA;font-size:14px;line-height:1.6;padding-bottom:16px;">'
        + body_text.replace("\n", "<br>") + '</td></tr>'
        '<tr><td style="padding:20px 0 0;color:#71717A;font-size:12px;">Sent via QuickHire</td></tr>'
        '</table>'
    )

    msg = MIMEMultipart("alternative")
    msg["From"] = gmail_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_addr, gmail_pass)
            server.send_message(msg)
        logger.info("Custom email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("Failed to send custom email to %s: %s", to_email, e)
        return False
