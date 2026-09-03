from services.messaging import send_email


def _shell(title, greeting, body):
    return f"""<!doctype html><html><body style=\"margin:0;background:#f4f7f5;font-family:Arial,sans-serif\"><table width=\"100%\"><tr><td align=\"center\" style=\"padding:32px 16px\"><table width=\"560\" style=\"max-width:560px;background:#fff;border:1px solid #e3e9e5;border-radius:16px;padding:32px\"><tr><td style=\"font-size:24px;font-weight:800;color:#15803d\">QuickHire</td></tr><tr><td><h2>{title}</h2></td></tr><tr><td style=\"color:#56635b;line-height:1.65\">{greeting}<br><br>{body}</td></tr><tr><td style=\"padding-top:24px;color:#8a938d;font-size:12px\">Sent securely via QuickHire</td></tr></table></td></tr></table></body></html>"""


def send_invite_email(to_email, candidate_name, job_title, interview_dt, duration_min, custom_message, company_name=None, scheduling_link=None, reply_to=None):
    when = interview_dt.strftime("%B %d, %Y at %I:%M %p") if interview_dt else None
    company = company_name or "the hiring team"
    body = f"You have been selected for an interview with <strong>{company}</strong> for <strong>{job_title or 'the position'}</strong>."
    if scheduling_link:
        body += f"<br><br><a href=\"{scheduling_link}\" style=\"display:inline-block;padding:11px 20px;background:#16a34a;color:white;text-decoration:none;border-radius:8px;font-weight:700\">Choose an interview time</a>"
    elif when:
        body += f"<br><br><strong>Date & time:</strong> {when}<br><strong>Duration:</strong> {duration_min} minutes"
    if custom_message:
        body += "<br><br>" + custom_message.replace("\n", "<br>")
    return send_email(to_email, f"Interview Invitation - {job_title or 'Position'}", _shell("Interview Invitation", f"Hi {candidate_name or 'there'},", body), reply_to)


def send_decision_email(to_email, candidate_name, job_title, decision, company_name=None, reply_to=None):
    if decision == "hire":
        title = "Congratulations!"
        subject = f"Congratulations - {job_title or 'Position'}"
        body = f"We are pleased to let you know that you have been selected for <strong>{job_title or 'the position'}</strong>" + (f" at <strong>{company_name}</strong>" if company_name else "") + ". The hiring team will contact you with the next steps."
    else:
        title = "Application Update"
        subject = f"Application Update - {job_title or 'Position'}"
        body = f"Thank you for your interest in <strong>{job_title or 'the position'}</strong>. After careful consideration, the hiring team has decided to progress with another applicant. We appreciate the time you invested in the process."
    return send_email(to_email, subject, _shell(title, f"Hi {candidate_name or 'there'},", body), reply_to)


def send_custom_email(to_email, candidate_name, subject, body_text, company_name=None, reply_to=None):
    body = body_text.replace("\n", "<br>")
    return send_email(to_email, subject, _shell(subject, f"Hi {candidate_name or 'there'},", body), reply_to)
