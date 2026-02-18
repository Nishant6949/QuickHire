import os
import io
import json
import re
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
import pdfplumber
import anthropic
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from user_model import db, Job, Candidate

dashboard_bp = Blueprint('dashboard_bp', __name__, url_prefix='/dashboard')


def extract_pdf_text(filepath):
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def parse_ai_json(raw_text):
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        text = brace_match.group(0)
    return json.loads(text)


def clamp_score(value):
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return 0


def call_claude(client, prompt, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            if attempt < max_retries:
                wait = 2 ** (attempt + 1)
                print(f"[Claude 429] Retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise


def call_claude_messages(client, system, messages, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system,
                messages=messages
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            if attempt < max_retries:
                wait = 2 ** (attempt + 1)
                print(f"[Claude 429] Retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise


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
        "interview_at": c.interview_at.isoformat() if c.interview_at else None,
        "final_notes": c.final_notes or "",
        "onboarding_generated": c.onboarding_generated
    }


@dashboard_bp.route("/")
@login_required
def dashboard():
    draft_job = db.session.execute(
        db.select(Job)
        .where(Job.user_id == current_user.id)
        .where(Job.status.in_(("draft", "ready", "processing")))
        .order_by(Job.updated_at.desc())
    ).scalars().first()

    return render_template(
        "dashboard/dashboard.html",
        active_page="dashboard",
        draft_job=draft_job
    )


@dashboard_bp.route("/upload-jd", methods=["POST"])
@login_required
def upload_jd():
    jd_text = ""
    jd_filename = None

    if "jd_file" in request.files and request.files["jd_file"].filename:
        file = request.files["jd_file"]
        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"success": False, "error": "Only PDF files are supported"}), 400

        jd_filename = secure_filename(file.filename)
        user_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "jd", str(current_user.id))
        os.makedirs(user_dir, exist_ok=True)
        filepath = os.path.join(user_dir, jd_filename)
        file.save(filepath)

        try:
            jd_text = extract_pdf_text(filepath)
        except Exception as e:
            print(f"[JD PDF Error] {e}")
            os.remove(filepath)
            return jsonify({"success": False, "error": "Could not read PDF. It may be image-based or corrupted."}), 400

        if not jd_text:
            os.remove(filepath)
            return jsonify({"success": False, "error": "No text found in PDF. It may be image-based."}), 400

    elif request.form.get("jd_text", "").strip():
        jd_text = request.form["jd_text"].strip()

    else:
        return jsonify({"success": False, "error": "Please provide a job description"}), 400

    title = extract_job_title(jd_text)
    department = extract_department(jd_text)
    location = extract_location(jd_text)
    job = Job(
        user_id=current_user.id, jd_text=jd_text, jd_filename=jd_filename,
        title=title, department=department, location=location, status="draft"
    )
    db.session.add(job)
    db.session.commit()

    return jsonify({"success": True, "job_id": job.id, "title": title})


@dashboard_bp.route("/analyze-jd/<int:job_id>", methods=["POST"])
@login_required
def analyze_jd(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"success": False, "fallback": True, "error": "AI service not configured"})

    try:
        client = anthropic.Anthropic(api_key=api_key)
        system_msg, user_msgs = build_jd_analysis_prompt(job.jd_text)
        raw = call_claude_messages(client, system_msg, user_msgs)
        result = parse_ai_json(raw)

        job.title = str(result.get("title", ""))[:200] or job.title
        job.department = str(result.get("department", ""))[:100] or job.department
        job.location = str(result.get("location", ""))[:100] or job.location
        job.seniority_level = str(result.get("seniority_level", ""))[:100] or None
        job.employment_type = str(result.get("employment_type", ""))[:100] or None
        job.salary_range_text = str(result.get("salary_range", ""))[:100] or None

        skills = result.get("key_skills", [])
        if isinstance(skills, list):
            job.required_skills = json.dumps(skills)

        job.ai_analyzed = True
        db.session.commit()

        return jsonify({
            "success": True,
            "analysis": {
                "title": job.title or "",
                "department": job.department or "",
                "location": job.location or "",
                "seniority_level": job.seniority_level or "",
                "employment_type": job.employment_type or "",
                "salary_range": job.salary_range_text or "",
                "key_skills": skills if isinstance(skills, list) else []
            }
        })
    except Exception as e:
        print(f"[JD Analysis Error] {e}")
        return jsonify({"success": False, "fallback": True, "error": str(e)[:200]})


def build_jd_analysis_prompt(jd_text):
    system = (
        "You are an expert HR analyst. Extract structured information from job descriptions. "
        "Return ONLY valid JSON with no markdown or explanation."
    )
    messages = [
        {
            "role": "user",
            "content": (
                "Analyze this job description and extract the following. Return ONLY a valid JSON object:\n"
                "{\n"
                '  "title": "<job title>",\n'
                '  "department": "<department like Engineering, Product, Design, Sales, Marketing, HR, Finance, Operations, Data>",\n'
                '  "location": "<location or Remote>",\n'
                '  "seniority_level": "<Junior, Mid-Level, Senior, Lead, Manager, Director, VP, C-Level>",\n'
                '  "employment_type": "<Full-time, Part-time, Contract, Internship>",\n'
                '  "salary_range": "<salary range if mentioned, or empty string>",\n'
                '  "key_skills": ["<skill1>", "<skill2>", "..."]  // 5-10 most important skills\n'
                "}\n\n"
                "=== JOB DESCRIPTION ===\n" + jd_text
            )
        }
    ]
    return system, messages


def extract_job_title(jd_text):
    lines = jd_text.strip().split("\n")
    for line in lines[:5]:
        cleaned = line.strip()
        if 10 < len(cleaned) < 80 and not cleaned.endswith(":"):
            return cleaned
    return "Untitled Position"


def extract_department(jd_text):
    text_lower = jd_text.lower()
    departments = {
        "Engineering": ["engineering", "software", "developer", "backend", "frontend", "fullstack", "devops", "sre", "infrastructure"],
        "Product": ["product manager", "product owner", "product lead", "product management"],
        "Design": ["design", "ux", "ui ", "ui/ux", "graphic design", "visual design"],
        "Sales": ["sales", "account executive", "business development", "bdr", "sdr"],
        "Marketing": ["marketing", "growth", "content", "seo", "brand"],
        "HR": ["human resources", "people operations", "talent", "recruiter", "recruiting"],
        "Finance": ["finance", "accounting", "financial", "controller", "cfo"],
        "Operations": ["operations", "logistics", "supply chain", "procurement"],
        "Data": ["data science", "data engineer", "machine learning", "ml ", "analytics", "data analyst"],
    }
    for dept, keywords in departments.items():
        for kw in keywords:
            if kw in text_lower:
                return dept
    return None


def extract_location(jd_text):
    text_lower = jd_text.lower()
    if "remote" in text_lower:
        return "Remote"
    loc_match = re.search(r"location\s*[:\-–]\s*(.+)", jd_text, re.IGNORECASE)
    if loc_match:
        return loc_match.group(1).strip()[:100]
    return None


@dashboard_bp.route("/upload-resumes/<int:job_id>", methods=["POST"])
@login_required
def upload_resumes(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    files = request.files.getlist("resumes")
    if not files:
        return jsonify({"success": False, "error": "No files provided"}), 400

    results = []
    resume_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "resumes", str(job_id))
    os.makedirs(resume_dir, exist_ok=True)

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            continue

        filename = secure_filename(file.filename)
        filepath = os.path.join(resume_dir, filename)
        file.save(filepath)

        try:
            resume_text = extract_pdf_text(filepath)
        except Exception as e:
            print(f"[Resume PDF Error] {filename}: {e}")
            os.remove(filepath)
            continue

        if not resume_text:
            os.remove(filepath)
            continue

        candidate = Candidate(job_id=job.id, resume_text=resume_text, resume_filename=filename)
        db.session.add(candidate)
        db.session.flush()
        results.append({"id": candidate.id, "filename": filename})

    if not results:
        db.session.commit()
        return jsonify({"success": False, "error": "No valid resumes could be processed"}), 400

    job.status = "ready"
    db.session.commit()

    return jsonify({"success": True, "candidates": results})


@dashboard_bp.route("/remove-resume/<int:candidate_id>", methods=["DELETE"])
@login_required
def remove_resume(candidate_id):
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    filepath = os.path.join(
        current_app.config["UPLOAD_FOLDER"], "resumes",
        str(candidate.job_id), candidate.resume_filename
    )
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(candidate)
    db.session.commit()

    return jsonify({"success": True})


@dashboard_bp.route("/start-screening/<int:job_id>", methods=["POST"])
@login_required
def start_screening(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    if job.status not in ("ready", "completed"):
        return jsonify({"success": False, "error": "Job is not ready for screening"}), 400

    job.status = "processing"
    db.session.commit()

    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        job.status = "ready"
        db.session.commit()
        return jsonify({"success": False, "error": "AI service not configured"}), 500

    client = anthropic.Anthropic(api_key=api_key)

    candidates = db.session.execute(
        db.select(Candidate).where(Candidate.job_id == job.id)
    ).scalars().all()

    if not candidates:
        job.status = "ready"
        db.session.commit()
        return jsonify({"success": False, "error": "No resumes to screen. Please upload resumes first."}), 400

    rate_limited = False
    for candidate in candidates:
        try:
            prompt = build_screening_prompt(job.jd_text, candidate.resume_text)
            raw = call_claude(client, prompt)
            print(f"[AI Response] {candidate.resume_filename}: {raw[:300]}")
            result = parse_ai_json(raw)

            candidate.match_score = clamp_score(result.get("match_score", 0))
            candidate.skills_score = clamp_score(result.get("skills_score", 0))
            candidate.experience_score = clamp_score(result.get("experience_score", 0))
            candidate.education_score = clamp_score(result.get("education_score", 0))
            candidate.match_summary = str(result.get("match_summary", ""))[:500]
            candidate.candidate_name = str(result.get("candidate_name", ""))[:200] or None
            candidate.candidate_email = str(result.get("candidate_email", ""))[:200] or None

            skills = result.get("matched_skills", [])
            if isinstance(skills, list):
                candidate.matched_skills = json.dumps(skills)

            candidate.status = "scored"

        except anthropic.RateLimitError:
            print(f"[AI 429] {candidate.resume_filename}: Rate limited after retries")
            rate_limited = True
            candidate.status = "error"
            candidate.match_score = 0
            candidate.match_summary = "AI service is temporarily busy. Please retry in a few minutes."
            candidate.candidate_name = candidate.candidate_name or ""
        except Exception as e:
            print(f"[AI Error] {candidate.resume_filename}: {e}")
            candidate.status = "error"
            candidate.match_score = 0
            candidate.match_summary = f"Could not analyze this resume: {str(e)[:100]}"
            candidate.candidate_name = candidate.candidate_name or ""

    job.status = "completed"
    db.session.commit()

    sorted_candidates = sorted(candidates, key=lambda c: c.match_score or 0, reverse=True)
    results = [serialize_candidate(c) for c in sorted_candidates]

    return jsonify({"success": True, "results": results, "rate_limited": rate_limited})


def build_screening_prompt(jd_text, resume_text):
    return (
        "You are an expert recruitment AI. Analyze the candidate's resume against the job description below.\n\n"
        "Return ONLY a valid JSON object (no markdown, no explanation) with exactly these fields:\n"
        "{\n"
        '  "candidate_name": "<full name from resume>",\n'
        '  "candidate_email": "<email from resume or empty string>",\n'
        '  "match_score": <integer 0-100, overall fit>,\n'
        '  "skills_score": <integer 0-100, how well skills match>,\n'
        '  "experience_score": <integer 0-100, how well experience matches>,\n'
        '  "education_score": <integer 0-100, how well education matches>,\n'
        '  "matched_skills": [<list of specific skills from resume that match the JD>],\n'
        '  "match_summary": "<2-3 sentence summary explaining the match>"\n'
        "}\n\n"
        "Scoring guide:\n"
        "- 90-100: Excellent match, meets nearly all requirements\n"
        "- 70-89: Good match, meets most key requirements\n"
        "- 50-69: Partial match, meets some requirements\n"
        "- 0-49: Poor match, significant gaps\n\n"
        "=== JOB DESCRIPTION ===\n" + jd_text + "\n\n"
        "=== RESUME ===\n" + resume_text
    )


@dashboard_bp.route("/results/<int:job_id>")
@login_required
def results(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    candidates = db.session.execute(
        db.select(Candidate)
        .where(Candidate.job_id == job.id)
        .order_by(Candidate.match_score.desc())
    ).scalars().all()

    results = [serialize_candidate(c) for c in candidates]

    return jsonify({"success": True, "results": results, "job_title": job.title or ""})



@dashboard_bp.route("/update-job-status/<int:job_id>", methods=["PATCH"])
@login_required
def update_job_status(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    data = request.get_json()
    new_status = data.get("status", "").strip()
    allowed = {"open", "draft", "closed", "completed"}
    if new_status not in allowed:
        return jsonify({"success": False, "error": "Invalid status"}), 400

    job.status = new_status
    db.session.commit()

    return jsonify({"success": True, "status": job.status})


@dashboard_bp.route("/screen-new-candidates/<int:job_id>", methods=["POST"])
@login_required
def screen_new_candidates(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    # Only screen candidates that haven't been analysed yet
    unscored = db.session.execute(
        db.select(Candidate)
        .where(Candidate.job_id == job.id)
        .where(Candidate.status.in_(["pending", None]))
    ).scalars().all()

    if not unscored:
        return jsonify({"success": False, "error": "No new candidates to screen"}), 400

    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"success": False, "error": "AI service not configured"}), 500

    client = anthropic.Anthropic(api_key=api_key)
    rate_limited = False

    for candidate in unscored:
        try:
            prompt = build_screening_prompt(job.jd_text, candidate.resume_text)
            raw = call_claude(client, prompt)
            result = parse_ai_json(raw)

            candidate.match_score = clamp_score(result.get("match_score", 0))
            candidate.skills_score = clamp_score(result.get("skills_score", 0))
            candidate.experience_score = clamp_score(result.get("experience_score", 0))
            candidate.education_score = clamp_score(result.get("education_score", 0))
            candidate.match_summary = str(result.get("match_summary", ""))[:500]
            candidate.candidate_name = str(result.get("candidate_name", ""))[:200] or None
            candidate.candidate_email = str(result.get("candidate_email", ""))[:200] or None

            skills = result.get("matched_skills", [])
            if isinstance(skills, list):
                candidate.matched_skills = json.dumps(skills)

            candidate.status = "scored"

        except anthropic.RateLimitError:
            rate_limited = True
            candidate.status = "error"
            candidate.match_score = 0
            candidate.match_summary = "AI service is temporarily busy. Please retry in a few minutes."
            candidate.candidate_name = candidate.candidate_name or ""
        except Exception as e:
            candidate.status = "error"
            candidate.match_score = 0
            candidate.match_summary = f"Could not analyze this resume: {str(e)[:100]}"
            candidate.candidate_name = candidate.candidate_name or ""

    job.status = "completed"
    db.session.commit()

    # Return ALL candidates for this job, sorted by score
    all_candidates = db.session.execute(
        db.select(Candidate)
        .where(Candidate.job_id == job.id)
        .order_by(Candidate.match_score.desc())
    ).scalars().all()

    return jsonify({
        "success": True,
        "results": [serialize_candidate(c) for c in all_candidates],
        "rate_limited": rate_limited,
        "new_count": len(unscored)
    })


@dashboard_bp.route("/delete-candidate/<int:candidate_id>", methods=["DELETE"])
@login_required
def delete_candidate(candidate_id):
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    # Remove resume file from disk if it exists
    try:
        resume_dir = os.path.join(
            current_app.config["UPLOAD_FOLDER"], "resumes", str(candidate.job_id)
        )
        filepath = os.path.join(resume_dir, candidate.resume_filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"[Delete Candidate] Could not remove file: {e}")

    db.session.delete(candidate)
    db.session.commit()
    return jsonify({"success": True})


@dashboard_bp.route("/delete-job/<int:job_id>", methods=["DELETE"])
@login_required
def delete_job(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    # Remove all resume files for this job
    try:
        resume_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "resumes", str(job_id))
        if os.path.isdir(resume_dir):
            import shutil
            shutil.rmtree(resume_dir)
    except Exception as e:
        print(f"[Delete Job] Could not remove resume dir: {e}")

    db.session.delete(job)
    db.session.commit()
    return jsonify({"success": True})


@dashboard_bp.route("/create-job", methods=["POST"])
@login_required
def create_job():
    title = request.form.get("title", "").strip()
    if not title:
        return jsonify({"success": False, "error": "Job title is required"}), 400

    department = request.form.get("department", "").strip() or None
    location = request.form.get("location", "").strip() or None
    description = request.form.get("description", "").strip() or ""
    skills = request.form.get("skills", "").strip() or None

    salary_min = None
    salary_max = None
    try:
        if request.form.get("salary_min"):
            salary_min = int(request.form["salary_min"])
        if request.form.get("salary_max"):
            salary_max = int(request.form["salary_max"])
    except ValueError:
        pass

    job = Job(
        user_id=current_user.id, title=title, jd_text=description,
        department=department, location=location,
        salary_min=salary_min, salary_max=salary_max,
        required_skills=skills, status="open"
    )
    db.session.add(job)
    db.session.commit()

    return jsonify({
        "success": True,
        "job": {
            "id": job.id, "title": job.title, "department": job.department or "",
            "location": job.location or "", "status": job.status,
            "candidate_count": 0, "created_at": job.created_at.strftime("%Y-%m-%d"),
        }
    })


@dashboard_bp.route("/job-detail/<int:job_id>")
@login_required
def job_detail(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Job not found"}), 404

    candidates = db.session.execute(
        db.select(Candidate)
        .where(Candidate.job_id == job.id)
        .order_by(Candidate.match_score.desc())
    ).scalars().all()

    return jsonify({
        "success": True,
        "job": {
            "id": job.id,
            "title": job.title or "Untitled",
            "department": job.department or "",
            "location": job.location or "",
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "required_skills": job.required_skills or "",
            "jd_text": job.jd_text or "",
            "status": job.status,
            "created_at": job.created_at.strftime("%Y-%m-%d"),
        },
        "candidates": [serialize_candidate(c) for c in candidates]
    })


@dashboard_bp.route("/jobs")
@login_required
def jobs():
    all_jobs = db.session.execute(
        db.select(Job)
        .where(Job.user_id == current_user.id)
        .order_by(Job.created_at.desc())
    ).scalars().all()

    jobs_data = []
    for j in all_jobs:
        candidate_count = db.session.execute(
            db.select(db.func.count(Candidate.id)).where(Candidate.job_id == j.id)
        ).scalar() or 0
        jobs_data.append({
            "id": j.id, "title": j.title or "Untitled",
            "department": j.department or "", "location": j.location or "",
            "candidate_count": candidate_count, "status": j.status,
            "created_at": j.created_at.strftime("%Y-%m-%d"),
        })

    departments = sorted(set(j["department"] for j in jobs_data if j["department"]))
    total = len(jobs_data)
    open_count = sum(1 for j in jobs_data if j["status"] == "open")
    draft_count = sum(1 for j in jobs_data if j["status"] == "draft")
    completed_count = sum(1 for j in jobs_data if j["status"] == "completed")

    return render_template(
        "dashboard/jobs.html", active_page="jobs",
        jobs_data=jobs_data, departments=departments,
        total=total, open_count=open_count,
        draft_count=draft_count, completed_count=completed_count,
    )


@dashboard_bp.route("/candidates")
@login_required
def candidates():
    all_candidates = db.session.execute(
        db.select(Candidate)
        .join(Job)
        .where(Job.user_id == current_user.id)
        .where(Candidate.match_score.isnot(None))
        .order_by(Candidate.match_score.desc())
    ).scalars().all()

    candidates_data = []
    for c in all_candidates:
        candidates_data.append({
            "id": c.id,
            "candidate_name": c.candidate_name or "",
            "candidate_email": c.candidate_email or "",
            "match_score": c.match_score or 0,
            "skills_score": c.skills_score or 0,
            "experience_score": c.experience_score or 0,
            "education_score": c.education_score or 0,
            "matched_skills": json.loads(c.matched_skills) if c.matched_skills else [],
            "match_summary": c.match_summary or "",
            "status": c.status,
            "job_id": c.job_id,
            "job_title": c.job.title if c.job else "Unknown",
        })

    total_count = len(candidates_data)
    invited_count = sum(1 for c in candidates_data if c["status"] in ("invited", "interview_done", "shortlisted"))
    pending_count = sum(1 for c in candidates_data if c["status"] in ("pending", "scored"))
    hired_count = sum(1 for c in candidates_data if c["status"] == "final_hired")

    return render_template(
        "dashboard/candidates.html",
        active_page="candidates",
        candidates_data=candidates_data,
        total_count=total_count,
        invited_count=invited_count,
        pending_count=pending_count,
        hired_count=hired_count,
    )


@dashboard_bp.route("/analytics")
@login_required
def analytics():
    return render_template("dashboard/analytics.html", active_page="analytics")


@dashboard_bp.route("/analytics-data")
@login_required
def analytics_data():
    from datetime import timedelta
    from collections import defaultdict

    range_param = request.args.get("range", "30d")
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(range_param, 30)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # All jobs for this user
    all_jobs = db.session.execute(
        db.select(Job).where(Job.user_id == current_user.id)
    ).scalars().all()
    job_ids = [j.id for j in all_jobs]

    if not job_ids:
        return jsonify({
            "kpis": {"total_candidates": 0, "avg_match_score": 0, "hired_count": 0, "shortlisted_count": 0},
            "candidates_over_time": [],
            "by_department": [],
            "funnel": {"total": 0, "scored": 0, "shortlisted": 0, "invited": 0, "hired": 0},
            "top_skills": [],
            "recent_hires": [],
        })

    # All candidates in range (by candidate created_at)
    all_candidates = db.session.execute(
        db.select(Candidate)
        .where(Candidate.job_id.in_(job_ids))
        .where(Candidate.created_at >= cutoff)
    ).scalars().all()

    # All candidates ever (for funnel totals)
    all_candidates_ever = db.session.execute(
        db.select(Candidate).where(Candidate.job_id.in_(job_ids))
    ).scalars().all()

    # KPIs
    total = len(all_candidates)
    scores = [c.match_score for c in all_candidates if c.match_score is not None]
    avg_score = round(sum(scores) / len(scores)) if scores else 0
    hired_count = sum(1 for c in all_candidates if c.status == "final_hired")
    shortlisted_count = sum(1 for c in all_candidates if c.status in ("shortlisted", "invited", "interview_done", "final_hired"))

    # Candidates over time – group by day bucket
    if days <= 7:
        fmt = "%a"  # Mon, Tue…
        bucket_fn = lambda dt: dt.strftime("%a")
    elif days <= 30:
        fmt = "%b %d"
        bucket_fn = lambda dt: dt.strftime("%b %d")
    else:
        fmt = "%b"
        bucket_fn = lambda dt: dt.strftime("%b")

    time_buckets = defaultdict(int)
    for c in all_candidates:
        created = c.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        time_buckets[bucket_fn(created)] += 1

    # Build ordered list of buckets within range
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

    # By department
    dept_counts = defaultdict(int)
    job_dept_map = {j.id: (j.department or "Other") for j in all_jobs}
    for c in all_candidates:
        dept_counts[job_dept_map.get(c.job_id, "Other")] += 1
    by_department = sorted(
        [{"dept": k, "count": v} for k, v in dept_counts.items()],
        key=lambda x: -x["count"]
    )

    # Hiring funnel (all time for this user)
    funnel_total = len(all_candidates_ever)
    funnel_scored = sum(1 for c in all_candidates_ever if c.match_score is not None)
    funnel_shortlisted = sum(1 for c in all_candidates_ever if c.status in ("shortlisted", "invited", "interview_done", "final_hired"))
    funnel_invited = sum(1 for c in all_candidates_ever if c.status in ("invited", "interview_done", "final_hired"))
    funnel_hired = sum(1 for c in all_candidates_ever if c.status == "final_hired")

    # Top skills
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

    # Recent hires
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

    return jsonify({
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
    })


@dashboard_bp.route("/settings")
@login_required
def settings():
    return render_template("dashboard/settings.html", active_page="settings")


@dashboard_bp.route("/candidate-pdf/<int:candidate_id>")
@login_required
def candidate_pdf(candidate_id):
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(34, 197, 94)
    pdf.cell(0, 12, "QuickHire", new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(34, 197, 94)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    pdf.set_text_color(40, 40, 40)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Candidate Report", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    job = candidate.job

    def add_field(label, value):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(45, 7, label + ":")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(0, 7, str(value or "N/A"), new_x="LMARGIN", new_y="NEXT")

    add_field("Name", candidate.candidate_name)
    add_field("Email", candidate.candidate_email)
    add_field("Resume File", candidate.resume_filename)
    add_field("Job Title", job.title)
    add_field("Department", job.department)
    add_field("Location", job.location)
    add_field("Status", candidate.status.title())
    if candidate.interview_at:
        add_field("Interview", candidate.interview_at.strftime("%b %d, %Y at %I:%M %p"))

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(34, 197, 94)
    pdf.cell(0, 10, "Match Scores", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    scores = [
        ("Overall Match", candidate.match_score),
        ("Skills", candidate.skills_score),
        ("Experience", candidate.experience_score),
        ("Education", candidate.education_score),
    ]
    for label, score in scores:
        score_val = score or 0
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(45, 7, label + ":")
        pdf.set_font("Helvetica", "B", 10)
        if score_val >= 90:
            pdf.set_text_color(34, 197, 94)
        elif score_val >= 70:
            pdf.set_text_color(234, 179, 8)
        else:
            pdf.set_text_color(239, 68, 68)
        pdf.cell(0, 7, str(score_val) + "/100", new_x="LMARGIN", new_y="NEXT")

    if candidate.matched_skills:
        try:
            skills = json.loads(candidate.matched_skills)
            if skills:
                pdf.ln(4)
                pdf.set_font("Helvetica", "B", 13)
                pdf.set_text_color(34, 197, 94)
                pdf.cell(0, 10, "Matched Skills", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(40, 40, 40)
                pdf.multi_cell(0, 6, ", ".join(skills))
        except (json.JSONDecodeError, TypeError):
            pass

    if candidate.match_summary:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(34, 197, 94)
        pdf.cell(0, 10, "AI Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 6, candidate.match_summary)

    pdf_bytes = pdf.output()
    buffer = io.BytesIO(pdf_bytes)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", candidate.candidate_name or "candidate")
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=f"{safe_name}_report.pdf")


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
        print(f"[Email Error] {to_email}: {e}")
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
        print(f"[Email] Decision email ({decision}) sent to {to_email}")
        return True
    except Exception as e:
        print(f"[Email Error] {to_email}: {e}")
        return False


@dashboard_bp.route("/send-invites", methods=["POST"])
@login_required
def send_invites():
    data = request.get_json()
    candidate_ids = data.get("candidate_ids", [])
    scheduling_link = data.get("scheduling_link", "").strip() or None
    custom_message = data.get("message", "").strip()

    if not candidate_ids or not scheduling_link:
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    candidates = db.session.execute(
        db.select(Candidate).where(Candidate.id.in_(candidate_ids))
    ).scalars().all()

    owned = [c for c in candidates if c.job.user_id == current_user.id]
    if not owned:
        return jsonify({"success": False, "error": "No valid candidates found"}), 404

    job = owned[0].job

    email_results = []
    for c in owned:
        c.status = "invited"
        c.interview_at = None

        email_sent = False
        if c.candidate_email:
            email_sent = send_invite_email(
                c.candidate_email, c.candidate_name, job.title,
                None, None, custom_message,
                company_name=current_user.company_name,
                scheduling_link=scheduling_link
            )
        email_results.append({
            "id": c.id,
            "email_sent": email_sent,
            "name": c.candidate_name or c.resume_filename
        })

    db.session.commit()

    return jsonify({
        "success": True,
        "results": email_results
    })


@dashboard_bp.route("/resume-pdf/<int:candidate_id>")
@login_required
def resume_pdf(candidate_id):
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    filepath = os.path.join(
        current_app.config["UPLOAD_FOLDER"], "resumes",
        str(candidate.job_id), candidate.resume_filename
    )
    if not os.path.exists(filepath):
        return jsonify({"success": False, "error": "Resume file not found"}), 404

    return send_file(filepath, mimetype="application/pdf")


@dashboard_bp.route("/final-decision", methods=["POST"])
@login_required
def final_decision():
    data = request.get_json()
    candidate_id = data.get("candidate_id")
    decision = data.get("decision")
    notes = data.get("notes", "").strip()

    if not candidate_id or decision not in ("hire", "reject"):
        return jsonify({"success": False, "error": "Invalid request"}), 400

    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    if candidate.status not in ("invited", "interview_done"):
        return jsonify({"success": False, "error": "Candidate not eligible for decision"}), 400

    candidate.status = "final_hired" if decision == "hire" else "final_rejected"
    if notes:
        candidate.final_notes = notes

    db.session.commit()

    email_sent = False
    if candidate.candidate_email:
        company_name = None
        if current_user.company_name:
            company_name = current_user.company_name
        job_title = candidate.job.title if candidate.job else None
        email_sent = send_decision_email(
            candidate.candidate_email,
            candidate.candidate_name,
            job_title,
            decision,
            company_name=company_name
        )

    return jsonify({"success": True, "email_sent": email_sent})


def send_custom_email_impl(to_email, candidate_name, subject, body_text, company_name=None):
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
        print(f"[Email] Custom email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[Email Error] {to_email}: {e}")
        return False


@dashboard_bp.route("/send-custom-email", methods=["POST"])
@login_required
def send_custom_email_route():
    data = request.get_json()
    candidate_id = data.get("candidate_id")
    subject = data.get("subject", "").strip()
    body = data.get("body", "").strip()

    if not candidate_id or not subject or not body:
        return jsonify({"success": False, "error": "Missing fields"}), 400

    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    if not candidate.candidate_email:
        return jsonify({"success": False, "error": "No email on file"}), 400

    company_name = current_user.company_name if current_user.company_name else None
    email_sent = send_custom_email_impl(
        candidate.candidate_email, candidate.candidate_name,
        subject, body, company_name=company_name
    )

    return jsonify({"success": True, "email_sent": email_sent})


@dashboard_bp.route("/generate-onboarding/<int:candidate_id>")
@login_required
def generate_onboarding(candidate_id):
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate or candidate.job.user_id != current_user.id:
        return jsonify({"success": False, "error": "Candidate not found"}), 404

    if candidate.status != "final_hired":
        return jsonify({"success": False, "error": "Candidate must be hired first"}), 400

    job = candidate.job
    api_key = current_app.config.get("ANTHROPIC_API_KEY")

    extracted = {}
    if api_key and candidate.resume_text:
        try:
            client = anthropic.Anthropic(api_key=api_key)
            prompt = (
                "Extract structured data from this resume. Return ONLY valid JSON:\n"
                "{\n"
                '  "full_name": "<name>",\n'
                '  "email": "<email or empty>",\n'
                '  "phone": "<phone or empty>",\n'
                '  "address": "<address or empty>",\n'
                '  "education": [{"degree": "<degree>", "institution": "<school>", "dates": "<dates>"}],\n'
                '  "experience": [{"title": "<role>", "company": "<company>", "duration": "<dates>"}],\n'
                '  "skills": ["<skill1>", "<skill2>"],\n'
                '  "certifications": ["<cert1>"],\n'
                '  "emergency_contact": "<if available or empty>"\n'
                "}\n\n=== RESUME ===\n" + candidate.resume_text
            )
            raw = call_claude(client, prompt)
            extracted = parse_ai_json(raw)
        except Exception as e:
            print(f"[Onboarding AI Error] {e}")

    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(34, 197, 94)
    pdf.cell(0, 12, current_user.company_name or "QuickHire", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "Employee Onboarding Document", new_x="LMARGIN", new_y="NEXT")

    pdf.set_draw_color(34, 197, 94)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
    pdf.ln(10)

    def section_title(title):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(34, 197, 94)
        pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    def field(label, value):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(50, 7, label + ":")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(0, 7, str(value or "N/A"), new_x="LMARGIN", new_y="NEXT")

    section_title("Personal Information")
    field("Name", extracted.get("full_name") or candidate.candidate_name)
    field("Email", extracted.get("email") or candidate.candidate_email)
    field("Phone", extracted.get("phone"))
    field("Address", extracted.get("address"))
    if extracted.get("emergency_contact"):
        field("Emergency Contact", extracted["emergency_contact"])
    pdf.ln(4)

    section_title("Position Details")
    field("Job Title", job.title)
    field("Department", job.department)
    field("Location", job.location)
    pdf.ln(4)

    skills = extracted.get("skills", [])
    if skills:
        section_title("Skills & Qualifications")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 6, ", ".join(skills))
        pdf.ln(4)

    matched_skills = []
    if candidate.matched_skills:
        try:
            matched_skills = json.loads(candidate.matched_skills)
        except (json.JSONDecodeError, TypeError):
            pass
    if matched_skills:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, "Matched to JD: " + ", ".join(matched_skills), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    education = extracted.get("education", [])
    if education:
        section_title("Education")
        for ed in education:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(40, 40, 40)
            pdf.cell(0, 7, str(ed.get("degree", "")), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, str(ed.get("institution", "")) + "  |  " + str(ed.get("dates", "")), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        pdf.ln(2)

    experience = extracted.get("experience", [])
    if experience:
        section_title("Work Experience")
        for exp in experience:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(40, 40, 40)
            pdf.cell(0, 7, str(exp.get("title", "")), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, str(exp.get("company", "")) + "  |  " + str(exp.get("duration", "")), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        pdf.ln(2)

    certs = extracted.get("certifications", [])
    if certs and any(certs):
        section_title("Certifications")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        for cert in certs:
            if cert:
                pdf.cell(0, 6, "- " + str(cert), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    if candidate.final_notes:
        section_title("Interviewer Notes")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 6, candidate.final_notes)

    candidate.onboarding_generated = True
    db.session.commit()

    pdf_bytes = pdf.output()
    buffer = io.BytesIO(pdf_bytes)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", candidate.candidate_name or "candidate")
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=f"{safe_name}_onboarding.pdf")
