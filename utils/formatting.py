import csv
import io
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import pdfplumber

from user_model import db, Job, Candidate


def extract_pdf_text(source):
    """Extract text from a PDF file path or in-memory bytes."""
    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(source)
    text = ""
    with pdfplumber.open(source) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def format_jd_text(text):
    if not text:
        return ""
    lines = text.split("\n")
    html = ""
    list_open = False

    def _close_list():
        nonlocal html, list_open
        if list_open:
            html += "</ul>"
            list_open = False

    def _esc(s):
        return (s.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace('"', "&quot;"))

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            _close_list()
            continue

        is_heading = (
            bool(re.match(r"^#+\s", trimmed)) or
            (trimmed.endswith(":") and len(trimmed) < 80 and not re.match(r"^[-•*]", trimmed)) or
            (trimmed == trimmed.upper() and 3 < len(trimmed) < 80 and re.search(r"[A-Z]", trimmed))
        )
        is_bullet = bool(re.match(r"^[-•*]\s", trimmed) or re.match(r"^\d+[.)\s]", trimmed))

        if is_heading:
            _close_list()
            heading_text = re.sub(r"^#+\s*", "", trimmed).rstrip(":")
            html += '<div class="jd-section-heading">' + _esc(heading_text) + "</div>"
        elif is_bullet:
            if not list_open:
                html += '<ul class="jd-list">'
                list_open = True
            bullet_text = re.sub(r"^[-•*]\s*", "", trimmed)
            bullet_text = re.sub(r"^\d+[.)\s]+", "", bullet_text)
            html += "<li>" + _esc(bullet_text) + "</li>"
        else:
            _close_list()
            html += '<p class="jd-paragraph">' + _esc(trimmed) + "</p>"

    _close_list()
    return html


def format_salary(salary_min, salary_max):
    if salary_min and salary_max:
        return "${:,} – ${:,}".format(salary_min, salary_max)
    if salary_min:
        return "From ${:,}".format(salary_min)
    if salary_max:
        return "Up to ${:,}".format(salary_max)
    return ""


def render_status_badge(status):
    badge_map = {
        "open": "badge-open",
        "draft": "badge-draft",
        "completed": "badge-completed",
        "closed": "badge-closed",
        "ready": "badge-open",
        "processing": "badge-draft",
    }
    cls = badge_map.get(status, "badge-draft")
    label = status.capitalize() if status else "Unknown"
    return '<span class="badge ' + cls + '">' + label + "</span>"


def render_candidate_status_badge(status):
    badge_map = {
        "scored": ("badge-ready", "Scored"),
        "pending": ("badge-draft", "Pending"),
        "invited": ("badge-invited", "Invited"),
        "interview_done": ("badge-interview-done", "Interview Done"),
        "shortlisted": ("badge-shortlisted", "Shortlisted"),
        "final_hired": ("badge-final-hired", "Hired"),
        "final_rejected": ("badge-final-rejected", "Rejected"),
        "error": ("badge-draft", "Error"),
    }
    cls, label = badge_map.get(status, ("badge-draft", status.capitalize() if status else "Unknown"))
    return '<span class="job-card-badge ' + cls + '">' + label + '</span>'


def serialize_candidate(c):
    matched_skills = []
    if c.matched_skills:
        try:
            matched_skills = json.loads(c.matched_skills)
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "id": c.id,
        "filename": c.resume_filename,
        "candidate_name": c.candidate_name or "",
        "candidate_email": c.candidate_email or "",
        "match_score": c.match_score or 0,
        "skills_score": c.skills_score or 0,
        "experience_score": c.experience_score or 0,
        "education_score": c.education_score or 0,
        "matched_skills": matched_skills,
        "match_summary": c.match_summary or "",
        "status": c.status,
        "status_html": render_candidate_status_badge(c.status),
        "interview_at": c.interview_at.isoformat() if c.interview_at else None,
        "final_notes": c.final_notes or "",
        "onboarding_generated": c.onboarding_generated
    }


def job_stats_for_user(user_id):
    all_jobs = db.session.execute(
        db.select(Job).where(Job.user_id == user_id)
    ).scalars().all()
    return {
        "total": len(all_jobs),
        "open": sum(1 for j in all_jobs if j.status == "open"),
        "draft": sum(1 for j in all_jobs if j.status == "draft"),
        "completed": sum(1 for j in all_jobs if j.status == "completed"),
    }


def build_jobs_list(user_id, q=None, dept=None, status=None, days=None):
    query = db.select(Job).where(Job.user_id == user_id).order_by(Job.created_at.desc())
    if dept and dept != "all":
        query = query.where(Job.department == dept)
    if status and status != "all":
        query = query.where(Job.status == status)
    if days and days != "all":
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))
            query = query.where(Job.created_at >= cutoff)
        except (ValueError, TypeError):
            pass

    all_jobs = db.session.execute(query).scalars().all()

    if q:
        q_lower = q.lower()
        all_jobs = [j for j in all_jobs if q_lower in (j.title or "").lower()]

    jobs_data = []
    for j in all_jobs:
        candidate_count = db.session.execute(
            db.select(db.func.count(Candidate.id)).where(Candidate.job_id == j.id)
        ).scalar() or 0
        jobs_data.append({
            "id": j.id, "title": j.title or "Untitled",
            "department": j.department or "", "location": j.location or "",
            "candidate_count": candidate_count, "status": j.status,
            "status_html": render_status_badge(j.status),
            "created_at": j.created_at.strftime("%Y-%m-%d"),
        })
    return jobs_data


def compute_analytics_data(user_id, range_param):
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(range_param, 30)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    all_jobs = db.session.execute(
        db.select(Job).where(Job.user_id == user_id)
    ).scalars().all()
    job_ids = [j.id for j in all_jobs]

    empty = {
        "kpis": {"total_candidates": 0, "avg_match_score": 0, "hired_count": 0, "shortlisted_count": 0},
        "candidates_over_time": [],
        "by_department": [],
        "funnel": {"total": 0, "scored": 0, "shortlisted": 0, "invited": 0, "hired": 0},
        "top_skills": [],
        "recent_hires": [],
    }
    if not job_ids:
        return empty

    all_candidates = db.session.execute(
        db.select(Candidate)
        .where(Candidate.job_id.in_(job_ids))
        .where(Candidate.created_at >= cutoff)
    ).scalars().all()

    all_candidates_ever = db.session.execute(
        db.select(Candidate).where(Candidate.job_id.in_(job_ids))
    ).scalars().all()

    total = len(all_candidates)
    scores = [c.match_score for c in all_candidates if c.match_score is not None]
    avg_score = round(sum(scores) / len(scores)) if scores else 0
    hired_count = sum(1 for c in all_candidates if c.status == "final_hired")
    shortlisted_count = sum(1 for c in all_candidates if c.status in ("shortlisted", "invited", "interview_done", "final_hired"))

    if days <= 7:
        bucket_fn = lambda dt: dt.strftime("%a")
    elif days <= 30:
        bucket_fn = lambda dt: dt.strftime("%b %d")
    else:
        bucket_fn = lambda dt: dt.strftime("%b")

    time_buckets = defaultdict(int)
    for c in all_candidates:
        created = c.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        time_buckets[bucket_fn(created)] += 1

    ordered_buckets = []
    seen = set()
    step = timedelta(days=1) if days <= 30 else timedelta(days=7)
    cursor = cutoff
    while cursor <= datetime.now(timezone.utc):
        label = bucket_fn(cursor)
        if label not in seen:
            seen.add(label)
            ordered_buckets.append({"label": label, "count": time_buckets.get(label, 0)})
        cursor += step

    dept_counts = defaultdict(int)
    job_dept_map = {j.id: (j.department or "Other") for j in all_jobs}
    for c in all_candidates:
        dept_counts[job_dept_map.get(c.job_id, "Other")] += 1
    by_department = sorted(
        [{"dept": k, "count": v} for k, v in dept_counts.items()],
        key=lambda x: -x["count"]
    )

    funnel_total = len(all_candidates_ever)
    funnel_scored = sum(1 for c in all_candidates_ever if c.match_score is not None)
    funnel_shortlisted = sum(1 for c in all_candidates_ever if c.status in ("shortlisted", "invited", "interview_done", "final_hired"))
    funnel_invited = sum(1 for c in all_candidates_ever if c.status in ("invited", "interview_done", "final_hired"))
    funnel_hired = sum(1 for c in all_candidates_ever if c.status == "final_hired")

    skill_counts = defaultdict(int)
    for c in all_candidates:
        if c.matched_skills:
            try:
                skills = json.loads(c.matched_skills)
                for s in skills:
                    skill_counts[s.strip()] += 1
            except (json.JSONDecodeError, TypeError):
                pass
    top_skills = sorted(
        [{"skill": k, "count": v} for k, v in skill_counts.items()],
        key=lambda x: -x["count"]
    )[:10]

    hired_candidates = [c for c in all_candidates_ever if c.status == "final_hired"]
    hired_candidates.sort(key=lambda c: c.created_at, reverse=True)
    recent_hires = []
    for c in hired_candidates[:10]:
        job = next((j for j in all_jobs if j.id == c.job_id), None)
        recent_hires.append({
            "name": c.candidate_name or c.resume_filename,
            "job_title": job.title if job else "Unknown",
            "dept": job.department if job else "",
            "match_score": c.match_score or 0,
            "hired_on": c.created_at.strftime("%b %d, %Y"),
        })

    return {
        "kpis": {
            "total_candidates": total,
            "avg_match_score": avg_score,
            "hired_count": hired_count,
            "shortlisted_count": shortlisted_count,
        },
        "candidates_over_time": ordered_buckets,
        "by_department": by_department,
        "funnel": {
            "total": funnel_total,
            "scored": funnel_scored,
            "shortlisted": funnel_shortlisted,
            "invited": funnel_invited,
            "hired": funnel_hired,
        },
        "top_skills": top_skills,
        "recent_hires": recent_hires,
    }


def build_analytics_csv(user_id, range_param):
    data = compute_analytics_data(user_id, range_param)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Section", "Label", "Value"])

    writer.writerow(["KPI", "Total Candidates", data["kpis"]["total_candidates"]])
    writer.writerow(["KPI", "Avg Match Score", str(data["kpis"]["avg_match_score"]) + "%"])
    writer.writerow(["KPI", "Shortlisted", data["kpis"]["shortlisted_count"]])
    writer.writerow(["KPI", "Hired", data["kpis"]["hired_count"]])

    for d in data["candidates_over_time"]:
        writer.writerow(["Over Time", d["label"], d["count"]])

    for d in data["by_department"]:
        writer.writerow(["By Department", d["dept"], d["count"]])

    writer.writerow(["Funnel", "Applied", data["funnel"]["total"]])
    writer.writerow(["Funnel", "AI Scored", data["funnel"]["scored"]])
    writer.writerow(["Funnel", "Shortlisted", data["funnel"]["shortlisted"]])
    writer.writerow(["Funnel", "Invited", data["funnel"]["invited"]])
    writer.writerow(["Funnel", "Hired", data["funnel"]["hired"]])

    for s in data["top_skills"]:
        writer.writerow(["Top Skills", s["skill"], s["count"]])

    return output.getvalue()
