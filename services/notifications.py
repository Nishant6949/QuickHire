from user_model import CandidateAccount, Notification, db


def notify_recruiter(user_id, title, message, category="info", link=None, commit=False):
    if not user_id:
        return None
    item = Notification(user_id=user_id, title=title[:180], message=message[:500], category=category[:50], link=link)
    db.session.add(item)
    if commit:
        db.session.commit()
    return item


def notify_candidate(candidate_email, title, message, category="info", link="/candidate/dashboard", commit=False):
    if not candidate_email:
        return None
    account = db.session.execute(
        db.select(CandidateAccount).where(CandidateAccount.email == candidate_email.strip().lower())
    ).scalar_one_or_none()
    if not account:
        return None
    item = Notification(candidate_account_id=account.id, title=title[:180], message=message[:500], category=category[:50], link=link)
    db.session.add(item)
    if commit:
        db.session.commit()
    return item
